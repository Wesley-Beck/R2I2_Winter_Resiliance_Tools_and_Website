"""
Publication-quality figure generation for wildfire risk analysis.

Generates matplotlib figures suitable for journal articles, with
consistent styling, proper axis labels, and colorbar configurations.

Figure types:
1. Hotspot maps (spatial heatmaps of FDI intensity)
2. Seasonality plots (onset/offset trends, seasonal profiles)
3. FDI comparison plots (similarity matrices, ROC curves)
4. Exceedance frequency maps
5. Temporal peak analysis
6. Lowest-risk mapping
"""

import logging
from pathlib import Path

import numpy as np

logger = logging.getLogger(__name__)

# Publication style defaults
STYLE = {
    "font.family": "serif",
    "font.size": 10,
    "axes.titlesize": 12,
    "axes.labelsize": 10,
    "xtick.labelsize": 8,
    "ytick.labelsize": 8,
    "legend.fontsize": 8,
    "figure.dpi": 300,
    "savefig.dpi": 300,
    "savefig.bbox": "tight",
    "axes.grid": False,
}

# FDI display names and colors
FDI_COLORS = {
    "FWI": "#d62728",
    "ISI": "#ff7f0e",
    "BUI": "#2ca02c",
    "FFMC": "#1f77b4",
    "DMC": "#9467bd",
    "DC": "#8c564b",
    "ERC": "#e377c2",
    "BI": "#7f7f7f",
    "SC": "#bcbd22",
    "FPI": "#17becf",
}


def _apply_style():
    """Apply publication style to matplotlib."""
    import matplotlib
    matplotlib.rcParams.update(STYLE)


def plot_hotspot_map(lats, lons, values, title="Fire Danger Hotspots",
                     cmap="YlOrRd", label="FDI Value", figsize=(10, 8),
                     hotspot_mask=None, save_path=None):
    """Plot spatial heatmap of FDI values with optional hotspot overlay.

    Args:
        lats, lons: 1-D arrays of point coordinates
        values: 1-D array of values to map (e.g., temporal means)
        title: figure title
        cmap: colormap name
        label: colorbar label
        figsize: figure size tuple
        hotspot_mask: optional boolean array — hotspot points get markers
        save_path: if provided, save figure to this path

    Returns:
        fig, ax: matplotlib figure and axes
    """
    import matplotlib.pyplot as plt
    _apply_style()

    fig, ax = plt.subplots(1, 1, figsize=figsize)

    scatter = ax.scatter(lons, lats, c=values, cmap=cmap, s=1,
                         alpha=0.8, edgecolors="none", rasterized=True)
    cbar = fig.colorbar(scatter, ax=ax, shrink=0.7, pad=0.02)
    cbar.set_label(label)

    if hotspot_mask is not None:
        ax.scatter(lons[hotspot_mask], lats[hotspot_mask],
                   c="none", edgecolors="black", s=5, linewidths=0.3,
                   label=f"Hotspot (n={hotspot_mask.sum()})")
        ax.legend(loc="lower left")

    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    ax.set_title(title)
    ax.set_aspect("equal")

    if save_path:
        fig.savefig(save_path)
        logger.info("Saved: %s", save_path)

    return fig, ax


def plot_multi_hotspot_comparison(lats, lons, fdi_hotspots, agreement_count,
                                  figsize=(14, 10), save_path=None):
    """Plot multi-FDI hotspot agreement map with per-FDI subplots.

    Args:
        lats, lons: coordinate arrays
        fdi_hotspots: dict mapping FDI name → boolean hotspot mask
        agreement_count: array of how many FDIs flag each point
        figsize: figure size
        save_path: output path

    Returns:
        fig: matplotlib figure
    """
    import matplotlib.pyplot as plt
    _apply_style()

    names = sorted(fdi_hotspots.keys())
    n = len(names)
    ncols = min(3, n)
    nrows = (n + ncols - 1) // ncols + 1  # +1 for agreement map

    fig, axes = plt.subplots(nrows, ncols, figsize=figsize)
    if nrows == 1:
        axes = axes.reshape(1, -1)
    axes_flat = axes.flatten()

    # Per-FDI hotspot maps
    for i, name in enumerate(names):
        ax = axes_flat[i]
        mask = fdi_hotspots[name]
        colors = np.where(mask, 1.0, 0.3)
        ax.scatter(lons, lats, c=colors, cmap="RdYlGn_r", s=0.5,
                   vmin=0, vmax=1, edgecolors="none", rasterized=True)
        ax.set_title(name)
        ax.set_aspect("equal")
        ax.tick_params(labelsize=6)

    # Agreement map in last row
    ax_agree = axes_flat[n]
    scatter = ax_agree.scatter(lons, lats, c=agreement_count, cmap="hot_r",
                               s=1, vmin=0, vmax=len(names),
                               edgecolors="none", rasterized=True)
    fig.colorbar(scatter, ax=ax_agree, shrink=0.7)
    ax_agree.set_title(f"Agreement (max={agreement_count.max()})")
    ax_agree.set_aspect("equal")

    # Hide unused axes
    for i in range(n + 1, len(axes_flat)):
        axes_flat[i].set_visible(False)

    fig.suptitle("Cross-FDI Hotspot Agreement", fontsize=14, y=1.02)
    fig.tight_layout()

    if save_path:
        fig.savefig(save_path)
        logger.info("Saved: %s", save_path)

    return fig


