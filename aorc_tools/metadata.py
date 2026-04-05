"""
Data provenance tracking for the AORC Wildfire Risk Analysis System.

Programmatically determines which source data contributed to every
AORC variable at a given time, plus provenance for NDVI, fuel models,
and calculation parameters.

The website metadata viewer reads these provenance records to show
researchers exactly what data sources underlie each map layer.

References:
    - Fall et al. 2023, JAWRA: AORC v1.1 sources and methods
    - AORC v1.1 Methods Document (NOAA/NWS/OWP)
"""

import json
from datetime import date, datetime
from pathlib import Path

from aorc_tools.config import NFDRS_FUEL_MODELS


class AORCProvenance:
    """Determine which source data contributed to a given AORC variable/date.

    AORC v1.1 is assembled from multiple source datasets that change
    across time periods. This class encodes the era boundaries and
    source descriptions from Fall et al. 2023 and the AORC methods doc.
    """

    # Precipitation source eras
    PRECIP_ERAS = [
        {
            "start": 1979, "end": 1994,
            "source": "NEXRAD Stage II + WSI NOWrad reflectivity + CPC CMORPH satellite",
            "type": "observed/modeled blend",
            "native_res": "~4 km",
            "notes": "Constrained to 1981-2010 PRISM 30-yr monthly climatology",
        },
        {
            "start": 1995, "end": 2001,
            "source": "NEXRAD Stage II hourly accumulations",
            "type": "observed/modeled blend",
            "native_res": "~4 km",
            "notes": "Constrained to PRISM climatology",
        },
        {
            "start": 2002, "end": 9999,
            "source": "Stage IV gauge-calibrated NEXRAD (hourly, QC by NWS RFCs)",
            "type": "observed/radar blend",
            "native_res": "~4 km",
            "notes": "Manually quality-controlled by NWS River Forecast Centers",
        },
    ]

    # Temperature source eras
    TEMP_ERAS = [
        {
            "start": 1979, "end": 2015,
            "source": "NLDAS-2 blended with LIV16 daily extrema, PRISM downscaled",
            "type": "reanalysis/observed blend",
            "native_res": "0.125° (~12 km)",
        },
        {
            "start": 2016, "end": 2017,
            "source": "NLDAS-2 → URMA transition blend",
            "type": "transitional",
            "native_res": "2.5 km → blended",
        },
        {
            "start": 2018, "end": 9999,
            "source": "URMA reanalysis (2.5 km, hourly)",
            "type": "reanalysis",
            "native_res": "2.5 km",
        },
    ]

    # Non-precipitation variable eras (humidity, pressure, wind)
    NONPRECIP_ERAS = [
        {
            "start": 1979, "end": 2015,
            "source": "GDAS/MERRA2 reanalysis",
            "type": "reanalysis",
            "native_res": "~12-55 km",
        },
        {
            "start": 2016, "end": 9999,
            "source": "URMA reanalysis",
            "type": "reanalysis",
            "native_res": "2.5 km",
        },
    ]

    # Radiation eras
    RADIATION_ERAS = [
        {
            "start": 1979, "end": 2015,
            "source": "MERRA2/CFSR reanalysis",
            "type": "modeled",
            "native_res": "~55 km / 0.2°",
        },
        {
            "start": 2016, "end": 9999,
            "source": "URMA-adjusted surface emissivities",
            "type": "modeled/adjusted",
            "native_res": "2.5 km",
            "notes": "DLWRF adjustment continues through 2017",
        },
    ]

    # Map AORC variable names to era tables
    VARIABLE_ERA_MAP = {
        "APCP_surface": "PRECIP_ERAS",
        "TMP_2maboveground": "TEMP_ERAS",
        "SPFH_2maboveground": "NONPRECIP_ERAS",
        "PRES_surface": "NONPRECIP_ERAS",
        "UGRD_10maboveground": "NONPRECIP_ERAS",
        "VGRD_10maboveground": "NONPRECIP_ERAS",
        "DSWRF_surface": "RADIATION_ERAS",
        "DLWRF_surface": "RADIATION_ERAS",
    }

    def get_provenance(self, variable, year):
        """Return provenance dict for a variable at a given year.

        Args:
            variable: AORC variable name (e.g. "TMP_2maboveground").
            year: Year (int).

        Returns:
            dict with source, type, native_res, and optional notes.
        """
        era_name = self.VARIABLE_ERA_MAP.get(variable)
        if era_name is None:
            return {"source": "unknown", "type": "unknown"}

        eras = getattr(self, era_name)
        for era in eras:
            if era["start"] <= year <= era["end"]:
                return {k: v for k, v in era.items() if k not in ("start", "end")}

        return {"source": "unknown", "type": "unknown"}

    def get_all_provenance(self, year):
        """Return provenance for all AORC variables at a given year.

        Returns:
            dict: variable_name → provenance dict.
        """
        return {var: self.get_provenance(var, year)
                for var in self.VARIABLE_ERA_MAP}

    def get_discontinuities_in_range(self, start_year, end_year):
        """Return all source transitions within a date range.

        Args:
            start_year: Start year (inclusive).
            end_year: End year (inclusive).

        Returns:
            list of dicts with: year, variable, from_source, to_source.
        """
        discontinuities = []
        all_eras = {
            "precipitation": self.PRECIP_ERAS,
            "temperature": self.TEMP_ERAS,
            "humidity/pressure/wind": self.NONPRECIP_ERAS,
            "radiation": self.RADIATION_ERAS,
        }

        for var_group, eras in all_eras.items():
            for i in range(len(eras) - 1):
                transition_year = eras[i + 1]["start"]
                if start_year <= transition_year <= end_year:
                    discontinuities.append({
                        "year": transition_year,
                        "variable_group": var_group,
                        "from_source": eras[i]["source"],
                        "to_source": eras[i + 1]["source"],
                        "severity": "major" if var_group == "precipitation"
                                    and transition_year == 2002 else "minor",
                    })

        return sorted(discontinuities, key=lambda x: x["year"])


