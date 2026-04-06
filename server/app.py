"""
FastAPI server for the WUP Wildfire Risk Explorer.

Serves climate data from SQLite databases and binary .bin files,
replacing static file serving with dynamic API endpoints.

Endpoints:
    GET /                     → Redirect to explorer
    GET /api/points           → Point index as JSON
    GET /api/data/{var}/{y}/{m} → Binary data (same format as .bin)
    GET /api/data/{var}/{y}/{m}/{hour} → Single-hour slice
    GET /api/availability/{y} → Which months have data
    GET /api/fdi-table        → Dataset capabilities JSON
    GET /api/variables/{y}/{m} → Available variables for a month

Static files served from ../website/ for the frontend.

Usage:
    cd server/
    uvicorn app:app --reload --port 8000
    # or from project root:
    python -m uvicorn server.app:app --reload --port 8000
"""

import json
import sqlite3
import struct
from pathlib import Path
from typing import Optional

import numpy as np
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response, RedirectResponse
from fastapi.staticfiles import StaticFiles

# Resolve paths relative to this file
SERVER_DIR = Path(__file__).parent
PROJECT_DIR = SERVER_DIR.parent
DATA_DIR = PROJECT_DIR / "data" / "output"
WEBSITE_DIR = PROJECT_DIR / "website"

app = FastAPI(
    title="WUP Wildfire Risk API",
    description="Serves fire danger index data for the Western Upper Peninsula of Michigan",
    version="1.0.0",
)

# CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)


# =====================================================================
# Database helpers
# =====================================================================

def _get_db_path(year: int, month: int) -> Path:
    return DATA_DIR / str(year) / f"{month:02d}" / f"data_{year}_{month:02d}.db"


def _open_db(year: int, month: int) -> sqlite3.Connection:
    db_path = _get_db_path(year, month)
    if not db_path.exists():
        raise HTTPException(404, f"No data for {year}-{month:02d}")
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA cache_size=-65536")  # 64MB read cache
    return conn


def _get_bin_path(variable: str, year: int, month: int) -> Path:
    return DATA_DIR / str(year) / f"{month:02d}" / "web" / f"{variable}.bin"


# =====================================================================
# API Endpoints
# =====================================================================

@app.get("/")
async def root():
    """Redirect to the explorer."""
    return RedirectResponse(url="/explorer/index.html")


@app.head("/api/points")
async def head_points():
    """HEAD probe for API detection — returns 200 with no body."""
    points_file = DATA_DIR / "points_index.csv"
    if not points_file.exists():
        raise HTTPException(404, "Point index not found.")
    return Response(status_code=200)


@app.get("/api/points")
async def get_points():
    """Return point index as JSON array."""
    points_file = DATA_DIR / "points_index.csv"
    if not points_file.exists():
        raise HTTPException(404, "Point index not found. Run aorc-tools points first.")

    import csv
    with open(points_file) as f:
        reader = csv.DictReader(f)
        points = []
        for row in reader:
            points.append({
                "point_id": int(row["point_id"]),
                "latitude": float(row["latitude"]),
                "longitude": float(row["longitude"]),
            })
    return points


@app.get("/api/data/{variable}/{year}/{month}")
async def get_monthly_data(variable: str, year: int, month: int):
    """Serve binary .bin file for a variable/year/month.

    Returns the exact same binary format the browser already expects:
    uint32 n_points, uint32 n_hours, uint32 ts_block_len,
    timestamps (UTF-8), float32 arrays.
    """
    bin_path = _get_bin_path(variable, year, month)
    if bin_path.exists():
        return FileResponse(
            bin_path,
            media_type="application/octet-stream",
            headers={"Cache-Control": "public, max-age=3600"},
        )

    # Fall back to SQLite if .bin doesn't exist
    try:
        conn = _open_db(year, month)
    except HTTPException:
        raise HTTPException(404, f"No data for {variable} in {year}-{month:02d}")

    try:
        rows = conn.execute(
            "SELECT timestamp, values_blob FROM data WHERE variable = ? ORDER BY timestamp",
            (variable,),
        ).fetchall()
    finally:
        conn.close()

    if not rows:
        raise HTTPException(404, f"Variable '{variable}' not found in {year}-{month:02d}")

    # Build binary response on-the-fly from SQLite
    n_points = len(rows[0][1]) // 4
    n_hours = len(rows)
    timestamps = [r[0] for r in rows]
    ts_block = "\n".join(timestamps).encode("utf-8")

    # Pad ts_block to 4-byte alignment so Float32Array views work directly
    padding = (4 - len(ts_block) % 4) % 4
    ts_block_padded = ts_block + b"\x00" * padding

    # Pre-allocate full buffer instead of O(n²) bytearray concatenation
    header = struct.pack("<III", n_points, n_hours, len(ts_block_padded))
    parts = [header, ts_block_padded]
    parts.extend(blob for _, blob in rows)
    content = b"".join(parts)

    return Response(
        content=content,
        media_type="application/octet-stream",
        headers={"Cache-Control": "public, max-age=3600"},
    )