def plot_seasonal_profile(doy_values, profile, fdi_name="FWI",
                          threshold=None, figsize=(10, 4), save_path=None):
    """Plot smoothed seasonal fire danger profile (by day of year).

    Args:
        doy_values: dict mapping DOY → mean FDI value (raw)
        profile: smoothed 366-element array
        fdi_name: name for labeling
        threshold: optional horizontal line for fire season threshold
        figsize: figure size
        save_path: output path

    Returns:
        fig, ax
    """
    import matplotlib.pyplot as plt
    _apply_style()

    fig, ax = plt.subplots(1, 1, figsize=figsize)

    # Raw values
    doys = sorted(doy_values.keys())
    raw_vals = [doy_values[d] for d in doys]
    ax.scatter(doys, raw_vals, s=3, alpha=0.4, color="gray", label="Daily mean")

    # Smoothed profile
    x = np.arange(1, 367)
    ax.plot(x, profile, color=FDI_COLORS.get(fdi_name, "#333333"),
            linewidth=2, label="Smoothed profile")

    if threshold is not None:
        ax.axhline(threshold, color="red", linestyle="--", linewidth=1,
                   label=f"Threshold = {threshold:.1f}")

    ax.set_xlabel("Day of Year")
    ax.set_ylabel(f"{fdi_name} (spatial mean)")
    ax.set_title(f"Seasonal {fdi_name} Profile")
    ax.set_xlim(1, 366)
    ax.legend()

    # Month labels on x-axis
    month_starts = [1, 32, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    month_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                   "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    ax.set_xticks(month_starts)
    ax.set_xticklabels(month_names)

    if save_path:
        fig.savefig(save_path)
        logger.info("Saved: %s", save_path)

    return fig, ax


def plot_season_onset_offset(yearly_results, fdi_name="FWI",
                             figsize=(10, 5), save_path=None):
    """Plot fire season onset/offset trends across years.

    Args:
        yearly_results: dict from detect_season_by_year()
        fdi_name: name for labeling
        figsize: figure size
        save_path: output path

    Returns:
        fig, ax
    """
    import matplotlib.pyplot as plt
    _apply_style()

    years = sorted(yearly_results.keys())
    onsets = [yearly_results[y]["spatial_mean_onset"] for y in years]
    offsets = [yearly_results[y]["spatial_mean_offset"] for y in years]
    lengths = [yearly_results[y]["spatial_mean_length"] for y in years]

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=figsize, sharex=True)

    # Onset and offset
    color_on = "#2ca02c"
    color_off = "#d62728"
    ax1.plot(years, onsets, "o-", color=color_on, label="Season onset (day)")
    ax1.plot(years, offsets, "s-", color=color_off, label="Season offset (day)")
    ax1.fill_between(years, onsets, offsets, alpha=0.15, color="orange")
    ax1.set_ylabel("Day of Year")
    ax1.set_title(f"{fdi_name} Fire Season Timing")
    ax1.legend()

    # Season length
    ax2.bar(years, lengths, color="#ff7f0e", alpha=0.7)
    ax2.set_ylabel("Season Length (days)")
    ax2.set_xlabel("Year")

    # Trend line
    if len(years) >= 3:
        z = np.polyfit(years, lengths, 1)
        trend = np.polyval(z, years)
        ax2.plot(years, trend, "k--", linewidth=1,
                 label=f"Trend: {z[0]:+.1f} days/year")
        ax2.legend()

    fig.tight_layout()

    if save_path:
        fig.savefig(save_path)
        logger.info("Saved: %s", save_path)

    return fig, (ax1, ax2)


def plot_roc_curves(roc_results, figsize=(7, 7), save_path=None):
    """Plot ROC curves for multiple FDIs.

    Args:
        roc_results: dict mapping FDI name → roc_analysis() output
        figsize: figure size
        save_path: output path

    Returns:
        fig, ax
    """
    import matplotlib.pyplot as plt
    _apply_style()

    fig, ax = plt.subplots(1, 1, figsize=figsize)

    for name, roc in sorted(roc_results.items(), key=lambda x: -x[1]["auc"]):
        color = FDI_COLORS.get(name, None)
        ax.plot(roc["fpr"], roc["tpr"],
                label=f"{name} (AUC={roc['auc']:.3f})",
                color=color, linewidth=1.5)

    ax.plot([0, 1], [0, 1], "k--", linewidth=0.5, label="Random")
    ax.set_xlabel("False Positive Rate")
    ax.set_ylabel("True Positive Rate (Hit Rate)")
    ax.set_title("ROC Curves: FDI as Wildfire Day Classifier")
    ax.legend(loc="lower right")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.set_aspect("equal")

    if save_path:
        fig.savefig(save_path)
        logger.info("Saved: %s", save_path)

    return fig, ax


