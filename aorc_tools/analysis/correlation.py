"""
FDI-wildfire occurrence correlation analysis.

Compares fire danger index values against actual wildfire incidents
from the NIFC Interagency Fire Perimeter History database to determine
which FDI systems best predict real fires in the WUP.

Methods:
1. Point-biserial correlation: FDI value vs fire/no-fire binary
2. ROC/AUC analysis: How well does FDI discriminate fire days?
3. Hit rate / false alarm analysis at various thresholds
4. Spatial correlation: FDI at fire locations vs background
"""

import json
import logging
from datetime import datetime

import numpy as np

logger = logging.getLogger(__name__)

# WUP bounding box for NIFC queries
WUP_BBOX = {
    "xmin": -90.5,
    "ymin": 45.9,
    "xmax": -87.4,
    "ymax": 48.3,
}

NIFC_URL = (
    "https://services3.arcgis.com/T4QMspbfLg3qTGWY/arcgis/rest/services/"
    "InteragencyFirePerimeterHistory_All_Years_View/FeatureServer/0/query"
)


def fetch_nifc_fires(year_start, year_end):
    """Fetch NIFC wildfire perimeters for the WUP region.

    Args:
        year_start: first year (inclusive)
        year_end: last year (inclusive)

    Returns:
        list of dicts with keys: name, acres, discovery_date, latitude,
            longitude, cause, year
    """
    import urllib.request
    import urllib.parse

    fires = []
    bbox = WUP_BBOX

    for year in range(year_start, year_end + 1):
        where = (
            f"FireDiscoveryDateTime >= DATE '{year}-01-01' AND "
            f"FireDiscoveryDateTime <= DATE '{year}-12-31'"
        )
        params = urllib.parse.urlencode({
            "where": where,
            "geometry": json.dumps({
                "xmin": bbox["xmin"], "ymin": bbox["ymin"],
                "xmax": bbox["xmax"], "ymax": bbox["ymax"],
                "spatialReference": {"wkid": 4326},
            }),
            "geometryType": "esriGeometryEnvelope",
            "spatialRel": "esriSpatialRelIntersects",
            "outFields": (
                "IncidentName,GISAcres,FireDiscoveryDateTime,"
                "POOLatitude,POOLongitude,FireCause,FireCauseGeneral"
            ),
            "returnGeometry": "false",
            "f": "json",
            "resultRecordCount": 2000,
        })

        url = f"{NIFC_URL}?{params}"
        try:
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode())

            for feat in data.get("features", []):
                attr = feat["attributes"]
                disc_ts = attr.get("FireDiscoveryDateTime")
                if disc_ts:
                    disc_date = datetime.utcfromtimestamp(disc_ts / 1000)
                else:
                    disc_date = None

                fires.append({
                    "name": attr.get("IncidentName", "Unknown"),
                    "acres": attr.get("GISAcres", 0),
                    "discovery_date": disc_date,
                    "latitude": attr.get("POOLatitude"),
                    "longitude": attr.get("POOLongitude"),
                    "cause": attr.get("FireCauseGeneral") or attr.get("FireCause"),
                    "year": year,
                })
        except Exception as e:
            logger.warning("Failed to fetch NIFC data for %d: %s", year, e)

    logger.info("Fetched %d fires from NIFC (%d-%d)", len(fires), year_start, year_end)
    return fires


def build_fire_calendar(fires, year_start, year_end):
    """Build a binary fire/no-fire calendar from NIFC data.

    Args:
        fires: list of fire dicts from fetch_nifc_fires()
        year_start, year_end: range

    Returns:
        fire_dates: set of "YYYY-MM-DD" strings when fires were discovered
        fires_by_date: dict mapping "YYYY-MM-DD" → list of fire dicts
    """
    fire_dates = set()
    fires_by_date = {}

    for f in fires:
        if f["discovery_date"] is None:
            continue
        date_str = f["discovery_date"].strftime("%Y-%m-%d")
        fire_dates.add(date_str)
        if date_str not in fires_by_date:
            fires_by_date[date_str] = []
        fires_by_date[date_str].append(f)

    return fire_dates, fires_by_date


def find_nearest_point(fire_lat, fire_lon, grid_lats, grid_lons):
    """Find the nearest grid point to a fire location.

    Args:
        fire_lat, fire_lon: fire coordinates
        grid_lats, grid_lons: arrays of grid coordinates

    Returns:
        point_index: integer index of nearest grid point
        distance_km: approximate distance in km
    """
    dlat = grid_lats - fire_lat
    dlon = grid_lons - fire_lon
    # Approximate distance using equirectangular projection
    cos_lat = np.cos(np.radians(fire_lat))
    dist_sq = dlat ** 2 + (dlon * cos_lat) ** 2
    idx = np.argmin(dist_sq)
    dist_km = np.sqrt(dist_sq[idx]) * 111.0  # rough deg-to-km
    return int(idx), float(dist_km)


