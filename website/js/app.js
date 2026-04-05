/**
 * Main application — initializes map, loads point index, wires up UI.
 *
 * Data source UI broken into two modes:
 *
 *   HISTORICAL
 *     - Dataset selector (AORC — expandable later)
 *
 *   FUTURE
 *     - Projection Period (near-term / mid-century / end-century)
 *     - Global Climate Model (GCM), grouped by modeling institution
 *     - Downscaling Method (statistical BCSD / dynamical WRF / RegCM4)
 *     - Emissions Scenario (SSP / RCP)
 *
 * Each combination updates a Data Characteristics card showing:
 *     badges, data type, spatial resolution, temporal resolution,
 *     available period, modeling chain, variable completeness, source.
 */

// =====================================================================
// GCM list (for mapping to downscaling methods)
// =====================================================================

const CMIP6_GCMS = [
    "ACCESS-CM2", "ACCESS-ESM1-5", "BCC-CSM2-MR", "CanESM5",
    "CMCC-CM2-SR5", "CMCC-ESM2", "EC-Earth3", "EC-Earth3-Veg-LR",
    "FGOALS-g3", "GFDL-CM4", "GFDL-ESM4", "GISS-E2-1-G",
    "HadGEM3-GC31-LL", "INM-CM4-8", "INM-CM5-0", "IPSL-CM6A-LR",
    "KACE-1-0-G", "KIOST-ESM", "MIROC-ES2L", "MIROC6",
    "MPI-ESM1-2-HR", "MPI-ESM1-2-LR", "MRI-ESM2-0", "NorESM2-LM",
    "NorESM2-MM", "TaiESM1", "UKESM1-0-LL",
];

// =====================================================================
// Downscaling method metadata
// =====================================================================

const DOWNSCALING = {
    bcsd: {
        label: "BCSD Statistical (NEX-GDDP-CMIP6)",
        dataKey: "nex-gddp-cmip6",
        scenarios: [
            { value: "ssp245", label: "SSP2-4.5 — mid-range emissions" },
            { value: "ssp585", label: "SSP5-8.5 — high emissions" },
        ],
        info: {
            badges:    ["modeled", "statistical", "daily", "coarse"],
            type:      "GCM output, bias-corrected spatial disaggregation (BCSD)",
            spatial:   "0.25° (~25 km)",
            temporal:  "Daily (disaggregated to hourly for fire indices)",
            period:    "2015 – 2100",
            variables: "T, RH, precip, wind (no radiation)",
            source:    "NASA NEX-GDDP-CMIP6 (Thrasher et al. 2022)",
            hasVars:   ["T", "RH", "wind", "precip"],
        },
        chain: (gcm) => `${gcm} → BCSD statistical → 0.25° grid`,
    },
    wrf: {
        label: "WRF Dynamical RCM (ClimRR / Argonne)",
        dataKey: "climrr",
        scenarios: [
            { value: "ssp245", label: "SSP2-4.5 — mid-range emissions" },
            { value: "ssp585", label: "SSP5-8.5 — high emissions" },
        ],
        info: {
            badges:    ["modeled", "dynamical", "daily"],
            type:      "Dynamical downscaling — WRF regional climate model",
            spatial:   "12 km",
            temporal:  "Daily (disaggregated to hourly for fire indices)",
            period:    "Hist: 1995–2014 | Mid: 2045–2064 | End: 2075–2094",
            variables: "T, Tmin, Tmax, precip, wind, humidity",
            source:    "Argonne National Lab ClimRR (CESM2 → WRF)",
            hasVars:   ["T", "RH", "wind", "precip"],
        },
        chain: (gcm) => `${gcm} → WRF (Argonne) → 12 km grid`,
    },
    regcm4: {
        label: "RegCM4 Dynamical RCM (GLARM / Michigan Tech)",
        dataKey: "glarm",
        scenarios: [
            { value: "rcp45", label: "RCP 4.5 — stabilization pathway" },
            { value: "rcp85", label: "RCP 8.5 — high emissions pathway" },
        ],
        info: {
            badges:    ["modeled", "dynamical", "daily"],
            type:      "Dynamical downscaling — RegCM4 regional climate model",
            spatial:   "18 km (atmosphere), 1–4 km (lake surface)",
            temporal:  "Daily (disaggregated to hourly for fire indices)",
            period:    "1981 – 2099",
            variables: "T, Q, wind, precip, SW/LW radiation",
            source:    "GLARM-Proj1, Michigan Tech (Xue et al. 2022)",
            hasVars:   ["T", "RH", "wind", "precip", "radiation"],
        },
        chain: () => "GCM ensemble → RegCM4 → 18 km grid",
    },
};