def plot_similarity_matrix(names, matrix, title="FDI Similarity Matrix",
                           figsize=(8, 7), save_path=None):
    """Plot heatmap of FDI pairwise similarity.

    Args:
        names: list of FDI names
        matrix: (n, n) similarity matrix
        title: figure title
        figsize: figure size
        save_path: output path

    Returns:
        fig, ax
    """
    import matplotlib.pyplot as plt
    _apply_style()

    fig, ax = plt.subplots(1, 1, figsize=figsize)

    im = ax.imshow(matrix, cmap="RdYlBu_r", vmin=-1, vmax=1, aspect="equal")
    cbar = fig.colorbar(im, ax=ax, shrink=0.8)
    cbar.set_label("Spearman Correlation")

    n = len(names)
    ax.set_xticks(range(n))
    ax.set_yticks(range(n))
    ax.set_xticklabels(names, rotation=45, ha="right")
    ax.set_yticklabels(names)

    # Annotate cells
    for i in range(n):
        for j in range(n):
            val = matrix[i, j]
            color = "white" if abs(val) > 0.7 else "black"
            ax.text(j, i, f"{val:.2f}", ha="center", va="center",
                    fontsize=7, color=color)

    ax.set_title(title)
    fig.tight_layout()

    if save_path:
        fig.savefig(save_path)
        logger.info("Saved: %s", save_path)

    return fig, ax


def plot_exceedance_map(lats, lons, frequency, fdi_name="FWI",
                        threshold=None, figsize=(10, 8), save_path=None):
    """Plot map of exceedance frequency (fraction of time above threshold).

    Args:
        lats, lons: coordinate arrays
        frequency: 1-D array of exceedance fractions (0-1)
        fdi_name: name for labeling
        threshold: threshold value used (for title)
        figsize: figure size
        save_path: output path

    Returns:
        fig, ax
    """
    import matplotlib.pyplot as plt
    _apply_style()

    fig, ax = plt.subplots(1, 1, figsize=figsize)

    scatter = ax.scatter(lons, lats, c=frequency * 100, cmap="YlOrRd",
                         s=1, vmin=0, edgecolors="none", rasterized=True)
    cbar = fig.colorbar(scatter, ax=ax, shrink=0.7, pad=0.02)
    cbar.set_label("Exceedance Frequency (%)")

    thresh_str = f" (threshold={threshold:.1f})" if threshold else ""
    ax.set_title(f"{fdi_name} Exceedance Frequency{thresh_str}")
    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    ax.set_aspect("equal")

    if save_path:
        fig.savefig(save_path)
        logger.info("Saved: %s", save_path)

    return fig, ax


def plot_peak_timing(peak_dates, peak_values, fdi_name="FWI",
                     figsize=(12, 4), save_path=None):
    """Plot when the highest FDI values occurred.

    Args:
        peak_dates: list of date strings
        peak_values: corresponding FDI values
        fdi_name: name for labeling
        figsize: figure size
        save_path: output path

    Returns:
        fig, ax
    """
    import matplotlib.pyplot as plt
    from datetime import datetime
    _apply_style()

    fig, ax = plt.subplots(1, 1, figsize=figsize)

    dates = [datetime.strptime(d[:10], "%Y-%m-%d") for d in peak_dates]
    color = FDI_COLORS.get(fdi_name, "#d62728")

    ax.stem(dates, peak_values, linefmt=f"{color}80", markerfmt="o",
            basefmt="k-", label=fdi_name)

    ax.set_xlabel("Date")
    ax.set_ylabel(f"{fdi_name} (spatial mean)")
    ax.set_title(f"Peak {fdi_name} Events (95th+ percentile)")
    ax.legend()
    fig.autofmt_xdate()
    fig.tight_layout()

    if save_path:
        fig.savefig(save_path)
        logger.info("Saved: %s", save_path)

    return fig, ax


def plot_lowest_risk_map(lats, lons, safe_mask, point_means,
                         figsize=(10, 8), save_path=None):
    """Plot map highlighting lowest fire risk areas.

    Args:
        lats, lons: coordinate arrays
        safe_mask: boolean array of low-risk points
        point_means: temporal mean FDI per point
        figsize: figure size
        save_path: output path

    Returns:
        fig, ax
    """
    import matplotlib.pyplot as plt
    _apply_style()

    fig, ax = plt.subplots(1, 1, figsize=figsize)

    # Background: all points in gray
    ax.scatter(lons, lats, c=point_means, cmap="YlOrRd", s=1,
               alpha=0.4, edgecolors="none", rasterized=True)

    # Overlay: safe points in blue
    ax.scatter(lons[safe_mask], lats[safe_mask], c="dodgerblue", s=3,
               alpha=0.8, edgecolors="none",
               label=f"Lowest risk (n={safe_mask.sum()})")

    cbar = fig.colorbar(
        plt.cm.ScalarMappable(cmap="YlOrRd",
                              norm=plt.Normalize(vmin=np.nanmin(point_means),
                                                 vmax=np.nanmax(point_means))),
        ax=ax, shrink=0.7, pad=0.02)
    cbar.set_label("Mean FDI")

    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    ax.set_title("Lowest Wildfire Risk Areas")
    ax.set_aspect("equal")
    ax.legend(loc="lower left")

    if save_path:
        fig.savefig(save_path)
        logger.info("Saved: %s", save_path)

    return fig, ax


