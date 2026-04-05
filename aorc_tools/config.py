"""
Configuration constants for the AORC Wildfire Risk Analysis System.

Includes AORC S3 paths, variable definitions, FWI defaults,
and the complete NFDRS fuel model parameter table (models A-Z).

References:
    - AORC v1.1: Fall et al. 2023, JAWRA
    - NFDRS fuel models: Bradshaw et al. 1984, USFS INT-169
    - Fuel model parameters from firelab/NFDRS4-TechDoc (NFDRSV4Calc.py)
"""

# =============================================================================
# AORC Dataset Configuration
# =============================================================================

AORC_BUCKET = "noaa-nws-aorc-v1-1-1km"
AORC_PATH_PATTERN = "{year}.zarr"
AORC_CRS = "EPSG:4326"
AORC_RESOLUTION = 1 / 120  # 30 arc-seconds ≈ 800 m

# AORC variable names as stored in the ZARR archive.
# All values are returned RAW — no unit conversions applied at access time.
AORC_VARIABLES = {
    "TMP_2maboveground": {
        "description": "Air temperature at 2m above ground",
        "units": "K",
    },
    "SPFH_2maboveground": {
        "description": "Specific humidity at 2m above ground",
        "units": "kg/kg",
    },
    "PRES_surface": {
        "description": "Surface pressure",
        "units": "Pa",
    },
    "UGRD_10maboveground": {
        "description": "U-component of wind at 10m",
        "units": "m/s",
    },
    "VGRD_10maboveground": {
        "description": "V-component of wind at 10m",
        "units": "m/s",
    },
    "APCP_surface": {
        "description": "Total precipitation",
        "units": "mm",
    },
    "DSWRF_surface": {
        "description": "Downward short-wave radiation flux at surface",
        "units": "W/m^2",
    },
    "DLWRF_surface": {
        "description": "Downward long-wave radiation flux at surface",
        "units": "W/m^2",
    },
}


# =============================================================================
# Western Upper Peninsula of Michigan — Default Bounding Box
# =============================================================================

WUP_COUNTIES = ["Houghton", "Keweenaw", "Ontonagon", "Gogebic", "Iron", "Baraga"]

# Approximate bounding box (WGS84) covering all 6 WUP counties
WUP_LAT_BOUNDS = (46.0, 47.6)
WUP_LON_BOUNDS = (-90.5, -87.5)


# =============================================================================
# Canadian FWI System Defaults
# =============================================================================

# Startup values (used when no carry-forward state is available)
FWI_DEFAULTS = {
    "FFMC": 85.0,    # Fine Fuel Moisture Code
    "DMC": 6.0,      # Duff Moisture Code
    "DC": 15.0,      # Drought Code
}

# Day-length adjustment factors for DMC (Le) and DC (Lf) by month index (0=Jan).
# From Van Wagner & Pickett 1985, Table 1 (latitude ~46°N for WUP).
FWI_DAY_LENGTH_DMC = [6.5, 7.5, 9.0, 12.8, 13.9, 13.9, 12.4, 10.9, 9.4, 8.0, 7.0, 6.0]
FWI_DAY_LENGTH_DC = [-1.6, -1.6, -1.6, 0.9, 3.8, 5.8, 6.4, 5.0, 2.4, 0.4, -1.6, -1.6]


# =============================================================================
# NFDRS Fuel Model Parameters
# =============================================================================
#
# Complete table of the 22 NFDRS fuel models (A-L, N-Z).
# Note: There is no model M in the NFDRS system.
#
# Parameters per model:
#   SG1..SG1000  Surface-area-to-volume ratio (1/ft) for dead fuel classes
#   SGWOOD       Surface-area-to-volume ratio for live woody fuel
#   SGHERB       Surface-area-to-volume ratio for live herbaceous fuel
#   L1..L1000    Fuel loading (tons/acre) for dead fuel classes
#   LWOOD        Live woody fuel loading (tons/acre)
#   LHERB        Live herbaceous fuel loading (tons/acre)
#   DEPTH        Fuel bed depth (ft)
#   MXD          Dead fuel moisture of extinction (%)
#   HD           Heat of combustion, dead fuels (BTU/lb)
#   SCM          Spread component maximum
#   WNDFC        Wind reduction factor (0-1)
#   DROUGHT      Drought fuel loading adjustment (models V-Z only)
#
# Source: firelab/NFDRS4-TechDoc, src/NFDRSV4Calc.py (USNFDRSFuelModel class)
# Reference: Bradshaw et al. 1984, "The 1978 National Fire-Danger Rating System"

