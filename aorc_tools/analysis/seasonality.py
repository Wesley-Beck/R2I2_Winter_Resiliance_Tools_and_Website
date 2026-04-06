"""
Fire season onset/offset detection with tunable smoothing filters.

Detects when fire danger indices rise above a threshold and stay elevated,
ignoring occasional brief dips. Tracks how fire season timing has shifted
across years.

Key concepts:
- **Onset**: First date when smoothed FDI exceeds threshold and remains
  above for a minimum sustained duration.
- **Offset**: First date after onset when FDI drops below threshold and
  stays below for a minimum sustained duration.
- **Tunable filter**: Rolling-window smoothing + minimum-duration gating
  to ignore short dips/spikes.
"""

import numpy as np


def smooth_timeseries(values, window=7, method="mean"):
    """Apply rolling-window smoothing to a 1-D time series.

    Args:
        values: 1-D array of daily values (may contain NaN)
        window: rolling window size in days (default 7)
        method: "mean" or "median"

    Returns:
        smoothed: same-length array with NaN-aware rolling statistic
    """
    arr = np.asarray(values, dtype=np.float64)
    n = len(arr)

    if method == "mean":
        # Vectorized NaN-aware rolling mean using cumsum trick
        valid = ~np.isnan(arr)
        filled = np.where(valid, arr, 0.0)
        half = window // 2

        cumsum = np.concatenate(([0.0], np.cumsum(filled)))
        count = np.concatenate(([0], np.cumsum(valid.astype(np.int64))))

        lo = np.clip(np.arange(n) - half, 0, n)
        hi = np.clip(np.arange(n) + half + 1, 0, n)

        sums = cumsum[hi] - cumsum[lo]
        counts = count[hi] - count[lo]

        with np.errstate(invalid="ignore"):
            smoothed = np.where(counts > 0, sums / counts, np.nan)
        return smoothed
    else:
        # Median requires per-element computation (no cumsum trick)
        smoothed = np.empty(n, dtype=np.float64)
        half = window // 2
        for i in range(n):
            lo = max(0, i - half)
            hi = min(n, i + half + 1)
            smoothed[i] = np.nanmedian(arr[lo:hi])
        return smoothed


def detect_season(values, threshold, min_above_days=5, min_below_days=7,
                  smooth_window=7, smooth_method="mean"):
    """Detect fire season onset and offset for a single time series.

    The algorithm:
    1. Smooth the daily values with a rolling window.
    2. Find runs where the smoothed value >= threshold.
    3. Merge runs separated by gaps shorter than `min_below_days`
       (this ignores brief dips below threshold).
    4. Keep only merged runs lasting >= `min_above_days`.
    5. Onset = start of first qualifying run; offset = end of last.

    Args:
        values: 1-D array of daily values (n_days,)
        threshold: FDI value that defines "active fire season"
        min_above_days: minimum consecutive days above threshold to
            count as a real season start (default 5)
        min_below_days: minimum consecutive days below threshold to
            count as a real season end — shorter dips are ignored (default 7)
        smooth_window: rolling window for pre-smoothing (default 7)
        smooth_method: "mean" or "median"

    Returns:
        dict with:
            onset_idx: index of season onset (None if no season detected)
            offset_idx: index of season offset (None if no season detected)
            season_length: number of days in fire season (0 if none)
            n_active_days: total days above threshold (before smoothing)
            smoothed: the smoothed time series used for detection
            runs: list of (start_idx, end_idx) for all qualifying runs
    """
    smoothed = smooth_timeseries(values, smooth_window, smooth_method)
    above = smoothed >= threshold

    raw_runs = _extract_runs(above)

    if not raw_runs:
        return {
            "onset_idx": None,
            "offset_idx": None,
            "season_length": 0,
            "n_active_days": int(np.nansum(values >= threshold)),
            "smoothed": smoothed,
            "runs": [],
        }

    merged = _merge_runs(raw_runs, min_gap=min_below_days)
    qualifying = [(s, e) for s, e in merged if (e - s) >= min_above_days]

    if not qualifying:
        return {
            "onset_idx": None,
            "offset_idx": None,
            "season_length": 0,
            "n_active_days": int(np.nansum(values >= threshold)),
            "smoothed": smoothed,
            "runs": [],
        }

    onset = qualifying[0][0]
    offset = qualifying[-1][1]
    season_length = offset - onset

    return {
        "onset_idx": int(onset),
        "offset_idx": int(offset),
        "season_length": int(season_length),
        "n_active_days": int(np.nansum(values >= threshold)),
        "smoothed": smoothed,
        "runs": qualifying,
    }