def plot_severity_distribution(yearly_dist, variable, figsize=(12, 6),
                               save_path=None):
    """Stacked bar chart showing severity level distribution per year.

    Args:
        yearly_dist: dict mapping year → {level_name: fraction}
        variable: FDI variable name for labeling
        figsize: figure size
        save_path: output path

    Returns:
        fig, ax
    """
    import matplotlib.pyplot as plt
    _apply_style()

    severity_colors = {
        "Low": "#2ca02c",
        "Moderate": "#ffdd57",
        "High": "#ff7f0e",
        "Very High": "#d62728",
        "Extreme": "#7b2d26",
    }

    fig, ax = plt.subplots(1, 1, figsize=figsize)

    years = sorted(yearly_dist.keys())
    levels = ["Low", "Moderate", "High", "Very High", "Extreme"]
    # Filter to levels that actually appear in the data
    levels = [lv for lv in levels if any(lv in yearly_dist[y] for y in years)]

    bottoms = np.zeros(len(years))
    for level in levels:
        fractions = [yearly_dist[y].get(level, 0.0) for y in years]
        ax.bar(years, fractions, bottom=bottoms,
               color=severity_colors.get(level, "#999999"),
               label=level, edgecolor="white", linewidth=0.3)
        bottoms += np.array(fractions)

    # Trend line for "High" and above combined
    high_levels = {"High", "Very High", "Extreme"}
    high_combined = []
    for y in years:
        total = sum(yearly_dist[y].get(lv, 0.0) for lv in high_levels)
        high_combined.append(total)

    if len(years) >= 3:
        z = np.polyfit(years, high_combined, 1)
        trend = np.polyval(z, years)
        ax.plot(years, trend, "k--", linewidth=1.5,
                label=f"High+ trend: {z[0]:+.4f}/yr")

    ax.set_xlabel("Year")
    ax.set_ylabel("Fraction")
    ax.set_ylim(0, 1)
    ax.set_title(f"{variable} Severity Distribution by Year")
    ax.legend(loc="upper left", bbox_to_anchor=(1.01, 1))
    fig.tight_layout()

    if save_path:
        fig.savefig(save_path)
        logger.info("Saved: %s", save_path)

    return fig, ax


def plot_extreme_event_timeline(events, variable, figsize=(14, 5),
                                save_path=None):
    """Timeline of extreme events as horizontal bars.

    Args:
        events: list of dicts with keys: start_date, end_date, duration,
                peak_value, spatial_extent
        variable: FDI variable name for labeling
        figsize: figure size
        save_path: output path

    Returns:
        fig, ax
    """
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    from datetime import datetime
    _apply_style()

    fig, ax = plt.subplots(1, 1, figsize=figsize)

    if not events:
        ax.text(0.5, 0.5, "No extreme events detected",
                transform=ax.transAxes, ha="center", va="center")
        ax.set_title(f"{variable} Extreme Event Timeline")
        if save_path:
            fig.savefig(save_path)
            logger.info("Saved: %s", save_path)
        return fig, ax

    # Parse dates and extract peak values for color mapping
    peak_values = [e["peak_value"] for e in events]
    vmin, vmax = min(peak_values), max(peak_values)

    cmap = plt.cm.YlOrRd
    norm = plt.Normalize(vmin=vmin, vmax=vmax)

    for i, event in enumerate(events):
        start = event["start_date"]
        if isinstance(start, str):
            start = datetime.strptime(start[:10], "%Y-%m-%d")
        end = event["end_date"]
        if isinstance(end, str):
            end = datetime.strptime(end[:10], "%Y-%m-%d")

        color = cmap(norm(event["peak_value"]))
        ax.barh(i, (end - start).days or 1, left=mdates.date2num(start),
                height=0.6, color=color, edgecolor="black", linewidth=0.3)

    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    ax.xaxis.set_major_locator(mdates.YearLocator())
    fig.autofmt_xdate()

    ax.set_ylabel("Event #")
    ax.set_xlabel("Date")
    ax.set_title(f"{variable} Extreme Event Timeline")
    ax.set_yticks(range(len(events)))
    ax.set_yticklabels([f"E{i+1}" for i in range(len(events))])

    sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
    sm.set_array([])
    cbar = fig.colorbar(sm, ax=ax, shrink=0.8, pad=0.02)
    cbar.set_label(f"Peak {variable}")

    fig.tight_layout()

    if save_path:
        fig.savefig(save_path)
        logger.info("Saved: %s", save_path)

    return fig, ax


