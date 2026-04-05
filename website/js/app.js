/**
 * Main application — initializes map, loads point index, wires up UI.
 *
 * Data source is split into two modes:
 *   Historical — AORC reanalysis (1979–present)
 *   Future     — Climate model projections (select Model → GCM → Scenario)
 */

const SCENARIO_OPTIONS = {
    "nex-gddp-cmip6": [
        { value: "ssp245", label: "SSP2-4.5 (Mid-range)" },
        { value: "ssp585", label: "SSP5-8.5 (High emissions)" },
    ],
    "glarm": [
        { value: "rcp45", label: "RCP 4.5" },
        { value: "rcp85", label: "RCP 8.5" },
    ],
    "climrr": [
        { value: "ssp245", label: "SSP2-4.5 (Mid-range)" },
        { value: "ssp585", label: "SSP5-8.5 (High emissions)" },
    ],
};

const MODEL_SUMMARIES = {
    "historical": "NOAA AORC v1.1 &mdash; ~800m hourly reanalysis, 1979&ndash;present",
    "nex-gddp-cmip6": "NASA NEX-GDDP-CMIP6 &mdash; 0.25&deg; daily, 2015&ndash;2100",
    "glarm": "GLARM-Proj1 &mdash; 18km daily, Great Lakes, 1981&ndash;2099",
    "climrr": "Argonne ClimRR &mdash; 12km WRF/CESM2, 2045&ndash;2094",
};

const App = {
    _mode: "historical",   // "historical" or "future"

    async init() {
        const status = document.getElementById("status-text");
        status.textContent = "Initializing map...";

        MapLayer.initMap();
        UIControls.init();
        this._initSourceSelectors();

        await this.loadPoints();
    },

    // ------------------------------------------------------------------
    // Historical / Future toggle + sub-selectors
    // ------------------------------------------------------------------

    _initSourceSelectors() {
        const toggleBtns     = document.querySelectorAll(".mode-btn");
        const futureOpts     = document.getElementById("future-options");
        const modelSelect    = document.getElementById("model-select");
        const gcmGroup       = document.getElementById("gcm-group");
        const scenarioGroup  = document.getElementById("scenario-group");
        const scenarioSelect = document.getElementById("scenario-select");
        const summaryEl      = document.getElementById("source-summary");

        // Toggle buttons: Historical / Future
        toggleBtns.forEach(btn => {
            btn.addEventListener("click", () => {
                toggleBtns.forEach(b => b.classList.remove("active"));
                btn.classList.add("active");
                this._mode = btn.dataset.mode;

                futureOpts.style.display = (this._mode === "future") ? "" : "none";
                this._updateSubSelectors();
                this._applySource();
            });
        });

        // Climate model changed → update GCM/scenario visibility
        modelSelect.addEventListener("change", () => {
            this._updateSubSelectors();
            this._applySource();
        });

        // GCM or scenario changed → update data path
        document.getElementById("gcm-select").addEventListener("change", () => this._applySource());
        scenarioSelect.addEventListener("change", () => this._applySource());

        // Initial state
        this._updateSubSelectors();
    },

    /** Show/hide GCM and scenario dropdowns based on selected model. */
    _updateSubSelectors() {
        const model          = document.getElementById("model-select").value;
        const gcmGroup       = document.getElementById("gcm-group");
        const scenarioSelect = document.getElementById("scenario-select");
        const summaryEl      = document.getElementById("source-summary");

        if (this._mode === "historical") {
            summaryEl.innerHTML = MODEL_SUMMARIES["historical"];
            return;
        }

        // GCM dropdown: only for NEX-GDDP-CMIP6
        gcmGroup.style.display = (model === "nex-gddp-cmip6") ? "" : "none";

        // Populate scenarios for selected model
        const scenarios = SCENARIO_OPTIONS[model] || [];
        const prev = scenarioSelect.value;
        scenarioSelect.innerHTML = "";
        scenarios.forEach(s => {
            const opt = document.createElement("option");
            opt.value = s.value;
            opt.textContent = s.label;
            if (s.value === prev) opt.selected = true;
            scenarioSelect.appendChild(opt);
        });

        summaryEl.innerHTML = MODEL_SUMMARIES[model] || "";
    },

    /** Build the data directory path from current selections and load data. */
    _applySource() {
        let path;

        if (this._mode === "historical") {
            path = "../data/output";
        } else {
            const model    = document.getElementById("model-select").value;
            const gcm      = document.getElementById("gcm-select").value;
            const scenario = document.getElementById("scenario-select").value;

            if (model === "nex-gddp-cmip6") {
                path = `../data/output_nex_${gcm}_${scenario}`;
            } else if (model === "glarm") {
                path = `../data/output_glarm_${scenario}`;
            } else if (model === "climrr") {
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
                const bounds = [
                    [Math.min(...lats), Math.min(...lons)],
                    [Math.max(...lats), Math.max(...lons)],
                ];
                MapLayer.map.fitBounds(bounds, { padding: [20, 20] });
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

document.addEventListener("DOMContentLoaded", () => {
    App.init();
});
