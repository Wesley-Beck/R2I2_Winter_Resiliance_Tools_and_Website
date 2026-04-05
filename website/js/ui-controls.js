/**
 * UI controls — wires up layer selectors, time slider, and legend.
 */

const UIControls = {
    currentLayerPath: null,
    currentYear: 2020,
    currentMonth: 7,
    currentHour: 12,

    /**
     * Initialize all UI event listeners.
     */
    init() {
        // Layer selectors — only one group can be active at a time
        const selects = document.querySelectorAll(".layer-select");
        selects.forEach(select => {
            select.addEventListener("change", (e) => {
                const value = e.target.value;
                if (!value) return;

                // Clear other selects
                selects.forEach(s => {
                    if (s !== e.target) s.value = "";
                });

                this.currentLayerPath = value;
                this._loadAndDisplay();
            });
        });

        // Date picker
        document.getElementById("date-picker").addEventListener("change", (e) => {
            const parts = e.target.value.split("-");
            this.currentYear = parseInt(parts[0]);
            this.currentMonth = parseInt(parts[1]);
            this._loadAndDisplay();
        });

        // Hour slider
        document.getElementById("hour-slider").addEventListener("input", (e) => {
            this.currentHour = parseInt(e.target.value);
            document.getElementById("hour-display").textContent =
                `${String(this.currentHour).padStart(2, "0")}:00`;
            this._updateTimeDisplay();
            this._displayCurrentTimestamp();
        });

        // Load data button
        document.getElementById("load-data-btn").addEventListener("click", () => {
            const path = document.getElementById("data-path").value;
            DataLoader.setBasePath(path);
            App.loadPoints();
        });

        // Set initial time display
        this._updateTimeDisplay();

        // Set initial provenance note
        this._updateProvenance();
    },

    /**
     * Get the current timestamp string.
     */
    getCurrentTimestamp() {
        const y = this.currentYear;
        const m = String(this.currentMonth).padStart(2, "0");
        const d = document.getElementById("date-picker").value.split("-")[2] || "15";
        const h = String(this.currentHour).padStart(2, "0");
        return `${y}-${m}-${d} ${h}:00`;
    },

    /**
     * Update the time display text.
     */
    _updateTimeDisplay() {
        const ts = this.getCurrentTimestamp();
        document.getElementById("full-time-display").textContent = ts;
    },

    /**
     * Load CSV data for current layer/time, then display.
     */
    async _loadAndDisplay() {
        if (!this.currentLayerPath) return;

        const status = document.getElementById("status-text");
        status.textContent = "Loading data...";
        MapLayer.showLoading("Loading CSV data...");

        try {
            const data = await DataLoader.loadMonthlyCSV(
                this.currentYear, this.currentMonth, this.currentLayerPath
            );
            MapLayer.currentData = data;
            MapLayer.currentLayer = this.currentLayerPath;
            this._displayCurrentTimestamp();
            this._updateLegend();
            this._updateProvenance();
            status.textContent = "Ready";
        } catch (err) {
            console.error("Load error:", err);
            status.textContent = `Error: ${err.message}`;
            MapLayer.resetColors();
        }

        MapLayer.hideLoading();
    },

    /**
     * Display data for the current timestamp (no CSV reload).
     */
    _displayCurrentTimestamp() {
        if (!MapLayer.currentData || !this.currentLayerPath) return;

        const targetTs = this.getCurrentTimestamp();
        const ts = DataLoader.findClosestTimestamp(
            MapLayer.currentData.timestamps, targetTs
        );

        if (!ts) {
            MapLayer.resetColors();
            return;
        }

        MapLayer.currentTimestamp = ts;
        const values = DataLoader.getValuesAtTime(MapLayer.currentData, ts);
        MapLayer.updateColors(this.currentLayerPath, values);
    },

    /**
     * Update the color legend for the current variable.
     */
    _updateLegend() {
        const config = VariableConfig[this.currentLayerPath];
        if (!config) return;

        const scale = ColorScales[config.scale];
        document.getElementById("legend-gradient").style.background = scale.gradient;
        document.getElementById("legend-min").textContent = config.min;
        document.getElementById("legend-max").textContent = config.max;
        document.getElementById("legend-title").textContent =
            `${config.label}${config.units ? " (" + config.units + ")" : ""}`;
    },

    /**
     * Update AORC data provenance note based on selected year.
     */
    _updateProvenance() {
        const y = this.currentYear;
        let note = "";

        if (y < 1995) {
            note = "Precip: NEXRAD Stage II + NOWrad + CMORPH satellite. Non-precip: GDAS/MERRA2 reanalysis.";
        } else if (y < 2002) {
            note = "Precip: NEXRAD Stage II hourly. Non-precip: GDAS/MERRA2 reanalysis.";
        } else if (y < 2016) {
            note = "Precip: Stage IV gauge-calibrated NEXRAD. Non-precip: GDAS/MERRA2 reanalysis.";
        } else if (y < 2018) {
            note = "Precip: Stage IV. Non-precip: NLDAS-2 to URMA transition blend.";
        } else {
            note = "Precip: Stage IV gauge-calibrated NEXRAD. Non-precip: URMA reanalysis (2.5 km).";
        }

        document.getElementById("provenance-note").textContent = note;
    },
};