def plot_return_periods(return_periods, return_levels, annual_maxima,
                        variable, gev_params=None, figsize=(8, 6),
                        save_path=None):
    """Return period plot on Gumbel paper.

    Args:
        return_periods: array of return periods (years)
        return_levels: array of fitted return levels
        annual_maxima: array of observed annual maxima
        variable: FDI variable name for labeling
        gev_params: optional dict with 'shape', 'loc', 'scale' for annotation
        figsize: figure size
        save_path: output path

    Returns:
        fig, ax
    """
    import matplotlib.pyplot as plt
    _apply_style()

    fig, ax = plt.subplots(1, 1, figsize=figsize)

    # Plot fitted curve
    ax.plot(return_periods, return_levels, "b-", linewidth=2,
            label="GEV fit")

    # Confidence intervals (approximate using +/- 10% for visual)
    if len(return_levels) > 0:
        upper = return_levels * 1.1
        lower = return_levels * 0.9
        ax.fill_between(return_periods, lower, upper, alpha=0.2, color="blue",
                        label="90% CI (approx)")

    # Plot observed points using Weibull plotting position
    n = len(annual_maxima)
    if n > 0:
        sorted_maxima = np.sort(annual_maxima)[::-1]
        empirical_rp = np.array([(n + 1) / i for i in range(1, n + 1)])
        ax.scatter(empirical_rp, sorted_maxima, c="red", s=30, zorder=5,
                   label="Observed annual maxima")

    ax.set_xscale("log")
    ax.set_xlabel("Return Period (years)")
    ax.set_ylabel(f"Return Level ({variable})")
    ax.set_title(f"{variable} Return Period Analysis")
    ax.legend()
    ax.grid(True, alpha=0.3)

    if gev_params is not None:
        text = (f"GEV params:\n"
                f"  shape = {gev_params.get('shape', 0):.3f}\n"
                f"  loc   = {gev_params.get('loc', 0):.1f}\n"
                f"  scale = {gev_params.get('scale', 0):.1f}")
        ax.text(0.02, 0.98, text, transform=ax.transAxes, fontsize=7,
                va="top", ha="left",
                bbox=dict(boxstyle="round", facecolor="wheat", alpha=0.5))

    fig.tight_layout()

    if save_path:
        fig.savefig(save_path)
        logger.info("Saved: %s", save_path)

    return fig, ax