def detect_season_spatial(data, threshold, **kwargs):
    """Detect fire season for each spatial point independently.

    Args:
        data: np.ndarray of shape (n_days, n_points)
        threshold: scalar threshold
        **kwargs: passed to detect_season()

    Returns:
        onset_days: array of shape (n_points,) — onset day index (NaN if none)
        offset_days: array of shape (n_points,) — offset day index (NaN if none)
        season_lengths: array of shape (n_points,) — season duration in days
    """
    n_days, n_points = data.shape
    onset_days = np.full(n_points, np.nan)
    offset_days = np.full(n_points, np.nan)
    season_lengths = np.zeros(n_points)

    for j in range(n_points):
        result = detect_season(data[:, j], threshold, **kwargs)
        if result["onset_idx"] is not None:
            onset_days[j] = result["onset_idx"]
            offset_days[j] = result["offset_idx"]
            season_lengths[j] = result["season_length"]

    return onset_days, offset_days, season_lengths


def detect_season_by_year(yearly_data, threshold, **kwargs):
    """Detect fire season for each year to track temporal shifts.

    Args:
        yearly_data: dict mapping year → (dates, data_array)
            where data_array is (n_days, n_points)
        threshold: scalar threshold
        **kwargs: passed to detect_season()

    Returns:
        results: dict mapping year → {
            "spatial_mean_onset": float (mean onset day across points),
            "spatial_mean_offset": float,
            "spatial_mean_length": float,
            "onset_days": array per point,
            "offset_days": array per point,
            "season_lengths": array per point,
            "dates": the date list for this year,
        }
    """
    results = {}
    for year, (dates, data) in sorted(yearly_data.items()):
        onset, offset, lengths = detect_season_spatial(data, threshold, **kwargs)
        results[year] = {
            "spatial_mean_onset": float(np.nanmean(onset)),
            "spatial_mean_offset": float(np.nanmean(offset)),
            "spatial_mean_length": float(np.nanmean(lengths)),
            "onset_days": onset,
            "offset_days": offset,
            "season_lengths": lengths,
            "dates": dates,
        }
    return results


def compute_seasonal_profile(dates, data, smooth_window=14):
    """Compute the average seasonal profile (spatial mean by day-of-year).

    Args:
        dates: list of date strings "YYYY-MM-DD"
        data: np.ndarray of shape (n_days, n_points)
        smooth_window: smoothing window for the profile

    Returns:
        doy_values: dict mapping day-of-year (1-366) → mean FDI value
        profile: array of 366 values (smoothed seasonal curve)
    """
    from datetime import datetime

    spatial_mean = np.nanmean(data, axis=1)
    doy_accum = {}

    for i, d in enumerate(dates):
        dt = datetime.strptime(d[:10], "%Y-%m-%d")
        doy = dt.timetuple().tm_yday
        if doy not in doy_accum:
            doy_accum[doy] = []
        doy_accum[doy].append(spatial_mean[i])

    # Average per DOY
    doy_values = {}
    profile_raw = np.full(366, np.nan)
    for doy, vals in doy_accum.items():
        mean_val = np.nanmean(vals)
        doy_values[doy] = float(mean_val)
        if 1 <= doy <= 366:
            profile_raw[doy - 1] = mean_val

    # Smooth the profile
    profile = smooth_timeseries(profile_raw, window=smooth_window)

    return doy_values, profile


def threshold_sensitivity(values, thresholds, **kwargs):
    """Test how season detection changes across a range of thresholds.

    Args:
        values: 1-D daily time series
        thresholds: list of threshold values to test
        **kwargs: passed to detect_season()

    Returns:
        results: list of dicts, one per threshold, each containing
            detect_season() output plus the threshold value
    """
    results = []
    for t in thresholds:
        r = detect_season(values, t, **kwargs)
        r["threshold"] = t
        results.append(r)
    return results


# -- Internal helpers --

def _extract_runs(mask):
    """Extract runs of True values from a boolean array.

    Returns list of (start, end) where end is exclusive.
    """
    if len(mask) == 0:
        return []

    runs = []
    in_run = False
    start = 0

    for i, val in enumerate(mask):
        if val and not in_run:
            start = i
            in_run = True
        elif not val and in_run:
            runs.append((start, i))
            in_run = False

    if in_run:
        runs.append((start, len(mask)))

    return runs


def _merge_runs(runs, min_gap):
    """Merge runs separated by gaps shorter than min_gap."""
    if not runs:
        return []

    merged = [runs[0]]
    for start, end in runs[1:]:
        prev_start, prev_end = merged[-1]
        gap = start - prev_end
        if gap < min_gap:
            merged[-1] = (prev_start, end)
        else:
            merged.append((start, end))

    return merged
