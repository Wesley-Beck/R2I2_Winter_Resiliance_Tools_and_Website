"""
Command-line interface for the AORC Wildfire Risk Analysis System.

Usage:
    python -m aorc_tools.cli points --shapefile path/to/WUP.shp --output ./data/output
    python -m aorc_tools.cli extract --points ./data/output/points_index.csv --year 2020
    python -m aorc_tools.cli status
"""

import logging
import sys

import click

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


@click.group()
def main():
    """AORC Wildfire Risk Analysis Tools for the Western Upper Peninsula."""
    pass


@main.command()
@click.option("--shapefile", required=True, help="Path to study area shapefile (.shp/.gpkg/.geojson)")
@click.option("--output", required=True, help="Output directory for point index CSV")
@click.option("--filter-water/--no-filter-water", default=True, help="Exclude large water bodies")
@click.option("--water-min-area", default=10.0, help="Min water body area in km² to exclude")
def points(shapefile, output, filter_water, water_min_area):
    """Generate AORC grid point index from a study area shapefile."""
    from pathlib import Path

    from aorc_tools.aorc_access import AORCDataLoader
    from aorc_tools.point_filter import (
        load_boundary, generate_point_index, save_point_index,
    )

    output_dir = Path(output)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Load boundary
    logger.info("Loading boundary from %s", shapefile)
    boundary = load_boundary(shapefile)

    # Get AORC coordinates
    logger.info("Fetching AORC coordinates...")
    loader = AORCDataLoader()
    lats, lons = loader.get_coordinates()

    # Generate points
    logger.info("Generating point index...")
    points_df = generate_point_index(boundary, lats, lons)
    logger.info("Generated %d points within boundary", len(points_df))

    # Optionally filter water
    if filter_water:
        from aorc_tools.water_filter import get_large_water_bodies, exclude_water_points
        logger.info("Downloading water body data...")
        water_geom = get_large_water_bodies(boundary, min_area_km2=water_min_area)
        points_df = exclude_water_points(points_df, water_geom)

    # Save
    output_file = output_dir / "points_index.csv"
    save_point_index(points_df, output_file)
    click.echo(f"Saved {len(points_df)} points to {output_file}")


@main.command()
@click.option("--points", "points_file", required=True, help="Path to points_index.csv")
@click.option("--year", required=True, type=int, help="Year to extract")
@click.option("--output", default="./data/output", help="Base output directory")
@click.option("--start-month", default=1, type=int, help="Start month (1-12)")
@click.option("--end-month", default=12, type=int, help="End month (1-12)")
@click.option("--fuel-model", default="G", help="NFDRS fuel model code (A-Z)")
@click.option("--fuel-moisture", default="emc", type=click.Choice(["emc", "nelson"]),
              help="Fuel moisture method")
@click.option("--latitude", default=46.5, type=float, help="Representative latitude for FWI")
@click.option("--format", "output_format", default="both",
              type=click.Choice(["sqlite", "csv", "both"]),
              help="Output format: sqlite (compact + web files), csv, or both")
@click.option("--skip-raw/--no-skip-raw", default=False,
              help="Skip raw AORC output (saves ~30% time/space)")
@click.option("--local-data", default=None,
              help="Path to local AORC mirror (use 'aorc-tools download' to create)")
def extract(points_file, year, output, start_month, end_month,
            fuel_model, fuel_moisture, latitude, output_format, skip_raw,
            local_data):
    """Extract hourly AORC data and compute fire danger indices."""
    from aorc_tools.point_filter import load_point_index
    from aorc_tools.extract import extract_year

    logger.info("Loading points from %s", points_file)
    points_df = load_point_index(points_file)
    logger.info("Loaded %d points", len(points_df))

    # Set up local mirror if path provided
    mirror = None
    if local_data:
        from aorc_tools.local_mirror import LocalAORCMirror
        mirror = LocalAORCMirror(local_data, points_df)
        status = mirror.status()
        logger.info("Local mirror: %d months cached (%.1f GB)",
                     status["months_downloaded"], status["total_size_gb"])

    def progress(pct, msg):
        click.echo(f"  [{pct:5.1f}%] {msg}")

    logger.info("Extracting %d-%02d through %d-%02d", year, start_month, year, end_month)
    extract_year(
        year, points_df, output,
        start_month=start_month, end_month=end_month,
        fuel_model=fuel_model,
        fuel_moisture_method=fuel_moisture,
        latitude=latitude,
        output_format=output_format,
        skip_raw=skip_raw,
        mirror=mirror,
        callback=progress,
    )
    click.echo(f"Extraction complete for {year}")


@main.command()
@click.option("--points", "points_file", required=True, help="Path to points_index.csv")
@click.option("--mirror-dir", required=True, help="Local directory to store AORC data")
@click.option("--start-year", required=True, type=int, help="Start year (e.g., 1979)")
@click.option("--end-year", required=True, type=int, help="End year (e.g., 2024)")
@click.option("--start-month", default=1, type=int, help="Start month in start year")
@click.option("--end-month", default=12, type=int, help="End month in end year")
def download(points_file, mirror_dir, start_year, end_year, start_month, end_month):
    """Download AORC data to local disk for offline computation.

    Downloads only the grid points in your study area (~28K points for WUP),
    not the full CONUS grid. Approximately 3 GB per year compressed.

    Once downloaded, use --local-data with the extract command to compute
    fire indices from local data instead of S3 (eliminates network bottleneck).
    """
    from aorc_tools.point_filter import load_point_index
    from aorc_tools.local_mirror import LocalAORCMirror

    points_df = load_point_index(points_file)
    click.echo(f"Loaded {len(points_df)} points")

    mirror = LocalAORCMirror(mirror_dir, points_df)
    status = mirror.status()
    click.echo(f"Mirror: {status['months_downloaded']} months cached "
               f"({status['total_size_gb']} GB) in {mirror_dir}")

    def progress(year, month, msg):
        click.echo(f"  {year}-{month:02d}: {msg}")

    count = mirror.download_range(
        start_year, end_year,
        start_month=start_month, end_month=end_month,
        callback=progress,
    )
    click.echo(f"Downloaded {count} new months")

    status = mirror.status()
    click.echo(f"Mirror total: {status['months_downloaded']} months, "
               f"{status['total_size_gb']} GB")


@main.command()
@click.option("--points", "points_file", required=True, help="Path to points_index.csv")
@click.option("--mirror-dir", required=True, help="Local AORC mirror directory")
def sync(points_file, mirror_dir):
    """Check for new AORC data and download any missing months.

    Compares the local mirror against what's available on S3 and downloads
    any months that haven't been cached yet.
    """
    from aorc_tools.point_filter import load_point_index
    from aorc_tools.local_mirror import LocalAORCMirror

    points_df = load_point_index(points_file)
    mirror = LocalAORCMirror(mirror_dir, points_df)

    click.echo("Checking for new AORC data on S3...")
    missing = mirror.check_for_updates()

    if not missing:
        click.echo("Local mirror is up to date!")
        return

    click.echo(f"Found {len(missing)} months to download:")
    for year, month in missing[:10]:
        click.echo(f"  {year}-{month:02d}")
    if len(missing) > 10:
        click.echo(f"  ... and {len(missing) - 10} more")

    def progress(year, month, msg):
        click.echo(f"  {year}-{month:02d}: {msg}")

    count = mirror.sync(callback=progress)
    click.echo(f"Synced {count} new months")


