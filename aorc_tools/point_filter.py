"""
Point index generation from shapefiles.

Rewritten from the existing PointsTab in program1_data_extraction.py
to use vectorized shapely operations instead of nested Python loops.

The existing code iterated every lat/lon pair individually:
    for lat in lats:
        for lon in lons:
            pt = Point(lon, lat)
            if study_union.contains(pt): ...

This version uses shapely.vectorized.contains() for ~100× speedup.
"""

import logging

import numpy as np
import pandas as pd
import geopandas as gpd
from shapely.ops import unary_union

logger = logging.getLogger(__name__)


def load_boundary(filepath):
    """Load and dissolve a study area boundary from a shapefile/geopackage.

    Accepts .shp, .gpkg, .geojson. Reprojects to WGS84 if needed.
    Returns a single dissolved geometry.

    Ported from existing PointsTab logic: gdf → dissolve → unary_union.

    Args:
        filepath: Path to the shapefile or geopackage.

    Returns:
        shapely geometry (Polygon or MultiPolygon) in EPSG:4326.
    """
    gdf = gpd.read_file(filepath)

    # Reproject to WGS84 if needed
    if gdf.crs is not None and gdf.crs.to_epsg() != 4326:
        gdf = gdf.to_crs(epsg=4326)
        logger.info("Reprojected boundary to EPSG:4326")

    boundary = unary_union(gdf.geometry)
    logger.info("Loaded boundary with %.1f km² area (approx)",
                gdf.to_crs(epsg=3857).area.sum() / 1e6)
    return boundary


def generate_point_index(boundary, aorc_lats, aorc_lons):
    """Generate a DataFrame of AORC grid points within a boundary.

    Uses vectorized point-in-polygon testing via shapely, replacing the
    existing nested-loop approach for ~100× speedup.

    Args:
        boundary: Shapely geometry (from load_boundary).
        aorc_lats: 1D array of AORC latitude values.
        aorc_lons: 1D array of AORC longitude values.

    Returns:
        DataFrame with columns: point_id, latitude, longitude, lat_idx, lon_idx.
        lat_idx/lon_idx are indices into the original AORC arrays for .isel() access.
    """
    # Bounding box pre-filter (fast numpy masking on 1D arrays)
    minx, miny, maxx, maxy = boundary.bounds
    lat_mask = (aorc_lats >= miny) & (aorc_lats <= maxy)
    lon_mask = (aorc_lons >= minx) & (aorc_lons <= maxx)

    candidate_lats = aorc_lats[lat_mask]
    candidate_lons = aorc_lons[lon_mask]
    lat_global_idx = np.where(lat_mask)[0]
    lon_global_idx = np.where(lon_mask)[0]

    logger.info("Bounding box candidates: %d lats × %d lons = %d points",
                len(candidate_lats), len(candidate_lons),
                len(candidate_lats) * len(candidate_lons))

    # Build meshgrid of candidate points
    lon_grid, lat_grid = np.meshgrid(candidate_lons, candidate_lats)
    lon_idx_grid, lat_idx_grid = np.meshgrid(
        lon_global_idx, lat_global_idx
    )

    # Vectorized point-in-polygon test
    try:
        from shapely.vectorized import contains
        mask = contains(boundary, lon_grid.ravel(), lat_grid.ravel())
    except ImportError:
        # Fallback: use prepared geometry with STRtree
        from shapely.prepared import prep
        from shapely.geometry import Point
        logger.warning("shapely.vectorized not available, using prepared geometry (slower)")
        prep_boundary = prep(boundary)
        flat_lons = lon_grid.ravel()
        flat_lats = lat_grid.ravel()
        mask = np.array([
            prep_boundary.contains(Point(lo, la))
            for lo, la in zip(flat_lons, flat_lats)
        ])

    n_inside = mask.sum()
    logger.info("Points inside boundary: %d", n_inside)

    # Build result DataFrame
    points = pd.DataFrame({
        "point_id": range(n_inside),
        "latitude": lat_grid.ravel()[mask],
        "longitude": lon_grid.ravel()[mask],
        "lat_idx": lat_idx_grid.ravel()[mask],
        "lon_idx": lon_idx_grid.ravel()[mask],
    })

    return points


def save_point_index(points_df, output_path):
    """Save point index DataFrame to CSV.

    Args:
        points_df: DataFrame from generate_point_index().
        output_path: Path to output CSV file.
    """
    points_df.to_csv(output_path, index=False)
    logger.info("Saved %d points to %s", len(points_df), output_path)


def load_point_index(filepath):
    """Load a previously generated point index CSV.

    Args:
        filepath: Path to the CSV file.

    Returns:
        DataFrame with columns: point_id, latitude, longitude, lat_idx, lon_idx.
    """
    return pd.read_csv(filepath)
