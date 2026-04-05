@echo off
echo ============================================
echo  AORC Fire Danger Index Extraction
echo  Western Upper Peninsula of Michigan
echo ============================================
echo.

REM Check if points_index.csv exists, generate if not
if not exist "data\output\points_index.csv" (
    echo Generating point index from shapefile...
    python -m aorc_tools.cli points --shapefile data/shapefiles/Western_Upper_Peninsula.shp --output data/output --no-filter-water
    echo.
)

REM Run the extraction (pass any command-line arguments through)
echo Starting extraction...
echo (This can be safely interrupted with Ctrl+C and resumed later)
echo.
python scripts/extract_all.py %*

echo.
pause