def plot_all_indices_seasonal_overlay(seasonal_profiles, figsize=(14, 6),
                                      save_path=None):
    """Overlay ALL wildfire indices on one plot by day-of-year.

    This is the key comparison figure showing when each index peaks
    and how they compare seasonally.

    Args:
        seasonal_profiles: dict mapping variable_name → 366-element
                          smoothed profile array
        figsize: figure size
        save_path: output path

    Returns:
        fig, ax
    """
    import matplotlib.pyplot as plt
    _apply_style()

    fig, ax = plt.subplots(1, 1, figsize=figsize)

    x = np.arange(1, 367)
    for name, profile in sorted(seasonal_profiles.items()):
        color = FDI_COLORS.get(name, None)
        # Normalize each profile to 0-1 for comparison
        pmin, pmax = np.nanmin(profile), np.nanmax(profile)
        if pmax > pmin:
            normalized = (profile - pmin) / (pmax - pmin)
        else:
            normalized = profile
        ax.plot(x, normalized, color=color, linewidth=1.8, label=name,
                alpha=0.85)

    ax.set_xlabel("Day of Year")
    ax.set_ylabel("Normalized Index Value (0-1)")
    ax.set_title("Seasonal Overlay of All Fire Danger Indices")
    ax.set_xlim(1, 366)
    ax.set_ylim(0, 1.05)

    # Month labels on x-axis
    month_starts = [1, 32, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    month_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                   "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    ax.set_xticks(month_starts)
    ax.set_xticklabels(month_names)

    ax.legend(loc="upper left", bbox_to_anchor=(1.01, 1), fontsize=8)
    ax.grid(True, alpha=0.2)
    fig.tight_layout()

    if save_path:
        fig.savefig(save_path)
        logger.info("Saved: %s", save_path)

    return fig, ax


def plot_intensity_duration(idf_results, variable, figsize=(10, 6),
                            save_path=None):
    """Intensity-Duration-Frequency curves.

    Args:
        idf_results: dict mapping duration_days → annual_maxima array
        variable: FDI variable name for labeling
        figsize: figure size
        save_path: output path

    Returns:
        fig, ax
    """
    import matplotlib.pyplot as plt
    _apply_style()

    fig, ax = plt.subplots(1, 1, figsize=figsize)

    durations = sorted(idf_results.keys())
    data_list = [idf_results[d] for d in durations]
    labels = [f"{d}d" for d in durations]

    bp = ax.boxplot(data_list, patch_artist=True,
                    widths=0.6, showmeans=True,
                    meanprops=dict(marker="D", markerfacecolor="red",
                                   markersize=5))
    ax.set_xticks(range(1, len(labels) + 1))
    ax.set_xticklabels(labels)

    colors = plt.cm.viridis(np.linspace(0.2, 0.8, len(durations)))
    for patch, color in zip(bp["boxes"], colors):
        patch.set_facecolor(color)
        patch.set_alpha(0.7)

    # Connect means with a line
    means = [np.mean(idf_results[d]) for d in durations]
    ax.plot(range(1, len(durations) + 1), means, "r--", linewidth=1,
            label="Mean", alpha=0.7)

    ax.set_xlabel("Duration")
    ax.set_ylabel(f"Rolling Max {variable}")
    ax.set_title(f"{variable} Intensity-Duration Analysis")
    ax.legend()
    fig.tight_layout()

    if save_path:
        fig.savefig(save_path)
        logger.info("Saved: %s", save_path)

    return fig, ax


def plot_snowmelt_fdi_lag(years, snowmelt_doys, fire_onset_doys, lags,
                          figsize=(12, 5), save_path=None):
    """Dual-axis plot of snowmelt date, fire onset date, and lag.

    Args:
        years: array of years
        snowmelt_doys: array of snowmelt day-of-year per year
        fire_onset_doys: array of fire onset day-of-year per year
        lags: array of lag in days (fire_onset - snowmelt) per year
        figsize: figure size
        save_path: output path

    Returns:
        fig, (ax1, ax2)
    """
    import matplotlib.pyplot as plt
    _apply_style()

    fig, ax1 = plt.subplots(1, 1, figsize=figsize)
    ax2 = ax1.twinx()

    # Left axis: DOY values
    ax1.plot(years, snowmelt_doys, "o-", color="#1f77b4", linewidth=1.5,
             markersize=5, label="Snowmelt date (DOY)")
    ax1.plot(years, fire_onset_doys, "s-", color="#d62728", linewidth=1.5,
             markersize=5, label="Fire onset date (DOY)")
    ax1.set_ylabel("Day of Year")
    ax1.set_xlabel("Year")

    # Right axis: lag bars
    ax2.bar(years, lags, alpha=0.3, color="#2ca02c", label="Lag (days)",
            width=0.6)
    ax2.set_ylabel("Lag (days)")

    # Trend lines
    years_arr = np.array(years, dtype=float)
    if len(years) >= 3:
        z_snow = np.polyfit(years_arr, snowmelt_doys, 1)
        ax1.plot(years, np.polyval(z_snow, years_arr), "--", color="#1f77b4",
                 linewidth=1, alpha=0.6)
        z_fire = np.polyfit(years_arr, fire_onset_doys, 1)
        ax1.plot(years, np.polyval(z_fire, years_arr), "--", color="#d62728",
                 linewidth=1, alpha=0.6)
        z_lag = np.polyfit(years_arr, lags, 1)
        ax2.plot(years, np.polyval(z_lag, years_arr), "--", color="#2ca02c",
                 linewidth=1, alpha=0.6)

    ax1.set_title("Snowmelt-to-Fire Season Lag Analysis")

    # Combine legends
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc="upper left")

    fig.tight_layout()

    if save_path:
        fig.savefig(save_path)
        logger.info("Saved: %s", save_path)

    return fig, (ax1, ax2)


def plot_snow_fdi_crosscorrelation(lags, correlations, optimal_lag,
                                   figsize=(8, 5), save_path=None):
    """Cross-correlation function plot between snowmelt and FDI.

    Args:
        lags: array of lag values in days
        correlations: array of correlation values at each lag
        optimal_lag: optimal lag value to highlight
        figsize: figure size
        save_path: output path

    Returns:
        fig, ax
    """
    import matplotlib.pyplot as plt
    _apply_style()

    fig, ax = plt.subplots(1, 1, figsize=figsize)

    ax.bar(lags, correlations, width=0.8, color="#1f77b4", alpha=0.7,
           edgecolor="none")
    ax.axvline(optimal_lag, color="#d62728", linestyle="--", linewidth=1.5,
               label=f"Optimal lag = {optimal_lag} days")
    ax.axhline(0, color="black", linewidth=0.5)

    # Significance bounds (approximate 95% CI for white noise)
    n_eff = len(correlations)
    if n_eff > 0:
        ci = 1.96 / np.sqrt(n_eff)
        ax.axhline(ci, color="gray", linestyle=":", linewidth=0.8,
                   label=f"95% CI (+/-{ci:.2f})")
        ax.axhline(-ci, color="gray", linestyle=":", linewidth=0.8)

    ax.set_xlabel("Lag (days)")
    ax.set_ylabel("Correlation")
    ax.set_title("Snow-FDI Cross-Correlation")
    ax.legend()
    ax.grid(True, alpha=0.2)
    fig.tight_layout()

    if save_path:
        fig.savefig(save_path)
        logger.info("Saved: %s", save_path)

    return fig, ax


