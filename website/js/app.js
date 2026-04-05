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

const HISTORICAL = {
    aorc: {
        label: "AORC v1.1 (NOAA)",
        badges:    ["observed", "reanalysis", "hourly", "highres"],
        type:      "Reanalysis — observations assimilated into atmospheric model",
        spatial:   "~800 m (~0.009°)",
        temporal:  "Hourly",
        period:    "1979 – present",
        variables: "Full suite (T, RH, wind U/V, precip, SW/LW radiation)",
        source:    "NOAA AORC v1.1 (Analysis of Record for Calibration)",
        chain:     null,
    },
};

// =====================================================================
// Badge display names and CSS class
// =====================================================================

const BADGE_CONFIG = {
    observed:    { text: "Observed",       css: "badge-observed" },
    reanalysis:  { text: "Reanalysis",     css: "badge-reanalysis" },
    modeled:     { text: "Modeled",        css: "badge-modeled" },
    statistical: { text: "Statistical DS", css: "badge-statistical" },
    dynamical:   { text: "Dynamical RCM",  css: "badge-dynamical" },
    hourly:      { text: "Hourly",         css: "badge-hourly" },
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
        const badgesEl = document.getElementById("card-badges");
        const typeEl   = document.getElementById("card-type");
        const spatEl   = document.getElementById("card-resolution");
        const tempEl   = document.getElementById("card-temporal");
        const periodEl = document.getElementById("card-period");
        const varsEl   = document.getElementById("card-variables");
        const sourceEl = document.getElementById("card-source");
        const chainRow = document.getElementById("card-chain-row");
        const chainEl  = document.getElementById("card-chain");

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
    },

    // ------------------------------------------------------------------
    // Build data path from selections and load
    // ------------------------------------------------------------------

    _applySource() {
        let path;

        if (this._mode === "historical") {
            path = "../data/output";
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
            return { mode: "historical", dataset: "aorc" };
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
