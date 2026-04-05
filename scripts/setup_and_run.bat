@echo off
echo ============================================
echo  WUP Wildfire Risk Tools - Setup and Run
echo ============================================
echo.

REM Install the package
echo Installing dependencies...
pip install -e . 2>nul
if errorlevel 1 (
    echo.
    echo ERROR: pip install failed. Make sure Python is installed and in your PATH.
    echo Download Python from https://python.org/downloads
    pause
    exit /b 1
)

echo.
echo Setup complete! Starting extraction for recent years (2020-2024)...
echo (Change years by editing this script or running extract_all.bat directly)
echo.

call scripts\extract_all.bat --start-year 2020 --end-year 2024
