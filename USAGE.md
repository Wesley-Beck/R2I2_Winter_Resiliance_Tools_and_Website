# AORC Wildfire Risk Analysis System — Usage Guide

A complete toolkit for computing hourly fire danger indices from NOAA's
Analysis of Record for Calibration (AORC) dataset, focused on the
Western Upper Peninsula of Michigan.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Installation](#installation)
3. [Quick Start](#quick-start)
4. [CLI Reference](#cli-reference)
5. [Output File Guide](#output-file-guide)
6. [Fire Danger Index Descriptions](#fire-danger-index-descriptions)
7. [Fuel Model Selection](#fuel-model-selection)
8. [Fuel Moisture Methods](#fuel-moisture-methods)
9. [Adding NDVI Data for FPI](#adding-ndvi-data-for-fpi)
10. [Troubleshooting](#troubleshooting)

---

## Prerequisites

- **Python** >= 3.9
- **Internet access** for AORC S3 data (bucket is public, no AWS credentials needed)
- **Study area shapefile** — a boundary polygon in `.shp`, `.gpkg`, or `.geojson` format
  - The Western Upper Peninsula shapefile is included at `data/shapefiles/Western_Upper_Peninsula.shp`
  - Includes full Isle Royale coverage (Keweenaw County)
- **RAM**: ~2 GB recommended for ~15,000 grid points
- **Disk**: ~500 MB per year of extracted data (all intermediates)

---

## Installation

```bash
# Clone the repository
git clone https://github.com/wesley-beck/r2i2_winter_resiliance_tools_and_website.git
cd r2i2_winter_resiliance_tools_and_website

# Install as editable package (creates the aorc-tools command)
pip install -e .
```

This installs all dependencies (xarray, zarr, s3fs, geopandas, shapely, etc.)
and registers the `aorc-tools` CLI command.

Verify installation:
```bash
aorc-tools status
```

---

## Quick Start

Three commands take you from shapefile to fire danger data:

### Step 1: Generate point index

This identifies which AORC grid points fall within your study area boundary.

```bash
aorc-tools points \
  --shapefile data/shapefiles/Western_Upper_Peninsula.shp \
  --output ./data/output
```

Output: `data/output/points_index.csv` — a table of ~15,000 land grid points
with their coordinates and AORC array indices.

### Step 2: Extract data and compute indices

This fetches hourly AORC weather data from S3 and computes all fire danger
indices for every point, every hour.

```bash
aorc-tools extract \
  --points ./data/output/points_index.csv \
  --year 2020 \
  --output ./data/output
```

This will take several hours for a full year (8,760 hours x ~15,000 points).
You can extract a single month to test:

```bash
aorc-tools extract \
  --points ./data/output/points_index.csv \
  --year 2020 \
  --start-month 7 --end-month 7 \
  --output ./data/output
```

### Step 3: Browse results

Open the website to view results on a map:

```bash
cd website
python -m http.server 8000
# Then open http://localhost:8000 in your browser
```

Or load any CSV directly in Python, R, or Excel:

```python
import pandas as pd
fwi = pd.read_csv("data/output/2020/07/cfwi/2020_07_FWI.csv", index_col=0)
# Rows = point_id, Columns = "YYYY-MM-DD HH:MM"
print(fwi.describe())
```

---

## CLI Reference

### `aorc-tools points`

Generate AORC grid point index from a study area boundary.

| Flag | Required | Default | Description |
|------|----------|---------|-------------|
| `--shapefile` | Yes | — | Path to boundary file (.shp, .gpkg, .geojson) |
| `--output` | Yes | — | Output directory for `points_index.csv` |
| `--filter-water` / `--no-filter-water` | No | `--filter-water` | Exclude large water bodies (Lake Superior, etc.) via OpenStreetMap |
| `--water-min-area` | No | `10.0` | Minimum water body area (km^2) to exclude |

**Output**: `{output}/points_index.csv` with columns:
- `point_id` — unique integer identifier
- `latitude` — WGS84 latitude
- `longitude` — WGS84 longitude
- `lat_idx` — index into AORC latitude array (for fast data access)
- `lon_idx` — index into AORC longitude array

### `aorc-tools extract`

Extract hourly AORC data and compute fire danger indices for all points.

| Flag | Required | Default | Description |
|------|----------|---------|-------------|
| `--points` | Yes | — | Path to `points_index.csv` from the `points` command |
| `--year` | Yes | — | Year to extract (e.g., 2020) |
| `--output` | No | `./data/output` | Base output directory |
| `--start-month` | No | `1` | First month to extract (1-12) |
| `--end-month` | No | `12` | Last month to extract (1-12) |
| `--fuel-model` | No | `G` | NFDRS fuel model code (A-Z, see [Fuel Model Selection](#fuel-model-selection)) |
| `--fuel-moisture` | No | `emc` | Fuel moisture method: `emc` (equilibrium) or `nelson` (timelag carry-forward) |
| `--latitude` | No | `46.5` | Representative latitude for FWI sunrise/sunset calculations |

### `aorc-tools status`

Check AORC S3 connectivity and report grid dimensions. No arguments.

---

## Output File Guide

Each extraction produces monthly CSV files organized in subdirectories.
**Every intermediate calculation step is saved as a separate CSV** so
researchers can inspect and verify any part of the pipeline.

### Directory Structure

```
data/output/{year}/{month}/
  raw_aorc/                          # Raw AORC values in native units
    {year}_{month}_TMP_2maboveground.csv     # Temperature (K)
    {year}_{month}_SPFH_2maboveground.csv    # Specific humidity (kg/kg)
    {year}_{month}_PRES_surface.csv           # Pressure (Pa)
    {year}_{month}_UGRD_10maboveground.csv   # U-wind (m/s)
    {year}_{month}_VGRD_10maboveground.csv   # V-wind (m/s)
    {year}_{month}_APCP_surface.csv           # Precipitation (mm)
    {year}_{month}_DSWRF_surface.csv          # Shortwave radiation (W/m^2)
    {year}_{month}_DLWRF_surface.csv          # Longwave radiation (W/m^2)

  converted/                         # Unit-converted weather variables
    {year}_{month}_temperature_c.csv          # Temperature (Celsius)
    {year}_{month}_temperature_f.csv          # Temperature (Fahrenheit)
    {year}_{month}_relative_humidity.csv      # Relative humidity (%)
    {year}_{month}_wind_speed_ms.csv          # Wind speed (m/s)
    {year}_{month}_wind_speed_kph.csv         # Wind speed (km/h)
    {year}_{month}_wind_speed_mph.csv         # Wind speed (mph)
    {year}_{month}_precipitation_mm.csv       # Precipitation (mm)

  cfwi/                              # Canadian Fire Weather Index system
    {year}_{month}_FFMC.csv                   # Fine Fuel Moisture Code (0-101)
    {year}_{month}_DMC.csv                    # Duff Moisture Code
    {year}_{month}_DC.csv                     # Drought Code
    {year}_{month}_ISI.csv                    # Initial Spread Index
    {year}_{month}_BUI.csv                    # Buildup Index
    {year}_{month}_FWI.csv                    # Fire Weather Index (final)

  nfdrs/                             # National Fire Danger Rating System
    {year}_{month}_FM1.csv                    # 1-hour fuel moisture (%)
    {year}_{month}_FM10.csv                   # 10-hour fuel moisture (%)
    {year}_{month}_FM100.csv                  # 100-hour fuel moisture (%)
    {year}_{month}_FM1000.csv                 # 1000-hour fuel moisture (%)
    {year}_{month}_SC.csv                     # Spread Component (ft/min)
    {year}_{month}_ERC.csv                    # Energy Release Component (BTU/ft^2)
    {year}_{month}_BI.csv                     # Burning Index

  fpi/                               # Fire Potential Index (requires NDVI)
    {year}_{month}_RG.csv                     # Relative Greenness (0-1)
    {year}_{month}_EMC.csv                    # Equilibrium Moisture Content (%)
    {year}_{month}_FM10_fpi.csv               # 10-hr fuel moisture, FPI method (%)
    {year}_{month}_FPI.csv                    # Fire Potential Index (0-100)

  state/                             # Carry-forward state for continuity
    fwi_state_{year}_{month}.json             # FFMC, DMC, DC per point
    nfdrs_state_{year}_{month}.json           # Fuel moisture per point

  metadata_{year}_{month}.json       # Full calculation parameters
```

### CSV Format

- **Rows**: Indexed by `point_id` (matches `points_index.csv`)
- **Columns**: Datetime strings in format `YYYY-MM-DD HH:MM` (hourly)
- **Values**: Floating-point numbers for the variable at that point and time

Example (FWI for July 2020):
```
point_id, 2020-07-01 00:00, 2020-07-01 01:00, ..., 2020-07-31 23:00
0,        2.34,              2.18,              ..., 5.67
1,        2.41,              2.25,              ..., 5.82
...
```

---

## Fire Danger Index Descriptions

### Canadian Fire Weather Index (CFWI) System

The FWI system tracks moisture content in three fuel layers and combines
them into fire behavior indicators. Higher values = greater fire danger.

| Component | What It Measures | Range | Key Inputs |
|-----------|-----------------|-------|------------|
| **FFMC** | Surface litter dryness (1-2 cm deep) | 0-101 | Temp, RH, wind, rain |
| **DMC** | Organic layer dryness (5-10 cm deep) | 0+ | Temp, RH, rain |
| **DC** | Deep drought severity (10-20 cm deep) | 0+ | Temp, rain |
| **ISI** | Expected fire spread rate | 0+ | Wind speed + FFMC |
| **BUI** | Fuel available for combustion | 0+ | DMC + DC |
| **FWI** | Overall fire intensity | 0+ | ISI + BUI |

**How to interpret FWI values** (approximate ranges for northern forests):

| FWI Range | Fire Danger Level |
|-----------|------------------|
| 0-5 | Low |
| 5-10 | Moderate |
| 10-20 | High |
| 20-30 | Very High |
| 30+ | Extreme |

### NFDRS Indices (ERC, SC, BI)

The National Fire Danger Rating System uses detailed fuel models to
estimate fire behavior. Different fuel models produce different value ranges.

| Index | What It Measures | Units | Interpretation |
|-------|-----------------|-------|----------------|
| **ERC** | Total energy available per unit area if the fire front passes | BTU/ft^2 | Higher = more intense fire. Climate-driven (no wind). |
| **SC** | Rate of forward fire spread | ft/min | Higher = faster spread. Wind-dependent. |
| **BI** | Combined measure of fire difficulty to suppress | dimensionless | BI = 3.01 x (SC x ERC)^0.46. Higher = harder to control. |

ERC is particularly useful for tracking **seasonal trends** — it rises
slowly through dry periods and drops sharply with sustained rain.

### Fire Potential Index (FPI)

FPI combines satellite vegetation data (NDVI) with weather to assess
fire potential. It accounts for both fuel condition (green vs. cured)
and fire weather.

| Value Range | Meaning |
|-------------|---------|
| 0-25 | Low potential |
| 25-50 | Moderate potential |
| 50-75 | High potential |
| 75-100 | Very high potential |

FPI requires NDVI satellite data. Without NDVI, FPI outputs will be NaN.
See [Adding NDVI Data for FPI](#adding-ndvi-data-for-fpi).

---

## Fuel Model Selection

The NFDRS fuel model determines the fuel loading parameters used for
ERC, SC, and BI calculations. The system supports all 22 standard
NFDRS fuel models (A through Z, excluding M).

### Default: Fuel Model G

Fuel model **G** ("Dense conifer with heavy dead fuel") is the default
for the Western Upper Peninsula, which is predominantly forested with
mixed conifer/hardwood stands and significant dead fuel accumulation.

### Other Fuel Models

Use `--fuel-model X` to select a different model. Common choices:

| Model | Description | When to Use |
|-------|-------------|-------------|
| **A** | Western annual grass | Open grassland |
| **C** | Open pine with grass | Sparse pine woodland |
| **D** | Southern rough | Shrubby areas |
| **F** | Intermediate brush | Moderate shrub |
| **G** | Dense conifer, heavy dead fuel | **WUP forests (default)** |
| **H** | Short needle conifer, light dead fuel | Young pine stands |
| **R** | Hardwood litter, closed canopy | Deciduous forest |
| **T** | Sagebrush/grass | Not typical for WUP |
| **U** | Western long needle pine | Not typical for WUP |

For spatially-varying fuel models (different models for different points),
future versions will support a fuel model map from LANDFIRE.

---

## Fuel Moisture Methods

The system supports two approaches for estimating dead fuel moisture:

### EMC Method (Default: `--fuel-moisture emc`)

Uses the **Equilibrium Moisture Content** approximation (Simard 1968):
- Computes EMC from current temperature and relative humidity
- 1-hr fuel moisture = EMC
- 10-hr fuel moisture = EMC x 1.28
- 100-hr and 1000-hr derived with additional lag factors
- **No carry-forward state** — each hour is independent

Best for: Quick analyses, when you don't need to track multi-day drying trends.

### Nelson Method (`--fuel-moisture nelson`)

Uses the **Nelson dead fuel moisture model** with timelag calculations:
- 1-hr moisture responds within hours (fast drying/wetting)
- 10-hr moisture has ~10 hour response time
- 100-hr moisture has ~100 hour response time (~4 days)
- 1000-hr moisture has ~1000 hour response time (~6 weeks)
- **Carry-forward state** — previous hour's moisture affects current hour

Best for: Multi-month analyses where cumulative drying matters (e.g.,
drought tracking). The 1000-hr fuel moisture is especially important
for capturing seasonal drought effects on ERC.

---

## Adding NDVI Data for FPI

The Fire Potential Index (FPI) requires satellite vegetation data that
is not included in the AORC dataset. Without NDVI data, FPI will output
NaN values.

### What You Need

1. **NASA Earthdata account** (free): https://urs.earthdata.nasa.gov/
2. **MODIS NDVI data** (MOD13A2): 1 km resolution, 16-day composites
   - Or **VIIRS NDVI** (VNP13A1): 500 m resolution, 16-day composites
3. **Static FPI inputs** (computed once from multi-year NDVI archive):
   - NDVI minimum per pixel (historical minimum)
   - NDVI maximum per pixel (historical maximum)
   - Live fuel moisture map (LLfm)
   - Dead fuel moisture map (DLfm)
   - Moisture of extinction map (MXd)

### File Format

Place static data in `data/static/`:
```
data/static/
  FPI_Input_Static.nc    # NetCDF with ND_min, ND_max, LLfm, DLfm, MXd
```

Place time-varying NDVI data organized by year:
```
data/static/ndvi/
  FPI_Input_2020.nc      # NetCDF with ND0 (daily NDVI), Tmax, RH_min
```

The system will auto-detect these files when running FPI calculations.

---

## Troubleshooting

### S3 Connection Fails

```
Error: Could not connect to AORC S3 bucket
```

- The AORC bucket (`noaa-nws-aorc-v1-1-1km`) is public and requires no
  AWS credentials, but does require internet access.
- Check your network connection and any proxy/firewall settings.
- Try: `aorc-tools status` to test connectivity.
- The system tries 5 different S3 access methods automatically.

### Out of Memory

If extraction runs out of RAM with many points:

1. Extract fewer months at a time: `--start-month 1 --end-month 3`
2. Use a smaller study area (fewer points)
3. The system processes data hour-by-hour so peak memory usage is
   proportional to point count, not time range.

### NaN Values in Output

- **FWI components**: Check that the carry-forward state from previous
  months is available in the `state/` directory. If starting fresh in
  the middle of a year, the first few days use default startup values
  (FFMC=85, DMC=6, DC=15).
- **FPI**: NaN is expected if NDVI data is not available.
- **ERC/BI**: Check fuel moisture values — if all moisture values are
  zero or negative, check the raw AORC temperature and humidity CSVs.

### Water Filtering Fails

If `--filter-water` fails due to network issues (OSM download), use
`--no-filter-water` to skip water body exclusion. Lake Superior points
will be included but can be filtered later in post-processing.

### CSV Files Are Too Large

Monthly CSVs can be 50-200 MB each (15K points x 744 hours). If this
is too large for Excel:
- Load in Python with `pandas.read_csv()`
- Load specific columns: `pd.read_csv(file, usecols=['2020-07-15 12:00'])`
- Use the website map interface instead of opening CSVs directly

---

## Data Sources and References

### AORC Dataset
- Fall et al. 2023: "The Office of Water Prediction's Analysis of Record
  for Calibration, version 1.1" — JAWRA
- S3 Bucket: `s3://noaa-nws-aorc-v1-1-1km` (public, no credentials)
- Resolution: 30 arc-seconds (~800 m), hourly, 1979-present

### Fire Danger Indices
- **CFWI**: Van Wagner & Pickett 1985; hourly method from Van Wagner 1977;
  cffdrs-ng (NRCan CFFDRS2025)
- **ERC/BI**: Bradshaw et al. 1984 (USFS INT-169); NFDRS4-TechDoc;
  Argonne National Laboratory (Yu/Feng 2023)
- **FPI**: Burgan et al. 1998; Argonne National Laboratory (Yu/Feng 2023)

### Validation
All fire danger index calculations are cross-validated against:
- Argonne National Laboratory code (Yu & Feng, doi:10.1029/2023EF003823)
- cffdrs-ng Python implementation (NRCan)
- firelab/NFDRS4-TechDoc (USFS Fire Lab)
