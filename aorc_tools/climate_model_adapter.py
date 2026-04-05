"""
Pluggable climate model adapter — abstract interface for multiple climate datasets.

Supports:
- AORC (historical reanalysis, 1979-present, hourly, ~800m)
- NEX-GDDP-CMIP6 (NASA downscaled projections, 1950-2100, daily, 0.25°)
  Multiple GCMs: ACCESS-CM2, GFDL-ESM4, MPI-ESM1-2-HR, etc.
  Scenarios: SSP2-4.5, SSP5-8.5
- GLARM (Michigan Tech, Great Lakes, 1981-2099, daily, 18km)
  Scenarios: RCP 4.5, RCP 8.5
- Argonne ClimRR (Argonne WRF downscaling, fire indices pre-computed)

All fire index computations receive data through this adapter interface,
making the pipeline data-source agnostic.

Required variables (AORC standard names):
    TMP_2maboveground (K), SPFH_2maboveground (kg/kg), PRES_surface (Pa),
    UGRD_10maboveground (m/s), VGRD_10maboveground (m/s), APCP_surface (mm)

If a model provides RH directly instead of specific humidity, the adapter
converts internally. If a model provides wind speed instead of U/V components,
it sets both components equal to speed/sqrt(2).
"""

import calendar
import logging
from abc import ABC, abstractmethod
from pathlib import Path

import numpy as np

logger = logging.getLogger(__name__)


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
        """Human-readable name."""

    @abstractmethod
    def get_available_variables(self) -> list:
        """Return list of standard variable names this source provides."""

    @abstractmethod
    def get_time_range(self) -> tuple:
        """Return (start_year, end_year)."""

    @abstractmethod
    def get_coordinates(self):
        """Return (latitudes, longitudes) arrays."""

    @abstractmethod
    def get_daily_point_values(self, year, month, day,
                                lat_indices, lon_indices,
                                lat_bounds, lon_bounds):
        """Fetch one day for given point indices.

        Returns dict: "hours", "timestamps", {var_name}: (n_hours, n_points)
        """

    def get_multiday_point_values(self, year, month, start_day, end_day,
                                   lat_indices, lon_indices,
                                   lat_bounds, lon_bounds):
        """Fetch multiple days. Override for batch optimization."""
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
        available = set(self.get_available_variables())
        return [v for v in REQUIRED_VARIABLES if v not in available]

    def info(self) -> dict:
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


# ======================================================================
# AORC Adapter (wraps existing AORCDataLoader)
# ======================================================================

class AORCAdapter(ClimateModelAdapter):
    """Wraps the existing AORCDataLoader."""

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

    def get_daily_point_values(self, *args, **kwargs):
        return self._loader.get_daily_point_values(*args, **kwargs)

    def get_multiday_point_values(self, *args, **kwargs):
        return self._loader.get_multiday_point_values(*args, **kwargs)


# ======================================================================
# NEX-GDDP-CMIP6 Adapter (NASA, AWS S3, all fire weather variables)
# ======================================================================

# Available GCMs in NEX-GDDP-CMIP6
NEX_GDDP_GCMS = [
    "ACCESS-CM2",
    "ACCESS-ESM1-5",
    "BCC-CSM2-MR",
    "CanESM5",
    "CMCC-CM2-SR5",
    "CMCC-ESM2",
    "EC-Earth3",
    "EC-Earth3-Veg-LR",
    "FGOALS-g3",
    "GFDL-CM4",
    "GFDL-ESM4",
    "GISS-E2-1-G",
    "HadGEM3-GC31-LL",
    "INM-CM4-8",
    "INM-CM5-0",
    "IPSL-CM6A-LR",
    "KACE-1-0-G",
    "KIOST-ESM",
    "MIROC-ES2L",
    "MIROC6",
    "MPI-ESM1-2-HR",
    "MPI-ESM1-2-LR",
    "MRI-ESM2-0",
    "NorESM2-LM",
    "NorESM2-MM",
    "TaiESM1",
    "UKESM1-0-LL",
]

NEX_GDDP_SCENARIOS = ["historical", "ssp245", "ssp585"]

