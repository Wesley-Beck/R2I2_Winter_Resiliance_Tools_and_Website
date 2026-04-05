"""
Pluggable climate model adapter — abstract interface for AORC, GLARM, and future datasets.

All fire index computations receive data through this adapter interface,
making the pipeline data-source agnostic. Swap AORC for GLARM (or any
other climate model) by providing a different adapter.

Adapters must supply the minimum fire weather variables:
    - TMP_2maboveground (K) — 2m air temperature
    - SPFH_2maboveground (kg/kg) — specific humidity (or RH directly)
    - PRES_surface (Pa) — surface pressure
    - UGRD_10maboveground (m/s) — U-wind component
    - VGRD_10maboveground (m/s) — V-wind component
    - APCP_surface (mm) — hourly precipitation

Optional:
    - DSWRF_surface (W/m²) — downward shortwave radiation
    - DLWRF_surface (W/m²) — downward longwave radiation

If a model doesn't provide all variables, the adapter should return
np.nan arrays for missing ones — the fire indices will degrade
gracefully (NaN propagation).
"""

import logging
from abc import ABC, abstractmethod

import numpy as np

logger = logging.getLogger(__name__)


# Standard variable names used by the fire index pipeline
REQUIRED_VARIABLES = [
    "TMP_2maboveground",
    "SPFH_2maboveground",
    "PRES_surface",
    "UGRD_10maboveground",
    "VGRD_10maboveground",
    "APCP_surface",
]

OPTIONAL_VARIABLES = [
    "DSWRF_surface",
    "DLWRF_surface",
]


class ClimateModelAdapter(ABC):
    """Abstract base for climate data sources."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable name of the data source."""

    @abstractmethod
    def get_available_variables(self) -> list:
        """Return list of variable names this source provides."""

    @abstractmethod
    def get_time_range(self) -> tuple:
        """Return (start_year, end_year) of available data."""

    @abstractmethod
    def get_coordinates(self):
        """Return (latitudes, longitudes) arrays of the native grid."""

    @abstractmethod
    def get_daily_point_values(self, year, month, day,
                                lat_indices, lon_indices,
                                lat_bounds, lon_bounds):
        """Fetch one day of data for the given point indices.

        Returns:
            dict with keys:
                "hours": list of hour values (0-23)
                "timestamps": DatetimeIndex
                {variable_name}: array (n_hours, n_points)
        """

    def get_multiday_point_values(self, year, month, start_day, end_day,
                                   lat_indices, lon_indices,
                                   lat_bounds, lon_bounds):
        """Fetch multiple days. Default: calls get_daily_point_values per day.

        Subclasses can override for batch optimization (e.g., AORC 6-day chunks).

        Returns:
            dict: day_number → daily data dict
        """
        result = {}
        for day in range(start_day, end_day + 1):
            try:
                result[day] = self.get_daily_point_values(
                    year, month, day, lat_indices, lon_indices,
                    lat_bounds, lon_bounds,
                )
            except Exception as e:
                logger.warning("Failed to fetch %d-%02d-%02d: %s", year, month, day, e)
        return result

    def get_missing_variables(self) -> list:
        """Return REQUIRED variables NOT provided by this source."""
        available = set(self.get_available_variables())
        return [v for v in REQUIRED_VARIABLES if v not in available]

    def info(self) -> dict:
        """Return summary information about this data source."""
        available = self.get_available_variables()
        missing = self.get_missing_variables()
        start, end = self.get_time_range()
        return {
            "name": self.name,
            "start_year": start,
            "end_year": end,
            "available_variables": available,
            "missing_variables": missing,
            "ready": len(missing) == 0,
        }


class AORCAdapter(ClimateModelAdapter):
    """Adapter wrapping the existing AORCDataLoader."""

    def __init__(self):
        from aorc_tools.aorc_access import AORCDataLoader
        self._loader = AORCDataLoader()

    @property
    def name(self):
        return "NOAA AORC v1.1"

    def get_available_variables(self):
        return list(self._loader.VARIABLES)

    def get_time_range(self):
        return (1979, 2025)

    def get_coordinates(self):
        return self._loader.get_coordinates()

    def get_daily_point_values(self, year, month, day,
                                lat_indices, lon_indices,
                                lat_bounds, lon_bounds):
        return self._loader.get_daily_point_values(
            year, month, day, lat_indices, lon_indices,
            lat_bounds, lon_bounds,
        )

    def get_multiday_point_values(self, year, month, start_day, end_day,
                                   lat_indices, lon_indices,
                                   lat_bounds, lon_bounds):
        return self._loader.get_multiday_point_values(
            year, month, start_day, end_day,
            lat_indices, lon_indices, lat_bounds, lon_bounds,
        )


