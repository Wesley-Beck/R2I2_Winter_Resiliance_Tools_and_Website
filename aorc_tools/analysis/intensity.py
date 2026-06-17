"""
Wildfire intensity analysis — magnitude and frequency of extreme fire danger.

Answers: "How big could fires potentially get and how far could they spread?"

Methods:
1. Severity classification into standard FDI risk tiers
2. Severity frequency mapping per spatial point
3. Annual severity distribution tracking
4. Extreme event cataloging (consecutive-day episodes)
5. Return period analysis via GEV distribution
6. Intensity-duration-frequency curves
7. Spatial severity summary for per-point risk profiles
"""

from datetime import datetime

import numpy as np
from scipy.stats import genextreme

SEVERITY_LEVELS = {
    "FWI": {"Low": (0, 5), "Moderate": (5, 10), "High": (10, 20), "Very High": (20, 30), "Extreme": (30, float("inf"))},
    "ISI": {"Low": (0, 2), "Moderate": (2, 5), "High": (5, 10), "Very High": (10, 20), "Extreme": (20, float("inf"))},
    "BUI": {"Low": (0, 20), "Moderate": (20, 40), "High": (40, 80), "Very High": (80, 120), "Extreme": (120, float("inf"))},
    "ERC": {"Low": (0, 15), "Moderate": (15, 30), "High": (30, 50), "Very High": (50, 80), "Extreme": (80, float("inf"))},
    "BI": {"Low": (0, 20), "Moderate": (20, 40), "High": (40, 60), "Very High": (60, 80), "Extreme": (80, float("inf"))},
    "SC": {"Low": (0, 2), "Moderate": (2, 4), "High": (4, 6), "Very High": (6, 8), "Extreme": (8, float("inf"))},
    "FPI": {"Low": (0, 20), "Moderate": (20, 40), "High": (40, 60), "Very High": (60, 80), "Extreme": (80, float("inf"))},
}

SEVERITY_COLORS = {
    "Low": "#2ca02c",
    "Moderate": "#ffdd57",
    "High": "#ff7f0e",
    "Very High": "#d62728",
    "Extreme": "#7b2d26",
}

SEVERITY_ORDER = ["Low", "Moderate", "High", "Very High", "Extreme"]


def classify_severity(values, variable):
    """Classify FDI values into severity levels.

    Args:
        values: array-like of FDI values (any shape)
        variable: FDI variable name (must be a key in SEVERITY_LEVELS)

    Returns:
        labels: np.ndarray of same shape, dtype object, containing severity
            level strings
    """
    values = np.asarray(values, dtype=np.float64)
    levels = SEVERITY_LEVELS[variable]
    labels = np.empty(values.shape, dtype=object)
    labels[:] = "Low"

    # Apply in ascending order so higher levels overwrite lower ones
    for level_name in SEVERITY_ORDER:
        lo, hi = levels[level_name]
        mask = (values >= lo) & (values < hi)
        labels[mask] = level_name

    return labels


def severity_frequency(data, variable):
    """Compute the fraction of days each spatial point spends at each severity level.

    Args:
        data: np.ndarray of shape (n_days, n_points)
        variable: FDI variable name

    Returns:
        dict mapping level_name -> array of shape (n_points,) with values 0-1
    """
    levels = SEVERITY_LEVELS[variable]
    valid_mask = ~np.isnan(data)
    valid_counts = np.sum(valid_mask, axis=0).astype(np.float64)
    valid_counts[valid_counts == 0] = 1.0

    result = {}
    for level_name in SEVERITY_ORDER:
        lo, hi = levels[level_name]
        in_level = (data >= lo) & (data < hi) & valid_mask
        result[level_name] = np.sum(in_level, axis=0).astype(np.float64) / valid_counts

    return result


def annual_severity_distribution(data, dates, variable):
    """Group by year and compute severity distribution per year.

    Args:
        data: np.ndarray of shape (n_days, n_points)
        dates: list of date strings "YYYY-MM-DD"
        variable: FDI variable name

    Returns:
        dict mapping year (int) -> {level_name: fraction} where fraction is
            the spatially-averaged fraction of days at that level
    """
    years = np.array([int(d[:4]) for d in dates])
    unique_years = np.unique(years)

    result = {}
    for year in unique_years:
        year_mask = years == year
        year_data = data[year_mask]

        spatial_mean = np.nanmean(year_data, axis=1)
        valid = ~np.isnan(spatial_mean)
        n_valid = np.sum(valid)
        if n_valid == 0:
            result[int(year)] = {level: 0.0 for level in SEVERITY_ORDER}
            continue

        levels = SEVERITY_LEVELS[variable]
        dist = {}
        for level_name in SEVERITY_ORDER:
            lo, hi = levels[level_name]
            in_level = (spatial_mean >= lo) & (spatial_mean < hi) & valid
            dist[level_name] = float(np.sum(in_level)) / float(n_valid)
        result[int(year)] = dist

    return result


