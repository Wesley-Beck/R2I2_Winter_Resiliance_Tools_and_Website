"""
Snow–fire danger correlation analysis.

Correlates gridded snow data (NetCDF) with fire danger index time series
to test whether snowmelt timing and rate predict wildfire ignition risk
in the Western Upper Peninsula.

Requires: xarray (lazy import), scipy, numpy.
"""

import logging
from datetime import datetime

import numpy as np
from scipy import stats

logger = logging.getLogger(__name__)

_SNOW_VAR_NAMES = [
    "SWE", "swe", "snow_water_equivalent",
    "SNOWDEPTH", "snowdepth", "snow_depth", "SNODAS_SWE",
    "snw", "SNW", "snowfall", "SNOW", "snow",
]

_COORD_NAMES_LAT = ["lat", "latitude", "y", "XLAT", "LATITUDE", "LAT"]
_COORD_NAMES_LON = ["lon", "longitude", "x", "XLONG", "LONGITUDE", "LON"]


def _find_name(ds, candidates, label):
    """Return the first matching name from candidates found in an xarray Dataset."""
    all_names = set(ds.dims) | set(ds.coords) | set(ds.data_vars)
    for name in candidates:
        if name in all_names:
            return name
    raise KeyError(
        f"Could not auto-detect {label} coordinate. "
        f"Tried {candidates}; dataset has {sorted(all_names)}"
    )


def load_snow_netcdf(filepath, variable=None, bbox=None):
    """Load snow data from a NetCDF file.

    Auto-detects the snow variable and coordinate names. Optionally subsets
    to a bounding box (dict with xmin/ymin/xmax/ymax in degrees).

    Returns:
        dict with keys: data (n_times, n_lat, n_lon), lats (1D), lons (1D),
        times (array of datetime.date), variable_name, units
    """
    import xarray as xr

    ds = xr.open_dataset(filepath)

    if variable is None:
        for name in _SNOW_VAR_NAMES:
            if name in ds.data_vars:
                variable = name
                break
        if variable is None:
            raise KeyError(
                f"No recognized snow variable in dataset. "
                f"Available: {list(ds.data_vars)}. "
                f"Pass variable= explicitly."
            )

    lat_name = _find_name(ds, _COORD_NAMES_LAT, "latitude")
    lon_name = _find_name(ds, _COORD_NAMES_LON, "longitude")

    lats = ds[lat_name].values.astype(np.float64)
    lons = ds[lon_name].values.astype(np.float64)

    if lats.ndim > 1:
        lats = lats[:, 0] if lats.shape[0] < lats.shape[1] else lats[0, :]
    if lons.ndim > 1:
        lons = lons[0, :] if lons.shape[1] > lons.shape[0] else lons[:, 0]

    # Ensure ascending order (some datasets store lat descending)
    lat_ascending = lats[0] < lats[-1] if len(lats) > 1 else True

    da = ds[variable]
    units = da.attrs.get("units", "unknown")

    # Subset to bounding box
    if bbox is not None:
        lat_mask = (lats >= bbox["ymin"]) & (lats <= bbox["ymax"])
        lon_mask = (lons >= bbox["xmin"]) & (lons <= bbox["xmax"])

        if not lat_mask.any() or not lon_mask.any():
            raise ValueError(
                f"Bounding box {bbox} does not overlap with data extent "
                f"(lat [{lats.min():.2f}, {lats.max():.2f}], "
                f"lon [{lons.min():.2f}, {lons.max():.2f}])"
            )

        da = da.isel(**{lat_name: lat_mask, lon_name: lon_mask})
        lats = lats[lat_mask]
        lons = lons[lon_mask]

    data = da.values.astype(np.float64)

    # Extract time coordinate
    time_name = None
    for candidate in ["time", "Time", "TIME", "t"]:
        if candidate in ds.dims or candidate in ds.coords:
            time_name = candidate
            break

    if time_name is not None:
        raw_times = ds[time_name].values
        times = _parse_times(raw_times)
        if data.ndim == 2:
            # Single time step — add time axis
            data = data[np.newaxis, :, :]
            times = np.array([times]) if not hasattr(times, '__len__') else times[:1]
    else:
        times = np.array([datetime.now().date()])
        if data.ndim == 2:
            data = data[np.newaxis, :, :]

    if not lat_ascending and data.shape[1] == len(lats):
        data = data[:, ::-1, :]
        lats = lats[::-1]

    ds.close()

    return {
        "data": data,
        "lats": lats,
        "lons": lons,
        "times": times,
        "variable_name": variable,
        "units": units,
    }