def point_biserial_correlation(fdi_values, fire_binary):
    """Compute point-biserial correlation between FDI and fire occurrence.

    Args:
        fdi_values: 1-D array of daily FDI values (spatial mean or at-point)
        fire_binary: 1-D boolean/int array (1 = fire day, 0 = no fire)

    Returns:
        r: correlation coefficient
        n_fire: number of fire days
        n_nofire: number of non-fire days
        mean_fire: mean FDI on fire days
        mean_nofire: mean FDI on non-fire days
    """
    valid = ~np.isnan(fdi_values)
    fdi = fdi_values[valid]
    fire = np.asarray(fire_binary)[valid].astype(bool)

    fire_vals = fdi[fire]
    nofire_vals = fdi[~fire]

    if len(fire_vals) == 0 or len(nofire_vals) == 0:
        return 0.0, len(fire_vals), len(nofire_vals), np.nan, np.nan

    mean_fire = np.mean(fire_vals)
    mean_nofire = np.mean(nofire_vals)
    n = len(fdi)
    n1 = len(fire_vals)
    n0 = len(nofire_vals)
    s = np.std(fdi)

    if s == 0:
        return 0.0, n1, n0, mean_fire, mean_nofire

    r = (mean_fire - mean_nofire) / s * np.sqrt(n1 * n0 / (n * n))
    return float(r), int(n1), int(n0), float(mean_fire), float(mean_nofire)


def roc_analysis(fdi_values, fire_binary, n_thresholds=200):
    """Compute ROC curve and AUC for an FDI as a fire-day classifier.

    Args:
        fdi_values: 1-D array of daily FDI values
        fire_binary: 1-D boolean/int array
        n_thresholds: number of threshold points

    Returns:
        dict with:
            fpr: false positive rates (array)
            tpr: true positive rates (array)
            auc: area under ROC curve
            thresholds: the threshold values tested
            optimal_threshold: threshold maximizing Youden's J
    """
    valid = ~np.isnan(fdi_values)
    fdi = fdi_values[valid]
    fire = np.asarray(fire_binary)[valid].astype(bool)

    if fire.sum() == 0 or (~fire).sum() == 0:
        return {"fpr": np.array([0, 1]), "tpr": np.array([0, 1]),
                "auc": 0.5, "thresholds": np.array([]), "optimal_threshold": np.nan}

    lo, hi = np.nanmin(fdi), np.nanmax(fdi)
    thresholds = np.linspace(lo, hi, n_thresholds)

    tpr = np.empty(n_thresholds)
    fpr = np.empty(n_thresholds)

    n_pos = fire.sum()
    n_neg = (~fire).sum()

    for i, t in enumerate(thresholds):
        predicted = fdi >= t
        tp = (predicted & fire).sum()
        fp = (predicted & ~fire).sum()
        tpr[i] = tp / n_pos
        fpr[i] = fp / n_neg

    # Sort by FPR for proper ROC curve
    order = np.argsort(fpr)
    fpr = fpr[order]
    tpr = tpr[order]
    thresholds = thresholds[order]

    # AUC via trapezoidal rule
    _trapz = getattr(np, "trapezoid", None) or np.trapz
    auc = float(_trapz(tpr, fpr))

    # Youden's J statistic
    j = tpr - fpr
    best_idx = np.argmax(j)
    optimal_threshold = float(thresholds[best_idx])

    return {
        "fpr": fpr,
        "tpr": tpr,
        "auc": auc,
        "thresholds": thresholds,
        "optimal_threshold": optimal_threshold,
    }


def hit_rate_analysis(fdi_values, fire_binary, thresholds):
    """Compute hit rate and false alarm rate at specified thresholds.

    Args:
        fdi_values: 1-D array of daily FDI values
        fire_binary: 1-D boolean/int array
        thresholds: list of threshold values

    Returns:
        list of dicts with: threshold, hit_rate (TPR), false_alarm_rate (FPR),
            precision, f1_score
    """
    valid = ~np.isnan(fdi_values)
    fdi = fdi_values[valid]
    fire = np.asarray(fire_binary)[valid].astype(bool)

    results = []
    n_pos = fire.sum()
    n_neg = (~fire).sum()

    for t in thresholds:
        predicted = fdi >= t
        tp = (predicted & fire).sum()
        fp = (predicted & ~fire).sum()
        fn = (~predicted & fire).sum()

        hit_rate = tp / n_pos if n_pos > 0 else 0.0
        far = fp / n_neg if n_neg > 0 else 0.0
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        f1 = 2 * tp / (2 * tp + fp + fn) if (2 * tp + fp + fn) > 0 else 0.0

        results.append({
            "threshold": float(t),
            "hit_rate": float(hit_rate),
            "false_alarm_rate": float(far),
            "precision": float(precision),
            "f1_score": float(f1),
        })

    return results


def compare_fdis(fdi_data_dict, fire_binary, dates, fire_dates):
    """Compare multiple FDIs against fire occurrence.

    Args:
        fdi_data_dict: dict mapping FDI name → (n_days, n_points) array
        fire_binary: 1-D boolean array aligned with dates
        dates: list of date strings
        fire_dates: set of date strings with fires

    Returns:
        comparison: dict mapping FDI name → {
            correlation, auc, optimal_threshold, mean_fire, mean_nofire
        }
        ranking: list of (fdi_name, auc) sorted by AUC descending
    """
    comparison = {}

    for name, data in fdi_data_dict.items():
        spatial_mean = np.nanmean(data, axis=1)

        r, n1, n0, mf, mnf = point_biserial_correlation(spatial_mean, fire_binary)
        roc = roc_analysis(spatial_mean, fire_binary)

        comparison[name] = {
            "correlation": r,
            "auc": roc["auc"],
            "optimal_threshold": roc["optimal_threshold"],
            "mean_fire_day": mf,
            "mean_non_fire_day": mnf,
            "n_fire_days": n1,
            "n_non_fire_days": n0,
        }

    ranking = sorted(comparison.items(), key=lambda x: x[1]["auc"], reverse=True)

    return comparison, ranking