@main.command(name="run-all")
@click.option("--points", "points_file", required=True, help="Path to points_index.csv")
@click.option("--mirror-dir", required=True, help="Local AORC mirror directory")
@click.option("--output", default="./data/output", help="Base output directory")
@click.option("--start-year", default=1979, type=int, help="Start year (default: 1979)")
@click.option("--end-year", default=None, type=int, help="End year (default: current year)")
@click.option("--fuel-model", default="G", help="NFDRS fuel model code")
@click.option("--format", "output_format", default="sqlite",
              type=click.Choice(["sqlite", "csv", "both"]),
              help="Output format (default: sqlite)")
@click.option("--skip-raw/--no-skip-raw", default=True,
              help="Skip raw AORC output (default: yes, saves space)")
@click.option("--download-first/--no-download-first", default=True,
              help="Download missing months before extraction")
def run_all(points_file, mirror_dir, output, start_year, end_year,
            fuel_model, output_format, skip_raw, download_first):
    """Download AORC data and compute fire indices for the entire timeline.

    This is the all-in-one command. It:
    1. Downloads any missing months from S3 to the local mirror
    2. Extracts fire indices year-by-year from local data
    3. Carries forward FWI/NFDRS state across months for continuity

    Example: Process the full AORC archive (1979-present):
        aorc-tools run-all --points data/output/points_index.csv --mirror-dir ./data/aorc_local

    Example: Process just fire seasons (May-Oct) for recent years:
        aorc-tools run-all --points data/output/points_index.csv --mirror-dir ./data/aorc_local \\
            --start-year 2015 --end-year 2024
    """
    import time
    from datetime import datetime as dt
    from aorc_tools.point_filter import load_point_index
    from aorc_tools.local_mirror import LocalAORCMirror
    from aorc_tools.extract import extract_year

    if end_year is None:
        end_year = dt.utcnow().year

    points_df = load_point_index(points_file)
    click.echo(f"Loaded {len(points_df)} points")

    mirror = LocalAORCMirror(mirror_dir, points_df)
    status_info = mirror.status()
    click.echo(f"Local mirror: {status_info['months_downloaded']} months cached "
               f"({status_info['total_size_gb']} GB)")

    total_years = end_year - start_year + 1
    total_months = total_years * 12

    # Step 1: Download missing months
    if download_first:
        click.echo(f"\n=== Step 1: Downloading AORC data ({start_year}-{end_year}) ===")
        def dl_progress(year, month, msg):
            click.echo(f"  {year}-{month:02d}: {msg}")

        downloaded = mirror.download_range(start_year, end_year, callback=dl_progress)
        click.echo(f"Downloaded {downloaded} new months")
    else:
        click.echo("\nSkipping download (--no-download-first)")

    # Step 2: Extract fire indices year by year
    click.echo(f"\n=== Step 2: Computing fire indices ({start_year}-{end_year}) ===")
    t_total = time.perf_counter()
    state = {"fwi_state": None, "fm_state": None}

    for yr_idx, year in enumerate(range(start_year, end_year + 1)):
        click.echo(f"\n--- Year {year} ({yr_idx + 1}/{total_years}) ---")
        t_year = time.perf_counter()

        def progress(pct, msg):
            click.echo(f"  [{pct:5.1f}%] {msg}")

        state = extract_year(
            year, points_df, output,
            fuel_model=fuel_model,
            output_format=output_format,
            skip_raw=skip_raw,
            mirror=mirror,
            fwi_state=state["fwi_state"],
            fm_state=state["fm_state"],
            callback=progress,
        )

        elapsed = time.perf_counter() - t_year
        click.echo(f"  Year {year} complete in {elapsed:.0f}s")

    total_time = time.perf_counter() - t_total
    click.echo(f"\n=== All done! {total_years} years processed in {total_time:.0f}s ===")
    click.echo(f"Output: {output}")


@main.command()
def status():
    """Check AORC S3 connection and system status."""
    click.echo("Checking AORC S3 access...")

    try:
        from aorc_tools.aorc_access import AORCDataLoader
        loader = AORCDataLoader()
        lats, lons = loader.get_coordinates()
        click.echo(f"  AORC grid: {len(lats)} lats × {len(lons)} lons")
        click.echo(f"  Lat range: {lats.min():.4f} to {lats.max():.4f}")
        click.echo(f"  Lon range: {lons.min():.4f} to {lons.max():.4f}")
        click.echo("  Status: OK")
    except Exception as e:
        click.echo(f"  Status: FAILED — {e}", err=True)
        sys.exit(1)


@main.command(name="glarm-info")
@click.option("--data-path", default=None, help="Path to GLARM NetCDF files")
@click.option("--scenario", default="rcp85", type=click.Choice(["rcp45", "rcp85"]),
              help="Emission scenario")
def glarm_info(data_path, scenario):
    """Show GLARM climate model adapter status and available variables."""
    from aorc_tools.climate_model_adapter import GLARMAdapter, REQUIRED_VARIABLES

    if data_path:
        adapter = GLARMAdapter(data_path, scenario=scenario)
    else:
        click.echo("GLARM Climate Model Adapter")
        click.echo("=" * 40)
        click.echo(f"Dataset: GLARM-Proj1 (Xue et al. 2022)")
        click.echo(f"Source:  https://digitalcommons.mtu.edu/glts/")
        click.echo(f"Period:  1981-2099 (RCP 4.5 & RCP 8.5)")
        click.echo(f"Grid:    18 km (atmospheric), 1-4 km (lake)")
        adapter = GLARMAdapter("/tmp/placeholder", scenario=scenario)

    info = adapter.info()
    click.echo(f"\nData source: {info['name']}")
    click.echo(f"Time range:  {info['start_year']}-{info['end_year']}")
    click.echo(f"\nVariables ({len(info['available_variables'])}):")
    for var in info["available_variables"]:
        req = "REQUIRED" if var in REQUIRED_VARIABLES else "optional"
        click.echo(f"  {var:30s} [{req}]")
    if info["missing_variables"]:
        for var in info["missing_variables"]:
            click.echo(f"  {var:30s} [MISSING]")
    click.echo(f"\nReady: {'YES' if info['ready'] else 'NO (missing variables)'}")


