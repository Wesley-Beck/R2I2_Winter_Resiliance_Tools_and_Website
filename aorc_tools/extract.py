"""
Hourly data extraction pipeline.

Orchestrates: AORC data fetch → unit conversion → fire index calculation
→ intermediate CSV output. Every step produces a separate CSV file that
becomes a selectable layer on the website map.

Refactored from existing ExtractionTab._run() in program1_data_extraction.py
to be a library function with no GUI dependency.
"""

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

from aorc_tools.aorc_access import AORCDataLoader
from aorc_tools.climate_convert import (
    kelvin_to_celsius,
    celsius_to_fahrenheit,
    kelvin_to_fahrenheit,
    wind_components_to_speed,
    ms_to_kph,
    ms_to_mph,
    specific_to_relative_humidity,
)
from aorc_tools.fire_indices.fwi import HourlyFWI
from aorc_tools.fire_indices.nfdrs import compute_erc_bi
from aorc_tools.fire_indices.fuel_moisture import emc_fuel_moisture, NelsonFuelMoisture
from aorc_tools.metadata import generate_metadata, save_metadata

logger = logging.getLogger(__name__)


class CSVAccumulator:
    """Accumulates hourly point data and writes monthly CSV files.

    Each CSV: rows = point_id, columns = datetime stamps.
    """

    def __init__(self, n_points, point_ids):
        self.n_points = n_points
        self.point_ids = point_ids
        self.data = {}  # variable_name → list of (timestamp, values_array)

    def add(self, name, timestamp, values):
        """Add one hour of data for a variable."""
        if name not in self.data:
            self.data[name] = []
        self.data[name].append((timestamp, np.asarray(values)))

    def save(self, output_dir, prefix=""):
        """Write all accumulated variables to CSV files.

        Args:
            output_dir: Directory path.
            prefix: Optional prefix for filenames.
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        for name, records in self.data.items():
            if not records:
                continue

            timestamps = [r[0] for r in records]
            columns = [t.strftime("%Y-%m-%d %H:%M") for t in timestamps]
            data_matrix = np.column_stack([r[1] for r in records])

            df = pd.DataFrame(
                data_matrix,
                index=self.point_ids,
                columns=columns,
            )
            df.index.name = "point_id"

            filename = f"{prefix}{name}.csv"
            df.to_csv(output_dir / filename, float_format="%.4g")

        logger.info("Saved %d CSV files to %s", len(self.data), output_dir)

    def clear(self):
        """Clear accumulated data (e.g., after saving a month)."""
        self.data.clear()


def extract_month(year, month, points_df, output_base, loader=None,
                  fuel_model="G", fuel_moisture_method="emc",
                  fwi_state=None, fm_state=None, latitude=46.5,
                  callback=None):
    """Extract one month of hourly AORC data and compute all indices.

    Every intermediate step is saved as a separate CSV file.
    Uses day-batch loading with spatial subsetting for performance:
    loads only the WUP bounding box (~100K pixels) instead of full
    CONUS (~35M pixels), and loads 24 hours at a time.

    Args:
        year: Year (int).
        month: Month (int, 1-12).
        points_df: DataFrame with point_id, latitude, longitude, lat_idx, lon_idx.
        output_base: Base output directory path.
        loader: AORCDataLoader instance (created if None).
        fuel_model: NFDRS fuel model code (default "G").
        fuel_moisture_method: "emc" or "nelson" (default "emc").
        fwi_state: Optional dict to restore FWI state (carry-forward).
        fm_state: Optional dict to restore fuel moisture state.
        latitude: Representative latitude for FWI sunrise/sunset.
        callback: Optional function(progress_pct, message) for status updates.

    Returns:
        dict with "fwi_state" and "fm_state" for carry-forward to next month.
    """
    if loader is None:
        loader = AORCDataLoader()

    n_points = len(points_df)
    point_ids = points_df["point_id"].values
    lat_indices = points_df["lat_idx"].values
    lon_indices = points_df["lon_idx"].values

    # Compute spatial bounding box from point locations (with small buffer)
    lat_bounds = (
        points_df["latitude"].min() - 0.05,
        points_df["latitude"].max() + 0.05,
    )
    lon_bounds = (
        points_df["longitude"].min() - 0.05,
        points_df["longitude"].max() + 0.05,
    )

    # Output directory structure
    month_dir = Path(output_base) / str(year) / f"{month:02d}"

    # Accumulators for each output category
    raw_acc = CSVAccumulator(n_points, point_ids)
    conv_acc = CSVAccumulator(n_points, point_ids)
    cfwi_acc = CSVAccumulator(n_points, point_ids)
    nfdrs_acc = CSVAccumulator(n_points, point_ids)

    # Initialize FWI state
    fwi = HourlyFWI(n_points, latitude=latitude, initial_state=fwi_state)

    # Initialize fuel moisture state
    if fuel_moisture_method == "nelson":
        fm_model = NelsonFuelMoisture(n_points, initial_fm=fm_state)
    else:
        fm_model = None

    # Determine date range for this month
    import calendar
    n_days = calendar.monthrange(year, month)[1]

    total_hours = n_days * 24
    hours_processed = 0

    # Day-batch loop: load 24 hours at a time with spatial subsetting
    for day in range(1, n_days + 1):
        if callback:
            pct = 100.0 * hours_processed / total_hours
            callback(pct, f"Loading {year}-{month:02d}-{day:02d}...")

        # Load entire day's data for the WUP bbox
        try:
            daily_data = loader.get_daily_point_values(
                year, month, day, lat_indices, lon_indices,
                lat_bounds, lon_bounds,
            )
        except Exception as e:
            logger.error("Failed to fetch AORC day %s-%02d-%02d: %s",
                         year, month, day, e)
            hours_processed += 24
            continue

        actual_hours = daily_data["hours"]
        actual_timestamps = daily_data["timestamps"]

        # Process each hour from the batch-loaded data
        for h_idx, (hour_val, ts) in enumerate(zip(actual_hours, actual_timestamps)):
            current = datetime(year, month, day, hour_val)
            doy = current.timetuple().tm_yday

            # Extract this hour's values from the batch (h_idx-th row)
            raw = {}
            for var in loader.VARIABLES:
                if var in daily_data:
                    raw[var] = daily_data[var][h_idx]

            # Record raw AORC values
            for var, values in raw.items():
                raw_acc.add(var, current, values)

            # ---------------------------------------------------------
            # Unit conversions
            # ---------------------------------------------------------
            temp_k = raw.get("TMP_2maboveground", np.full(n_points, np.nan))
            spfh = raw.get("SPFH_2maboveground", np.full(n_points, np.nan))
            pres_pa = raw.get("PRES_surface", np.full(n_points, np.nan))
            ugrd = raw.get("UGRD_10maboveground", np.full(n_points, np.nan))
            vgrd = raw.get("VGRD_10maboveground", np.full(n_points, np.nan))
            precip_mm = raw.get("APCP_surface", np.full(n_points, np.nan))

            temp_c = kelvin_to_celsius(temp_k)
            temp_f = celsius_to_fahrenheit(temp_c)
            rh = specific_to_relative_humidity(spfh, temp_k, pres_pa)
            ws_ms = wind_components_to_speed(ugrd, vgrd)
            ws_kph = ms_to_kph(ws_ms)
            ws_mph = ms_to_mph(ws_ms)

            conv_acc.add("temperature_c", current, temp_c)
            conv_acc.add("temperature_f", current, temp_f)
            conv_acc.add("relative_humidity", current, rh)
            conv_acc.add("wind_speed_ms", current, ws_ms)
            conv_acc.add("wind_speed_kph", current, ws_kph)
            conv_acc.add("wind_speed_mph", current, ws_mph)
            conv_acc.add("precipitation_mm", current, precip_mm)

            # ---------------------------------------------------------
            # Canadian FWI System (hourly)
            # ---------------------------------------------------------
            fwi_result = fwi.update(temp_c, rh, ws_kph, precip_mm, doy, current.hour)
            for key, values in fwi_result.items():
                cfwi_acc.add(key, current, values)

            # ---------------------------------------------------------
            # NFDRS: Fuel Moisture → ERC/SC/BI
            # ---------------------------------------------------------
            if fuel_moisture_method == "nelson" and fm_model is not None:
                fm = fm_model.update(temp_f, rh, precip_mm)
            else:
                fm = emc_fuel_moisture(temp_f, rh)

            for key in ["fm1", "fm10", "fm100", "fm1000"]:
                nfdrs_acc.add(key.upper(), current, fm[key])

            mcherb = np.full(n_points, 120.0)
            mcwood = np.full(n_points, 100.0)

            nfdrs_result = compute_erc_bi(
                fm["fm1"], fm["fm10"], fm["fm100"], fm["fm1000"],
                mcherb, mcwood, ws_mph,
                fuel_model=fuel_model,
            )

            for key, values in nfdrs_result.items():
                nfdrs_acc.add(key, current, values)

            hours_processed += 1

    # -----------------------------------------------------------------
    # Save all CSVs
    # -----------------------------------------------------------------
    prefix = f"{year}_{month:02d}_"
    raw_acc.save(month_dir / "raw_aorc", prefix)
    conv_acc.save(month_dir / "converted", prefix)
    cfwi_acc.save(month_dir / "cfwi", prefix)
    nfdrs_acc.save(month_dir / "nfdrs", prefix)

    # Save state for carry-forward
    state_dir = month_dir / "state"
    state_dir.mkdir(parents=True, exist_ok=True)

    fwi_state_out = fwi.get_state()
    with open(state_dir / f"fwi_state_{year}_{month:02d}.json", "w") as f:
        json.dump(fwi_state_out, f)

    fm_state_out = fm_model.get_state() if fm_model else None
    if fm_state_out:
        with open(state_dir / f"nfdrs_state_{year}_{month:02d}.json", "w") as f:
            json.dump({k: v.tolist() if hasattr(v, "tolist") else v
                       for k, v in fm_state_out.items()}, f)

    # Save metadata
    metadata = generate_metadata(
        year, month, fuel_model,
        calculation_params={
            "fuel_moisture_method": fuel_moisture_method,
            "latitude": latitude,
            "n_points": n_points,
        },
    )
    save_metadata(metadata, month_dir / f"metadata_{year}_{month:02d}.json")

    if callback:
        callback(100.0, f"Completed {year}-{month:02d}")

    return {
        "fwi_state": fwi_state_out,
        "fm_state": fm_state_out,
    }


def extract_year(year, points_df, output_base, start_month=1, end_month=12,
                 **kwargs):
    """Extract a full year of data, month by month with state carry-forward.

    Args:
        year: Year to extract.
        points_df: Point index DataFrame.
        output_base: Base output directory.
        start_month: First month to extract (default 1).
        end_month: Last month to extract (default 12).
        **kwargs: Passed to extract_month (fuel_model, latitude, etc.)

    Returns:
        Final carry-forward state dict.
    """
    state = {"fwi_state": kwargs.pop("fwi_state", None),
             "fm_state": kwargs.pop("fm_state", None)}

    for month in range(start_month, end_month + 1):
        logger.info("Extracting %d-%02d", year, month)
        state = extract_month(
            year, month, points_df, output_base,
            fwi_state=state["fwi_state"],
            fm_state=state["fm_state"],
            **kwargs,
        )

    return state