def _parse_times(raw_times):
    """Convert numpy datetime64 or cftime objects to datetime.date array."""
    import pandas as pd

    try:
        return np.array([pd.Timestamp(t).date() for t in raw_times])
    except Exception:
        return np.array([datetime.now().date() for _ in raw_times])


def regrid_snow_to_points(snow_data, point_lats, point_lons, method="nearest"):
    """Regrid snow NetCDF data onto the FDI point grid.

    For regular source grids uses scipy RegularGridInterpolator; for
    irregular grids falls back to cKDTree nearest-neighbor lookup.

    Args:
        snow_data: dict from load_snow_netcdf()
        point_lats: 1-D array of target latitudes (n_points,)
        point_lons: 1-D array of target longitudes (n_points,)
        method: "nearest" or "linear"

    Returns:
        np.ndarray of shape (n_times, n_points)
    """
    src_lats = snow_data["lats"]
    src_lons = snow_data["lons"]
    data = snow_data["data"]
    n_times = data.shape[0]
    n_points = len(point_lats)

    is_regular = _is_regular_grid(src_lats, src_lons)

    if is_regular:
        from scipy.interpolate import RegularGridInterpolator

        result = np.empty((n_times, n_points), dtype=np.float64)
        target_pts = np.column_stack([point_lats, point_lons])

        for t in range(n_times):
            interp = RegularGridInterpolator(
                (src_lats, src_lons), data[t],
                method=method, bounds_error=False, fill_value=np.nan,
            )
            result[t] = interp(target_pts)
    else:
        from scipy.spatial import cKDTree

        # Build KD-tree from source grid (flattened lat/lon pairs)
        if data.ndim == 3:
            src_lat_grid, src_lon_grid = np.meshgrid(src_lats, src_lons, indexing="ij")
        else:
            src_lat_grid = src_lats
            src_lon_grid = src_lons

        src_points = np.column_stack([src_lat_grid.ravel(), src_lon_grid.ravel()])
        tree = cKDTree(src_points)
        _, indices = tree.query(np.column_stack([point_lats, point_lons]))

        result = np.empty((n_times, n_points), dtype=np.float64)
        for t in range(n_times):
            flat = data[t].ravel()
            result[t] = flat[indices]

    return result


def _is_regular_grid(lats, lons, tol=1e-6):
    """Check whether 1-D coordinate arrays form a regular (uniform-spacing) grid."""
    if len(lats) < 2 or len(lons) < 2:
        return True
    dlat = np.diff(lats)
    dlon = np.diff(lons)
    return (np.ptp(dlat) < tol * np.abs(dlat[0] + 1e-30) and
            np.ptp(dlon) < tol * np.abs(dlon[0] + 1e-30))