@main.command(name="projections")
def projections():
    """List all available climate models for future wildfire risk."""
    from aorc_tools.climate_model_adapter import list_models, NEX_GDDP_GCMS

    models = list_models()
    click.echo("Available Climate Models for Wildfire Risk Projection")
    click.echo("=" * 60)

    for key, m in models.items():
        status = "READY" if m.get("adapter_class") else "PLANNED"
        click.echo(f"\n  [{status}] {m['name']}")
        click.echo(f"    Key:        {key}")
        click.echo(f"    Type:       {m['type']}")
        click.echo(f"    Period:     {m['period']}")
        click.echo(f"    Resolution: {m['resolution']}")
        click.echo(f"    Variables:  {m['variables']}")
        click.echo(f"    Source:     {m['source']}")
        if "scenarios" in m:
            click.echo(f"    Scenarios:  {', '.join(m['scenarios'])}")
        if "gcms" in m:
            click.echo(f"    GCMs:       {len(m['gcms'])} available")
        if "note" in m:
            click.echo(f"    Note:       {m['note']}")

    click.echo(f"\n\nNEX-GDDP-CMIP6 GCMs ({len(NEX_GDDP_GCMS)}):")
    for i, gcm in enumerate(NEX_GDDP_GCMS):
        click.echo(f"  {i+1:2d}. {gcm}")

    click.echo("\nUsage:")
    click.echo("  # Download and compute from NEX-GDDP-CMIP6 (recommended first):")
    click.echo("  aorc-tools project-download --points data/output/points_index.csv \\")
    click.echo("      --mirror-dir ./data/projections --source nex-gddp-cmip6 \\")
    click.echo("      --gcm ACCESS-CM2 --scenario ssp585 --start-year 2040 --end-year 2060")
    click.echo()
    click.echo("  # Compute fire indices from downloaded projections:")
    click.echo("  aorc-tools project-extract --points data/output/points_index.csv \\")
    click.echo("      --mirror-dir ./data/projections --source nex-gddp-cmip6 \\")
    click.echo("      --gcm ACCESS-CM2 --scenario ssp585 --start-year 2040 --end-year 2060")


@main.command(name="project-download")
@click.option("--points", "points_file", required=True, help="Path to points_index.csv")
@click.option("--mirror-dir", required=True, help="Local directory for projection data")
@click.option("--source", required=True,
              type=click.Choice(["nex-gddp-cmip6", "glarm", "climrr"]),
              help="Climate model source")
@click.option("--gcm", default="ACCESS-CM2", help="GCM name (for NEX-GDDP-CMIP6)")
@click.option("--scenario", required=True, help="Scenario (ssp245, ssp585, rcp45, rcp85)")
@click.option("--start-year", required=True, type=int)
@click.option("--end-year", required=True, type=int)
@click.option("--start-month", default=1, type=int)
@click.option("--end-month", default=12, type=int)
def project_download(points_file, mirror_dir, source, gcm, scenario,
                     start_year, end_year, start_month, end_month):
    """Download climate projection data to local disk.

    Downloads only your study-area points (same as AORC mirror pattern).
    Supports NEX-GDDP-CMIP6 (27 GCMs, SSP2-4.5/SSP5-8.5) and GLARM.
    """
    from aorc_tools.point_filter import load_point_index
    from aorc_tools.climate_model_adapter import get_adapter
    from aorc_tools.projection_mirror import ProjectionMirror

    points_df = load_point_index(points_file)
    click.echo(f"Loaded {len(points_df)} points")

    adapter = get_adapter(source, gcm=gcm, scenario=scenario)
    click.echo(f"Source: {adapter.name}")

    source_name = f"{source}/{gcm}/{scenario}" if source == "nex-gddp-cmip6" else f"{source}/{scenario}"
    mirror = ProjectionMirror(mirror_dir, source_name, adapter, points_df)
    status_info = mirror.status()
    click.echo(f"Mirror: {status_info['months_downloaded']} months cached "
               f"({status_info['total_size_gb']} GB)")

    def progress(year, month, msg):
        click.echo(f"  {year}-{month:02d}: {msg}")

    count = mirror.download_range(start_year, end_year,
                                   start_month=start_month, end_month=end_month,
                                   callback=progress)
    click.echo(f"\nDownloaded {count} new months")
    status_info = mirror.status()
    click.echo(f"Total: {status_info['months_downloaded']} months, "
               f"{status_info['total_size_gb']} GB")


@main.command(name="project-extract")
@click.option("--points", "points_file", required=True, help="Path to points_index.csv")
@click.option("--mirror-dir", required=True, help="Local projection data directory")
@click.option("--source", required=True,
              type=click.Choice(["nex-gddp-cmip6", "glarm", "climrr"]))
@click.option("--gcm", default="ACCESS-CM2", help="GCM name (for NEX-GDDP-CMIP6)")
@click.option("--scenario", required=True, help="Scenario (ssp245, ssp585, rcp45, rcp85)")
@click.option("--output", default=None, help="Output directory (auto-generated if omitted)")
@click.option("--start-year", required=True, type=int)
@click.option("--end-year", required=True, type=int)
@click.option("--fuel-model", default="G")
@click.option("--format", "output_format", default="sqlite",
              type=click.Choice(["sqlite", "csv", "both"]))
def project_extract(points_file, mirror_dir, source, gcm, scenario, output,
                    start_year, end_year, fuel_model, output_format):
    """Compute fire indices from downloaded climate projections.

    Uses the same fire index pipeline as AORC extraction but with
    projection data as input. Results go to a separate output directory.
    """
    import time as t
    from aorc_tools.point_filter import load_point_index
    from aorc_tools.climate_model_adapter import get_adapter
    from aorc_tools.projection_mirror import ProjectionMirror
    from aorc_tools.extract import extract_year

    points_df = load_point_index(points_file)
    adapter = get_adapter(source, gcm=gcm, scenario=scenario)
    source_name = f"{source}/{gcm}/{scenario}" if source == "nex-gddp-cmip6" else f"{source}/{scenario}"
    mirror = ProjectionMirror(mirror_dir, source_name, adapter, points_df)

    # Auto-generate output directory matching website data source paths
    if output is None:
        if source == "nex-gddp-cmip6":
            output = f"./data/output_nex_{gcm}_{scenario}"
        elif source == "glarm":
            output = f"./data/output_glarm_{scenario}"
        elif source == "climrr":
            output = f"./data/output_climrr_{scenario}"
        else:
            safe_name = source_name.replace("/", "_")
            output = f"./data/output_{safe_name}"
    click.echo(f"Source:  {adapter.name}")
    click.echo(f"Output:  {output}")
    click.echo(f"Years:   {start_year}-{end_year}")

    t_total = t.perf_counter()
    state = {"fwi_state": None, "fm_state": None}

    for year in range(start_year, end_year + 1):
        click.echo(f"\n--- {year} ---")
        t_yr = t.perf_counter()

        # Auto-download any months not yet cached
        for m in range(1, 13):
            if not mirror.is_downloaded(year, m):
                click.echo(f"  Downloading {year}-{m:02d}...")
                mirror.download_month(year, m)

        def progress(pct, msg):
            click.echo(f"  [{pct:5.1f}%] {msg}")

        state = extract_year(
            year, points_df, output,
            fuel_model=fuel_model,
            output_format=output_format,
            skip_raw=True,
            mirror=mirror,
            fwi_state=state["fwi_state"],
            fm_state=state["fm_state"],
            callback=progress,
        )
        click.echo(f"  {year} done in {t.perf_counter() - t_yr:.0f}s")

    click.echo(f"\nAll done! {end_year - start_year + 1} years in "
               f"{t.perf_counter() - t_total:.0f}s")
    click.echo(f"Output: {output}")


