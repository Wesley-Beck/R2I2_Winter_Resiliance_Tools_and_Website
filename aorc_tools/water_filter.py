"""
Water body exclusion using OpenStreetMap data.

Downloads large water body polygons (≥10 km² by default) via osmnx
and removes AORC grid points that fall within them.

This replaces the existing approach that required manual shapefile sourcing.
"""

import logging
from pathlib import Path

import numpy as np
import geopandas as gpd
from shapely.ops import unary_union

logger = logging.getLogger(__name__)

# Local cache for downloaded water body data
WATER_CACHE_DIR = Path.home() / ".aorc_cache" / "water"


def get_large_water_bodies(boundary, min_area_km2=10.0, cache_name="wup_water"):
    """Download large water body polygons from OpenStreetMap.

    Uses osmnx to fetch water features, filters by area threshold.
    Caches result locally to avoid repeated downloads.

    Args:
        boundary: Shapely geometry defining the search area (WGS84).
        min_area_km2: Minimum water body area in km² (default 10.0
            to capture Lake Superior but skip small ponds/streams).
        cache_name: Name for the local cache file.

    Returns:
        Shapely geometry (union of all large water bodies), or None
        if no water bodies meet the threshold.
    """
    cache_file = WATER_CACHE_DIR / f"{cache_name}.gpkg"

    if cache_file.exists():
        logger.info("Loading cached water bodies from %s", cache_file)
        gdf = gpd.read_file(cache_file)
        return unary_union(gdf.geometry) if len(gdf) > 0 else None

    # Download from OSM
    import osmnx as ox

    logger.info("Downloading water bodies from OpenStreetMap...")
    try:
        water = ox.features_from_polygon(
            boundary.buffer(0.1),  # Small buffer to catch shoreline features
            tags={"natural": "water"},
        )
    except Exception as e:
        logger.warning("Failed to download water bodies: %s", e)
        return None

    if len(water) == 0:
        logger.info("No water body features found")
        return None

    # Filter to polygons only and compute areas
    water = water[water.geometry.type.isin(["Polygon", "MultiPolygon"])].copy()
    water_projected = water.to_crs(epsg=3857)
    water["area_km2"] = water_projected.geometry.area / 1e6

    large_water = water[water["area_km2"] >= min_area_km2]
    logger.info("Found %d water bodies ≥ %.0f km² (of %d total)",
                len(large_water), min_area_km2, len(water))

    # Cache
    WATER_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    if len(large_water) > 0:
        large_water[["geometry", "area_km2"]].to_file(cache_file, driver="GPKG")

    return unary_union(large_water.geometry) if len(large_water) > 0 else None


def exclude_water_points(points_df, water_geom):
    """Remove points that fall within water body polygons.

    Args:
        points_df: DataFrame with latitude/longitude columns.
        water_geom: Shapely geometry of water bodies (from get_large_water_bodies).

    Returns:
        Filtered DataFrame (only land points).
    """
    if water_geom is None:
        logger.info("No water geometry provided, keeping all points")
        return points_df

    try:
        from shapely.vectorized import contains
        mask = contains(
            water_geom,
            points_df["longitude"].values,
            points_df["latitude"].values,
        )
    except ImportError:
        from shapely.prepared import prep
        from shapely.geometry import Point
        prep_water = prep(water_geom)
        mask = np.array([
            prep_water.contains(Point(row.longitude, row.latitude))
            for _, row in points_df.iterrows()
        ])

    n_removed = mask.sum()
    land_points = points_df[~mask].reset_index(drop=True)
    land_points["point_id"] = range(len(land_points))

    logger.info("Excluded %d water points, %d land points remaining",
                n_removed, len(land_points))
    return land_points
