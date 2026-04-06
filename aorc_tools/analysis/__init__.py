"""
Wildfire risk analysis and figure generation package.

Modules:
    data_access   — Unified data loading from SQLite / .bin / CSV
    hotspots      — Spatial hotspot detection and percentile mapping
    seasonality   — Fire season onset/offset detection with tunable filters
    correlation   — FDI-wildfire occurrence correlation analysis
    monte_carlo   — Monte Carlo FDI cross-comparison and similarity
    figures       — Publication-quality figure generation
"""

# Known fire danger index variable names across all FDI systems
ALL_FDI_VARS = frozenset({
    "FWI", "ISI", "BUI", "FFMC", "DMC", "DC",     # Canadian FWI
    "ERC", "BI", "SC", "FM1", "FM10", "FM100", "FM1000",  # NFDRS
    "FPI", "EMC", "RG",                             # FPI
})

# Subset most commonly used for comparison/correlation analysis
CORE_FDI_VARS = frozenset({
    "FWI", "ISI", "BUI", "ERC", "BI", "SC", "FPI",
})

# WUP bounding box (shared between correlation.py and wildfire-overlay.js)
WUP_BBOX = {
    "xmin": -90.5,
    "ymin": 45.9,
    "xmax": -87.4,
    "ymax": 48.3,
}