@main.command()
@click.option("--data-dir", default="./data/output", help="Base output directory with SQLite data")
@click.option("--figures-dir", default="./data/figures", help="Directory to save generated figures")
@click.option("--fdis", default=None, help="Comma-separated FDI names (default: auto-detect)")
@click.option("--months", default=None,
              help="Comma-separated YYYY-MM ranges (default: all available)")
def analyze(data_dir, figures_dir, fdis, months):
    """Generate publication figures from extracted FDI data.

    Produces hotspot maps, seasonality profiles, exceedance frequency maps,
    FDI similarity matrices, ROC curves, and lowest-risk area maps.

    Example:
        aorc-tools analyze --data-dir ./data/output --figures-dir ./data/figures
        aorc-tools analyze --fdis FWI,ERC,BI,FPI --figures-dir ./figures
    """
    from aorc_tools.analysis.data_access import AnalysisDataStore
    from aorc_tools.analysis.figures import generate_all_figures

    store = AnalysisDataStore(data_dir)
    available = store.available_months()
    click.echo(f"Data directory: {data_dir}")
    click.echo(f"Available months: {len(available)}")

    if not available:
        click.echo("No data found. Run 'aorc-tools extract' first.", err=True)
        sys.exit(1)

    for y, m in available:
        click.echo(f"  {y}-{m:02d}")

    # Parse months filter
    month_list = None
    if months:
        month_list = []
        for part in months.split(","):
            part = part.strip()
            y, m = part.split("-")
            month_list.append((int(y), int(m)))
    else:
        month_list = available

    # Parse FDI filter
    fdi_list = None
    if fdis:
        fdi_list = [f.strip() for f in fdis.split(",")]

    click.echo(f"\nGenerating figures in {figures_dir}...")
    generated = generate_all_figures(store, figures_dir, fdis=fdi_list, months=month_list)

    click.echo(f"\nGenerated {len(generated)} figures:")
    for path in generated:
        click.echo(f"  {path}")


@main.command(name="analyze-correlation")
@click.option("--data-dir", default="./data/output", help="Base output directory")
@click.option("--figures-dir", default="./data/figures", help="Figure output directory")
@click.option("--year-start", default=2000, type=int, help="Start year for NIFC data")
@click.option("--year-end", default=2024, type=int, help="End year for NIFC data")
@click.option("--fdis", default=None, help="Comma-separated FDI names")
def analyze_correlation(data_dir, figures_dir, year_start, year_end, fdis):
    """Correlate FDI values with actual NIFC wildfire occurrences.

    Fetches fire perimeters from the NIFC Interagency Fire Perimeter History
    for the WUP region and computes point-biserial correlations, ROC curves,
    and hit rate analyses for each FDI.

    Example:
        aorc-tools analyze-correlation --year-start 2015 --year-end 2023
    """
    from pathlib import Path
    from aorc_tools.analysis.data_access import AnalysisDataStore
    from aorc_tools.analysis.correlation import (
        fetch_nifc_fires, build_fire_calendar, compare_fdis, roc_analysis,
    )
    from aorc_tools.analysis.figures import plot_roc_curves
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    store = AnalysisDataStore(data_dir)
    available = store.available_months()

    if not available:
        click.echo("No data found.", err=True)
        sys.exit(1)

    # Fetch NIFC fires
    click.echo(f"Fetching NIFC wildfire data ({year_start}-{year_end})...")
    fires = fetch_nifc_fires(year_start, year_end)
    click.echo(f"Found {len(fires)} fires in WUP region")

    fire_dates, fires_by_date = build_fire_calendar(fires, year_start, year_end)
    click.echo(f"Fire days: {len(fire_dates)}")

    # Load FDI data
    fdi_list = None
    if fdis:
        fdi_list = [f.strip() for f in fdis.split(",")]
    else:
        y, m = available[0]
        all_vars = store.get_variables(y, m)
        from aorc_tools.analysis import CORE_FDI_VARS
        fdi_list = [v for v in all_vars if v in CORE_FDI_VARS]

    click.echo(f"Analyzing FDIs: {', '.join(fdi_list)}")

    import numpy as np
    fdi_data = {}
    dates_all = None
    for fdi in fdi_list:
        try:
            dates, data = store.load_multi_month(available, fdi, "daily_max")
            fdi_data[fdi] = data
            if dates_all is None:
                dates_all = dates
        except Exception as e:
            click.echo(f"  Skipping {fdi}: {e}")

    if not fdi_data or dates_all is None:
        click.echo("No FDI data loaded.", err=True)
        sys.exit(1)

    fire_binary = np.array([1 if d in fire_dates else 0 for d in dates_all])
    click.echo(f"Date range: {dates_all[0]} to {dates_all[-1]}")
    click.echo(f"Fire days in range: {fire_binary.sum()}")

    # Compare FDIs
    comparison, ranking = compare_fdis(fdi_data, fire_binary, dates_all, fire_dates)

    click.echo("\n=== FDI-Wildfire Correlation Ranking ===")
    click.echo(f"{'Rank':>4} {'FDI':>6} {'AUC':>8} {'Corr':>8} {'Opt.Thresh':>12}")
    for i, (name, metrics) in enumerate(ranking):
        click.echo(f"{i+1:4d} {name:>6} {metrics['auc']:8.3f} "
                   f"{metrics['correlation']:8.3f} {metrics['optimal_threshold']:12.1f}")

    # Generate ROC curves
    figures_path = Path(figures_dir)
    figures_path.mkdir(parents=True, exist_ok=True)

    roc_results = {}
    for name, data in fdi_data.items():
        spatial_mean = np.nanmean(data, axis=1)
        roc_results[name] = roc_analysis(spatial_mean, fire_binary)

    path = figures_path / "roc_curves_wildfire.png"
    fig, _ = plot_roc_curves(roc_results, save_path=str(path))
    plt.close(fig)
    click.echo(f"\nSaved ROC curves: {path}")


