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
        fdi_vars = [v for v in all_vars if v in
                    {"FWI", "ISI", "BUI", "FFMC", "DMC", "DC",
                     "ERC", "BI", "SC", "FPI", "FM1", "FM10"}]
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

    logger.info("Generated %d figures in %s", len(generated), output_dir)
    return generated