class GLARMAdapter(ClimateModelAdapter):
    """Adapter for GLARM (Great Lakes Atmosphere-Regional Model) projections.

    GLARM-Proj1 provides daily 2m air temperature at 18km resolution
    over the Great Lakes basin (1981-2099, RCP 4.5 and RCP 8.5).

    Data source: https://digitalcommons.mtu.edu/glts/
    Reference: Xue et al. 2022 (GMD)

    NOTE: GLARM-Proj1 is primarily a lake thermal model. It provides
    air temperature but may not include humidity, wind, or precipitation.
    Missing variables will produce NaN fire indices — supplement with
    the driving GCM (RegCM4) or another dataset for full coverage.

    Configuration:
        data_path: Path to GLARM NetCDF files on disk
        scenario: "rcp45" or "rcp85"
        variable_map: Optional custom mapping of GLARM var names → standard names
    """

    # Default mapping of GLARM variable names → fire weather standard names
    # These are the expected names based on RegCM4/WRF convention.
    # Update once the actual GLARM file contents are inspected.
    DEFAULT_VARIABLE_MAP = {
        "T2": "TMP_2maboveground",        # 2m air temperature (K)
        "Q2": "SPFH_2maboveground",       # 2m specific humidity (kg/kg)
        "PSFC": "PRES_surface",            # Surface pressure (Pa)
        "U10": "UGRD_10maboveground",      # 10m U-wind (m/s)
        "V10": "VGRD_10maboveground",      # 10m V-wind (m/s)
        "RAIN": "APCP_surface",            # Precipitation (mm)
        "SWDOWN": "DSWRF_surface",         # Downward shortwave (W/m²)
        "GLW": "DLWRF_surface",            # Downward longwave (W/m²)
    }

    def __init__(self, data_path, scenario="rcp85", variable_map=None):
        from pathlib import Path

        self.data_path = Path(data_path)
        self.scenario = scenario
        self.variable_map = variable_map or self.DEFAULT_VARIABLE_MAP
        self._reverse_map = {v: k for k, v in self.variable_map.items()}
        self._ds_cache = {}

        if not self.data_path.exists():
            logger.warning("GLARM data path does not exist: %s", self.data_path)

    @property
    def name(self):
        return f"GLARM-Proj1 ({self.scenario.upper()})"

    def get_available_variables(self):
        """Check which variables actually exist in the data files."""
        # If data path doesn't exist, report based on variable map
        if not self.data_path.exists():
            return list(self.variable_map.values())

        # Try to open a sample file and check variables
        try:
            ds = self._open_sample()
            found = []
            for glarm_name, standard_name in self.variable_map.items():
                if glarm_name in ds:
                    found.append(standard_name)
            return found
        except Exception:
            return list(self.variable_map.values())

    def get_time_range(self):
        return (1981, 2099)

    def get_coordinates(self):
        """Return lat/lon arrays from GLARM grid.

        NOTE: GLARM uses a different grid than AORC. The extraction
        pipeline will need to regrid or use nearest-neighbor matching.
        """
        try:
            ds = self._open_sample()
            lats = ds["lat"].values if "lat" in ds else ds["XLAT"].values
            lons = ds["lon"].values if "lon" in ds else ds["XLONG"].values
            return lats, lons
        except Exception as e:
            logger.error("Cannot read GLARM coordinates: %s", e)
            raise

    def get_daily_point_values(self, year, month, day,
                                lat_indices, lon_indices,
                                lat_bounds, lon_bounds):
        """Extract point values from GLARM NetCDF for one day.

        This is a stub — the actual implementation depends on the
        GLARM file naming convention and internal structure.
        """
        import pandas as pd

        try:
            ds = self._open_dataset(year, month)
        except FileNotFoundError:
            logger.warning("No GLARM data for %d-%02d", year, month)
            return self._empty_day(year, month, day, len(lat_indices))

        n_points = len(lat_indices)
        timestamps = pd.date_range(
            f"{year}-{month:02d}-{day:02d} 00:00",
            f"{year}-{month:02d}-{day:02d} 23:00",
            freq="h",
        )

        result = {
            "hours": list(range(24)),
            "timestamps": timestamps,
        }

        for glarm_name, standard_name in self.variable_map.items():
            if glarm_name in ds:
                try:
                    # Attempt to extract data for this day
                    # Actual indexing depends on GLARM file structure
                    day_data = self._extract_variable(ds, glarm_name, year, month, day,
                                                       lat_indices, lon_indices)
                    result[standard_name] = day_data
                except Exception as e:
                    logger.debug("Cannot extract %s: %s", glarm_name, e)
                    result[standard_name] = np.full((24, n_points), np.nan, dtype=np.float32)
            else:
                result[standard_name] = np.full((24, n_points), np.nan, dtype=np.float32)

        return result

    def _open_sample(self):
        """Open a sample GLARM file to inspect structure."""
        import xarray as xr
        from pathlib import Path

        # Try common naming patterns
        patterns = [
            f"{self.scenario}/*.nc",
            f"*{self.scenario}*.nc",
            "*.nc",
        ]
        for pattern in patterns:
            files = sorted(self.data_path.glob(pattern))
            if files:
                return xr.open_dataset(files[0])

        raise FileNotFoundError(f"No NetCDF files found in {self.data_path}")

    def _open_dataset(self, year, month):
        """Open GLARM dataset for a specific year/month.

        Tries common file naming conventions. Override if your
        GLARM files use a different naming scheme.
        """
        import xarray as xr

        cache_key = f"{year}-{month:02d}"
        if cache_key in self._ds_cache:
            return self._ds_cache[cache_key]

        # Try various naming patterns
        patterns = [
            self.data_path / self.scenario / f"glarm_{year}_{month:02d}.nc",
            self.data_path / self.scenario / f"glarm_{year}.nc",
            self.data_path / f"{self.scenario}_{year}_{month:02d}.nc",
            self.data_path / f"{self.scenario}_{year}.nc",
        ]

        for path in patterns:
            if path.exists():
                ds = xr.open_dataset(path)
                self._ds_cache[cache_key] = ds
                return ds

        raise FileNotFoundError(
            f"No GLARM file found for {year}-{month:02d}. "
            f"Tried: {[str(p) for p in patterns]}"
        )

    def _extract_variable(self, ds, var_name, year, month, day,
                           lat_indices, lon_indices):
        """Extract point values for a variable on a specific day.

        Override this method if GLARM uses non-standard dimensions.
        """
        import pandas as pd

        # Find time dimension
        time_dim = None
        for dim in ["time", "Time", "XTIME"]:
            if dim in ds.dims:
                time_dim = dim
                break

        if time_dim is None:
            raise ValueError(f"Cannot find time dimension in GLARM dataset")

        # Select the day
        target_date = pd.Timestamp(year, month, day)
        var = ds[var_name]

        # Try time selection
        times = pd.DatetimeIndex(ds[time_dim].values)
        day_mask = times.date == target_date.date()

        if not day_mask.any():
            n_points = len(lat_indices)
            return np.full((24, n_points), np.nan, dtype=np.float32)

        day_data = var.isel({time_dim: day_mask})

        # Extract point values (nearest neighbor)
        # This depends on the grid structure — lat/lon might be 1D or 2D
        n_times = day_data.shape[0]
        n_points = len(lat_indices)
        result = np.full((n_times, n_points), np.nan, dtype=np.float32)

        for i, (lat_idx, lon_idx) in enumerate(zip(lat_indices, lon_indices)):
            try:
                result[:, i] = day_data.values[:, lat_idx, lon_idx]
            except (IndexError, ValueError):
                pass

        # Pad to 24 hours if needed (daily data → repeat for all hours)
        if n_times == 1:
            result = np.repeat(result, 24, axis=0)
        elif n_times < 24:
            pad = np.full((24 - n_times, n_points), np.nan, dtype=np.float32)
            result = np.concatenate([result, pad], axis=0)

        return result[:24]

    def _empty_day(self, year, month, day, n_points):
        """Return empty data structure for a day with no data."""
        import pandas as pd

        timestamps = pd.date_range(
            f"{year}-{month:02d}-{day:02d} 00:00",
            f"{year}-{month:02d}-{day:02d} 23:00",
            freq="h",
        )
        result = {
            "hours": list(range(24)),
            "timestamps": timestamps,
        }
        for standard_name in self.variable_map.values():
            result[standard_name] = np.full((24, n_points), np.nan, dtype=np.float32)
        return result


def get_adapter(source="aorc", **kwargs):
    """Factory function to get the appropriate climate model adapter.

    Args:
        source: "aorc" (default), "glarm", or path to a config file.
        **kwargs: Passed to the adapter constructor.

    Returns:
        ClimateModelAdapter instance.
    """
    if source == "aorc":
        return AORCAdapter()
    elif source == "glarm":
        return GLARMAdapter(**kwargs)
    else:
        # Treat as config file path
        import json
        from pathlib import Path

        config_path = Path(source)
        if config_path.exists():
            with open(config_path) as f:
                config = json.load(f)
            adapter_type = config.pop("type", "glarm")
            if adapter_type == "glarm":
                return GLARMAdapter(**config)
            elif adapter_type == "aorc":
                return AORCAdapter()
            else:
                raise ValueError(f"Unknown adapter type: {adapter_type}")

        raise ValueError(f"Unknown data source: {source}")