@main.command(name="analyze-monte-carlo")
@click.option("--data-dir", default="./data/output", help="Base output directory")
@click.option("--figures-dir", default="./data/figures", help="Figure output directory")
@click.option("--n-samples", default=500, type=int, help="Monte Carlo iterations")
@click.option("--fdis", default=None, help="Comma-separated FDI names")
def analyze_monte_carlo(data_dir, figures_dir, n_samples, fdis):
    """Run Monte Carlo FDI cross-comparison analysis.

    Repeatedly samples time periods and measures hotspot overlap between
    FDI systems. Reveals which indices agree on high-risk locations.

    Example:
        aorc-tools analyze-monte-carlo --n-samples 1000 --fdis FWI,ERC,BI,FPI
    """
    from pathlib import Path
    from aorc_tools.analysis.data_access import AnalysisDataStore
    from aorc_tools.analysis.monte_carlo import (
        monte_carlo_fdi_comparison, fdi_similarity_matrix, cluster_fdis,
    )
    from aorc_tools.analysis.figures import plot_similarity_matrix
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    store = AnalysisDataStore(data_dir)
    available = store.available_months()

    if not available:
        click.echo("No data found.", err=True)
        sys.exit(1)

    fdi_list = None
    if fdis:
        fdi_list = [f.strip() for f in fdis.split(",")]
    else:
        y, m = available[0]
        all_vars = store.get_variables(y, m)
        from aorc_tools.analysis import ALL_FDI_VARS
        fdi_list = [v for v in all_vars if v in ALL_FDI_VARS]

    click.echo(f"FDIs: {', '.join(fdi_list)}")
    click.echo(f"Monte Carlo samples: {n_samples}")

    # Load data
    fdi_data = {}
    for fdi in fdi_list:
        try:
            _, data = store.load_multi_month(available, fdi, "daily_max")
            fdi_data[fdi] = data
        except Exception as e:
            click.echo(f"  Skipping {fdi}: {e}")

    if len(fdi_data) < 2:
        click.echo("Need at least 2 FDIs for comparison.", err=True)
        sys.exit(1)

    # Run Monte Carlo
    click.echo("Running Monte Carlo comparison...")
    mc_result = monte_carlo_fdi_comparison(fdi_data, n_samples=n_samples)

    click.echo("\n=== Monte Carlo Hotspot Overlap (Jaccard Similarity) ===")
    names = mc_result["names"]
    mean_sim = mc_result["mean_similarity"]
    click.echo(f"{'':>6}", nl=False)
    for n in names:
        click.echo(f"{n:>8}", nl=False)
    click.echo()
    for i, name in enumerate(names):
        click.echo(f"{name:>6}", nl=False)
        for j in range(len(names)):
            click.echo(f"{mean_sim[i,j]:8.3f}", nl=False)
        click.echo()

    # Rank correlation matrix
    fdi_means = {name: np.nanmean(data, axis=0) for name, data in fdi_data.items()}
    corr_names, corr_matrix, _ = fdi_similarity_matrix(fdi_means)

    # Clustering
    clusters, merges = cluster_fdis(corr_matrix, corr_names, n_clusters=3)
    click.echo("\n=== FDI Clusters ===")
    for cid, members in clusters.items():
        click.echo(f"  Cluster {cid}: {', '.join(members)}")

    # Save figures
    figures_path = Path(figures_dir)
    figures_path.mkdir(parents=True, exist_ok=True)

    path = figures_path / "fdi_similarity_rank_correlation.png"
    fig, _ = plot_similarity_matrix(corr_names, corr_matrix,
                                     title="FDI Rank Correlation", save_path=str(path))
    plt.close(fig)
    click.echo(f"\nSaved: {path}")

    path = figures_path / "fdi_monte_carlo_overlap.png"
    fig, _ = plot_similarity_matrix(names, mean_sim,
                                     title=f"Monte Carlo Hotspot Overlap (n={n_samples})",
                                     save_path=str(path))
    plt.close(fig)
    click.echo(f"Saved: {path}")


@main.command(name="analyze-intensity")
@click.option("--data-dir", default="./data/output",
              help="Base output directory with SQLite data")
@click.option("--figures-dir", default="./data/figures",
              help="Directory to save generated figures")
@click.option("--fdis", default=None,
              help="Comma-separated FDI names")
def analyze_intensity(data_dir, figures_dir, fdis):
    """Run intensity analysis: severity distributions, extreme events, return periods.

    Computes severity-level distributions per year, catalogs extreme events,
    performs return period / GEV analysis, and generates all intensity figures
    including the all-indices seasonal overlay.

    Example:
        aorc-tools analyze-intensity --data-dir ./data/output --fdis FWI,ERC,BI
    """
    from pathlib import Path
    from aorc_tools.analysis.data_access import AnalysisDataStore
    from aorc_tools.analysis import ALL_FDI_VARS

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    store = AnalysisDataStore(data_dir)
    available = store.available_months()

    if not available:
        click.echo("No data found. Run 'aorc-tools extract' first.", err=True)
        sys.exit(1)

    # Parse FDI filter
    fdi_list = None
    if fdis:
        fdi_list = [f.strip() for f in fdis.split(",")]
    else:
        y, m = available[0]
        all_vars = store.get_variables(y, m)
        fdi_list = [v for v in all_vars if v in ALL_FDI_VARS]

    click.echo(f"Data directory: {data_dir}")
    click.echo(f"Available months: {len(available)}")
    click.echo(f"FDIs: {', '.join(fdi_list)}")

    figures_path = Path(figures_dir)
    figures_path.mkdir(parents=True, exist_ok=True)

    from aorc_tools.analysis import intensity, seasonality
    from aorc_tools.analysis.figures import (
        plot_severity_distribution, plot_extreme_event_timeline,
        plot_return_periods, plot_all_indices_seasonal_overlay,
    )

    generated = []

    # Load all FDI data
    fdi_data = {}
    for fdi in fdi_list:
        try:
            click.echo(f"  Loading {fdi}...")
            dates, data = store.load_multi_month(available, fdi, "daily_max")
            fdi_data[fdi] = (dates, data)
        except Exception as e:
            click.echo(f"  Skipping {fdi}: {e}")

    # Severity distributions
    click.echo("\nComputing severity distributions...")
    for fdi, (dates, data) in fdi_data.items():
        try:
            if fdi not in intensity.SEVERITY_LEVELS:
                click.echo(f"  No severity tiers defined for {fdi}, skipping")
                continue
            yearly_dist = intensity.annual_severity_distribution(data, dates, fdi)
            if yearly_dist:
                path = figures_path / f"severity_distribution_{fdi}.png"
                fig, _ = plot_severity_distribution(
                    yearly_dist, fdi, save_path=str(path))
                plt.close(fig)
                generated.append(str(path))
                click.echo(f"  Saved: {path}")
        except Exception as e:
            click.echo(f"  Failed severity distribution for {fdi}: {e}")

    # Extreme event cataloging
    click.echo("\nCataloging extreme events...")
    for fdi, (dates, data) in fdi_data.items():
        try:
            events = intensity.extreme_event_catalog(data, dates, fdi)
            click.echo(f"  {fdi}: {len(events)} extreme events")
            path = figures_path / f"extreme_events_{fdi}.png"
            fig, _ = plot_extreme_event_timeline(
                events, fdi, save_path=str(path))
            plt.close(fig)
            generated.append(str(path))
            click.echo(f"  Saved: {path}")
        except Exception as e:
            click.echo(f"  Failed extreme events for {fdi}: {e}")

    # Return period analysis
    click.echo("\nComputing return periods...")
    for fdi, (dates, data) in fdi_data.items():
        try:
            rp_result = intensity.return_period_analysis(data, dates, fdi)
            if rp_result:
                path = figures_path / f"return_period_{fdi}.png"
                fig, _ = plot_return_periods(
                    rp_result["return_periods"],
                    rp_result["return_levels"],
                    rp_result["annual_maxima"],
                    fdi,
                    gev_params=rp_result.get("gev_params"),
                    save_path=str(path))
                plt.close(fig)
                generated.append(str(path))
                click.echo(f"  Saved: {path}")
        except Exception as e:
            click.echo(f"  Failed return period for {fdi}: {e}")

    # All-indices seasonal overlay
    if len(fdi_data) >= 2:
        click.echo("\nGenerating all-indices seasonal overlay...")
        try:
            seasonal_profiles = {}
            for fdi_name, (fdi_dates, fdi_arr) in fdi_data.items():
                _, profile = seasonality.compute_seasonal_profile(
                    fdi_dates, fdi_arr)
                seasonal_profiles[fdi_name] = profile
            if seasonal_profiles:
                path = figures_path / "all_indices_seasonal_overlay.png"
                fig, _ = plot_all_indices_seasonal_overlay(
                    seasonal_profiles, save_path=str(path))
                plt.close(fig)
                generated.append(str(path))
                click.echo(f"  Saved: {path}")
        except Exception as e:
            click.echo(f"  Failed all-indices overlay: {e}")

    click.echo(f"\nGenerated {len(generated)} intensity figures in {figures_dir}")


