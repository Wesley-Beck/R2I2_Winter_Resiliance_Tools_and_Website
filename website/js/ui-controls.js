/**
 * UI controls — wires up layer selectors, time navigation, and legend.
 * Supports full AORC timeline (1979-2024) with year/month/day/hour controls.
 *
 * Optimized:
 * - Debounced loading prevents rapid-fire CSV requests
 * - Uses array-indexed data (Float32Array) instead of object lookups
 * - Error recovery resets state cleanly on load failure
 */

const UIControls = {
    currentLayerPath: null,
    currentYear: 2020,
    currentMonth: 7,
    currentDay: 15,
    currentHour: 12,

    _loadDebounceTimer: null,
    _isLoading: false,

    init() {
        // Populate year dropdown (1979-2024)
        const yearSelect = document.getElementById("year-select");
        for (let y = 2024; y >= 1979; y--) {
            const opt = document.createElement("option");
            opt.value = y;
            opt.textContent = y;
            if (y === this.currentYear) opt.selected = true;
            yearSelect.appendChild(opt);
        }

        this._populateDays();

        // Layer selectors — only one group can be active at a time
        const selects = document.querySelectorAll(".layer-select");
        selects.forEach(select => {
            select.addEventListener("change", (e) => {
                const value = e.target.value;
                if (!value) return;
                selects.forEach(s => { if (s !== e.target) s.value = ""; });
                this.currentLayerPath = value;
                this._debouncedLoad();
            });
        });

        // Year selector
        yearSelect.addEventListener("change", (e) => {
            this.currentYear = parseInt(e.target.value);
            this._populateDays();
            this._debouncedLoad();
        });

        // Month selector
        document.getElementById("month-select").addEventListener("change", (e) => {
            this.currentMonth = parseInt(e.target.value);
            this._populateDays();
            this._debouncedLoad();
        });

        // Day selector — no CSV reload needed, just re-display
        document.getElementById("day-select").addEventListener("change", (e) => {
            this.currentDay = parseInt(e.target.value);
            this._updateTimeDisplay();
            this._displayCurrentTimestamp();
        });

        // Hour slider — no CSV reload needed, just re-display
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

        // Wildfire overlay toggle
        document.getElementById("wildfire-toggle").addEventListener("change", (e) => {
            if (e.target.checked) {
                WildfireOverlay.load(this.currentYear);
            } else {
                WildfireOverlay.hide();
            }
        });

        this._updateTimeDisplay();
        this._updateProvenance();
    },

    _populateDays() {
        const daySelect = document.getElementById("day-select");
        const daysInMonth = new Date(this.currentYear, this.currentMonth, 0).getDate();
        const prevDay = this.currentDay;
        daySelect.innerHTML = "";

        for (let d = 1; d <= daysInMonth; d++) {
            const opt = document.createElement("option");
            opt.value = d;
            opt.textContent = d;
            daySelect.appendChild(opt);
        }

        this.currentDay = Math.min(prevDay, daysInMonth);
        daySelect.value = this.currentDay;
        this._updateTimeDisplay();
    },

    getCurrentTimestamp() {
        const y = this.currentYear;
        const m = String(this.currentMonth).padStart(2, "0");
        const d = String(this.currentDay).padStart(2, "0");
        const h = String(this.currentHour).padStart(2, "0");
        return `${y}-${m}-${d} ${h}:00`;
    },

    _updateTimeDisplay() {
        document.getElementById("full-time-display").textContent = this.getCurrentTimestamp();
    },

    /**
     * Debounce CSV loading — waits 150ms after last change before loading.
     * Prevents rapid dropdown changes from triggering multiple CSV downloads.
     */
    _debouncedLoad() {
        if (this._loadDebounceTimer) {
            clearTimeout(this._loadDebounceTimer);
        }
        this._loadDebounceTimer = setTimeout(() => {
            this._loadAndDisplay();
        }, 150);
    },

    async _loadAndDisplay() {
        if (!this.currentLayerPath) return;
        if (this._isLoading) return; // Prevent concurrent loads

        this._isLoading = true;
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
            if (err.message === "Request superseded") {
                // A newer request replaced this one — don't show error
                this._isLoading = false;
                return;
            }
            console.warn("Load error:", err.message);
            status.textContent = `No data for ${this.currentYear}-${String(this.currentMonth).padStart(2, "0")}`;
            MapLayer.currentData = null;
            MapLayer.currentHourIndex = -1;
            MapLayer.resetColors();
        }

        MapLayer.hideLoading();
        this._isLoading = false;

        // Reload wildfire perimeters if toggled on
        if (document.getElementById("wildfire-toggle").checked) {
            WildfireOverlay.load(this.currentYear);
        }
    },

    /**
     * Display data for the current timestamp using array-indexed access.
     * No object allocation — reads directly from Float32Array.
     */
    _displayCurrentTimestamp() {
        if (!MapLayer.currentData || !this.currentLayerPath) return;

        const targetTs = this.getCurrentTimestamp();
        const hourIdx = DataLoader.findClosestTimestampIndex(
            MapLayer.currentData.timestamps, targetTs
        );

        if (hourIdx < 0) {
            MapLayer.resetColors();
            return;
        }

        MapLayer.currentHourIndex = hourIdx;
        const values = DataLoader.getValuesAtHourIndex(MapLayer.currentData, hourIdx);
        if (values) {
            MapLayer.updateColors(this.currentLayerPath, values);
        }
    },

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
