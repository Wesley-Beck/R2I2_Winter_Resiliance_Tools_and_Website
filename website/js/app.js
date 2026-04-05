/**
 * Main application — initializes map, loads point index, wires up UI.
 *
 * Data source is built from three selectors:
 *   Model Family → GCM (if applicable) → Scenario (if applicable)
 * These combine to produce a data directory path that DataLoader uses.
 */

const NEX_SCENARIOS = [
    { value: "ssp245", label: "SSP2-4.5 (Mid-range emissions)" },
    { value: "ssp585", label: "SSP5-8.5 (High emissions)" },
];

const GLARM_SCENARIOS = [
    { value: "rcp45", label: "RCP 4.5" },
    { value: "rcp85", label: "RCP 8.5" },
];

const CLIMRR_SCENARIOS = [
    { value: "ssp245", label: "SSP2-4.5 (Mid-range)" },
    { value: "ssp585", label: "SSP5-8.5 (High emissions)" },
];

const MODEL_INFO = {
    "aorc":          { summary: "NOAA AORC v1.1 &mdash; ~800m hourly reanalysis, 1979&ndash;present" },
    "nex-gddp-cmip6":{ summary: "NASA NEX-GDDP-CMIP6 &mdash; 0.25&deg; daily, 27 GCMs, 2015&ndash;2100" },
    "glarm":         { summary: "GLARM-Proj1 (Michigan Tech) &mdash; 18km daily, Great Lakes, 1981&ndash;2099" },
    "climrr":        { summary: "Argonne ClimRR &mdash; 12km WRF downscaling, CESM2, 2045&ndash;2094" },
};

const App = {
    async init() {
        const status = document.getElementById("status-text");
        status.textContent = "Initializing map...";

        MapLayer.initMap();
        UIControls.init();
        this._initSourceSelectors();

        await this.loadPoints();
    },

    /**
     * Wire up the tiered data source selectors:
     *   Model Family → GCM → Scenario
     */
    _initSourceSelectors() {
        const familySelect   = document.getElementById("model-family-select");
        const gcmGroup       = document.getElementById("gcm-group");
        const scenarioGroup  = document.getElementById("scenario-group");
        const scenarioSelect = document.getElementById("scenario-select");
        const summaryEl      = document.getElementById("source-summary");

        const updateVisibility = () => {
            const family = familySelect.value;

            // GCM dropdown: only for NEX-GDDP-CMIP6
            gcmGroup.style.display = (family === "nex-gddp-cmip6") ? "" : "none";

            // Scenario dropdown: for all projections
            if (family === "aorc") {
                scenarioGroup.style.display = "none";
            } else {
                scenarioGroup.style.display = "";
                // Populate scenario options
                let scenarios = [];
                if (family === "nex-gddp-cmip6") scenarios = NEX_SCENARIOS;
                else if (family === "glarm")       scenarios = GLARM_SCENARIOS;
                else if (family === "climrr")      scenarios = CLIMRR_SCENARIOS;

                const prev = scenarioSelect.value;
                scenarioSelect.innerHTML = "";
                scenarios.forEach(s => {
                    const opt = document.createElement("option");
                    opt.value = s.value;
                    opt.textContent = s.label;
                    // Try to preserve previous selection
                    if (s.value === prev) opt.selected = true;
                    scenarioSelect.appendChild(opt);
                });
            }

            // Summary
            summaryEl.innerHTML = (MODEL_INFO[family] || {}).summary || "";
        };

        const applySource = () => {
            const family   = familySelect.value;
            const gcm      = document.getElementById("gcm-select").value;
            const scenario = scenarioSelect.value;

            let path;
            if (family === "aorc") {
                path = "../data/output";
            } else if (family === "nex-gddp-cmip6") {
                path = `../data/output_nex_${gcm}_${scenario}`;
            } else if (family === "glarm") {
                path = `../data/output_glarm_${scenario}`;
            } else if (family === "climrr") {
                path = `../data/output_climrr_${scenario}`;
            }

            DataLoader.setBasePath(path);
            UIControls._updateProvenance();
            this.loadPoints();
        };

        // Event listeners
        familySelect.addEventListener("change", () => {
            updateVisibility();
            applySource();
        });
        document.getElementById("gcm-select").addEventListener("change", () => applySource());
        scenarioSelect.addEventListener("change", () => applySource());

        // Initial state
        updateVisibility();
    },

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
            status.textContent = "No data loaded — select a data source with computed results";
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
                    <li>Run <code>aorc-tools extract</code> to compute fire indices</li>
                    <li>Select a <strong>Data Source</strong> above</li>
                </ol>
                <p style="margin-top: 8px; color: #a08060;">
                    See USAGE.md for detailed instructions.
                </p>
            </div>
        `;
        document.getElementById("info-panel").style.display = "block";
    },
};

document.addEventListener("DOMContentLoaded", () => {
    App.init();
});