def detect_snowmelt_date(snow_timeseries, dates, threshold_fraction=0.1):
    """Find the day-of-year when snow drops below a fraction of the seasonal max.

    For each spatial point, the snowmelt date is when the value first falls
    and stays below threshold_fraction * seasonal_max after the seasonal peak.

    Args:
        snow_timeseries: (n_times, n_points) array of SWE or snow depth
        dates: array of datetime.date objects (length n_times)
        threshold_fraction: fraction of seasonal max defining "melted" (default 0.1)

    Returns:
        snowmelt_doys: (n_points,) array of day-of-year values; NaN where
            the point had no snow or never melted
    """
    n_times, n_points = snow_timeseries.shape
    snowmelt_doys = np.full(n_points, np.nan)

    doys = np.array([d.timetuple().tm_yday for d in dates])
    # All-NaN columns (snow-free points) legitimately produce NaN here
    with np.errstate(all="ignore"):
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", category=RuntimeWarning)
            seasonal_max = np.nanmax(snow_timeseries, axis=0)

    # Points with negligible snow get NaN
    no_snow = (seasonal_max <= 0) | np.isnan(seasonal_max)
    thresholds = seasonal_max * threshold_fraction

    # nanargmax raises on all-NaN columns; fill them first (those points are
    # skipped via no_snow anyway, so the bogus index is never used)
    safe = np.where(np.isnan(snow_timeseries), -np.inf, snow_timeseries)
    peak_idx = np.argmax(safe, axis=0)

    for j in range(n_points):
        if no_snow[j]:
            continue

        post_peak = snow_timeseries[peak_idx[j]:, j]
        if len(post_peak) == 0:
            continue

        below = post_peak <= thresholds[j]
        where_below = np.where(below)[0]
        if len(where_below) == 0:
            continue

        melt_time_idx = peak_idx[j] + where_below[0]
        snowmelt_doys[j] = doys[melt_time_idx]

    return snowmelt_doys


def compute_snowmelt_fdi_lag(snowmelt_doys, fdi_onset_doys):
    """Compute the lag between snowmelt and fire season onset at each point.

    A positive lag means fire season starts after snowmelt (expected).
    A negative lag means fire season starts before snowmelt (unusual).

    Args:
        snowmelt_doys: (n_points,) day-of-year of snowmelt
        fdi_onset_doys: (n_points,) day-of-year of fire season onset

    Returns:
        lag_days: (n_points,) array; NaN where either input is NaN
    """
    snowmelt_doys = np.asarray(snowmelt_doys, dtype=np.float64)
    fdi_onset_doys = np.asarray(fdi_onset_doys, dtype=np.float64)
    return fdi_onset_doys - snowmelt_doys


def snowmelt_fdi_correlation(snow_regridded, fdi_data, dates_snow, dates_fdi):
    """Compute per-point correlation between snow change rate and FDI.

    Aligns the two datasets on their common date range, then computes
    Pearson and Spearman correlations between daily snow change (dSWE/dt)
    and daily FDI values.

    Args:
        snow_regridded: (n_times_snow, n_points) regridded snow values
        fdi_data: (n_times_fdi, n_points) FDI values
        dates_snow: array of datetime.date (length n_times_snow)
        dates_fdi: list of date strings "YYYY-MM-DD" (length n_times_fdi)

    Returns:
        dict with pearson_r, spearman_r, p_values_pearson, p_values_spearman
        — all arrays of shape (n_points,)
    """
    snow_date_set = {d: i for i, d in enumerate(dates_snow)}
    fdi_dates_parsed = [
        datetime.strptime(d[:10], "%Y-%m-%d").date() if isinstance(d, str) else d
        for d in dates_fdi
    ]
    fdi_date_set = {d: i for i, d in enumerate(fdi_dates_parsed)}

    common = sorted(set(snow_date_set) & set(fdi_date_set))
    if len(common) < 10:
        raise ValueError(
            f"Only {len(common)} overlapping dates between snow and FDI data; "
            f"need at least 10 for meaningful correlation."
        )

    snow_idx = np.array([snow_date_set[d] for d in common])
    fdi_idx = np.array([fdi_date_set[d] for d in common])

    snow_aligned = snow_regridded[snow_idx]
    fdi_aligned = fdi_data[fdi_idx]

    # Daily snow change (forward difference, first value dropped)
    snow_delta = np.diff(snow_aligned, axis=0)
    fdi_trimmed = fdi_aligned[1:]

    n_times, n_points = snow_delta.shape
    pearson_r = np.full(n_points, np.nan)
    spearman_r = np.full(n_points, np.nan)
    p_pearson = np.full(n_points, np.nan)
    p_spearman = np.full(n_points, np.nan)

    for j in range(n_points):
        s = snow_delta[:, j]
        f = fdi_trimmed[:, j]
        valid = ~(np.isnan(s) | np.isnan(f))
        if valid.sum() < 10:
            continue

        sv, fv = s[valid], f[valid]

        if np.std(sv) == 0 or np.std(fv) == 0:
            continue

        pr, pp = stats.pearsonr(sv, fv)
        sr, sp = stats.spearmanr(sv, fv)
        pearson_r[j] = pr
        spearman_r[j] = sr
        p_pearson[j] = pp
        p_spearman[j] = sp

    return {
        "pearson_r": pearson_r,
        "spearman_r": spearman_r,
        "p_values_pearson": p_pearson,
        "p_values_spearman": p_spearman,
    }


