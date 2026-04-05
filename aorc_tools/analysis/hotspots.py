"""
Spatial hotspot detection and percentile mapping.

Identifies locations where fire danger indices consistently reach
the highest values — the "hottest spots" in the study area.

Analysis methods:
1. Temporal mean/max per point → spatial percentile ranking
2. Exceedance frequency: how often each point exceeds a threshold
3. Percentile-based extreme event mapping
4. Cross-FDI hotspot agreement (points hot across multiple indices)
"""

import numpy as np


def compute_point_statistics(data):
    """Compute temporal statistics for each spatial point.

    Args:
        data: np.ndarray of shape (n_timesteps, n_points)

    Returns:
        dict with arrays of shape (n_points,):
            mean, max, std, p90, p95, p99, median
    """
    return {
        "mean": np.nanmean(data, axis=0),
        "max": np.nanmax(data, axis=0),
        "std": np.nanstd(data, axis=0),
        "median": np.nanmedian(data, axis=0),
        "p90": np.nanpercentile(data, 90, axis=0),
        "p95": np.nanpercentile(data, 95, axis=0),
        "p99": np.nanpercentile(data, 99, axis=0),
    }


def find_hotspots(data, percentile=95):
    """Find spatial hotspots — points with temporal mean above given percentile.

    Args:
        data: np.ndarray of shape (n_timesteps, n_points)
        percentile: percentile threshold (default 95)

    Returns:
        hotspot_mask: boolean array of shape (n_points,)
        point_means: array of temporal means per point
        threshold: the percentile value used as cutoff
    """
    point_means = np.nanmean(data, axis=0)
    threshold = np.nanpercentile(point_means, percentile)
    hotspot_mask = point_means >= threshold
    return hotspot_mask, point_means, threshold


def exceedance_frequency(data, threshold):
    """Count what fraction of timesteps each point exceeds a threshold.

    Args:
        data: np.ndarray of shape (n_timesteps, n_points)
        threshold: scalar threshold value

    Returns:
        frequency: array of shape (n_points,) with values 0-1
    """
    exceed = data >= threshold
    valid = ~np.isnan(data)
    count = np.sum(exceed & valid, axis=0).astype(np.float64)
    total = np.sum(valid, axis=0).astype(np.float64)
    total[total == 0] = 1.0  # avoid division by zero
    return count / total


def percentile_timing(data, dates, percentile=95):
    """Find WHEN the highest percentile values occur.

    Args:
        data: np.ndarray of shape (n_timesteps, n_points)
        dates: list of date strings
        percentile: percentile threshold

    Returns:
        peak_dates: list of dates when spatial-mean values exceeded the percentile
        peak_values: corresponding spatial-mean values
        threshold: the percentile value
    """
    spatial_mean = np.nanmean(data, axis=1)
    threshold = np.nanpercentile(spatial_mean, percentile)
    mask = spatial_mean >= threshold
    peak_dates = [d for d, m in zip(dates, mask) if m]
    peak_values = spatial_mean[mask]
    return peak_dates, peak_values, threshold


def cross_fdi_hotspot_agreement(fdi_data_dict, percentile=90):
    """Find points that are hotspots across multiple FDI systems.

    Args:
        fdi_data_dict: dict mapping FDI name → np.ndarray (n_timesteps, n_points)
        percentile: hotspot percentile threshold per FDI

    Returns:
        agreement_count: array of shape (n_points,) — how many FDIs flag this point
        fdi_hotspots: dict mapping FDI name → boolean mask
    """
    fdi_hotspots = {}
    for name, data in fdi_data_dict.items():
        mask, _, _ = find_hotspots(data, percentile)
        fdi_hotspots[name] = mask

    n_points = next(iter(fdi_data_dict.values())).shape[1]
    agreement_count = np.zeros(n_points, dtype=np.int32)
    for mask in fdi_hotspots.values():
        agreement_count += mask.astype(np.int32)

    return agreement_count, fdi_hotspots


def lowest_risk_points(data, percentile=10):
    """Find points with consistently lowest fire danger (safest areas).

    Args:
        data: np.ndarray of shape (n_timesteps, n_points)
        percentile: bottom percentile (default 10 = lowest 10%)

    Returns:
        safe_mask: boolean array of shape (n_points,)
        point_means: temporal means per point
        threshold: the low-risk cutoff
    """
    point_means = np.nanmean(data, axis=0)
    threshold = np.nanpercentile(point_means, percentile)
    safe_mask = point_means <= threshold
    return safe_mask, point_means, threshold