@app.get("/api/data/{variable}/{year}/{month}/{hour}")
async def get_hourly_data(variable: str, year: int, month: int, hour: int,
                          day: int = Query(1, ge=1, le=31)):
    """Get a single hour of data as JSON.

    Returns { "timestamp": "...", "values": [float, ...] }
    """
    timestamp_str = f"{year}-{month:02d}-{day:02d} {hour:02d}:00"

    try:
        conn = _open_db(year, month)
    except HTTPException:
        raise HTTPException(404, f"No data for {year}-{month:02d}")

    try:
        row = conn.execute(
            "SELECT values_blob FROM data WHERE variable = ? AND timestamp = ?",
            (variable, timestamp_str),
        ).fetchone()
    finally:
        conn.close()

    if not row:
        raise HTTPException(404, f"No data for {variable} at {timestamp_str}")

    values = np.frombuffer(row[0], dtype=np.float32).tolist()
    return {"timestamp": timestamp_str, "values": values}


@app.get("/api/availability/{year}")
async def get_availability(year: int):
    """Check which months have data for a given year.

    Returns { "months": { "01": ["FWI", "ERC", ...], "07": [...], ... } }
    """
    year_dir = DATA_DIR / str(year)
    if not year_dir.exists():
        return {"year": year, "months": {}}

    months = {}
    for month_dir in sorted(year_dir.iterdir()):
        if not month_dir.is_dir():
            continue
        month_str = month_dir.name

        # Check web/ directory for .bin files
        web_dir = month_dir / "web"
        if web_dir.exists():
            variables = [f.stem for f in web_dir.glob("*.bin")]
            if variables:
                months[month_str] = sorted(variables)
                continue

        # Fall back to checking SQLite
        db_files = list(month_dir.glob("data_*.db"))
        if db_files:
            try:
                conn = sqlite3.connect(str(db_files[0]))
                cursor = conn.execute("SELECT DISTINCT variable FROM data ORDER BY variable")
                variables = [r[0] for r in cursor]
                conn.close()
                if variables:
                    months[month_str] = variables
            except Exception:
                pass

    return {"year": year, "months": months}


@app.get("/api/variables/{year}/{month}")
async def get_variables(year: int, month: int):
    """List available variables for a specific month."""
    web_dir = DATA_DIR / str(year) / f"{month:02d}" / "web"

    # Check variables.json manifest first
    manifest = web_dir / "variables.json"
    if manifest.exists():
        with open(manifest) as f:
            return {"variables": json.load(f)}

    # Check .bin files
    if web_dir.exists():
        variables = sorted(f.stem for f in web_dir.glob("*.bin"))
        if variables:
            return {"variables": variables}

    # Fall back to SQLite
    try:
        conn = _open_db(year, month)
        cursor = conn.execute("SELECT DISTINCT variable FROM data ORDER BY variable")
        variables = [r[0] for r in cursor]
        conn.close()
        return {"variables": variables}
    except HTTPException:
        raise HTTPException(404, f"No data for {year}-{month:02d}")


@app.get("/api/fdi-table")
async def get_fdi_table():
    """Return the FDI dataset capability table as JSON."""
    csv_path = PROJECT_DIR / "data" / "fdi_dataset_capabilities.csv"
    if not csv_path.exists():
        raise HTTPException(404, "FDI capability table not found")

    import csv
    with open(csv_path) as f:
        reader = csv.DictReader(f)
        return [dict(row) for row in reader]


@app.get("/api/benchmark")
async def get_benchmark():
    """Return current data coverage statistics."""
    stats = {"years": {}, "total_months": 0, "total_variables": set()}

    if not DATA_DIR.exists():
        return {"years": {}, "total_months": 0, "total_variables": []}

    for year_dir in sorted(DATA_DIR.iterdir()):
        if not year_dir.is_dir() or not year_dir.name.isdigit():
            continue
        year = year_dir.name
        month_count = 0
        for month_dir in year_dir.iterdir():
            if not month_dir.is_dir():
                continue
            web_dir = month_dir / "web"
            if web_dir.exists() and list(web_dir.glob("*.bin")):
                month_count += 1
                for f in web_dir.glob("*.bin"):
                    stats["total_variables"].add(f.stem)
        if month_count > 0:
            stats["years"][year] = month_count
            stats["total_months"] += month_count

    stats["total_variables"] = sorted(stats["total_variables"])
    return stats


# =====================================================================
# Static file serving (website frontend)
# =====================================================================


@app.middleware("http")
async def no_cache_dev_assets(request, call_next):
    """Disable browser caching for JS/CSS during development."""
    response = await call_next(request)
    path = request.url.path
    if path.endswith((".js", ".css", ".html")):
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response


# Mount the website directory for static file serving
# This replaces the need for a separate HTTP server
app.mount("/explorer", StaticFiles(directory=str(WEBSITE_DIR), html=True), name="explorer")
# Also serve data directory for backward compatibility with direct .bin access
app.mount("/data", StaticFiles(directory=str(DATA_DIR)), name="data")