def annual_snowmelt_vs_fire_season(snow_data_by_year, fdi_data_by_year):
    """Compute year-by-year snowmelt and fire season metrics.

    Args:
        snow_data_by_year: dict mapping year → (dates, snow_array)
            where snow_array is (n_days, n_points) of SWE/depth
        fdi_data_by_year: dict mapping year → {
            "onset_days": (n_points,) onset day-of-year,
            "season_lengths": (n_points,) season length in days,
            "peak_fdi": (n_points,) peak FDI value (optional; computed from
                data if "data" key is present),
            "data": (n_days, n_points) FDI array (optional),
        }

    Returns:
        dict of lists (DataFrame-ready) with keys: year, snowmelt_date,
        fire_season_onset, lag, peak_fdi, season_length — each a list
        of per-year spatially-averaged values.
    """
    result = {
        "year": [],
        "snowmelt_date": [],
        "fire_season_onset": [],
        "lag": [],
        "peak_fdi": [],
        "season_length": [],
    }

    common_years = sorted(set(snow_data_by_year) & set(fdi_data_by_year))

    for year in common_years:
        snow_dates, snow_arr = snow_data_by_year[year]
        fdi_info = fdi_data_by_year[year]

        melt_doys = detect_snowmelt_date(snow_arr, snow_dates)
        onset_doys = fdi_info["onset_days"]
        lag = compute_snowmelt_fdi_lag(melt_doys, onset_doys)

        if "peak_fdi" in fdi_info:
            peak = fdi_info["peak_fdi"]
        elif "data" in fdi_info:
            peak = np.nanmax(fdi_info["data"], axis=0)
        else:
            peak = np.full_like(onset_doys, np.nan)

        result["year"].append(year)
        result["snowmelt_date"].append(float(np.nanmean(melt_doys)))
        result["fire_season_onset"].append(float(np.nanmean(onset_doys)))
        result["lag"].append(float(np.nanmean(lag)))
        result["peak_fdi"].append(float(np.nanmean(peak)))
        result["season_length"].append(float(np.nanmean(fdi_info["season_lengths"])))

    return result


def snow_fdi_cross_correlation(snow_spatial_mean, fdi_spatial_mean, max_lag_days=90):
    """Cross-correlation between spatially-averaged snow and FDI time series.

    Slides the FDI series relative to snow from -max_lag_days to
    +max_lag_days and computes Pearson r at each offset.

    Args:
        snow_spatial_mean: 1-D array of daily spatially-averaged snow values
        fdi_spatial_mean: 1-D array of daily spatially-averaged FDI values
            (must be same length as snow_spatial_mean)
        max_lag_days: maximum lag to test in either direction (default 90)

    Returns:
        dict with lags (array), correlations (array), optimal_lag (int),
        optimal_r (float)
    """
    snow = np.asarray(snow_spatial_mean, dtype=np.float64)
    fdi = np.asarray(fdi_spatial_mean, dtype=np.float64)

    if len(snow) != len(fdi):
        raise ValueError(
            f"snow and fdi must have same length; got {len(snow)} vs {len(fdi)}"
        )

    n = len(snow)
    lags = np.arange(-max_lag_days, max_lag_days + 1)
    correlations = np.full(len(lags), np.nan)

    for i, lag in enumerate(lags):
        if lag >= 0:
            s = snow[:n - lag] if lag > 0 else snow
            f = fdi[lag:] if lag > 0 else fdi
        else:
            s = snow[-lag:]
            f = fdi[:n + lag]

        valid = ~(np.isnan(s) | np.isnan(f))
        if valid.sum() < 10:
            continue

        sv, fv = s[valid], f[valid]
        if np.std(sv) == 0 or np.std(fv) == 0:
            continue

        correlations[i], _ = stats.pearsonr(sv, fv)

    # Optimal lag = highest absolute correlation
    abs_corr = np.abs(correlations)
    valid_mask = ~np.isnan(abs_corr)
    if valid_mask.any():
        best_idx = np.nanargmax(abs_corr)
        optimal_lag = int(lags[best_idx])
        optimal_r = float(correlations[best_idx])
    else:
        optimal_lag = 0
        optimal_r = np.nan

    return {
        "lags": lags,
        "correlations": correlations,
        "optimal_lag": optimal_lag,
        "optimal_r": optimal_r,
    }