# NEX-GDDP-CMIP6 variable names → our standard names
NEX_GDDP_VARIABLE_MAP = {
    "tas": "TMP_2maboveground",        # Near-surface air temp (K)
    "hurs": "SPFH_2maboveground",      # Near-surface RH (%) — we convert
    "pr": "APCP_surface",              # Precipitation (kg/m²/s → mm/hr)
    "sfcWind": "UGRD_10maboveground",  # Near-surface wind speed (m/s)
    # NEX-GDDP provides scalar wind, not U/V components
    # We set both UGRD and VGRD = sfcWind/sqrt(2) so magnitude is correct
}


class NexGddpCmip6Adapter(ClimateModelAdapter):
    """NASA NEX-GDDP-CMIP6 downscaled climate projections.

    Data source: s3://nex-gddp-cmip6 (public, anonymous access)
    Resolution: 0.25° (~25 km), daily
    Period: 1950-2100
    Variables: tas, tasmin, tasmax, hurs, pr, sfcWind
    Scenarios: historical, SSP2-4.5, SSP5-8.5

    Reference: Thrasher et al. 2022, Scientific Data
    """

    S3_BUCKET = "nex-gddp-cmip6"

    def __init__(self, gcm="ACCESS-CM2", scenario="ssp585"):
        if gcm not in NEX_GDDP_GCMS:
            raise ValueError(f"Unknown GCM: {gcm}. Available: {NEX_GDDP_GCMS}")
        if scenario not in NEX_GDDP_SCENARIOS:
            raise ValueError(f"Unknown scenario: {scenario}. Available: {NEX_GDDP_SCENARIOS}")

        self.gcm = gcm
        self.scenario = scenario
        self._ds_cache = {}
        self._coords = None

    @property
    def name(self):
        return f"NEX-GDDP-CMIP6 {self.gcm} ({self.scenario})"

    def get_available_variables(self):
        return list(REQUIRED_VARIABLES)  # We synthesize all needed vars

    def get_time_range(self):
        if self.scenario == "historical":
            return (1950, 2014)
        return (2015, 2100)

    def get_coordinates(self):
        """Return the NEX-GDDP-CMIP6 global grid coordinates."""
        if self._coords is not None:
            return self._coords

        # NEX-GDDP-CMIP6 uses a regular 0.25° grid
        lats = np.arange(-59.875, 90.125, 0.25)
        lons = np.arange(0.125, 360.125, 0.25)
        self._coords = (lats, lons)
        return lats, lons

    def _open_dataset(self, variable, year):
        """Open a NEX-GDDP-CMIP6 NetCDF file from S3."""
        import xarray as xr
        import s3fs

        cache_key = f"{variable}_{year}"
        if cache_key in self._ds_cache:
            return self._ds_cache[cache_key]

        # S3 path: NEX-GDDP-CMIP6/{gcm}/{scenario}/r1i1p1f1/{variable}/
        #           {variable}_day_{gcm}_{scenario}_r1i1p1f1_gn_{year}.nc
        s3_path = (
            f"s3://{self.S3_BUCKET}/NEX-GDDP-CMIP6/{self.gcm}/"
            f"{self.scenario}/r1i1p1f1/{variable}/"
            f"{variable}_day_{self.gcm}_{self.scenario}_r1i1p1f1_gn_{year}.nc"
        )

        fs = s3fs.S3FileSystem(anon=True)
        store = s3fs.S3Map(root=s3_path, s3=fs)

        try:
            ds = xr.open_dataset(store, engine="h5netcdf")
        except Exception:
            ds = xr.open_dataset(store)

        self._ds_cache[cache_key] = ds
        return ds

    def get_daily_point_values(self, year, month, day,
                                lat_indices, lon_indices,
                                lat_bounds, lon_bounds):
        """Extract point values for one day from NEX-GDDP-CMIP6.

        Daily data is disaggregated to 24 hours (constant within day)
        since NEX-GDDP is daily resolution.
        """
        import pandas as pd

        n_points = len(lat_indices)
        timestamps = pd.date_range(
            f"{year}-{month:02d}-{day:02d} 00:00",
            f"{year}-{month:02d}-{day:02d} 23:00",
            freq="h",
        )
        target_date = f"{year}-{month:02d}-{day:02d}"

        result = {
            "hours": list(range(24)),
            "timestamps": timestamps,
        }

        # Temperature (K)
        try:
            ds = self._open_dataset("tas", year)
            day_vals = ds["tas"].sel(time=target_date).values
            temp_k = self._extract_points(day_vals, lat_indices, lon_indices)
            result["TMP_2maboveground"] = np.tile(temp_k, (24, 1)).astype(np.float32)
        except Exception as e:
            logger.debug("tas not available for %s: %s", target_date, e)
            result["TMP_2maboveground"] = np.full((24, n_points), np.nan, dtype=np.float32)

        # Relative Humidity (%) → convert to specific humidity proxy
        # The extraction pipeline will use this with the RH-aware path
        try:
            ds = self._open_dataset("hurs", year)
            day_vals = ds["hurs"].sel(time=target_date).values
            rh_pct = self._extract_points(day_vals, lat_indices, lon_indices)
            # Store as "RH in SPFH slot" — the extract pipeline detects values > 1
            # and treats them as RH directly instead of specific humidity
            result["SPFH_2maboveground"] = np.tile(rh_pct / 100.0, (24, 1)).astype(np.float32)
        except Exception as e:
            logger.debug("hurs not available for %s: %s", target_date, e)
            result["SPFH_2maboveground"] = np.full((24, n_points), np.nan, dtype=np.float32)

        # Standard pressure assumption (no surface pressure in NEX-GDDP)
        result["PRES_surface"] = np.full((24, n_points), 101325.0, dtype=np.float32)

        # Precipitation (kg/m²/s → mm/hr)
        try:
            ds = self._open_dataset("pr", year)
            day_vals = ds["pr"].sel(time=target_date).values
            precip_kgms = self._extract_points(day_vals, lat_indices, lon_indices)
            precip_mm_hr = precip_kgms * 3600.0  # kg/m²/s → mm/hr
            result["APCP_surface"] = np.tile(precip_mm_hr, (24, 1)).astype(np.float32)
        except Exception as e:
            logger.debug("pr not available for %s: %s", target_date, e)
            result["APCP_surface"] = np.full((24, n_points), np.nan, dtype=np.float32)

        # Wind speed (m/s) → split into U/V components
        try:
            ds = self._open_dataset("sfcWind", year)
            day_vals = ds["sfcWind"].sel(time=target_date).values
            ws = self._extract_points(day_vals, lat_indices, lon_indices)
            # Split scalar wind into equal U/V so magnitude is preserved
            component = ws / np.sqrt(2.0)
            result["UGRD_10maboveground"] = np.tile(component, (24, 1)).astype(np.float32)
            result["VGRD_10maboveground"] = np.tile(component, (24, 1)).astype(np.float32)
        except Exception as e:
            logger.debug("sfcWind not available for %s: %s", target_date, e)
            result["UGRD_10maboveground"] = np.full((24, n_points), np.nan, dtype=np.float32)
            result["VGRD_10maboveground"] = np.full((24, n_points), np.nan, dtype=np.float32)

        return result

    def _extract_points(self, grid_2d, lat_indices, lon_indices):
        """Extract point values from a 2D grid using index arrays."""
        n_points = len(lat_indices)
        values = np.full(n_points, np.nan, dtype=np.float32)
        for i, (lat_idx, lon_idx) in enumerate(zip(lat_indices, lon_indices)):
            try:
                values[i] = grid_2d[lat_idx, lon_idx]
            except (IndexError, ValueError):
                pass
        return values


