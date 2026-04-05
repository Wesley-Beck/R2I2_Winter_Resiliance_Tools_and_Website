"""
AORC S3/ZARR data access layer.

Ported from the existing aorc_data_loader.py with the following changes:
- get_hourly_data() returns RAW AORC values (no unit conversions)
- Removed convert_aorc_to_fire_weather() (conversions now in climate_convert.py)
- Added coordinate caching to ~/.aorc_cache/
- Kept the proven multi-method S3 fallback approach

The 5 fallback methods for S3 access are preserved exactly from the
original code since they handle various AWS access configurations.
"""

import os
import logging
from pathlib import Path

import numpy as np

logger = logging.getLogger(__name__)

# Cache directory for AORC coordinates
CACHE_DIR = Path.home() / ".aorc_cache"


class AORCDataLoader:
    """Load hourly AORC data from the NOAA S3 bucket.

    Uses ZARR format via multiple fallback S3 access methods.
    Returns raw AORC values with no unit conversions applied.

    Ported from existing aorc_data_loader.py — same bucket, same
    fallback methods, proven to work with the NOAA AORC archive.
    """

    BUCKET = "noaa-nws-aorc-v1-1-1km"

    # AORC variable names to extract
    VARIABLES = [
        "TMP_2maboveground",
        "SPFH_2maboveground",
        "PRES_surface",
        "UGRD_10maboveground",
        "VGRD_10maboveground",
        "APCP_surface",
        "DSWRF_surface",
        "DLWRF_surface",
    ]

    def __init__(self):
        self._ds_cache = {}  # year → xarray Dataset
        self._coords = None  # cached lat/lon arrays

    # ------------------------------------------------------------------
    # S3 Dataset Access (5 fallback methods from existing code)
    # ------------------------------------------------------------------

    def _open_dataset(self, year):
        """Open AORC ZARR dataset for a given year, trying 5 methods.

        Ported directly from existing aorc_data_loader.py — these
        fallback methods handle different AWS SDK configurations and
        are proven to work in production.
        """
        if year in self._ds_cache:
            return self._ds_cache[year]

        zarr_path = f"{self.BUCKET}/{year}.zarr"
        ds = None
        errors = []

        # Method 1: fsspec mapper (most common)
        try:
            import fsspec
            mapper = fsspec.get_mapper(
                f"s3://{zarr_path}",
                anon=True,
                default_fill_cache=False,
            )
            import xarray as xr
            ds = xr.open_zarr(mapper, consolidated=True)
            logger.info("AORC %d opened via fsspec mapper", year)
        except Exception as e:
            errors.append(f"Method 1 (fsspec): {e}")

        # Method 2: S3Map
        if ds is None:
            try:
                import s3fs
                import xarray as xr
                s3 = s3fs.S3FileSystem(anon=True)
                store = s3fs.S3Map(root=f"s3://{zarr_path}", s3=s3)
                ds = xr.open_zarr(store, consolidated=True)
                logger.info("AORC %d opened via S3Map", year)
            except Exception as e:
                errors.append(f"Method 2 (S3Map): {e}")

        # Method 3: Direct URL
        if ds is None:
            try:
                import xarray as xr
                url = f"https://{self.BUCKET}.s3.amazonaws.com/{year}.zarr"
                ds = xr.open_zarr(url, consolidated=True)
                logger.info("AORC %d opened via direct URL", year)
            except Exception as e:
                errors.append(f"Method 3 (URL): {e}")

        # Method 4: open_dataset with engine='zarr'
        if ds is None:
            try:
                import xarray as xr
                ds = xr.open_dataset(
                    f"s3://{zarr_path}",
                    engine="zarr",
                    backend_kwargs={"storage_options": {"anon": True}},
                )
                logger.info("AORC %d opened via open_dataset", year)
            except Exception as e:
                errors.append(f"Method 4 (open_dataset): {e}")

        # Method 5: Non-consolidated zarr
        if ds is None:
            try:
                import fsspec
                import xarray as xr
                mapper = fsspec.get_mapper(
                    f"s3://{zarr_path}",
                    anon=True,
                )
                ds = xr.open_zarr(mapper, consolidated=False)
                logger.info("AORC %d opened via non-consolidated zarr", year)
            except Exception as e:
                errors.append(f"Method 5 (non-consolidated): {e}")

        if ds is None:
            raise ConnectionError(
                f"Failed to open AORC dataset for {year}. "
                f"All 5 methods failed:\n" + "\n".join(errors)
            )

        self._ds_cache[year] = ds
        return ds

    # ------------------------------------------------------------------
    # Coordinate Access
    # ------------------------------------------------------------------

    def get_coordinates(self, year=2020):
        """Get AORC latitude and longitude 1D arrays.

        Caches to ~/.aorc_cache/coordinates.npz for fast subsequent access.

        Args:
            year: Any valid AORC year (just used to access the dataset
                  for coordinate extraction).

        Returns:
            (lats, lons): 1D numpy arrays of latitude and longitude values.
        """
        if self._coords is not None:
            return self._coords

        # Try cache first
        cache_file = CACHE_DIR / "coordinates.npz"
        if cache_file.exists():
            data = np.load(cache_file)
            self._coords = (data["lats"], data["lons"])
            logger.info("Loaded coordinates from cache (%d lats, %d lons)",
                        len(self._coords[0]), len(self._coords[1]))
            return self._coords

        # Fetch from AORC
        ds = self._open_dataset(year)
        lats = ds.latitude.values
        lons = ds.longitude.values

        # Cache locally
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        np.savez(cache_file, lats=lats, lons=lons)
        logger.info("Cached AORC coordinates (%d lats, %d lons)", len(lats), len(lons))

        self._coords = (lats, lons)
        return self._coords

    def get_coordinate_indices(self, target_lats, target_lons, year=2020):
        """Find the nearest AORC grid indices for given lat/lon points.

        Args:
            target_lats: Array of target latitudes.
            target_lons: Array of target longitudes.
            year: AORC year for coordinate lookup.

        Returns:
            (lat_indices, lon_indices): Arrays of integer indices into the
            AORC grid. Use with .isel(latitude=lat_idx, longitude=lon_idx).
        """
        lats, lons = self.get_coordinates(year)
        target_lats = np.asarray(target_lats)
        target_lons = np.asarray(target_lons)

        lat_indices = np.abs(lats[:, None] - target_lats[None, :]).argmin(axis=0)
        lon_indices = np.abs(lons[:, None] - target_lons[None, :]).argmin(axis=0)

        return lat_indices, lon_indices

    # ------------------------------------------------------------------
    # Hourly Data Extraction
    # ------------------------------------------------------------------

    def get_hourly_data(self, year, month, day, hour, lat_bounds=None, lon_bounds=None):
        """Extract one hour of AORC data for a geographic region.

        Returns RAW AORC values — no unit conversions applied.
        Units: TMP=K, SPFH=kg/kg, PRES=Pa, U/VGRD=m/s, APCP=mm, xSWRF=W/m².

        Ported from existing aorc_data_loader.py with the double-conversion
        issue fixed (conversions now handled by climate_convert.py).

        Args:
            year: Year (int).
            month: Month (int, 1-12).
            day: Day (int, 1-31).
            hour: Hour (int, 0-23).
            lat_bounds: Optional (lat_min, lat_max) tuple for subsetting.
            lon_bounds: Optional (lon_min, lon_max) tuple for subsetting.

        Returns:
            dict: Variable name → 2D numpy array (lat × lon), raw AORC units.
        """
        import pandas as pd

        ds = self._open_dataset(year)
        timestamp = pd.Timestamp(year, month, day, hour)

        # Select the time step
        hourly = ds.sel(time=timestamp, method="nearest")

        # Optionally subset by geographic bounds
        if lat_bounds is not None:
            hourly = hourly.sel(
                latitude=slice(lat_bounds[0], lat_bounds[1])
            )
        if lon_bounds is not None:
            hourly = hourly.sel(
                longitude=slice(lon_bounds[0], lon_bounds[1])
            )

        # Extract raw values for each variable
        result = {}
        for var in self.VARIABLES:
            if var in hourly:
                result[var] = hourly[var].values
            else:
                logger.warning("Variable %s not found in AORC for %s", var, timestamp)

        return result

    def get_hourly_point_values(self, year, month, day, hour, lat_indices, lon_indices):
        """Extract one hour of AORC data at specific grid point indices.

        Faster than get_hourly_data() for point-based extraction since it
        uses .isel() instead of geographic subsetting.

        Args:
            year, month, day, hour: Timestamp components.
            lat_indices: Array of latitude indices (from get_coordinate_indices).
            lon_indices: Array of longitude indices.

        Returns:
            dict: Variable name → 1D numpy array (one value per point), raw units.
        """
        import pandas as pd

        ds = self._open_dataset(year)
        timestamp = pd.Timestamp(year, month, day, hour)

        hourly = ds.sel(time=timestamp, method="nearest")

        result = {}
        for var in self.VARIABLES:
            if var in hourly:
                data = hourly[var].values
                # Extract values at each point index
                result[var] = data[lat_indices, lon_indices]
            else:
                logger.warning("Variable %s not found for %s", var, timestamp)

        return result