/** Available downscaling methods for a given GCM. */
function getDownscalingKeys(gcm) {
    if (CMIP6_GCMS.includes(gcm)) return ["bcsd"];
    if (gcm === "CESM2")          return ["wrf"];
    if (gcm === "RegCM4-driven")  return ["regcm4"];
    return ["bcsd"];
}

// =====================================================================
// Historical dataset metadata
// =====================================================================

// =====================================================================
// Fire Danger Index variable requirements
// =====================================================================

/**
 * Maps each FDI system to the weather variables it requires.
 * Used to determine which indices a dataset can compute.
 */
const FDI_REQUIREMENTS = {
    cfwi: { label: "Canadian FWI", needs: ["T", "RH", "wind", "precip"] },
    nfdrs: { label: "NFDRS", needs: ["T", "RH", "wind", "precip"] },
    fpi: { label: "FPI", needs: ["T", "RH"] },
};

const HISTORICAL = {

    // --- Reanalysis (Observed + Modeled) ---

    aorc: {
        badges:    ["observed", "reanalysis", "hourly", "highres"],
        type:      "Reanalysis — observations assimilated into atmospheric model",
        spatial:   "~800 m (~0.009\u00b0)",
        temporal:  "Hourly",
        period:    "1979 \u2013 present",
        variables: "Full suite (T, RH, wind U/V, precip, SW/LW radiation, pressure)",
        source:    "NOAA AORC v1.1 (Analysis of Record for Calibration)",
        access:    "S3: s3://noaa-nws-aorc-v1-1-1km (ZARR)",
        hasVars:   ["T", "RH", "wind", "precip", "radiation", "pressure"],
    },
    nldas2: {
        badges:    ["observed", "reanalysis", "hourly"],
        type:      "Land-surface reanalysis — gauge-corrected forcing blend",
        spatial:   "0.125\u00b0 (~12 km)",
        temporal:  "Hourly",
        period:    "1979 \u2013 present",
        variables: "T, precip, RH, wind, SW/LW radiation, surface pressure",
        source:    "NASA NLDAS-2 (North American Land Data Assimilation System)",
        access:    "NASA GES DISC (OPeNDAP, HTTPS). Requires Earthdata login.",
        hasVars:   ["T", "RH", "wind", "precip", "radiation", "pressure"],
    },
    era5: {
        badges:    ["observed", "reanalysis", "hourly", "global"],
        type:      "Global reanalysis — full atmospheric model + data assimilation",
        spatial:   "0.25\u00b0 (~31 km)",
        temporal:  "Hourly",
        period:    "1940 \u2013 present",
        variables: "200+ vars: T, wind (multi-level), precip, RH, radiation, CAPE, soil, snow",
        source:    "ECMWF ERA5 (Hersbach et al. 2020)",
        access:    "S3: s3://era5-pds/ (AWS Open Data). Also Copernicus CDS API.",
        hasVars:   ["T", "RH", "wind", "precip", "radiation", "pressure"],
    },
    era5land: {
        badges:    ["observed", "reanalysis", "hourly"],
        type:      "Land-focused reanalysis — ERA5 forcing with enhanced land model",
        spatial:   "0.1\u00b0 (~9 km)",
        temporal:  "Hourly",
        period:    "1950 \u2013 present",
        variables: "T (2m), dewpoint, wind, precip, snow, soil moisture/temp, runoff, evaporation",
        source:    "ECMWF ERA5-Land (Mu\u00f1oz-Sabater et al. 2021)",
        access:    "Copernicus CDS API. Also Google Cloud.",
        hasVars:   ["T", "RH", "wind", "precip"],
    },
    narr: {
        badges:    ["observed", "reanalysis", "subhourly"],
        type:      "Regional reanalysis — NCEP Eta model + North American observations",
        spatial:   "32 km",
        temporal:  "3-hourly",
        period:    "1979 \u2013 2024 (discontinued)",
        variables: "T, precip, wind, RH, radiation, pressure, soil moisture, snow, clouds",
        source:    "NCEP NARR (North American Regional Reanalysis)",
        access:    "NCEI THREDDS/OPeNDAP, NOMADS. No S3.",
        hasVars:   ["T", "RH", "wind", "precip", "radiation", "pressure"],
    },
    hrrr: {
        badges:    ["modeled", "reanalysis", "hourly", "highres"],
        type:      "NWP analysis — high-resolution model with radar/obs assimilation",
        spatial:   "3 km",
        temporal:  "Hourly (analysis + forecasts)",
        period:    "2014 \u2013 present",
        variables: "T, wind, precip, RH, radiation, snow, CAPE, visibility, smoke (HRRRsmoke)",
        source:    "NOAA HRRR (High-Resolution Rapid Refresh)",
        access:    "S3: s3://noaa-hrrr-bdp-pds/ (GRIB2). Zarr: s3://hrrrzarr/",
        hasVars:   ["T", "RH", "wind", "precip", "radiation"],
    },
    rtma: {
        badges:    ["observed", "reanalysis", "hourly", "highres"],
        type:      "Mesoscale analysis — observation-corrected model background",
        spatial:   "2.5 km",
        temporal:  "Hourly",
        period:    "2011 \u2013 present",
        variables: "T, dewpoint, wind U/V + gust, pressure, visibility, ceiling, precip (URMA)",
        source:    "NOAA RTMA/URMA (Real-Time / UnRestricted Mesoscale Analysis)",
        access:    "S3: s3://noaa-rtma-pds/, s3://noaa-urma-pds/",
        hasVars:   ["T", "RH", "wind", "precip", "pressure"],
    },

    // --- Gridded Observations (Station-interpolated) ---

    prism: {
        badges:    ["observed", "station", "daily", "highres"],
        type:      "Gridded station obs — topographic regression interpolation",
        spatial:   "800 m (daily), 4 km (normals)",
        temporal:  "Daily (monthly normals available)",
        period:    "1895 \u2013 present (daily from 1981)",
        variables: "Tmax, Tmin, Tmean, precip, dewpoint, VPD",
        source:    "PRISM Climate Group (Oregon State University)",
        access:    "PRISM FTP/HTTP. Also on Google Earth Engine.",
        hasVars:   ["T", "RH", "precip"],  // dewpoint → RH derivable, no wind
    },
    daymet: {
        badges:    ["observed", "station", "daily", "highres"],
        type:      "Gridded station obs — Gaussian interpolation with DEM corrections",
        spatial:   "1 km",
        temporal:  "Daily",
        period:    "1980 \u2013 present (~2-year lag)",
        variables: "Tmax, Tmin, precip, shortwave radiation, vapor pressure, SWE, day length",
        source:    "Daymet v4 (ORNL DAAC, Thornton et al.)",
        access:    "S3: s3://daymet-v4-na/ (AWS Open Data). Also THREDDS.",
        hasVars:   ["T", "RH", "precip", "radiation"],  // vapor pressure → RH derivable, no wind
    },
    gridmet: {
        badges:    ["observed", "station", "daily"],
        type:      "Hybrid gridded obs — PRISM climate + NLDAS-2 meteorology",
        spatial:   "~4 km (1/24\u00b0)",
        temporal:  "Daily",
        period:    "1979 \u2013 present",
        variables: "Tmax, Tmin, precip, wind, RH, radiation, ET, VPD, fire indices (ERC, BI, FM100)",
        source:    "GridMET (Climatology Lab, Abatzoglou 2013)",
        access:    "Climatology Lab HTTP. Also Google Earth Engine.",
        hasVars:   ["T", "RH", "wind", "precip", "radiation"],
    },
    livneh: {
        badges:    ["observed", "station", "daily"],
        type:      "Gridded station obs — interpolated with SNOTEL/COOP gauge corrections",
        spatial:   "1/16\u00b0 (~6 km)",
        temporal:  "Daily",
        period:    "1915 \u2013 2015 (static, no updates)",
        variables: "Tmax, Tmin, precip, wind",
        source:    "Livneh et al. (USGS/NCAR)",
        access:    "NCAR Climate Data Gateway, USGS ScienceBase.",
        hasVars:   ["T", "wind", "precip"],  // no RH or humidity variable
    },

    // --- Radar / Satellite Derived ---

    mrms: {
        badges:    ["observed", "radar", "subhourly", "highres"],
        type:      "Multi-sensor blend — NEXRAD radar + gauges + satellite",
        spatial:   "1 km",
        temporal:  "2-minute (precipitation)",
        period:    "2014 \u2013 present (reprocessed to ~2001)",
        variables: "Precip rate/accumulation, radar reflectivity, rotation, hail indicators",
        source:    "NOAA MRMS (Multi-Radar Multi-Sensor)",
        access:    "S3: s3://noaa-mrms-pds/ (AWS NODD). Also Iowa Mesonet archive.",
        hasVars:   ["precip"],
    },
    cpc: {
        badges:    ["observed", "station", "daily"],
        type:      "Gridded gauge obs — optimal interpolation of global station network",
        spatial:   "0.25\u00b0 (~25 km, CONUS precip) / 0.5\u00b0 (global temp)",
        temporal:  "Daily",
        period:    "1948 \u2013 present (temp) / 1979 \u2013 present (precip)",
        variables: "Precipitation (unified gauge); separately: Tmax, Tmin",
        source:    "NOAA CPC Unified (Climate Prediction Center)",
        access:    "CPC FTP. Also NOAA PSL OPeNDAP.",
        hasVars:   ["T", "precip"],
    },
};