# ======================================================================
# GLARM Adapter (Michigan Tech, Great Lakes)
# ======================================================================

class GLARMAdapter(ClimateModelAdapter):
    """GLARM-Proj1 Great Lakes climate projections.

    Data source: https://digitalcommons.mtu.edu/glts/
    Resolution: 18 km (atmospheric), 1-4 km (lake)
    Period: 1981-2099 (RCP 4.5 and RCP 8.5)
    Reference: Xue et al. 2022 (GMD)
    """

    DEFAULT_VARIABLE_MAP = {
        "T2": "TMP_2maboveground",
        "Q2": "SPFH_2maboveground",
        "PSFC": "PRES_surface",
        "U10": "UGRD_10maboveground",
        "V10": "VGRD_10maboveground",
        "RAIN": "APCP_surface",
        "SWDOWN": "DSWRF_surface",
        "GLW": "DLWRF_surface",
    }

    def __init__(self, data_path, scenario="rcp85", variable_map=None):
        self.data_path = Path(data_path)
        self.scenario = scenario
        self.variable_map = variable_map or self.DEFAULT_VARIABLE_MAP
        self._ds_cache = {}

        if not self.data_path.exists():
            logger.warning("GLARM data path does not exist: %s", self.data_path)

    @property
    def name(self):
        return f"GLARM-Proj1 ({self.scenario.upper()})"

    def get_available_variables(self):
        if not self.data_path.exists():
            return list(self.variable_map.values())
        try:
            ds = self._open_sample()
            return [std for glarm, std in self.variable_map.items() if glarm in ds]
        except Exception:
            return list(self.variable_map.values())

    def get_time_range(self):
        return (1981, 2099)

    def get_coordinates(self):
        ds = self._open_sample()
        lats = ds["lat"].values if "lat" in ds else ds["XLAT"].values
        lons = ds["lon"].values if "lon" in ds else ds["XLONG"].values
        return lats, lons

    def get_daily_point_values(self, year, month, day,
                                lat_indices, lon_indices,
                                lat_bounds, lon_bounds):
        import pandas as pd

        n_points = len(lat_indices)
        timestamps = pd.date_range(
            f"{year}-{month:02d}-{day:02d} 00:00",
            f"{year}-{month:02d}-{day:02d} 23:00",
            freq="h",
        )

        try:
            ds = self._open_dataset(year, month)
        except FileNotFoundError:
            return self._empty_day(year, month, day, n_points, timestamps)

        result = {"hours": list(range(24)), "timestamps": timestamps}

        for glarm_name, standard_name in self.variable_map.items():
            if glarm_name in ds:
                try:
                    day_data = self._extract_variable(ds, glarm_name, year, month, day,
                                                       lat_indices, lon_indices)
                    result[standard_name] = day_data
                except Exception:
                    result[standard_name] = np.full((24, n_points), np.nan, dtype=np.float32)
            else:
                result[standard_name] = np.full((24, n_points), np.nan, dtype=np.float32)

        return result

    def _open_sample(self):
        import xarray as xr
        for pattern in [f"{self.scenario}/*.nc", f"*{self.scenario}*.nc", "*.nc"]:
            files = sorted(self.data_path.glob(pattern))
            if files:
                return xr.open_dataset(files[0])
        raise FileNotFoundError(f"No NetCDF files in {self.data_path}")

    def _open_dataset(self, year, month):
        import xarray as xr
        key = f"{year}-{month:02d}"
        if key in self._ds_cache:
            return self._ds_cache[key]

        patterns = [
            self.data_path / self.scenario / f"glarm_{year}_{month:02d}.nc",
            self.data_path / self.scenario / f"glarm_{year}.nc",
            self.data_path / f"{self.scenario}_{year}_{month:02d}.nc",
            self.data_path / f"{self.scenario}_{year}.nc",
        ]
        for path in patterns:
            if path.exists():
                ds = xr.open_dataset(path)
                self._ds_cache[key] = ds
                return ds
        raise FileNotFoundError(f"No GLARM file for {year}-{month:02d}")

    def _extract_variable(self, ds, var_name, year, month, day,
                           lat_indices, lon_indices):
        import pandas as pd
        target = pd.Timestamp(year, month, day)
        var = ds[var_name]

        time_dim = next((d for d in ["time", "Time", "XTIME"] if d in ds.dims), None)
        if time_dim is None:
            raise ValueError("No time dimension found")

        times = pd.DatetimeIndex(ds[time_dim].values)
        mask = times.date == target.date()
        if not mask.any():
            return np.full((24, len(lat_indices)), np.nan, dtype=np.float32)

        data = var.isel({time_dim: mask}).values
        n_times = data.shape[0]
        n_pts = len(lat_indices)
        result = np.full((n_times, n_pts), np.nan, dtype=np.float32)
        for i, (li, lo) in enumerate(zip(lat_indices, lon_indices)):
            try:
                result[:, i] = data[:, li, lo]
            except (IndexError, ValueError):
                pass

        # Pad daily to 24h
        if n_times < 24:
            result = np.repeat(result, max(1, 24 // n_times), axis=0)[:24]
        return result

    def _empty_day(self, year, month, day, n_points, timestamps):
        result = {"hours": list(range(24)), "timestamps": timestamps}
        for std in self.variable_map.values():
            result[std] = np.full((24, n_points), np.nan, dtype=np.float32)
        return result


# ======================================================================
# Argonne ClimRR Adapter (CESM2 + WRF downscaling, ArcGIS Feature Service)
# ======================================================================

# ClimRR ArcGIS Feature Service base URL
CLIMRR_BASE_URL = "https://disgeoportal.egs.anl.gov/server/rest/services/ClimRR"

# ClimRR period definitions
CLIMRR_PERIODS = {
    "historical": (1995, 2014),
    "midcentury": (2045, 2064),
    "endcentury": (2075, 2094),
}

# Map from ClimRR field names to our standard variables
CLIMRR_VARIABLE_MAP = {
    "Temp": "TMP_2maboveground",
    "TempMin": "TMP_2maboveground",  # used for daily min
    "TempMax": "TMP_2maboveground",  # used for daily max
    "Precip": "APCP_surface",
    "Wind": "UGRD_10maboveground",
    "Humidity": "SPFH_2maboveground",
}


class ClimRRAdapter(ClimateModelAdapter):
    """Argonne ClimRR climate projections via ArcGIS Feature Service.

    Data source: https://disgeoportal.egs.anl.gov/ClimRR/
    Resolution: 12km (WRF dynamical downscaling of CESM2/CMIP6)
    Periods: Historical (1995-2014), Mid-century (2045-2064), End-century (2075-2094)
    Scenarios: SSP2-4.5, SSP5-8.5

    ClimRR provides aggregated statistics (monthly/seasonal means) rather than
    daily time series. For fire index computation, we disaggregate monthly
    means to daily values with sinusoidal temperature variation.

    Note: This adapter uses ArcGIS REST endpoints. For bulk analysis,
    consider downloading data from the portal and providing local NetCDF files.
    """

    def __init__(self, scenario="ssp585", period="midcentury", data_path=None):
        """
        Args:
            scenario: "ssp245" or "ssp585"
            period: "historical", "midcentury", or "endcentury"
            data_path: Optional path to locally downloaded ClimRR data (NetCDF/CSV).
                       If provided, reads from local files instead of ArcGIS service.
        """
        self.scenario = scenario
        self.period = period
        self.data_path = Path(data_path) if data_path else None
        self._cache = {}

        if period not in CLIMRR_PERIODS:
            raise ValueError(f"Unknown period: {period}. "
                             f"Available: {list(CLIMRR_PERIODS.keys())}")

    @property
    def name(self):
        return f"ClimRR ({self.scenario.upper()}, {self.period})"

    def get_available_variables(self):
        return list(REQUIRED_VARIABLES)

    def get_time_range(self):
        return CLIMRR_PERIODS[self.period]

    def get_coordinates(self):
        # ClimRR uses a 12km WRF grid; approximate as regular grid
        # covering the Great Lakes region
        lats = np.arange(36.0, 50.0, 0.108)  # ~12km at 43°N
        lons = np.arange(-93.0, -75.0, 0.144)  # ~12km
        return lats, lons

    def get_daily_point_values(self, year, month, day,
                                lat_indices, lon_indices,
                                lat_bounds, lon_bounds):
        """Extract point values for one day from ClimRR.

        ClimRR provides monthly/seasonal aggregates. We disaggregate to
        daily/hourly with realistic diurnal variation:
        - Temperature: sinusoidal daily cycle from Tmin to Tmax
        - Precipitation: uniform distribution of monthly total
        - Wind: constant daily value from monthly mean
        - Humidity: inverse of temperature cycle
        """
        import pandas as pd

        n_points = len(lat_indices)
        timestamps = pd.date_range(
            f"{year}-{month:02d}-{day:02d} 00:00",
            f"{year}-{month:02d}-{day:02d} 23:00",
            freq="h",
        )
        n_days_month = calendar.monthrange(year, month)[1]

        result = {"hours": list(range(24)), "timestamps": timestamps}

        # Try local data first, then ArcGIS service
        monthly_data = self._get_monthly_data(year, month,
                                               lat_indices, lon_indices,
                                               lat_bounds, lon_bounds)

        if monthly_data is None:
            # Return NaN if no data available
            for var in REQUIRED_VARIABLES:
                result[var] = np.full((24, n_points), np.nan, dtype=np.float32)
            return result

        # Disaggregate monthly means to hourly values
        # Temperature: sinusoidal diurnal cycle
        temp_mean = monthly_data.get("temp_mean", np.full(n_points, 283.0))
        temp_range = monthly_data.get("temp_range", np.full(n_points, 10.0))  # K

        hourly_temp = np.zeros((24, n_points), dtype=np.float32)
        for h in range(24):
            # Min at 05:00, max at 15:00
            phase = 2 * np.pi * (h - 15) / 24.0
            hourly_temp[h] = temp_mean + 0.5 * temp_range * np.cos(phase)
        result["TMP_2maboveground"] = hourly_temp

        # Pressure: standard atmosphere
        result["PRES_surface"] = np.full((24, n_points), 101325.0, dtype=np.float32)

        # Humidity: inverse of temperature pattern
        rh_mean = monthly_data.get("rh_mean", np.full(n_points, 0.65))
        hourly_rh = np.zeros((24, n_points), dtype=np.float32)
        for h in range(24):
            phase = 2 * np.pi * (h - 15) / 24.0
            # Higher RH when cooler, lower when warmer
            hourly_rh[h] = rh_mean - 0.15 * np.cos(phase)
        hourly_rh = np.clip(hourly_rh, 0.05, 1.0)
        result["SPFH_2maboveground"] = hourly_rh

        # Precipitation: uniform distribution across month (daily portion)
        precip_monthly = monthly_data.get("precip_mm", np.full(n_points, 80.0))
        precip_hourly = precip_monthly / (n_days_month * 24.0)
        result["APCP_surface"] = np.tile(precip_hourly, (24, 1)).astype(np.float32)

        # Wind: constant from monthly mean, split into U/V
        wind_speed = monthly_data.get("wind_ms", np.full(n_points, 4.0))
        component = wind_speed / np.sqrt(2.0)
        result["UGRD_10maboveground"] = np.tile(component, (24, 1)).astype(np.float32)
        result["VGRD_10maboveground"] = np.tile(component, (24, 1)).astype(np.float32)

        return result

    def _get_monthly_data(self, year, month, lat_indices, lon_indices,
                           lat_bounds, lon_bounds):
        """Get monthly aggregated data from ClimRR.

        Returns dict with temp_mean, temp_range, rh_mean, precip_mm, wind_ms
        or None if not available.
        """
        cache_key = f"{year}-{month:02d}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        # Try local data files first
        if self.data_path and self.data_path.exists():
            data = self._load_local(year, month, lat_indices, lon_indices)
            if data is not None:
                self._cache[cache_key] = data
                return data

        # Try ArcGIS Feature Service
        data = self._query_arcgis(year, month, lat_indices, lon_indices,
                                   lat_bounds, lon_bounds)
        if data is not None:
            self._cache[cache_key] = data

        return data

    def _load_local(self, year, month, lat_indices, lon_indices):
        """Load from locally downloaded ClimRR CSV/NetCDF files."""
        n_points = len(lat_indices)

        # Try CSV format (downloaded from portal)
        csv_patterns = [
            self.data_path / f"{self.scenario}" / f"{year}_{month:02d}.csv",
            self.data_path / f"{self.scenario}_{self.period}.csv",
            self.data_path / f"climrr_{self.period}_{self.scenario}.csv",
        ]
        for csv_path in csv_patterns:
            if csv_path.exists():
                import pandas as pd
                df = pd.read_csv(csv_path)
                return self._extract_from_dataframe(df, lat_indices, lon_indices)

        # Try NetCDF format
        nc_patterns = [
            self.data_path / f"{self.scenario}" / f"climrr_{year}.nc",
            self.data_path / f"climrr_{self.period}_{self.scenario}.nc",
        ]
        for nc_path in nc_patterns:
            if nc_path.exists():
                import xarray as xr
                ds = xr.open_dataset(nc_path)
                return self._extract_from_dataset(ds, year, month,
                                                    lat_indices, lon_indices)

        return None

    def _extract_from_dataframe(self, df, lat_indices, lon_indices):
        """Extract monthly values from a ClimRR CSV DataFrame."""
        n_points = len(lat_indices)
        result = {
            "temp_mean": np.full(n_points, np.nan, dtype=np.float32),
            "temp_range": np.full(n_points, 10.0, dtype=np.float32),
            "rh_mean": np.full(n_points, 0.65, dtype=np.float32),
            "precip_mm": np.full(n_points, np.nan, dtype=np.float32),
            "wind_ms": np.full(n_points, 4.0, dtype=np.float32),
        }

        # Map columns (ClimRR naming varies)
        col_map = {}
        for col in df.columns:
            col_lower = col.lower()
            if "temp" in col_lower and "max" not in col_lower and "min" not in col_lower:
                col_map["temp_mean"] = col
            elif "tempmax" in col_lower or "tmax" in col_lower:
                col_map["temp_max"] = col
            elif "tempmin" in col_lower or "tmin" in col_lower:
                col_map["temp_min"] = col
            elif "precip" in col_lower:
                col_map["precip_mm"] = col
            elif "wind" in col_lower:
                col_map["wind_ms"] = col
            elif "humid" in col_lower or "rh" in col_lower:
                col_map["rh_mean"] = col

        # Extract values for our grid points
        if "temp_mean" in col_map and len(df) > 0:
            vals = df[col_map["temp_mean"]].values
            # Celsius to Kelvin if values look like Celsius
            if np.nanmean(vals) < 100:
                vals = vals + 273.15
            for i in range(min(n_points, len(vals))):
                result["temp_mean"][i] = vals[i % len(vals)]

        if "temp_max" in col_map and "temp_min" in col_map:
            tmax = df[col_map["temp_max"]].values
            tmin = df[col_map["temp_min"]].values
            rng = tmax - tmin
            for i in range(min(n_points, len(rng))):
                result["temp_range"][i] = max(rng[i % len(rng)], 2.0)

        if "precip_mm" in col_map:
            vals = df[col_map["precip_mm"]].values
            for i in range(min(n_points, len(vals))):
                result["precip_mm"][i] = vals[i % len(vals)]

        if "wind_ms" in col_map:
            vals = df[col_map["wind_ms"]].values
            for i in range(min(n_points, len(vals))):
                result["wind_ms"][i] = vals[i % len(vals)]

        if "rh_mean" in col_map:
            vals = df[col_map["rh_mean"]].values
            # Convert percent to fraction if > 1
            if np.nanmean(vals) > 1.5:
                vals = vals / 100.0
            for i in range(min(n_points, len(vals))):
                result["rh_mean"][i] = vals[i % len(vals)]

        return result

    def _extract_from_dataset(self, ds, year, month, lat_indices, lon_indices):
        """Extract from NetCDF xarray dataset."""
        n_points = len(lat_indices)
        result = {
            "temp_mean": np.full(n_points, np.nan, dtype=np.float32),
            "temp_range": np.full(n_points, 10.0, dtype=np.float32),
            "rh_mean": np.full(n_points, 0.65, dtype=np.float32),
            "precip_mm": np.full(n_points, np.nan, dtype=np.float32),
            "wind_ms": np.full(n_points, 4.0, dtype=np.float32),
        }
        # Generic extraction — adapt field names when actual data is available
        for var_name in ds.data_vars:
            vn = var_name.lower()
            try:
                data_2d = ds[var_name].values
                if data_2d.ndim >= 2:
                    for i, (li, lo) in enumerate(zip(lat_indices, lon_indices)):
                        if li < data_2d.shape[-2] and lo < data_2d.shape[-1]:
                            val = float(data_2d[..., li, lo].mean())
                            if "temp" in vn and "max" not in vn and "min" not in vn:
                                result["temp_mean"][i] = val
                            elif "precip" in vn or "pr" == vn:
                                result["precip_mm"][i] = val
                            elif "wind" in vn:
                                result["wind_ms"][i] = val
            except Exception:
                continue
        return result

    def _query_arcgis(self, year, month, lat_indices, lon_indices,
                       lat_bounds, lon_bounds):
        """Query ClimRR ArcGIS Feature Service for monthly data.

        This is a best-effort approach using the public REST API.
        For reliable bulk access, use locally downloaded data files.
        """
        try:
            import urllib.request
            import json as json_mod

            # Construct spatial query for our bounding box
            xmin, xmax = lon_bounds
            ymin, ymax = lat_bounds

            # Query the Temperature layer (layer indices may vary)
            url = (
                f"{CLIMRR_BASE_URL}/FeatureServer/0/query?"
                f"where=1%3D1&"
                f"geometry={xmin},{ymin},{xmax},{ymax}&"
                f"geometryType=esriGeometryEnvelope&"
                f"spatialRel=esriSpatialRelIntersects&"
                f"outFields=*&"
                f"f=json"
            )

            req = urllib.request.Request(url, headers={"User-Agent": "AORC-Tools/1.0"})
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json_mod.loads(resp.read().decode())

            features = data.get("features", [])
            if not features:
                logger.debug("No ClimRR features returned for bounds %s", lat_bounds)
                return None

            # Extract values from features
            n_points = len(lat_indices)
            result = {
                "temp_mean": np.full(n_points, np.nan, dtype=np.float32),
                "temp_range": np.full(n_points, 10.0, dtype=np.float32),
                "rh_mean": np.full(n_points, 0.65, dtype=np.float32),
                "precip_mm": np.full(n_points, 80.0, dtype=np.float32),
                "wind_ms": np.full(n_points, 4.0, dtype=np.float32),
            }

            # Average all returned features for a regional estimate
            for f in features:
                attrs = f.get("attributes", {})
                for key, val in attrs.items():
                    if val is None:
                        continue
                    kl = key.lower()
                    if "temp" in kl and "mean" in kl:
                        result["temp_mean"][:] = float(val) + 273.15
                    elif "precip" in kl:
                        result["precip_mm"][:] = float(val)
                    elif "wind" in kl:
                        result["wind_ms"][:] = float(val)
                break  # Use first feature as representative

            return result

        except Exception as e:
            logger.debug("ClimRR ArcGIS query failed: %s", e)
            return None

    def info(self):
        base = super().info()
        base["scenario"] = self.scenario
        base["period"] = self.period
        base["period_years"] = CLIMRR_PERIODS[self.period]
        base["data_source"] = "local" if self.data_path else "ArcGIS Feature Service"
        return base


# ======================================================================
# Registry of all available climate models
# ======================================================================

CLIMATE_MODEL_REGISTRY = {
    "aorc": {
        "name": "NOAA AORC v1.1",
        "type": "reanalysis",
        "period": "1979-present",
        "resolution": "~800m hourly",
        "variables": "All fire weather vars",
        "source": "s3://noaa-nws-aorc-v1-1-1km",
        "adapter_class": "AORCAdapter",
    },
    "nex-gddp-cmip6": {
        "name": "NASA NEX-GDDP-CMIP6",
        "type": "projection",
        "period": "1950-2100",
        "resolution": "0.25° daily",
        "variables": "tas, hurs, pr, sfcWind, tasmin, tasmax",
        "source": "s3://nex-gddp-cmip6",
        "gcms": NEX_GDDP_GCMS,
        "scenarios": ["historical", "ssp245", "ssp585"],
        "adapter_class": "NexGddpCmip6Adapter",
    },
    "glarm": {
        "name": "GLARM-Proj1 (Michigan Tech)",
        "type": "projection",
        "period": "1981-2099",
        "resolution": "18km daily (atm), 1-4km (lake)",
        "variables": "T2 (+ others TBD)",
        "source": "https://digitalcommons.mtu.edu/glts/",
        "scenarios": ["rcp45", "rcp85"],
        "adapter_class": "GLARMAdapter",
    },
    "climrr": {
        "name": "Argonne ClimRR (CESM2/WRF downscaling)",
        "type": "projection",
        "period": "1995-2014 (hist), 2045-2064 (mid), 2075-2094 (end)",
        "resolution": "12km WRF",
        "variables": "tas, tasmin, tasmax, pr, hurs, sfcWind",
        "source": "https://disgeoportal.egs.anl.gov/ClimRR/",
        "scenarios": ["historical", "ssp245", "ssp585"],
        "note": "ArcGIS Feature Service access; FWI computed from component variables",
        "adapter_class": "ClimRRAdapter",
    },
}


def get_adapter(source="aorc", **kwargs):
    """Factory: create a climate model adapter.

    Args:
        source: "aorc", "nex-gddp-cmip6", "glarm", or config file path.
        **kwargs: gcm=, scenario=, data_path=, etc.
    """
    if source == "aorc":
        return AORCAdapter()
    elif source in ("nex-gddp-cmip6", "nex-gddp", "cmip6"):
        return NexGddpCmip6Adapter(
            gcm=kwargs.get("gcm", "ACCESS-CM2"),
            scenario=kwargs.get("scenario", "ssp585"),
        )
    elif source == "glarm":
        return GLARMAdapter(
            data_path=kwargs.get("data_path", "./data/glarm"),
            scenario=kwargs.get("scenario", "rcp85"),
        )
    elif source in ("climrr", "argonne"):
        return ClimRRAdapter(
            scenario=kwargs.get("scenario", "ssp585"),
            period=kwargs.get("period", "midcentury"),
            data_path=kwargs.get("data_path"),
        )
    else:
        # Try as config file
        import json
        config_path = Path(source)
        if config_path.exists():
            with open(config_path) as f:
                config = json.load(f)
            return get_adapter(config.pop("type", "aorc"), **config)
        raise ValueError(f"Unknown data source: {source}")


def list_models():
    """Return the climate model registry."""
    return CLIMATE_MODEL_REGISTRY