def extreme_event_catalog(data, dates, variable, threshold_percentile=95):
    """Identify discrete extreme events as consecutive days above a threshold.

    An event is a contiguous block of days where the spatial-mean FDI
    exceeds the threshold percentile. Events are characterized by their
    duration, peak intensity, and spatial extent.

    Args:
        data: np.ndarray of shape (n_days, n_points)
        dates: list of date strings "YYYY-MM-DD"
        variable: FDI variable name
        threshold_percentile: percentile of the spatial-mean time series
            used as the event threshold (default 95)

    Returns:
        list of dicts, each with:
            start_date: str
            end_date: str
            duration: int (days)
            peak_value: float
            peak_date: str
            spatial_extent: float (fraction of points above threshold on peak day)
            mean_intensity: float (mean spatial-mean value during the event)
    """
    spatial_mean = np.nanmean(data, axis=1)
    threshold = np.nanpercentile(spatial_mean, threshold_percentile)

    above = spatial_mean >= threshold
    runs = _extract_runs(above)

    events = []
    for start_idx, end_idx in runs:
        event_values = spatial_mean[start_idx:end_idx]
        peak_offset = np.argmax(event_values)
        peak_day_idx = start_idx + peak_offset

        # Spatial extent: fraction of points above threshold on the peak day
        peak_day_data = data[peak_day_idx]
        valid_points = ~np.isnan(peak_day_data)
        n_valid = np.sum(valid_points)
        if n_valid > 0:
            spatial_extent = float(np.sum(peak_day_data[valid_points] >= threshold)) / float(n_valid)
        else:
            spatial_extent = 0.0

        events.append({
            "start_date": dates[start_idx],
            "end_date": dates[end_idx - 1],
            "duration": end_idx - start_idx,
            "peak_value": float(event_values[peak_offset]),
            "peak_date": dates[peak_day_idx],
            "spatial_extent": spatial_extent,
            "mean_intensity": float(np.mean(event_values)),
        })

    return events


def return_period_analysis(data, dates, variable):
    """Compute return periods for extreme values using annual maxima and GEV.

    Fits a Generalized Extreme Value distribution to the series of annual
    maxima of the spatial-mean daily values.

    Args:
        data: np.ndarray of shape (n_days, n_points)
        dates: list of date strings "YYYY-MM-DD"
        variable: FDI variable name

    Returns:
        dict with:
            return_periods: 1-D array of return periods in years
            return_levels: 1-D array of corresponding FDI values
            annual_maxima: 1-D array of observed annual max values
            gev_params: dict with "shape", "loc", "scale"
    """
    spatial_mean = np.nanmean(data, axis=1)
    years = np.array([int(d[:4]) for d in dates])
    unique_years = np.unique(years)

    annual_maxima = np.array([
        np.nanmax(spatial_mean[years == yr]) for yr in unique_years
    ])

    # Fit GEV to annual maxima
    shape, loc, scale = genextreme.fit(annual_maxima)

    return_periods = np.array([2, 5, 10, 25, 50, 100], dtype=np.float64)
    # Return level for period T: quantile at probability 1 - 1/T
    exceedance_prob = 1.0 / return_periods
    return_levels = genextreme.isf(exceedance_prob, shape, loc=loc, scale=scale)

    return {
        "return_periods": return_periods,
        "return_levels": return_levels,
        "annual_maxima": annual_maxima,
        "gev_params": {"shape": float(shape), "loc": float(loc), "scale": float(scale)},
    }


def intensity_duration_frequency(data, dates, variable, durations=None):
    """Compute maximum rolling-average intensity for multiple duration windows.

    For each duration, computes a rolling mean of the spatial-mean time
    series, then extracts annual maxima of that rolling mean.

    Args:
        data: np.ndarray of shape (n_days, n_points)
        dates: list of date strings "YYYY-MM-DD"
        variable: FDI variable name
        durations: list of window sizes in days (default [1, 3, 7, 14, 30])

    Returns:
        dict mapping duration (int) -> 1-D array of annual maxima of the
            rolling-mean spatial-mean time series
    """
    if durations is None:
        durations = [1, 3, 7, 14, 30]

    spatial_mean = np.nanmean(data, axis=1)
    years = np.array([int(d[:4]) for d in dates])
    unique_years = np.unique(years)

    result = {}
    for dur in durations:
        if dur == 1:
            rolling = spatial_mean.copy()
        else:
            kernel = np.ones(dur) / dur
            rolling = np.convolve(spatial_mean, kernel, mode="same")

        annual_max = np.array([
            np.nanmax(rolling[years == yr]) for yr in unique_years
        ])
        result[dur] = annual_max

    return result


def spatial_severity_summary(data, variable):
    """Per-point severity profile and worst-case characterization.

    Args:
        data: np.ndarray of shape (n_days, n_points)
        variable: FDI variable name

    Returns:
        dict suitable for DataFrame construction, with keys:
            Low, Moderate, High, Very High, Extreme: fraction of time at each level
            max_value: maximum observed value per point
            percentile_rank: each point's max value ranked among all points (0-100)
    """
    freq = severity_frequency(data, variable)

    point_max = np.nanmax(data, axis=0)

    # Percentile rank: what fraction of points have a lower max value
    n_points = len(point_max)
    ranks = np.empty(n_points, dtype=np.float64)
    sorted_indices = np.argsort(point_max)
    ranks[sorted_indices] = np.linspace(0, 100, n_points)

    result = {}
    for level_name in SEVERITY_ORDER:
        result[level_name] = freq[level_name]
    result["max_value"] = point_max
    result["percentile_rank"] = ranks

    return result


def _extract_runs(mask):
    """Extract runs of True values from a boolean array.

    Returns list of (start, end) where end is exclusive.
    """
    if len(mask) == 0:
        return []

    diff = np.diff(mask.astype(np.int8))
    starts = np.where(diff == 1)[0] + 1
    ends = np.where(diff == -1)[0] + 1

    if mask[0]:
        starts = np.concatenate(([0], starts))
    if mask[-1]:
        ends = np.concatenate((ends, [len(mask)]))

    return list(zip(starts.tolist(), ends.tolist()))
