"""
Unified data access for analysis — reads FDI data from SQLite databases.

Provides a clean API for loading multi-month time series across the
28,408-point grid, with spatial subsetting and temporal aggregation.
"""

import logging
import sqlite3
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class AnalysisDataStore:
    """Read-only access to extracted fire danger index data.

    Loads data from SQLite databases (one per year-month) and provides
    numpy arrays for analysis.
    """

    def __init__(self, output_base="data/output"):
        self.output_base = Path(output_base)
        self._points = None
        self._points_df = None

    @property
    def points(self):
        """Load point index (cached)."""
        if self._points_df is None:
            path = self.output_base / "points_index.csv"
            self._points_df = pd.read_csv(path)
            self._points = self._points_df[["point_id", "latitude", "longitude"]].values
        return self._points_df

    @property
    def n_points(self):
        return len(self.points)

    @property
    def lats(self):
        return self.points["latitude"].values

    @property
    def lons(self):
        return self.points["longitude"].values

    def available_months(self):
        """Return list of (year, month) tuples with data."""
        months = []
        for year_dir in sorted(self.output_base.iterdir()):
            if not year_dir.is_dir() or not year_dir.name.isdigit():
                continue
            year = int(year_dir.name)
            for month_dir in sorted(year_dir.iterdir()):
                if not month_dir.is_dir():
                    continue
                try:
                    month = int(month_dir.name)
                    db_path = month_dir / f"data_{year}_{month:02d}.db"
                    if db_path.exists():
                        months.append((year, month))
                except ValueError:
                    continue
        return months

    def _open_db(self, year, month):
        db_path = self.output_base / str(year) / f"{month:02d}" / f"data_{year}_{month:02d}.db"
        if not db_path.exists():
            raise FileNotFoundError(f"No database for {year}-{month:02d}")
        conn = sqlite3.connect(str(db_path))
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA cache_size=-131072")
        return conn

    def get_variables(self, year, month):
        """List available variables for a month."""
        conn = self._open_db(year, month)
        cursor = conn.execute("SELECT DISTINCT variable FROM data ORDER BY variable")
        variables = [r[0] for r in cursor]
        conn.close()
        return variables

    def load_month(self, year, month, variable):
        """Load a full month of data for one variable.

        Returns:
            timestamps: list of datetime strings
            data: np.ndarray of shape (n_hours, n_points), float32
        """
        conn = self._open_db(year, month)
        rows = conn.execute(
            "SELECT timestamp, values_blob FROM data WHERE variable = ? ORDER BY timestamp",
            (variable,),
        ).fetchall()
        conn.close()

        if not rows:
            raise ValueError(f"No data for {variable} in {year}-{month:02d}")

        timestamps = [r[0] for r in rows]
        n_points = len(rows[0][1]) // 4
        data = np.empty((len(rows), n_points), dtype=np.float32)
        for i, (_, blob) in enumerate(rows):
            data[i] = np.frombuffer(blob, dtype=np.float32)

        return timestamps, data

    def load_daily_max(self, year, month, variable):
        """Load daily maximum values (reduces 744 hours → 31 days).

        Returns:
            days: list of day numbers (1-31)
            data: np.ndarray of shape (n_days, n_points), float32
        """
        timestamps, hourly = self.load_month(year, month, variable)

        # Group by day
        from collections import defaultdict
        day_hours = defaultdict(list)
        for i, ts in enumerate(timestamps):
            day = int(ts.split("-")[2].split(" ")[0])
            day_hours[day].append(i)

        days = sorted(day_hours.keys())
        daily_max = np.empty((len(days), hourly.shape[1]), dtype=np.float32)
        for d_idx, day in enumerate(days):
            indices = day_hours[day]
            daily_max[d_idx] = np.nanmax(hourly[indices], axis=0)

        return days, daily_max

    def load_daily_mean(self, year, month, variable):
        """Load daily mean values."""
        timestamps, hourly = self.load_month(year, month, variable)

        from collections import defaultdict
        day_hours = defaultdict(list)
        for i, ts in enumerate(timestamps):
            day = int(ts.split("-")[2].split(" ")[0])
            day_hours[day].append(i)

        days = sorted(day_hours.keys())
        daily_mean = np.empty((len(days), hourly.shape[1]), dtype=np.float32)
        for d_idx, day in enumerate(days):
            indices = day_hours[day]
            daily_mean[d_idx] = np.nanmean(hourly[indices], axis=0)

        return days, daily_mean

    def load_multi_month(self, months, variable, aggregation="daily_max"):
        """Load multiple months and concatenate.

        Args:
            months: list of (year, month) tuples
            variable: variable name
            aggregation: "hourly", "daily_max", or "daily_mean"

        Returns:
            dates: list of date strings (YYYY-MM-DD for daily, YYYY-MM-DD HH:MM for hourly)
            data: np.ndarray of shape (n_timesteps, n_points)
        """
        all_dates = []
        all_data = []

        for year, month in months:
            try:
                if aggregation == "hourly":
                    ts, d = self.load_month(year, month, variable)
                    all_dates.extend(ts)
                elif aggregation == "daily_max":
                    days, d = self.load_daily_max(year, month, variable)
                    all_dates.extend([f"{year}-{month:02d}-{day:02d}" for day in days])
                elif aggregation == "daily_mean":
                    days, d = self.load_daily_mean(year, month, variable)
                    all_dates.extend([f"{year}-{month:02d}-{day:02d}" for day in days])
                all_data.append(d)
            except (FileNotFoundError, ValueError) as e:
                logger.warning("Skipping %d-%02d: %s", year, month, e)

        if not all_data:
            raise ValueError(f"No data found for {variable}")

        return all_dates, np.concatenate(all_data, axis=0)

    def load_spatial_mean_timeseries(self, months, variable, aggregation="daily_max"):
        """Load time series of spatially-averaged values (single value per timestep).

        Useful for seasonality analysis.
        """
        dates, data = self.load_multi_month(months, variable, aggregation)
        spatial_mean = np.nanmean(data, axis=1)
        return dates, spatial_mean