NFDRS_FUEL_MODELS = {
    # -------------------------------------------------------------------------
    # Grass group
    # -------------------------------------------------------------------------
    "A": {
        "name": "Western annual grass",
        "SG1": 3000, "SG10": 0, "SG100": 0, "SG1000": 0,
        "SGWOOD": 0, "SGHERB": 3000,
        "L1": 0.2, "L10": 0, "L100": 0, "L1000": 0,
        "LWOOD": 0, "LHERB": 0.3,
        "DEPTH": 0.8, "MXD": 15, "HD": 8000, "SCM": 301, "WNDFC": 0.6,
    },
    "L": {
        "name": "Western perennial grass",
        "SG1": 2000, "SG10": 109, "SG100": 30, "SG1000": 8,
        "SGWOOD": 1500, "SGHERB": 2000,
        "L1": 0.25, "L10": 0, "L100": 0, "L1000": 0,
        "LWOOD": 0, "LHERB": 0.5,
        "DEPTH": 1.0, "MXD": 15, "HD": 8000, "SCM": 178, "WNDFC": 0.6,
    },
    # -------------------------------------------------------------------------
    # Brush group
    # -------------------------------------------------------------------------
    "B": {
        "name": "Mature brush (6+ ft)",
        "SG1": 700, "SG10": 109, "SG100": 30, "SG1000": 8,
        "SGWOOD": 1250, "SGHERB": 3000,
        "L1": 3.5, "L10": 4, "L100": 0.5, "L1000": 0,
        "LWOOD": 11.5, "LHERB": 0,
        "DEPTH": 4.5, "MXD": 15, "HD": 9500, "SCM": 58, "WNDFC": 0.5,
    },
    "D": {
        "name": "Southern rough",
        "SG1": 1250, "SG10": 109, "SG100": 30, "SG1000": 8,
        "SGWOOD": 1500, "SGHERB": 1500,
        "L1": 2, "L10": 1, "L100": 0, "L1000": 0,
        "LWOOD": 3, "LHERB": 0.75,
        "DEPTH": 2.0, "MXD": 30, "HD": 9000, "SCM": 68, "WNDFC": 0.4,
    },
    "F": {
        "name": "Intermediate brush",
        "SG1": 700, "SG10": 109, "SG100": 30, "SG1000": 0,
        "SGWOOD": 1250, "SGHERB": 0,
        "L1": 2.5, "L10": 2, "L100": 1.5, "L1000": 0,
        "LWOOD": 9, "LHERB": 0,
        "DEPTH": 4.5, "MXD": 15, "HD": 9500, "SCM": 24, "WNDFC": 0.5,
    },
    "N": {
        "name": "Sawgrass",
        "SG1": 1600, "SG10": 109, "SG100": 30, "SG1000": 8,
        "SGWOOD": 1500, "SGHERB": 2000,
        "L1": 1.5, "L10": 1.5, "L100": 0, "L1000": 0,
        "LWOOD": 2, "LHERB": 0,
        "DEPTH": 3.0, "MXD": 25, "HD": 8700, "SCM": 167, "WNDFC": 0.6,
    },
    "O": {
        "name": "High pocosin",
        "SG1": 1500, "SG10": 109, "SG100": 30, "SG1000": 8,
        "SGWOOD": 1500, "SGHERB": 1500,
        "L1": 2, "L10": 3, "L100": 3, "L1000": 2,
        "LWOOD": 7, "LHERB": 0,
        "DEPTH": 4.0, "MXD": 30, "HD": 9000, "SCM": 99, "WNDFC": 0.5,
    },
    "Q": {
        "name": "Alaska black spruce",
        "SG1": 1500, "SG10": 109, "SG100": 30, "SG1000": 8,
        "SGWOOD": 1200, "SGHERB": 1500,
        "L1": 2, "L10": 2.5, "L100": 2, "L1000": 1,
        "LWOOD": 4, "LHERB": 0.5,
        "DEPTH": 3.0, "MXD": 25, "HD": 8000, "SCM": 59, "WNDFC": 0.4,
    },
    "T": {
        "name": "Sagebrush-grass",
        "SG1": 2500, "SG10": 109, "SG100": 30, "SG1000": 8,
        "SGWOOD": 1500, "SGHERB": 2000,
        "L1": 1, "L10": 0.5, "L100": 0, "L1000": 0,
        "LWOOD": 2.5, "LHERB": 0.5,
        "DEPTH": 1.25, "MXD": 15, "HD": 8000, "SCM": 96, "WNDFC": 0.6,
    },
    # -------------------------------------------------------------------------
    # Timber group
    # -------------------------------------------------------------------------
    "C": {
        "name": "Open pine with grass understory",
        "SG1": 2000, "SG10": 109, "SG100": 30, "SG1000": 8,
        "SGWOOD": 1500, "SGHERB": 2500,
        "L1": 0.4, "L10": 1, "L100": 0, "L1000": 0,
        "LWOOD": 0.5, "LHERB": 0.8,
        "DEPTH": 0.75, "MXD": 20, "HD": 8000, "SCM": 32, "WNDFC": 0.5,
    },
    "E": {
        "name": "Hardwood litter (fall/winter)",
        "SG1": 2000, "SG10": 109, "SG100": 30, "SG1000": 8,
        "SGWOOD": 1500, "SGHERB": 2000,
        "L1": 1.5, "L10": 0.5, "L100": 0.25, "L1000": 0,
        "LWOOD": 0.5, "LHERB": 0.5,
        "DEPTH": 0.4, "MXD": 25, "HD": 8000, "SCM": 25, "WNDFC": 0.4,
    },
    "G": {
        "name": "Dense conifer with heavy dead fuel (timber understory)",
        "SG1": 2000, "SG10": 109, "SG100": 30, "SG1000": 8,
        "SGWOOD": 1500, "SGHERB": 2000,
        "L1": 2.5, "L10": 2, "L100": 5, "L1000": 12,
        "LWOOD": 0.5, "LHERB": 0.5,
        "DEPTH": 1.0, "MXD": 25, "HD": 8000, "SCM": 30, "WNDFC": 0.4,
    },
    "H": {
        "name": "Short needle conifer (normal dead)",
        "SG1": 2000, "SG10": 109, "SG100": 30, "SG1000": 8,
        "SGWOOD": 1500, "SGHERB": 2000,
        "L1": 1.5, "L10": 1, "L100": 2, "L1000": 2,
        "LWOOD": 0.5, "LHERB": 0.5,
        "DEPTH": 0.3, "MXD": 20, "HD": 8000, "SCM": 8, "WNDFC": 0.4,
    },
    "P": {
        "name": "Southern pine plantation",
        "SG1": 1750, "SG10": 109, "SG100": 30, "SG1000": 8,
        "SGWOOD": 1500, "SGHERB": 2000,
        "L1": 1, "L10": 1, "L100": 0.5, "L1000": 2,
        "LWOOD": 0.5, "LHERB": 0.5,
        "DEPTH": 0.4, "MXD": 30, "HD": 8000, "SCM": 14, "WNDFC": 0.4,
    },
    "R": {
        "name": "Hardwood litter (spring/summer)",
        "SG1": 1500, "SG10": 109, "SG100": 30, "SG1000": 8,
        "SGWOOD": 1500, "SGHERB": 2000,
        "L1": 0.5, "L10": 0.5, "L100": 0.5, "L1000": 0,
        "LWOOD": 0.5, "LHERB": 0.5,
        "DEPTH": 0.25, "MXD": 25, "HD": 8000, "SCM": 6, "WNDFC": 0.4,
    },
    "S": {
        "name": "Alaska spruce-lichen tundra",
        "SG1": 1500, "SG10": 109, "SG100": 30, "SG1000": 8,
        "SGWOOD": 1200, "SGHERB": 1500,
        "L1": 0.5, "L10": 0.5, "L100": 0.5, "L1000": 0.5,
        "LWOOD": 0.5, "LHERB": 0.5,
        "DEPTH": 0.4, "MXD": 25, "HD": 8000, "SCM": 17, "WNDFC": 0.6,
    },
    "U": {
        "name": "Western long-needle pine",
        "SG1": 1750, "SG10": 109, "SG100": 30, "SG1000": 8,
        "SGWOOD": 1500, "SGHERB": 2000,
        "L1": 1.5, "L10": 1.5, "L100": 1, "L1000": 0,
        "LWOOD": 0.5, "LHERB": 0.5,
        "DEPTH": 0.5, "MXD": 20, "HD": 8000, "SCM": 16, "WNDFC": 0.4,
    },
    # -------------------------------------------------------------------------
    # Slash group
    # -------------------------------------------------------------------------
    "I": {
        "name": "Heavy slash (3+ yr)",
        "SG1": 1500, "SG10": 109, "SG100": 30, "SG1000": 8,
        "SGWOOD": 1500, "SGHERB": 2000,
        "L1": 12, "L10": 12, "L100": 10, "L1000": 12,
        "LWOOD": 0, "LHERB": 0,
        "DEPTH": 2.0, "MXD": 25, "HD": 8000, "SCM": 65, "WNDFC": 0.5,
    },
    "J": {
        "name": "Medium slash (1-2 yr)",
        "SG1": 1500, "SG10": 109, "SG100": 30, "SG1000": 8,
        "SGWOOD": 1500, "SGHERB": 2000,
        "L1": 7, "L10": 7, "L100": 6, "L1000": 5.5,
        "LWOOD": 0, "LHERB": 0,
        "DEPTH": 1.3, "MXD": 25, "HD": 8000, "SCM": 44, "WNDFC": 0.5,
    },
    "K": {
        "name": "Light slash (<1 yr)",
        "SG1": 1500, "SG10": 109, "SG100": 30, "SG1000": 8,
        "SGWOOD": 1500, "SGHERB": 2000,
        "L1": 2.5, "L10": 2.5, "L100": 2, "L1000": 2.5,
        "LWOOD": 0, "LHERB": 0,
        "DEPTH": 0.6, "MXD": 25, "HD": 8000, "SCM": 23, "WNDFC": 0.5,
    },
    # -------------------------------------------------------------------------
    # Drought-adjusted models (V-Z)
    # -------------------------------------------------------------------------
    "V": {
        "name": "Western grass (drought-adjusted)",
        "SG1": 2000, "SG10": 109, "SG100": 30, "SG1000": 8,
        "SGWOOD": 1500, "SGHERB": 2000,
        "L1": 0.1, "L10": 0.0, "L100": 0.0, "L1000": 0.0,
        "LWOOD": 0.0, "LHERB": 1.0,
        "DEPTH": 1.0, "MXD": 15, "HD": 8000, "SCM": 108, "WNDFC": 0.6,
        "DROUGHT": 0,
    },
    "W": {
        "name": "Western shrub (drought-adjusted)",
        "SG1": 2000, "SG10": 109, "SG100": 30, "SG1000": 8,
        "SGWOOD": 1500, "SGHERB": 2000,
        "L1": 0.5, "L10": 0.5, "L100": 0.0, "L1000": 0.0,
        "LWOOD": 1.0, "LHERB": 0.6,
        "DEPTH": 1.5, "MXD": 15, "HD": 8000, "SCM": 62, "WNDFC": 0.4,
        "DROUGHT": 1,
    },
    "X": {
        "name": "Western brush/timber (drought-adjusted)",
        "SG1": 2000, "SG10": 109, "SG100": 30, "SG1000": 8,
        "SGWOOD": 1500, "SGHERB": 2000,
        "L1": 4.5, "L10": 2.45, "L100": 0.0, "L1000": 0.0,
        "LWOOD": 7.0, "LHERB": 1.55,
        "DEPTH": 4.4, "MXD": 25, "HD": 8000, "SCM": 104, "WNDFC": 0.4,
        "DROUGHT": 2.5,
    },
    "Y": {
        "name": "Western timber (drought-adjusted)",
        "SG1": 2000, "SG10": 109, "SG100": 30, "SG1000": 8,
        "SGWOOD": 1500, "SGHERB": 2000,
        "L1": 2.5, "L10": 2.2, "L100": 3.6, "L1000": 10.16,
        "LWOOD": 0, "LHERB": 0,
        "DEPTH": 0.6, "MXD": 25, "HD": 8000, "SCM": 5, "WNDFC": 0.2,
        "DROUGHT": 5,
    },
    "Z": {
        "name": "Western slash (drought-adjusted)",
        "SG1": 2000, "SG10": 109, "SG100": 30, "SG1000": 8,
        "SGWOOD": 1500, "SGHERB": 2000,
        "L1": 4.5, "L10": 4.25, "L100": 4.0, "L1000": 4.0,
        "LWOOD": 0.0, "LHERB": 0.0,
        "DEPTH": 1.5, "MXD": 25, "HD": 8000, "SCM": 19, "WNDFC": 0.4,
        "DROUGHT": 7,
    },
}