def plot_snowmelt_rate_severity(bins_data, variable, figsize=(10, 6),
                                save_path=None):
    """Box plots of FDI values grouped by snowmelt rate category.

    Shows whether faster snowmelt leads to higher FDI values.

    Args:
        bins_data: dict mapping category name (e.g., "Fast", "Medium",
                   "Slow") → array of FDI values
        variable: FDI variable name for labeling
        figsize: figure size
        save_path: output path

    Returns:
        fig, ax
    """
    import matplotlib.pyplot as plt
    _apply_style()

    fig, ax = plt.subplots(1, 1, figsize=figsize)

    # Order categories from Fast to Slow
    order = ["Fast", "Medium", "Slow"]
    categories = [c for c in order if c in bins_data]
    # Add any categories not in the standard order
    for c in bins_data:
        if c not in categories:
            categories.append(c)

    data_list = [bins_data[c] for c in categories]
    category_colors = {"Fast": "#d62728", "Medium": "#ff7f0e", "Slow": "#2ca02c"}

    bp = ax.boxplot(data_list, patch_artist=True,
                    widths=0.5, showmeans=True,
                    meanprops=dict(marker="D", markerfacecolor="black",
                                   markersize=5))
    ax.set_xticks(range(1, len(categories) + 1))
    ax.set_xticklabels(categories)

    for patch, cat in zip(bp["boxes"], categories):
        patch.set_facecolor(category_colors.get(cat, "#999999"))
        patch.set_alpha(0.7)

    ax.set_xlabel("Snowmelt Rate Category")
    ax.set_ylabel(f"{variable} Value")
    ax.set_title(f"{variable} by Snowmelt Rate Category")

    # Add sample sizes
    for i, cat in enumerate(categories):
        n = len(bins_data[cat])
        ax.text(i + 1, ax.get_ylim()[0], f"n={n}", ha="center", va="bottom",
                fontsize=7)

    fig.tight_layout()

    if save_path:
        fig.savefig(save_path)
        logger.info("Saved: %s", save_path)

    return fig, ax


