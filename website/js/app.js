/**
 * Main application — initializes map, loads point index, wires up UI.
 *
 * Data source split into Historical (observed) and Future (modeled):
 *
 *   Historical:  AORC reanalysis — no sub-options
 *   Future:      GCM → Downscaling Method → Emissions Scenario
 *
 * The downscaling dropdown adapts to the selected GCM:
 *   - CMIP6 GCMs  → BCSD statistical (NEX-GDDP-CMIP6)
 *   - CESM2       → WRF dynamical (ClimRR / Argonne)
 *   - RegCM4      → RegCM4 dynamical (GLARM / Michigan Tech)
 *
 * This makes the GCM→RCM chain explicit and switchable.
 */

// =====================================================================
// Downscaling methods available per GCM
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

/**
 * Each downscaling method defines: label, key (for path building),
 * scenarios, and the info card fields.
 */
const DOWNSCALING_METHODS = {
    "bcsd": {
        label: "BCSD Statistical (NEX-GDDP-CMIP6)",
        key: "nex-gddp-cmip6",
        scenarios: [
            { value: "ssp245", label: "SSP2-4.5 (mid-range emissions)" },
            { value: "ssp585", label: "SSP5-8.5 (high emissions)" },
        ],
        badge: "statistical",
        badgeText: "Statistically Downscaled",
        type: "Statistical downscaling (BCSD)",
        resolution: "0.25° (~25 km), daily",
        period: "2015 – 2100",
        source: "NASA NEX-GDDP-CMIP6",
    },
    "wrf": {
        label: "WRF Dynamical (ClimRR / Argonne)",
        key: "climrr",
        scenarios: [
            { value: "ssp245", label: "SSP2-4.5 (mid-range emissions)" },
            { value: "ssp585", label: "SSP5-8.5 (high emissions)" },
        ],
        badge: "dynamical",
        badgeText: "Dynamically Downscaled (RCM)",
        type: "Regional climate model (WRF)",
        resolution: "12 km, daily",
        period: "2045 – 2094",
        source: "Argonne ClimRR",
    },
    "regcm4": {
        label: "RegCM4 Dynamical (GLARM / Michigan Tech)",
        key: "glarm",
        scenarios: [
            { value: "rcp45", label: "RCP 4.5" },
            { value: "rcp85", label: "RCP 8.5" },
        ],
        badge: "dynamical",
        badgeText: "Dynamically Downscaled (RCM)",
        type: "Regional climate model (RegCM4)",
        resolution: "18 km, daily",
        period: "1981 – 2099",
        source: "GLARM-Proj1 (Michigan Tech)",
    },
};

/** Map each GCM to available downscaling methods. */
function getDownscalingForGCM(gcm) {
    if (CMIP6_GCMS.includes(gcm)) return ["bcsd"];
    if (gcm === "CESM2")           return ["wrf"];
    if (gcm === "RegCM4-driven")   return ["regcm4"];
    return ["bcsd"];
}

// =====================================================================
// Historical data info
// =====================================================================