// =====================================================================
// Badge display names and CSS class
// =====================================================================

const BADGE_CONFIG = {
    observed:    { text: "Observed",       css: "badge-observed" },
    reanalysis:  { text: "Reanalysis",     css: "badge-reanalysis" },
    modeled:     { text: "Modeled",        css: "badge-modeled" },
    station:     { text: "Station-based",  css: "badge-station" },
    radar:       { text: "Radar/Satellite",css: "badge-radar" },
    statistical: { text: "Statistical DS", css: "badge-statistical" },
    dynamical:   { text: "Dynamical RCM",  css: "badge-dynamical" },
    global:      { text: "Global",         css: "badge-global" },
    hourly:      { text: "Hourly",         css: "badge-hourly" },
    subhourly:   { text: "Sub-hourly",     css: "badge-hourly" },
    daily:       { text: "Daily",          css: "badge-daily" },
    highres:     { text: "High-res",       css: "badge-highres" },
    coarse:      { text: "~25 km",         css: "badge-coarse" },
};

// =====================================================================
// App
// =====================================================================

const App = {
    _mode: "historical",

    async init() {
        document.getElementById("status-text").textContent = "Initializing map...";
        MapLayer.initMap();
        UIControls.init();
        this._initSourceSelectors();
        this._updateInfoCard();
        this._updateFdiAvailability();
        await this.loadPoints();
    },

    // ------------------------------------------------------------------
    // Wire up all source selectors
    // ------------------------------------------------------------------

    _initSourceSelectors() {
        const self = this;

        // Historical / Future toggle
        document.querySelectorAll(".mode-btn").forEach(btn => {
            btn.addEventListener("click", () => {
                document.querySelectorAll(".mode-btn").forEach(b => b.classList.remove("active"));
                btn.classList.add("active");
                self._mode = btn.dataset.mode;
                document.getElementById("historical-options").style.display =
                    self._mode === "historical" ? "" : "none";
                document.getElementById("future-options").style.display =
                    self._mode === "future" ? "" : "none";
                self._onFilterChange();
            });
        });

        // Historical dataset change
        document.getElementById("hist-dataset-select")
            .addEventListener("change", () => self._onFilterChange());

        // Future: all four filters trigger the same update
        ["period-select", "gcm-select", "downscaling-select", "scenario-select"]
            .forEach(id => {
                document.getElementById(id).addEventListener("change", () => {
                    // GCM change cascades to downscaling → scenarios
                    if (id === "gcm-select") self._populateDownscaling();
                    if (id === "gcm-select" || id === "downscaling-select") self._populateScenarios();
                    self._onFilterChange();
                });
            });

        // Initial cascade
        this._populateDownscaling();
        this._populateScenarios();
    },

    /** Common handler: any filter changed → update card + load data. */
    _onFilterChange() {
        this._updateInfoCard();
        this._updateFdiAvailability();
        this._applySource();
    },

    // ------------------------------------------------------------------
    // Cascading dropdown population
    // ------------------------------------------------------------------

    _populateDownscaling() {
        const gcm = document.getElementById("gcm-select").value;
        const sel = document.getElementById("downscaling-select");
        const prev = sel.value;
        sel.innerHTML = "";

        getDownscalingKeys(gcm).forEach(key => {
            const d = DOWNSCALING[key];
            if (!d) return;
            const opt = document.createElement("option");
            opt.value = key;
            opt.textContent = d.label;
            if (key === prev) opt.selected = true;
            sel.appendChild(opt);
        });

        this._populateScenarios();
    },

    _populateScenarios() {
        const dsKey = document.getElementById("downscaling-select").value;
        const d = DOWNSCALING[dsKey];
        const sel = document.getElementById("scenario-select");
        const prev = sel.value;
        sel.innerHTML = "";

        if (d) {
            d.scenarios.forEach(s => {
                const opt = document.createElement("option");
                opt.value = s.value;
                opt.textContent = s.label;
                if (s.value === prev) opt.selected = true;
                sel.appendChild(opt);
            });
        }
    },

    // ------------------------------------------------------------------
    // Data characteristics card
    // ------------------------------------------------------------------

    _updateInfoCard() {
        const badgesEl  = document.getElementById("card-badges");
        const typeEl    = document.getElementById("card-type");
        const spatEl    = document.getElementById("card-resolution");
        const tempEl    = document.getElementById("card-temporal");
        const periodEl  = document.getElementById("card-period");
        const varsEl    = document.getElementById("card-variables");
        const sourceEl  = document.getElementById("card-source");
        const chainRow  = document.getElementById("card-chain-row");
        const chainEl   = document.getElementById("card-chain");
        const accessRow = document.getElementById("card-access-row");
        const accessEl  = document.getElementById("card-access");

        let info;

        if (this._mode === "historical") {
            const dsKey = document.getElementById("hist-dataset-select").value;
            info = HISTORICAL[dsKey] || HISTORICAL.aorc;
            chainRow.style.display = "none";
        } else {
            const gcm   = document.getElementById("gcm-select").value;
            const dsKey = document.getElementById("downscaling-select").value;
            const d     = DOWNSCALING[dsKey];
            if (!d) return;
            info = d.info;

            // Modeling chain
            chainRow.style.display = "";
            chainEl.textContent = d.chain(gcm);
        }

        // Render badges
        badgesEl.innerHTML = "";
        (info.badges || []).forEach(key => {
            const bc = BADGE_CONFIG[key];
            if (!bc) return;
            const span = document.createElement("span");
            span.className = `source-badge ${bc.css}`;
            span.textContent = bc.text;
            badgesEl.appendChild(span);
        });

        typeEl.textContent   = info.type;
        spatEl.textContent   = info.spatial;
        tempEl.textContent   = info.temporal;
        periodEl.textContent = info.period;
        varsEl.textContent   = info.variables;
        sourceEl.textContent = info.source;

        // Access method (historical datasets)
        if (info.access) {
            accessRow.style.display = "";
            accessEl.textContent = info.access;
        } else {
            accessRow.style.display = "none";
        }
    },

    // ------------------------------------------------------------------
    // FDI capability checking
    // ------------------------------------------------------------------

    /**
     * Get the hasVars array for the current data source selection.
     */
    _getCurrentHasVars() {
        if (this._mode === "historical") {
            const dsKey = document.getElementById("hist-dataset-select").value;
            const ds = HISTORICAL[dsKey] || HISTORICAL.aorc;
            return ds.hasVars || [];
        }
        const dsKey = document.getElementById("downscaling-select").value;
        const d = DOWNSCALING[dsKey];
        return (d && d.info && d.info.hasVars) ? d.info.hasVars : [];
    },

    /**
     * Check if a dataset can compute a specific FDI system.
     * @param {string[]} hasVars - variables the dataset provides
     * @param {string} fdiKey - key into FDI_REQUIREMENTS (cfwi, nfdrs, fpi)
     * @returns {boolean}
     */
    _canComputeFdi(hasVars, fdiKey) {
        const req = FDI_REQUIREMENTS[fdiKey];
        if (!req) return false;
        return req.needs.every(v => hasVars.includes(v));
    },

    /**
     * Update layer panel dropdowns: disable FDI options the current dataset
     * cannot compute, and show an FDI capability summary on the info card.
     */
    _updateFdiAvailability() {
        const hasVars = this._getCurrentHasVars();

        // Map layer select IDs to their FDI system key
        const fdiSelects = {
            "layer-fdi": null,     // composite — check per-option
            "layer-cfwi": "cfwi",
            "layer-nfdrs": "nfdrs",
            "layer-fpi": "fpi",
        };

        for (const [selId, fdiKey] of Object.entries(fdiSelects)) {
            const sel = document.getElementById(selId);
            if (!sel) continue;

            const options = sel.querySelectorAll("option");
            options.forEach(opt => {
                if (!opt.value) return; // skip placeholder

                let canCompute;
                if (fdiKey) {
                    canCompute = this._canComputeFdi(hasVars, fdiKey);
                } else {
                    // Composite FDI dropdown — check by option value prefix
                    const prefix = opt.value.split("/")[0];
                    canCompute = this._canComputeFdi(hasVars, prefix);
                }

                opt.disabled = !canCompute;
                opt.style.color = canCompute ? "" : "#5c3a20";
            });

            // If current selection is now disabled, reset to placeholder
            if (sel.value && sel.selectedOptions[0] && sel.selectedOptions[0].disabled) {
                sel.value = "";
            }
        }

        // Update FDI capability badges on info card
        this._renderFdiBadges(hasVars);
    },

    /**
     * Render FDI capability indicators below the existing badges on the info card.
     */
    _renderFdiBadges(hasVars) {
        let container = document.getElementById("card-fdi-badges");
        if (!container) {
            // Create container after main badges
            const badgesEl = document.getElementById("card-badges");
            container = document.createElement("div");
            container.id = "card-fdi-badges";
            container.className = "source-card-badges";
            container.style.marginTop = "4px";
            badgesEl.parentNode.insertBefore(container, badgesEl.nextSibling);
        }
        container.innerHTML = "";

        for (const [key, req] of Object.entries(FDI_REQUIREMENTS)) {
            const can = this._canComputeFdi(hasVars, key);
            const span = document.createElement("span");
            span.className = `source-badge ${can ? "badge-fdi-yes" : "badge-fdi-no"}`;
            span.textContent = `${req.label}: ${can ? "Yes" : "No"}`;
            span.title = can
                ? `Can compute ${req.label} (has ${req.needs.join(", ")})`
                : `Missing: ${req.needs.filter(v => !hasVars.includes(v)).join(", ")}`;
            container.appendChild(span);
        }
    },

    // ------------------------------------------------------------------
    // Build data path from selections and load
    // ------------------------------------------------------------------

    _applySource() {
        let path;

        if (this._mode === "historical") {
            const ds = document.getElementById("hist-dataset-select").value;
            path = (ds === "aorc") ? "../data/output" : `../data/output_${ds}`;
        } else {
            const gcm      = document.getElementById("gcm-select").value;
            const dsKey    = document.getElementById("downscaling-select").value;
            const scenario = document.getElementById("scenario-select").value;
            const d        = DOWNSCALING[dsKey];
            if (!d) return;

            if (d.dataKey === "nex-gddp-cmip6") {
                path = `../data/output_nex_${gcm}_${scenario}`;
            } else if (d.dataKey === "glarm") {
                path = `../data/output_glarm_${scenario}`;
            } else if (d.dataKey === "climrr") {
                path = `../data/output_climrr_${scenario}`;
            }
        }

        DataLoader.setBasePath(path);
        UIControls._updateProvenance();
        this.loadPoints();
    },

    // ------------------------------------------------------------------
    // Helper getters used by UIControls for provenance
    // ------------------------------------------------------------------

    getSourceInfo() {
        if (this._mode === "historical") {
            return {
                mode: "historical",
                dataset: document.getElementById("hist-dataset-select").value,
            };
        }
        return {
            mode:         "future",
            gcm:          document.getElementById("gcm-select").value,
            downscaling:  document.getElementById("downscaling-select").value,
            scenario:     document.getElementById("scenario-select").value,
            period:       document.getElementById("period-select").value,
        };
    },

    // ------------------------------------------------------------------
    // Point loading
    // ------------------------------------------------------------------

    async loadPoints() {
        const status = document.getElementById("status-text");

        try {
            status.textContent = "Loading point index...";
            MapLayer.showLoading("Loading point index...");

            const points = await DataLoader.loadPointIndex();
            MapLayer.plotPoints(points);

            if (points.length > 0) {
                const lats = points.map(p => p.latitude);
                const lons = points.map(p => p.longitude);
                MapLayer.map.fitBounds([
                    [Math.min(...lats), Math.min(...lons)],
                    [Math.max(...lats), Math.max(...lons)],
                ], { padding: [20, 20] });
            }

            status.textContent = `${points.length} points loaded`;
            MapLayer.hideLoading();
        } catch (err) {
            console.warn("Could not load point index:", err.message);
            status.textContent = "No data — run extraction for this source first";
            MapLayer.hideLoading();
            this._showWelcome();
        }
    },

    _showWelcome() {
        const info = document.getElementById("point-info");
        info.innerHTML = `
            <div style="padding: 8px; font-size: 0.8rem; line-height: 1.6;">
                <p><strong>Welcome!</strong></p>
                <p>To get started:</p>
                <ol style="padding-left: 16px; margin-top: 4px;">
                    <li>Run <code>aorc-tools points</code> to generate the point index</li>
                    <li>Run <code>aorc-tools extract</code> for historical data</li>
                    <li>Run <code>aorc-tools project-extract</code> for future projections</li>
                </ol>
            </div>
        `;
        document.getElementById("info-panel").style.display = "block";
    },
};

document.addEventListener("DOMContentLoaded", () => App.init());