def generate_all_figures(data_store, output_dir, fdis=None, months=None):
    """Generate a complete set of publication figures.

    This is the main entry point that orchestrates all figure types.

    Args:
        data_store: AnalysisDataStore instance
        output_dir: directory to save figures
        fdis: list of FDI variable names (default: auto-detect)
        months: list of (year, month) tuples (default: all available)

    Returns:
        generated: list of saved file paths
    """
    import matplotlib
    matplotlib.use("Agg")  # Non-interactive backend
    import matplotlib.pyplot as plt

    from . import hotspots, seasonality, correlation

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    generated = []

    lats = data_store.lats
    lons = data_store.lons

    if months is None:
        months = data_store.available_months()
    if not months:
        logger.error("No data available")
        return generated

    if fdis is None:
        # Auto-detect from first available month
        y, m = months[0]
        all_vars = data_store.get_variables(y, m)
        from aorc_tools.analysis import ALL_FDI_VARS
        fdi_vars = [v for v in all_vars if v in ALL_FDI_VARS]
        fdis = fdi_vars if fdi_vars else all_vars[:5]

    logger.info("Generating figures for %d FDIs across %d months",
                len(fdis), len(months))

    # --- Figure 1: Hotspot maps per FDI ---
    fdi_data = {}
    for fdi in fdis:
        try:
            dates, data = data_store.load_multi_month(months, fdi, "daily_max")
            fdi_data[fdi] = (dates, data)

            # Individual hotspot map
            mask, means, thresh = hotspots.find_hotspots(data, percentile=95)
            path = output_dir / f"hotspot_{fdi}.png"
            fig, _ = plot_hotspot_map(
                lats, lons, means,
                title=f"{fdi} Hotspots (95th percentile, threshold={thresh:.1f})",
                hotspot_mask=mask, save_path=str(path))
            plt.close(fig)
            generated.append(str(path))

            # Exceedance frequency
            freq = hotspots.exceedance_frequency(data, thresh)
            path = output_dir / f"exceedance_{fdi}.png"
            fig, _ = plot_exceedance_map(
                lats, lons, freq, fdi_name=fdi,
                threshold=thresh, save_path=str(path))
            plt.close(fig)
            generated.append(str(path))

            # Peak timing
            peak_dates, peak_vals, _ = hotspots.percentile_timing(data, dates)
            if len(peak_dates) > 0:
                path = output_dir / f"peak_timing_{fdi}.png"
                fig, _ = plot_peak_timing(
                    peak_dates, peak_vals, fdi_name=fdi, save_path=str(path))
                plt.close(fig)
                generated.append(str(path))

            # Lowest risk
            safe, means, _ = hotspots.lowest_risk_points(data, percentile=10)
            path = output_dir / f"lowest_risk_{fdi}.png"
            fig, _ = plot_lowest_risk_map(
                lats, lons, safe, means, save_path=str(path))
            plt.close(fig)
            generated.append(str(path))

        except Exception as e:
            logger.warning("Failed to generate figures for %s: %s", fdi, e)

    # --- Figure 2: Cross-FDI agreement ---
    if len(fdi_data) >= 2:
        try:
            fdi_arrays = {name: d for name, (_, d) in fdi_data.items()}
            agreement, fdi_masks = hotspots.cross_fdi_hotspot_agreement(
                fdi_arrays, percentile=90)
            path = output_dir / "cross_fdi_agreement.png"
            fig = plot_multi_hotspot_comparison(
                lats, lons, fdi_masks, agreement, save_path=str(path))
            plt.close(fig)
            generated.append(str(path))
        except Exception as e:
            logger.warning("Failed cross-FDI agreement: %s", e)

    # --- Figure 3: Seasonal profiles ---
    for fdi in fdis:
        if fdi not in fdi_data:
            continue
        try:
            dates, data = fdi_data[fdi]
            doy_vals, profile = seasonality.compute_seasonal_profile(dates, data)
            path = output_dir / f"seasonal_profile_{fdi}.png"
            fig, _ = plot_seasonal_profile(
                doy_vals, profile, fdi_name=fdi, save_path=str(path))
            plt.close(fig)
            generated.append(str(path))
        except Exception as e:
            logger.warning("Failed seasonal profile for %s: %s", fdi, e)

    # --- Figure 4: FDI similarity matrix ---
    if len(fdi_data) >= 2:
        try:
            from . import monte_carlo
            fdi_means = {}
            for name, (_, d) in fdi_data.items():
                fdi_means[name] = np.nanmean(d, axis=0)

            names, matrix, _ = monte_carlo.fdi_similarity_matrix(fdi_means)
            path = output_dir / "fdi_similarity_matrix.png"
            fig, _ = plot_similarity_matrix(
                names, matrix, save_path=str(path))
            plt.close(fig)
            generated.append(str(path))
        except Exception as e:
            logger.warning("Failed similarity matrix: %s", e)

    # --- Figure 5: Severity distribution per FDI ---
    for fdi in fdis:
        if fdi not in fdi_data:
            continue
        try:
            dates, data = fdi_data[fdi]
            from . import intensity
            if fdi not in intensity.SEVERITY_LEVELS:
                continue
            yearly_dist = intensity.annual_severity_distribution(data, dates, fdi)
            if yearly_dist:
                path = output_dir / f"severity_distribution_{fdi}.png"
                fig, _ = plot_severity_distribution(
                    yearly_dist, fdi, save_path=str(path))
                plt.close(fig)
                generated.append(str(path))
        except Exception as e:
            logger.warning("Failed severity distribution for %s: %s", fdi, e)

    # --- Figure 6: Extreme event timeline per FDI ---
    for fdi in fdis:
        if fdi not in fdi_data:
            continue
        try:
            dates, data = fdi_data[fdi]
            from . import intensity
            events = intensity.extreme_event_catalog(data, dates, fdi)
            path = output_dir / f"extreme_events_{fdi}.png"
            fig, _ = plot_extreme_event_timeline(
                events, fdi, save_path=str(path))
            plt.close(fig)
            generated.append(str(path))
        except Exception as e:
            logger.warning("Failed extreme event timeline for %s: %s", fdi, e)

    # --- Figure 7: Return period analysis per FDI ---
    for fdi in fdis:
        if fdi not in fdi_data:
            continue
        try:
            dates, data = fdi_data[fdi]
            from . import intensity
            rp_result = intensity.return_period_analysis(data, dates, fdi)
            if rp_result:
                path = output_dir / f"return_period_{fdi}.png"
                fig, _ = plot_return_periods(
                    rp_result["return_periods"],
                    rp_result["return_levels"],
                    rp_result["annual_maxima"],
                    fdi,
                    gev_params=rp_result.get("gev_params"),
                    save_path=str(path))
                plt.close(fig)
                generated.append(str(path))
        except Exception as e:
            logger.warning("Failed return period for %s: %s", fdi, e)

    # --- Figure 8: All-indices seasonal overlay ---
    if len(fdi_data) >= 2:
        try:
            seasonal_profiles = {}
            for fdi_name, (fdi_dates, fdi_arr) in fdi_data.items():
                _, profile = seasonality.compute_seasonal_profile(
                    fdi_dates, fdi_arr)
                seasonal_profiles[fdi_name] = profile
            if seasonal_profiles:
                path = output_dir / "all_indices_seasonal_overlay.png"
                fig, _ = plot_all_indices_seasonal_overlay(
                    seasonal_profiles, save_path=str(path))
                plt.close(fig)
                generated.append(str(path))
        except Exception as e:
            logger.warning("Failed all-indices overlay: %s", e)

    logger.info("Generated %d figures in %s", len(generated), output_dir)
    return generated