class NDVIProvenance:
    """Track NDVI satellite data source for FPI layer."""

    SENSORS = [
        {
            "start": 2000, "end": 2011,
            "sensor": "MODIS Terra (MOD13A2)",
            "resolution": "1 km",
            "cadence": "16-day composite",
        },
        {
            "start": 2012, "end": 9999,
            "sensor": "VIIRS (VNP13A1)",
            "resolution": "500 m",
            "cadence": "16-day composite",
            "notes": "Higher resolution than MODIS",
        },
    ]

    def get_sensor(self, year):
        """Return which sensor provided NDVI for this year."""
        for s in self.SENSORS:
            if s["start"] <= year <= s["end"]:
                return {k: v for k, v in s.items() if k not in ("start", "end")}
        return {"sensor": "unknown"}

    def get_composite_window(self, day_of_year):
        """Return the 16-day composite window containing this DOY.

        Returns:
            (start_doy, end_doy) tuple.
        """
        window_start = ((day_of_year - 1) // 16) * 16 + 1
        window_end = min(window_start + 15, 366)
        return window_start, window_end


class FuelModelProvenance:
    """Track fuel model assignment source for NFDRS layers."""

    def get_provenance(self, fuel_model_code):
        """Return fuel model metadata.

        Args:
            fuel_model_code: NFDRS model letter (e.g. "G").

        Returns:
            dict with model name, all parameters, and source info.
        """
        fm = NFDRS_FUEL_MODELS.get(fuel_model_code, {})
        return {
            "model_code": fuel_model_code,
            "model_name": fm.get("name", "Unknown"),
            "source": "LANDFIRE FBFM40 crosswalked to NFDRS",
            "native_resolution": "30 m",
            "parameters": {k: v for k, v in fm.items() if k != "name"},
        }


def generate_metadata(year, month, fuel_model_code="G", calculation_params=None):
    """Generate complete metadata JSON for an extraction month.

    Called by extract.py to create metadata_YYYY_MM.json files.

    Args:
        year: Year.
        month: Month (1-12).
        fuel_model_code: NFDRS fuel model used.
        calculation_params: Optional dict of additional parameters.

    Returns:
        dict suitable for JSON serialization.
    """
    aorc = AORCProvenance()
    ndvi = NDVIProvenance()
    fuel = FuelModelProvenance()

    metadata = {
        "generated": datetime.utcnow().isoformat() + "Z",
        "period": f"{year}-{month:02d}",
        "aorc_provenance": aorc.get_all_provenance(year),
        "aorc_grid": {
            "resolution": "30 arc-seconds (~800 m)",
            "crs": "EPSG:4326",
            "source": "NOAA AORC v1.1",
        },
        "discontinuities": aorc.get_discontinuities_in_range(year, year),
        "ndvi_provenance": ndvi.get_sensor(year),
        "fuel_model": fuel.get_provenance(fuel_model_code),
        "calculation_params": calculation_params or {},
    }

    return metadata


def save_metadata(metadata, output_path):
    """Save metadata dict to JSON file."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(metadata, f, indent=2, default=str)