# Default fuel model for Western Upper Peninsula (dense conifer forest)
DEFAULT_FUEL_MODEL = "G"

# Conversion factor: tons/acre to lbs/ft² (used in NFDRS calculations)
NFDRS_CTA = 0.046

# Physical constants used across NFDRS calculations
NFDRS_STD = 0.0555    # Mineral content of dead fuel
NFDRS_STL = 0.0555    # Mineral content of live fuel
NFDRS_RHOD = 32.0     # Particle density of dead fuel (lb/ft³)
NFDRS_RHOL = 32.0     # Particle density of live fuel (lb/ft³)
NFDRS_SD = 0.01       # Effective mineral content, dead
NFDRS_SL = 0.01       # Effective mineral content, live
NFDRS_DEFAULT_SLOPE = 12.67  # Default slope angle (degrees) if terrain data unavailable


# =============================================================================
# NDVI / Satellite Data Configuration (for FPI)
# =============================================================================

# NASA Earthdata MODIS NDVI product
MODIS_NDVI_PRODUCT = "MOD13A2"         # 1 km, 16-day composite
MODIS_NDVI_COLLECTION = "061"
VIIRS_NDVI_PRODUCT = "VNP13A1"         # 500 m, 16-day composite

# NDVI physical range
NDVI_SCALE_FACTOR = 0.0001  # MODIS NDVI is stored as int16 × 10000
NDVI_VALID_RANGE = (-2000, 10000)  # Before scale factor
