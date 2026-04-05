"""
Local mirror for climate projection datasets (NEX-GDDP-CMIP6, GLARM).

Same pattern as local_mirror.py for AORC: downloads only study-area points
as compressed .npz files for fast offline computation.

Storage: {mirror_dir}/{source}/{gcm}/{scenario}/{year}/{month}.npz
Manifest: {mirror_dir}/{source}/manifest.json
"""

import calendar
import json
import logging
import time
from datetime import datetime
from pathlib import Path

import numpy as np

logger = logging.getLogger(__name__)


class ProjectionMirror:
    """Download and cache climate projection data locally.

    Supports any ClimateModelAdapter that implements get_daily_point_values().
    """

    def __init__(self, mirror_dir, source_name, adapter, points_df):
        """
        Args:
            mirror_dir: Base directory for all projection mirrors.
            source_name: Key like "nex-gddp-cmip6/ACCESS-CM2/ssp585".
            adapter: ClimateModelAdapter instance.
            points_df: DataFrame with point_id, latitude, longitude, lat_idx, lon_idx.
        """
        self.base_dir = Path(mirror_dir)
        self.source_name = source_name
        self.mirror_dir = self.base_dir / source_name.replace("/", "_")
        self.mirror_dir.mkdir(parents=True, exist_ok=True)
        self.adapter = adapter
        self.points_df = points_df
        self.n_points = len(points_df)
        self.lat_indices = points_df["lat_idx"].values
        self.lon_indices = points_df["lon_idx"].values
        self.lat_bounds = (
            points_df["latitude"].min() - 0.05,
            points_df["latitude"].max() + 0.05,
        )
        self.lon_bounds = (
            points_df["longitude"].min() - 0.05,
            points_df["longitude"].max() + 0.05,
        )
        self._manifest = self._load_manifest()

    # ------------------------------------------------------------------
    # Manifest
    # ------------------------------------------------------------------

    def _manifest_path(self):
        return self.mirror_dir / "manifest.json"

    def _load_manifest(self):
        path = self._manifest_path()
        if path.exists():
            with open(path) as f:
                return json.load(f)
        return {"downloaded": {}, "source": self.source_name,
                "n_points": 0, "last_sync": None}

    def _save_manifest(self):
        self._manifest["n_points"] = self.n_points
        self._manifest["source"] = self.source_name
        self._manifest["last_sync"] = datetime.utcnow().isoformat() + "Z"
        with open(self._manifest_path(), "w") as f:
            json.dump(self._manifest, f, indent=2)

    def is_downloaded(self, year, month):
        return f"{year}-{month:02d}" in self._manifest.get("downloaded", {})

    def _month_path(self, year, month):
        return self.mirror_dir / str(year) / f"{month:02d}.npz"

    # ------------------------------------------------------------------
    # Download
    # ------------------------------------------------------------------

    def download_month(self, year, month, force=False):
        """Download one month of projection data for all points.

        Since projection data is daily (not hourly), each day is fetched
        individually and the adapter disaggregates to 24h internally.
        """
        key = f"{year}-{month:02d}"
        npz_path = self._month_path(year, month)

        if not force and npz_path.exists() and self.is_downloaded(year, month):
            logger.info("Already downloaded: %s %s", self.source_name, key)
            return npz_path

        npz_path.parent.mkdir(parents=True, exist_ok=True)
        n_days = calendar.monthrange(year, month)[1]

        logger.info("Downloading %s %s (%d days, %d points)...",
                     self.source_name, key, n_days, self.n_points)

        all_timestamps = []
        var_data = {}
        t_start = time.perf_counter()

        for day in range(1, n_days + 1):
            try:
                daily = self.adapter.get_daily_point_values(
                    year, month, day,
                    self.lat_indices, self.lon_indices,
                    self.lat_bounds, self.lon_bounds,
                )
            except Exception as e:
                logger.warning("Failed day %d: %s", day, e)
                continue

            for ts in daily.get("timestamps", []):
                all_timestamps.append(ts.strftime("%Y-%m-%d %H:%M")
                                       if hasattr(ts, "strftime") else str(ts))

            for var_name in FIRE_WEATHER_VARS:
                if var_name in daily:
                    if var_name not in var_data:
                        var_data[var_name] = []
                    var_data[var_name].append(daily[var_name])

        t_download = time.perf_counter() - t_start

        if not all_timestamps:
            logger.warning("No data downloaded for %s %s", self.source_name, key)
            return None

        # Concatenate and save
        save_dict = {"timestamps": np.array(all_timestamps)}
        for var_name, arrays in var_data.items():
            save_dict[var_name] = np.concatenate(arrays, axis=0).astype(np.float32)

        np.savez_compressed(npz_path, **save_dict)

        size_mb = npz_path.stat().st_size / 1048576
        n_hours = len(all_timestamps)
        logger.info("Saved %s: %.1f MB (%d hours × %d points) [%.1fs]",
                     npz_path.name, size_mb, n_hours, self.n_points, t_download)

        self._manifest.setdefault("downloaded", {})[key] = {
            "path": str(npz_path),
            "size_mb": round(size_mb, 1),
            "n_hours": n_hours,
            "downloaded_at": datetime.utcnow().isoformat() + "Z",
        }
        self._save_manifest()
        return npz_path

    def download_range(self, start_year, end_year, start_month=1, end_month=12,
                       callback=None):
        """Download a range of months. Returns count of new downloads."""
        count = 0
        months = []
        for year in range(start_year, end_year + 1):
            sm = start_month if year == start_year else 1
            em = end_month if year == end_year else 12
            for month in range(sm, em + 1):
                months.append((year, month))

        for i, (year, month) in enumerate(months):
            if self.is_downloaded(year, month):
                if callback:
                    callback(year, month, f"[{i+1}/{len(months)}] Already cached")
                continue

            if callback:
                callback(year, month, f"[{i+1}/{len(months)}] Downloading...")

            try:
                self.download_month(year, month)
                count += 1
            except Exception as e:
                logger.error("Failed %d-%02d: %s", year, month, e)
                if callback:
                    callback(year, month, f"[{i+1}/{len(months)}] FAILED: {e}")

        return count

    # ------------------------------------------------------------------
    # Load from local disk
    # ------------------------------------------------------------------

    def load_month(self, year, month):
        """Load a month from local disk. Same format as local_mirror."""
        import pandas as pd

        npz_path = self._month_path(year, month)
        if not npz_path.exists():
            raise FileNotFoundError(f"No local data for {self.source_name} {year}-{month:02d}")

        data = np.load(npz_path, allow_pickle=True)
        timestamps = data["timestamps"]
        dt_index = pd.DatetimeIndex(timestamps)
        variables = [k for k in data.files if k != "timestamps"]

        result = {}
        n_days = calendar.monthrange(year, month)[1]
        for day in range(1, n_days + 1):
            mask = dt_index.day == day
            if not mask.any():
                continue
            day_times = dt_index[mask]
            daily = {
                "hours": [t.hour for t in day_times],
                "timestamps": day_times,
            }
            for var in variables:
                daily[var] = data[var][mask]
            result[day] = daily

        return result

    def is_month_available(self, year, month):
        return self.is_downloaded(year, month)

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------

    def status(self):
        downloaded = self._manifest.get("downloaded", {})
        total_mb = sum(d.get("size_mb", 0) for d in downloaded.values())
        years = set()
        for key in downloaded:
            years.add(int(key.split("-")[0]))
        return {
            "source": self.source_name,
            "adapter": self.adapter.name,
            "mirror_dir": str(self.mirror_dir),
            "months_downloaded": len(downloaded),
            "years_covered": sorted(years) if years else [],
            "total_size_gb": round(total_mb / 1024, 2),
            "n_points": self.n_points,
            "last_sync": self._manifest.get("last_sync"),
        }


# Variables the fire index pipeline needs
FIRE_WEATHER_VARS = [
    "TMP_2maboveground",
    "SPFH_2maboveground",
    "PRES_surface",
    "UGRD_10maboveground",
    "VGRD_10maboveground",
    "APCP_surface",
    "DSWRF_surface",
    "DLWRF_surface",
]
