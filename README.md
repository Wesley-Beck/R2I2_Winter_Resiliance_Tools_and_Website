# R2I2 Winter Resilient Electric Power Systems — Wildfire Risk Tools

Wildfire risk analysis tools for the **Western Upper Peninsula of Michigan**
(Houghton, Keweenaw, Ontonagon, Gogebic, Iron, Baraga counties + Isle Royale),
built as part of the R2I2 Winter Resilient Electric Power Systems project.

## What This Does

Extracts hourly weather data from NOAA's Analysis of Record for Calibration
(AORC) dataset at ~800m resolution and computes four fire danger indices
matching Argonne National Laboratory's methodology:

| Index | System | What It Measures |
|-------|--------|-----------------|
| **FWI** | Canadian Fire Weather Index | Overall fire intensity (weather-driven) |
| **ERC** | NFDRS Energy Release Component | Energy available per unit area |
| **BI** | NFDRS Burning Index | Difficulty of fire suppression |
| **FPI** | Fire Potential Index (Burgan 1998) | Vegetation + weather fire potential |

Every intermediate calculation step is saved as a separate CSV file for
full transparency and researcher access.

## Quick Start

```bash
pip install -e .

# Generate point index from study area shapefile
aorc-tools points --shapefile data/shapefiles/Western_Upper_Peninsula.shp --output ./data/output

# Extract a month of data
aorc-tools extract --points ./data/output/points_index.csv --year 2020 --start-month 7 --end-month 7

# View results on a map
cd website && python -m http.server 8000
```

See **[USAGE.md](USAGE.md)** for the complete user guide.

## Project Structure

```
aorc_tools/              # Python package — fire index calculations
  fire_indices/          # FWI, ERC/BI, FPI implementations
  cli.py                 # Command-line interface
  extract.py             # Hourly extraction pipeline
  config.py              # AORC constants, NFDRS fuel models (A-Z)
website/                 # Leaflet.js map interface
  index.html             # Single-page map app
  js/                    # Data loading, rendering, controls
  css/                   # Copper Country theme
data/
  shapefiles/            # Study area boundary (includes Isle Royale)
  output/                # Extracted CSV results (git-ignored)
tests/                   # Validation against Argonne & cffdrs-ng
```

## Data Sources

- **AORC v1.1**: NOAA S3 bucket `noaa-nws-aorc-v1-1-1km` (public, ~800m hourly, 1979-present)
- **Fire indices**: Validated against Argonne National Laboratory code (Yu & Feng 2023)
- **Fuel models**: NFDRS fuel model G default (dense conifer), all 22 models supported
- **NDVI** (for FPI): NASA MODIS/VIIRS (optional, see USAGE.md)

## References

- Fall et al. 2023: AORC v1.1 methods (JAWRA)
- Yu & Feng 2023: Characterizing compound wildfire and heat wave events (AGU Earth's Future)
- Van Wagner & Pickett 1985: Canadian FWI System
- Bradshaw et al. 1984: NFDRS fuel models (USFS INT-169)
- Burgan et al. 1998: Fire Potential Index