const HISTORICAL_INFO = {
    badge: "observed",
    badgeText: "Observed + Modeled",
    type: "Reanalysis",
    resolution: "~800m (~0.009°), hourly",
    period: "1979 – present",
    source: "NOAA AORC v1.1",
    chain: null,
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
        await this.loadPoints();
    },

    // ------------------------------------------------------------------
    // Source selector wiring
    // ------------------------------------------------------------------

    _initSourceSelectors() {
        // Mode toggle buttons
        document.querySelectorAll(".mode-btn").forEach(btn => {
            btn.addEventListener("click", () => {
                document.querySelectorAll(".mode-btn").forEach(b => b.classList.remove("active"));
                btn.classList.add("active");
                this._mode = btn.dataset.mode;
                document.getElementById("future-options").style.display =
                    (this._mode === "future") ? "" : "none";
                this._updateDownscalingOptions();
                this._updateInfoCard();
                this._applySource();
            });
        });

        // GCM changed → update available downscaling methods
        document.getElementById("gcm-select").addEventListener("change", () => {
            this._updateDownscalingOptions();
            this._updateInfoCard();
            this._applySource();
        });

        // Downscaling changed → update scenarios + info
        document.getElementById("downscaling-select").addEventListener("change", () => {
            this._updateScenarioOptions();
            this._updateInfoCard();
            this._applySource();
        });

        // Scenario changed → reload data
        document.getElementById("scenario-select").addEventListener("change", () => {
            this._updateInfoCard();
            this._applySource();
        });

        // Initial population
        this._updateDownscalingOptions();
        this._updateInfoCard();
    },

    /** Populate downscaling dropdown based on selected GCM. */
    _updateDownscalingOptions() {
        const gcm = document.getElementById("gcm-select").value;
        const dsSelect = document.getElementById("downscaling-select");
        const methods = getDownscalingForGCM(gcm);
        const prev = dsSelect.value;

        dsSelect.innerHTML = "";
        methods.forEach(key => {
            const m = DOWNSCALING_METHODS[key];
            if (!m) return;
            const opt = document.createElement("option");
            opt.value = key;
            opt.textContent = m.label;
            if (key === prev) opt.selected = true;
            dsSelect.appendChild(opt);
        });

        this._updateScenarioOptions();
    },

    /** Populate scenario dropdown based on selected downscaling method. */
    _updateScenarioOptions() {
        const dsKey = document.getElementById("downscaling-select").value;
        const method = DOWNSCALING_METHODS[dsKey];
        const scenSelect = document.getElementById("scenario-select");
        const prev = scenSelect.value;

        scenSelect.innerHTML = "";
        if (method) {
            method.scenarios.forEach(s => {
                const opt = document.createElement("option");
                opt.value = s.value;
                opt.textContent = s.label;
                if (s.value === prev) opt.selected = true;
                scenSelect.appendChild(opt);
            });
        }
    },

    /** Update the info card to reflect current data characteristics. */
    _updateInfoCard() {
        const badgeEl   = document.querySelector(".source-badge");
        const typeEl    = document.getElementById("card-type");
        const resEl     = document.getElementById("card-resolution");
        const periodEl  = document.getElementById("card-period");
        const sourceEl  = document.getElementById("card-source");
        const chainRow  = document.getElementById("card-chain-row");
        const chainEl   = document.getElementById("card-chain");

        if (this._mode === "historical") {
            badgeEl.className = "source-badge badge-observed";
            badgeEl.textContent = HISTORICAL_INFO.badgeText;
            typeEl.textContent = HISTORICAL_INFO.type;
            resEl.textContent = HISTORICAL_INFO.resolution;
            periodEl.innerHTML = HISTORICAL_INFO.period;
            sourceEl.textContent = HISTORICAL_INFO.source;
            chainRow.style.display = "none";
            return;
        }

        const gcm    = document.getElementById("gcm-select").value;
        const dsKey  = document.getElementById("downscaling-select").value;
        const method = DOWNSCALING_METHODS[dsKey];
        if (!method) return;

        badgeEl.className = `source-badge badge-${method.badge}`;
        badgeEl.textContent = method.badgeText;
        typeEl.textContent = method.type;
        resEl.textContent = method.resolution;
        periodEl.textContent = method.period;
        sourceEl.textContent = method.source;

        // Show the modeling chain: GCM → downscaling → local grid
        chainRow.style.display = "";
        if (dsKey === "bcsd") {
            chainEl.textContent = `${gcm} → BCSD → 0.25° grid`;
        } else if (dsKey === "wrf") {
            chainEl.textContent = `${gcm} → WRF → 12 km grid`;
        } else if (dsKey === "regcm4") {
            chainEl.textContent = `GCM ensemble → RegCM4 → 18 km grid`;
        }
    },

    /** Build the data path from selections and reload. */
    _applySource() {
        let path;

        if (this._mode === "historical") {
            path = "../data/output";
        } else {
            const gcm      = document.getElementById("gcm-select").value;
            const dsKey    = document.getElementById("downscaling-select").value;
            const scenario = document.getElementById("scenario-select").value;
            const method   = DOWNSCALING_METHODS[dsKey];
            if (!method) return;

            if (method.key === "nex-gddp-cmip6") {
                path = `../data/output_nex_${gcm}_${scenario}`;
            } else if (method.key === "glarm") {
                path = `../data/output_glarm_${scenario}`;
            } else if (method.key === "climrr") {
                path = `../data/output_climrr_${scenario}`;
            }
        }

        DataLoader.setBasePath(path);
        UIControls._updateProvenance();
        this.loadPoints();
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