def snowmelt_rate_vs_fdi_severity(snow_regridded, fdi_data, dates, variable="FDI"):
    """Test whether faster snowmelt predicts more severe fire conditions.

    Bins points by snowmelt rate (fast / medium / slow terciles) and
    compares the distribution of peak FDI values across bins.

    Args:
        snow_regridded: (n_times, n_points) regridded snow values
        fdi_data: (n_times, n_points) FDI values (same time axis)
        dates: array of datetime.date objects (length n_times)
        variable: FDI variable name (for labeling only)

    Returns:
        dict with:
            bins: ["fast", "medium", "slow"]
            bin_edges: (2,) array of tercile boundaries for melt rate
            peak_fdi_by_bin: dict mapping bin name → array of peak FDI values
            mean_fdi_by_bin: dict mapping bin name → float
            kruskal_statistic: Kruskal-Wallis H statistic across bins
            kruskal_p: p-value for the Kruskal-Wallis test
            variable: the FDI variable name
    """
    n_times, n_points = snow_regridded.shape

    # Snowmelt rate = magnitude of maximum daily snow decrease per point
    snow_diff = np.diff(snow_regridded, axis=0)
    # Most negative daily change = fastest melt (use negative so "fast" = large magnitude)
    melt_rate = np.nanmin(snow_diff, axis=0)  # most negative value per point
    melt_rate_mag = -melt_rate  # positive magnitude; larger = faster melt

    peak_fdi = np.nanmax(fdi_data, axis=0)

    # Exclude points with no snow or no valid FDI
    valid = ~(np.isnan(melt_rate_mag) | np.isnan(peak_fdi) | (melt_rate_mag <= 0))
    if valid.sum() < 9:
        raise ValueError(
            f"Too few valid points ({valid.sum()}) for tercile analysis."
        )

    melt_valid = melt_rate_mag[valid]
    fdi_valid = peak_fdi[valid]

    t33, t67 = np.percentile(melt_valid, [33.33, 66.67])

    slow_mask = melt_valid <= t33
    med_mask = (melt_valid > t33) & (melt_valid <= t67)
    fast_mask = melt_valid > t67

    bins = ["fast", "medium", "slow"]
    masks = {"fast": fast_mask, "medium": med_mask, "slow": slow_mask}

    peak_fdi_by_bin = {b: fdi_valid[masks[b]] for b in bins}
    mean_fdi_by_bin = {b: float(np.nanmean(peak_fdi_by_bin[b]))
                       if len(peak_fdi_by_bin[b]) > 0 else np.nan
                       for b in bins}

    groups = [peak_fdi_by_bin[b] for b in bins if len(peak_fdi_by_bin[b]) > 0]
    if len(groups) >= 2:
        h_stat, h_p = stats.kruskal(*groups)
    else:
        h_stat, h_p = np.nan, np.nan

    return {
        "bins": bins,
        "bin_edges": np.array([t33, t67]),
        "peak_fdi_by_bin": peak_fdi_by_bin,
        "mean_fdi_by_bin": mean_fdi_by_bin,
        "kruskal_statistic": float(h_stat),
        "kruskal_p": float(h_p),
        "variable": variable,
    }