@main.command(name="analyze-snowmelt")
@click.option("--data-dir", default="./data/output",
              help="Base output directory with SQLite data")
@click.option("--snow-file", required=True,
              help="Path to snow NetCDF file")
@click.option("--figures-dir", default="./data/figures",
              help="Directory to save generated figures")
@click.option("--fdi", default="FWI",
              help="FDI variable to correlate with snowmelt")
def analyze_snowmelt(data_dir, snow_file, figures_dir, fdi):
    """Correlate snowmelt timing with fire danger index onset.

    Loads snow data from a NetCDF file, regrids to FDI grid points,
    computes snowmelt dates per year, correlates with FDI fire season
    onset, and generates snowmelt-FDI relationship figures.

    Example:
        aorc-tools analyze-snowmelt --snow-file ./data/snow.nc --fdi FWI
    """
    from pathlib import Path
    import numpy as np

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    from aorc_tools.analysis.data_access import AnalysisDataStore
    from aorc_tools.analysis import seasonality
    from aorc_tools.analysis.figures import (
        plot_snowmelt_fdi_lag, plot_snow_fdi_crosscorrelation,
        plot_snowmelt_rate_severity,
    )

    store = AnalysisDataStore(data_dir)
    available = store.available_months()

    if not available:
        click.echo("No FDI data found. Run 'aorc-tools extract' first.", err=True)
        sys.exit(1)

    click.echo(f"Data directory: {data_dir}")
    click.echo(f"Snow file: {snow_file}")
    click.echo(f"FDI variable: {fdi}")

    figures_path = Path(figures_dir)
    figures_path.mkdir(parents=True, exist_ok=True)
    generated = []

    # Load snow NetCDF
    click.echo("\nLoading snow NetCDF data...")
    try:
        import xarray as xr
        snow_ds = xr.open_dataset(snow_file)
        click.echo(f"  Variables: {list(snow_ds.data_vars)}")
        click.echo(f"  Dimensions: {dict(snow_ds.dims)}")
    except Exception as e:
        click.echo(f"Failed to load snow file: {e}", err=True)
        sys.exit(1)

    # Load FDI data
    click.echo(f"\nLoading {fdi} data...")
    try:
        dates, data = store.load_multi_month(available, fdi, "daily_max")
        click.echo(f"  Loaded {len(dates)} days of {fdi} data")
    except Exception as e:
        click.echo(f"Failed to load {fdi}: {e}", err=True)
        sys.exit(1)

    # Regrid snow data to FDI points
    click.echo("\nRegridding snow data to FDI grid points...")
    try:
        from scipy.interpolate import griddata

        fdi_lats = store.lats
        fdi_lons = store.lons

        # Detect snow variable (SWE, snow_depth, SNOWH, etc.)
        snow_var = None
        for candidate in ["SWE", "swe", "snow_depth", "SNOWH", "snowh",
                          "snow_water_equivalent", "SNOD"]:
            if candidate in snow_ds.data_vars:
                snow_var = candidate
                break
        if snow_var is None:
            snow_var = list(snow_ds.data_vars)[0]
            click.echo(f"  Warning: using first variable '{snow_var}' as snow data")
        else:
            click.echo(f"  Using snow variable: {snow_var}")

        snow_data = snow_ds[snow_var]
        snow_lats = snow_ds["latitude"].values if "latitude" in snow_ds else snow_ds["lat"].values
        snow_lons = snow_ds["longitude"].values if "longitude" in snow_ds else snow_ds["lon"].values
        snow_times = snow_ds["time"].values

        # Regrid spatial mean for each time step
        click.echo("  Computing spatial mean snow values...")
        snow_spatial_mean = np.nanmean(snow_data.values, axis=tuple(
            range(1, snow_data.ndim)))
        click.echo(f"  Snow time series: {len(snow_spatial_mean)} steps")
    except Exception as e:
        click.echo(f"Failed to regrid snow data: {e}", err=True)
        sys.exit(1)

    # Compute snowmelt dates per year
    click.echo("\nComputing snowmelt dates...")
    try:
        import pandas as pd
        snow_times_pd = pd.to_datetime(snow_times)
        snow_years = sorted(set(snow_times_pd.year))

        years = []
        snowmelt_doys = []
        for yr in snow_years:
            mask = snow_times_pd.year == yr
            yr_snow = snow_spatial_mean[mask]
            yr_doys = snow_times_pd[mask].dayofyear

            # Snowmelt = first day after peak where SWE drops below 10% of max
            if len(yr_snow) == 0:
                continue
            peak_idx = np.nanargmax(yr_snow)
            peak_val = yr_snow[peak_idx]
            if peak_val <= 0:
                continue
            threshold = 0.1 * peak_val
            post_peak = yr_snow[peak_idx:]
            melt_indices = np.where(post_peak < threshold)[0]
            if len(melt_indices) > 0:
                melt_doy = yr_doys[peak_idx + melt_indices[0]]
                years.append(yr)
                snowmelt_doys.append(melt_doy)

        click.echo(f"  Found snowmelt dates for {len(years)} years")
    except Exception as e:
        click.echo(f"Failed to compute snowmelt dates: {e}", err=True)
        sys.exit(1)

    # Compute fire onset dates per year
    click.echo(f"\nComputing {fdi} fire season onset dates...")
    try:
        from datetime import datetime as _dt

        # Group dates/data by year for detect_season_by_year (expects
        # {year: (dates, array)} plus a scalar threshold).
        all_years = np.array([int(d[:4]) for d in dates])
        yearly_data = {}
        first_doy = {}
        for yr in np.unique(all_years):
            yr_mask = all_years == yr
            yr_dates = [d for d, keep in zip(dates, yr_mask) if keep]
            yearly_data[int(yr)] = (yr_dates, data[yr_mask])
            # DOY of this year's first available day, to convert onset index → DOY
            first_doy[int(yr)] = _dt.strptime(yr_dates[0][:10], "%Y-%m-%d").timetuple().tm_yday

        # Data-driven threshold: 60th percentile of the spatial-mean series
        spatial_mean_all = np.nanmean(data, axis=1)
        threshold = float(np.nanpercentile(spatial_mean_all, 60))
        click.echo(f"  Using onset threshold = {threshold:.1f} ({fdi} 60th pct)")

        yearly_results = seasonality.detect_season_by_year(yearly_data, threshold)
        fire_onset_doys = []
        valid_years = []
        valid_snowmelt = []

        for i, yr in enumerate(years):
            if yr in yearly_results:
                onset = yearly_results[yr]["spatial_mean_onset"]
                if onset is not None and not np.isnan(onset):
                    valid_years.append(yr)
                    valid_snowmelt.append(snowmelt_doys[i])
                    # onset is a mean day-index into the year; convert to DOY
                    fire_onset_doys.append(onset + first_doy.get(yr, 1) - 1)

        lags = [f - s for f, s in zip(fire_onset_doys, valid_snowmelt)]
        click.echo(f"  Matched {len(valid_years)} years with both snowmelt and fire onset")
    except Exception as e:
        click.echo(f"Failed to compute fire onset: {e}", err=True)
        sys.exit(1)

    if len(valid_years) < 3:
        click.echo("Too few matching years for analysis.", err=True)
        sys.exit(1)

    # Generate snowmelt-FDI lag figure
    click.echo("\nGenerating snowmelt-FDI lag figure...")
    try:
        path = figures_path / f"snowmelt_fdi_lag_{fdi}.png"
        fig, _ = plot_snowmelt_fdi_lag(
            valid_years, valid_snowmelt, fire_onset_doys, lags,
            save_path=str(path))
        plt.close(fig)
        generated.append(str(path))
        click.echo(f"  Saved: {path}")
    except Exception as e:
        click.echo(f"  Failed: {e}")

    # Cross-correlation analysis
    click.echo("\nComputing cross-correlation...")
    try:
        # Compute daily cross-correlation between snow and FDI
        fdi_spatial_mean = np.nanmean(data, axis=1)

        # Align time series
        import pandas as pd
        fdi_dates_pd = pd.to_datetime(dates)
        common_start = max(fdi_dates_pd[0], snow_times_pd[0])
        common_end = min(fdi_dates_pd[-1], snow_times_pd[-1])

        fdi_mask = (fdi_dates_pd >= common_start) & (fdi_dates_pd <= common_end)
        snow_mask = (snow_times_pd >= common_start) & (snow_times_pd <= common_end)

        fdi_aligned = fdi_spatial_mean[fdi_mask]
        snow_aligned = snow_spatial_mean[snow_mask]

        # Resample to same length if needed (use shorter)
        min_len = min(len(fdi_aligned), len(snow_aligned))
        fdi_aligned = fdi_aligned[:min_len]
        snow_aligned = snow_aligned[:min_len]

        max_lag = min(180, min_len // 2)
        cc_lags = np.arange(-max_lag, max_lag + 1)
        correlations = np.zeros(len(cc_lags))

        for i, lag in enumerate(cc_lags):
            if lag >= 0:
                s = snow_aligned[:min_len - lag]
                f = fdi_aligned[lag:]
            else:
                s = snow_aligned[-lag:]
                f = fdi_aligned[:min_len + lag]
            if len(s) > 0 and np.std(s) > 0 and np.std(f) > 0:
                correlations[i] = np.corrcoef(s, f)[0, 1]

        optimal_idx = np.argmax(np.abs(correlations))
        optimal_lag = cc_lags[optimal_idx]
        click.echo(f"  Optimal lag: {optimal_lag} days (r={correlations[optimal_idx]:.3f})")

        path = figures_path / f"snow_fdi_crosscorrelation_{fdi}.png"
        fig, _ = plot_snow_fdi_crosscorrelation(
            cc_lags, correlations, optimal_lag, save_path=str(path))
        plt.close(fig)
        generated.append(str(path))
        click.echo(f"  Saved: {path}")
    except Exception as e:
        click.echo(f"  Failed cross-correlation: {e}")

    # Snowmelt rate vs FDI severity
    click.echo("\nAnalyzing snowmelt rate vs FDI severity...")
    try:
        import pandas as pd
        snow_times_pd = pd.to_datetime(snow_times)
        # Compute melt rate per year (days from peak to melt)
        melt_rates = []
        melt_fdi_values = []

        for yr in valid_years:
            mask = snow_times_pd.year == yr
            yr_snow = snow_spatial_mean[mask]
            if len(yr_snow) == 0:
                continue
            peak_idx = np.nanargmax(yr_snow)
            peak_val = yr_snow[peak_idx]
            if peak_val <= 0:
                continue
            threshold = 0.1 * peak_val
            post_peak = yr_snow[peak_idx:]
            melt_indices = np.where(post_peak < threshold)[0]
            if len(melt_indices) > 0:
                melt_duration = melt_indices[0]  # days from peak to melt
                melt_rates.append(melt_duration)

                # Get FDI values for fire season of this year
                fdi_dates_pd_arr = pd.to_datetime(dates)
                yr_fdi_mask = fdi_dates_pd_arr.year == yr
                yr_fdi = np.nanmean(data[yr_fdi_mask], axis=1)
                if len(yr_fdi) > 0:
                    melt_fdi_values.append(np.nanmax(yr_fdi))
                else:
                    melt_fdi_values.append(np.nan)

        if len(melt_rates) >= 3:
            melt_rates = np.array(melt_rates)
            melt_fdi_values = np.array(melt_fdi_values)

            # Bin into Fast/Medium/Slow thirds
            terciles = np.percentile(melt_rates, [33, 67])
            bins_data = {"Fast": [], "Medium": [], "Slow": []}
            for rate, fdi_val in zip(melt_rates, melt_fdi_values):
                if np.isnan(fdi_val):
                    continue
                if rate <= terciles[0]:
                    bins_data["Fast"].append(fdi_val)
                elif rate <= terciles[1]:
                    bins_data["Medium"].append(fdi_val)
                else:
                    bins_data["Slow"].append(fdi_val)

            # Convert to arrays
            bins_data = {k: np.array(v) for k, v in bins_data.items() if len(v) > 0}

            if bins_data:
                path = figures_path / f"snowmelt_rate_severity_{fdi}.png"
                fig, _ = plot_snowmelt_rate_severity(
                    bins_data, fdi, save_path=str(path))
                plt.close(fig)
                generated.append(str(path))
                click.echo(f"  Saved: {path}")
    except Exception as e:
        click.echo(f"  Failed snowmelt rate analysis: {e}")

    snow_ds.close()
    click.echo(f"\nGenerated {len(generated)} snowmelt figures in {figures_dir}")


@main.command(name="analyze-all")
@click.option("--data-dir", default="./data/output",
              help="Base output directory with SQLite data")
@click.option("--figures-dir", default="./data/figures",
              help="Directory to save generated figures")
@click.option("--snow-file", default=None,
              help="Optional snow NetCDF file for snowmelt analysis")
def analyze_all(data_dir, figures_dir, snow_file):
    """Run ALL analyses in sequence: figures, intensity, correlation, monte carlo, snowmelt.

    This is the all-in-one analysis command. It runs:
    1. Basic publication figures (hotspots, seasonal profiles, etc.)
    2. Intensity analysis (severity, extreme events, return periods)
    3. FDI-wildfire correlation analysis
    4. Monte Carlo FDI comparison
    5. Snowmelt analysis (if --snow-file provided)

    Example:
        aorc-tools analyze-all --data-dir ./data/output --figures-dir ./data/figures
        aorc-tools analyze-all --snow-file ./data/snow.nc
    """
    from pathlib import Path
    from aorc_tools.analysis.data_access import AnalysisDataStore

    store = AnalysisDataStore(data_dir)
    available = store.available_months()

    if not available:
        click.echo("No data found. Run 'aorc-tools extract' first.", err=True)
        sys.exit(1)

    click.echo(f"Data directory: {data_dir}")
    click.echo(f"Available months: {len(available)}")
    click.echo(f"Figures directory: {figures_dir}")

    figures_path = Path(figures_dir)
    figures_path.mkdir(parents=True, exist_ok=True)

    # Step 1: Basic figures
    click.echo("\n=== Step 1: Basic Publication Figures ===")
    try:
        from aorc_tools.analysis.figures import generate_all_figures
        generated = generate_all_figures(store, figures_dir)
        click.echo(f"  Generated {len(generated)} basic figures")
    except Exception as e:
        click.echo(f"  Failed basic figures: {e}")

    # Step 2: shared setup for correlation / Monte Carlo steps.
    # Intensity figures (severity, extreme events, return periods, all-indices
    # overlay) are already produced by generate_all_figures() in Step 1.
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    from aorc_tools.analysis import ALL_FDI_VARS

    y, m = available[0]
    all_vars = store.get_variables(y, m)
    fdi_list = [v for v in all_vars if v in ALL_FDI_VARS]

    # Step 3: Correlation analysis
    click.echo("\n=== Step 3: Correlation Analysis ===")
    try:
        from aorc_tools.analysis.correlation import (
            fetch_nifc_fires, build_fire_calendar, compare_fdis, roc_analysis,
        )
        from aorc_tools.analysis.figures import plot_roc_curves

        fires = fetch_nifc_fires(2000, 2024)
        click.echo(f"  Found {len(fires)} NIFC fires")

        fire_dates, fires_by_date = build_fire_calendar(fires, 2000, 2024)

        fdi_data_corr = {}
        dates_all = None
        for fdi in fdi_list:
            try:
                d, arr = store.load_multi_month(available, fdi, "daily_max")
                fdi_data_corr[fdi] = arr
                if dates_all is None:
                    dates_all = d
            except Exception:
                pass

        if fdi_data_corr and dates_all is not None:
            fire_binary = np.array([1 if d in fire_dates else 0
                                    for d in dates_all])
            comparison, ranking = compare_fdis(
                fdi_data_corr, fire_binary, dates_all, fire_dates)

            roc_results = {}
            for name, arr in fdi_data_corr.items():
                spatial_mean = np.nanmean(arr, axis=1)
                roc_results[name] = roc_analysis(spatial_mean, fire_binary)

            path = figures_path / "roc_curves_wildfire.png"
            fig, _ = plot_roc_curves(roc_results, save_path=str(path))
            plt.close(fig)
            click.echo(f"  Saved ROC curves")
    except Exception as e:
        click.echo(f"  Failed correlation analysis: {e}")

    # Step 4: Monte Carlo
    click.echo("\n=== Step 4: Monte Carlo Analysis ===")
    try:
        from aorc_tools.analysis.monte_carlo import (
            monte_carlo_fdi_comparison, fdi_similarity_matrix,
        )
        from aorc_tools.analysis.figures import plot_similarity_matrix

        fdi_data_mc = {}
        for fdi in fdi_list:
            try:
                _, arr = store.load_multi_month(available, fdi, "daily_max")
                fdi_data_mc[fdi] = arr
            except Exception:
                pass

        if len(fdi_data_mc) >= 2:
            mc_result = monte_carlo_fdi_comparison(fdi_data_mc, n_samples=500)
            path = figures_path / "fdi_monte_carlo_overlap.png"
            fig, _ = plot_similarity_matrix(
                mc_result["names"], mc_result["mean_similarity"],
                title="Monte Carlo Hotspot Overlap (n=500)",
                save_path=str(path))
            plt.close(fig)
            click.echo(f"  Saved Monte Carlo overlap figure")

            fdi_means = {n: np.nanmean(d, axis=0) for n, d in fdi_data_mc.items()}
            corr_names, corr_matrix, _ = fdi_similarity_matrix(fdi_means)
            path = figures_path / "fdi_similarity_rank_correlation.png"
            fig, _ = plot_similarity_matrix(
                corr_names, corr_matrix,
                title="FDI Rank Correlation",
                save_path=str(path))
            plt.close(fig)
            click.echo(f"  Saved similarity matrix")
    except Exception as e:
        click.echo(f"  Failed Monte Carlo: {e}")

    # Step 5: Snowmelt (optional)
    if snow_file:
        click.echo("\n=== Step 5: Snowmelt Analysis ===")
        click.echo(f"  Snow file: {snow_file}")
        try:
            # Invoke the analyze-snowmelt command logic via Click context
            ctx = click.get_current_context()
            ctx.invoke(analyze_snowmelt, data_dir=data_dir,
                       snow_file=snow_file, figures_dir=figures_dir,
                       fdi="FWI")
        except Exception as e:
            click.echo(f"  Failed snowmelt analysis: {e}")
    else:
        click.echo("\n=== Step 5: Snowmelt Analysis (skipped, no --snow-file) ===")

    click.echo("\n=== All analyses complete! ===")
    click.echo(f"Figures saved to: {figures_dir}")


if __name__ == "__main__":
    main()
