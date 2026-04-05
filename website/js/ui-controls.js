/**
 * UI controls — calendar date-range picker with hourly playback.
 *
 * Year → Month → Mini calendar (click start day, click end day) → Hour slider
 * Play button animates through all hours in the selected date range.
 */

const UIControls = {
    currentLayerPath: null,
    currentYear: 2020,
    currentMonth: 7,
    currentHour: 12,

    // Date range selection
    rangeStart: 15,   // start day
    rangeEnd: 15,     // end day
    currentDay: 15,   // day being displayed
    _selectingEnd: false,

    // Playback state
    _playing: false,
    _playTimer: null,
    _playFrames: [],   // list of {day, hour} for the playback range
    _playIndex: 0,

    _loadDebounceTimer: null,
    _isLoading: false,
    _fireDates: new Set(),  // days in current month with fire discoveries

    /**
     * Format an hour (0-23) as AM/PM string.
     */
    _formatHourAmPm(hour) {
        if (hour === 0) return "12:00 AM";
        if (hour < 12) return `${hour}:00 AM`;
        if (hour === 12) return "12:00 PM";
        return `${hour - 12}:00 PM`;
    },

    init() {
        // Populate year dropdown
        const yearSelect = document.getElementById("year-select");
        for (let y = 2100; y >= 1979; y--) {
            const opt = document.createElement("option");
            opt.value = y;
            opt.textContent = y;
            if (y === this.currentYear) opt.selected = true;
            yearSelect.appendChild(opt);
        }

        // Build calendar
        this._buildCalendar();

        // Layer selectors
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

        // Year change
        yearSelect.addEventListener("change", (e) => {
            this.currentYear = parseInt(e.target.value);
            this._buildCalendar();
            this._debouncedLoad();
        });

        // Month change
        document.getElementById("month-select").addEventListener("change", (e) => {
            this.currentMonth = parseInt(e.target.value);
            this._buildCalendar();
            this._debouncedLoad();
        });

        // Hour slider
        document.getElementById("hour-slider").addEventListener("input", (e) => {
            this.currentHour = parseInt(e.target.value);
            document.getElementById("hour-display").textContent =
                this._formatHourAmPm(this.currentHour);
            this._updateTimeDisplay();
            this._displayCurrentTimestamp();
            this._syncPlaybackSlider();
        });

        // Playback button
        document.getElementById("play-btn").addEventListener("click", () => {
            this._togglePlayback();
        });

        // Playback slider (scrub through range)
        document.getElementById("playback-slider").addEventListener("input", (e) => {
            this._playIndex = parseInt(e.target.value);
            this._showPlaybackFrame();
        });

        // Speed selector
        // (speed is read dynamically during playback)

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
        this._updateRangeDisplay();
        this._buildPlaybackFrames();
    },

    // ------------------------------------------------------------------
    // Mini Calendar
    // ------------------------------------------------------------------

    _buildCalendar() {
        const container = document.getElementById("cal-days");
        container.innerHTML = "";

        const daysInMonth = new Date(this.currentYear, this.currentMonth, 0).getDate();
        const firstDow = new Date(this.currentYear, this.currentMonth - 1, 1).getDay();

        // Clamp range to valid days
        this.rangeStart = Math.min(this.rangeStart, daysInMonth);
        this.rangeEnd = Math.min(this.rangeEnd, daysInMonth);
        this.currentDay = Math.min(this.currentDay, daysInMonth);

        // Empty cells for offset
        for (let i = 0; i < firstDow; i++) {
            const empty = document.createElement("div");
            empty.className = "cal-day empty";
            container.appendChild(empty);
        }

        // Day cells
        for (let d = 1; d <= daysInMonth; d++) {
            const cell = document.createElement("div");
            cell.className = "cal-day";
            cell.textContent = d;

            if (d === this.rangeStart) cell.classList.add("selected-start");
            if (d === this.rangeEnd) cell.classList.add("selected-end");
            if (d > this.rangeStart && d < this.rangeEnd) cell.classList.add("in-range");
            if (d === this.currentDay) cell.classList.add("current");
            if (this._fireDates.has(d)) cell.classList.add("fire-day");

            cell.addEventListener("click", () => this._onDayClick(d));
            container.appendChild(cell);
        }
    },

    _onDayClick(day) {
        if (!this._selectingEnd) {
            // First click: set start day
            this.rangeStart = day;
            this.rangeEnd = day;
            this.currentDay = day;
            this._selectingEnd = true;
        } else {
            // Second click: set end day
            if (day < this.rangeStart) {
                this.rangeEnd = this.rangeStart;
                this.rangeStart = day;
            } else {
                this.rangeEnd = day;
            }
            this.currentDay = this.rangeStart;
            this._selectingEnd = false;
        }

        this._buildCalendar();
        this._updateTimeDisplay();
        this._updateRangeDisplay();
        this._buildPlaybackFrames();
        this._displayCurrentTimestamp();
    },

    _updateRangeDisplay() {
        const el = document.getElementById("range-display");
        const y = this.currentYear;
        const m = String(this.currentMonth).padStart(2, "0");

        if (this.rangeStart === this.rangeEnd) {
            el.textContent = `${y}-${m}-${String(this.rangeStart).padStart(2, "0")}`;
        } else {
            el.textContent = `${y}-${m}-${String(this.rangeStart).padStart(2, "0")} → ${y}-${m}-${String(this.rangeEnd).padStart(2, "0")}`;
        }

        if (this._selectingEnd) {
            el.textContent += "  (click end day)";
        }
    },

    // ------------------------------------------------------------------
    // Playback
    // ------------------------------------------------------------------

    _buildPlaybackFrames() {
        this._playFrames = [];
        for (let d = this.rangeStart; d <= this.rangeEnd; d++) {
            for (let h = 0; h < 24; h++) {
                this._playFrames.push({ day: d, hour: h });
            }
        }

        const slider = document.getElementById("playback-slider");
        slider.max = Math.max(0, this._playFrames.length - 1);

        // Set slider to current position
        this._syncPlaybackSlider();
    },

    _syncPlaybackSlider() {
        const idx = this._playFrames.findIndex(
            f => f.day === this.currentDay && f.hour === this.currentHour
        );
        if (idx >= 0) {
            this._playIndex = idx;
            document.getElementById("playback-slider").value = idx;
        }
    },

    _togglePlayback() {
        if (this._playing) {
            this._stopPlayback();
        } else {
            this._startPlayback();
        }
    },

    _startPlayback() {
        if (this._playFrames.length === 0) return;

        this._playing = true;
        document.getElementById("play-btn").textContent = "⏸";
        document.getElementById("play-btn").classList.add("playing");

        const tick = () => {
            if (!this._playing) return;

            this._playIndex++;
            if (this._playIndex >= this._playFrames.length) {
                if (true) {  // Always continue across months
                    // Advance to next month
                    this._advanceMonth();
                    return; // _advanceMonth will resume playback after data loads
                }
                this._playIndex = 0; // Loop within current range
            }

            this._showPlaybackFrame();

            const speed = parseInt(document.getElementById("speed-select").value);
            this._playTimer = setTimeout(tick, speed);
        };

        // Start immediately
        const speed = parseInt(document.getElementById("speed-select").value);
        this._playTimer = setTimeout(tick, speed);
    },

    _stopPlayback() {
        this._playing = false;
        if (this._playTimer) {
            clearTimeout(this._playTimer);
            this._playTimer = null;
        }
        document.getElementById("play-btn").textContent = "▶";
        document.getElementById("play-btn").classList.remove("playing");
    },

    _showPlaybackFrame() {
        const frame = this._playFrames[this._playIndex];
        if (!frame) return;

        this.currentDay = frame.day;
        this.currentHour = frame.hour;

        document.getElementById("playback-slider").value = this._playIndex;
        document.getElementById("hour-slider").value = this.currentHour;
        document.getElementById("hour-display").textContent =
            this._formatHourAmPm(this.currentHour);

        // Update calendar highlight
        document.querySelectorAll(".cal-day.current").forEach(el => el.classList.remove("current"));
        const dayIdx = this.currentDay - 1 + new Date(this.currentYear, this.currentMonth - 1, 1).getDay();
        const cells = document.querySelectorAll("#cal-days .cal-day");
        if (cells[dayIdx]) cells[dayIdx].classList.add("current");

        this._updateTimeDisplay();
        this._displayCurrentTimestamp();
    },

    /**
     * Advance to the next month during continuous playback.
     * Pauses playback, loads the next month's data, then resumes.
     */
    async _advanceMonth() {
        this._stopPlayback();

        let nextMonth = this.currentMonth + 1;
        let nextYear = this.currentYear;
        if (nextMonth > 12) {
            nextMonth = 1;
            nextYear++;
        }

        this.currentYear = nextYear;
        this.currentMonth = nextMonth;
        this.currentDay = 1;
        this.currentHour = 0;
        this.rangeStart = 1;
        const daysInMonth = new Date(nextYear, nextMonth, 0).getDate();
        this.rangeEnd = daysInMonth;

        // Update UI selects
        document.getElementById("year-select").value = nextYear;
        document.getElementById("month-select").value = nextMonth;

        this._buildCalendar();
        this._updateRangeDisplay();
        this._buildPlaybackFrames();
        this._playIndex = 0;

        // Load data for new month, then resume
        await this._loadAndDisplay();
        if (true) {  // Always continue across months
            this._startPlayback();
        }
    },

    /**
     * Set fire discovery dates for calendar markers.
     * Called by WildfireOverlay after loading fire data.
     * @param {Set<number>} daySet - set of day-of-month numbers with fires
     */
    setFireDates(daySet) {
        this._fireDates = daySet || new Set();
        this._buildCalendar();
    },

    // ------------------------------------------------------------------
    // Timestamp & Data Display
    // ------------------------------------------------------------------

    getCurrentTimestamp() {
        const y = this.currentYear;
        const m = String(this.currentMonth).padStart(2, "0");
        const d = String(this.currentDay).padStart(2, "0");
        const h = String(this.currentHour).padStart(2, "0");
        return `${y}-${m}-${d} ${h}:00`;
    },

    _updateTimeDisplay() {
        const y = this.currentYear;
        const m = String(this.currentMonth).padStart(2, "0");
        const d = String(this.currentDay).padStart(2, "0");
        document.getElementById("full-time-display").textContent =
            `${y}-${m}-${d} ${this._formatHourAmPm(this.currentHour)}`;
    },

    _debouncedLoad() {
        if (this._loadDebounceTimer) clearTimeout(this._loadDebounceTimer);
        this._loadDebounceTimer = setTimeout(() => this._loadAndDisplay(), 150);
    },

    async _loadAndDisplay() {
        if (!this.currentLayerPath) return;
        if (this._isLoading) return;

        this._isLoading = true;
        const status = document.getElementById("status-text");
        status.textContent = "Loading data...";
        MapLayer.showLoading("Loading data...");

        try {
            const data = await DataLoader.loadMonthlyData(
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

        if (document.getElementById("wildfire-toggle").checked) {
            WildfireOverlay.load(this.currentYear);
        }
    },

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
        const src = (typeof App !== "undefined" && App.getSourceInfo) ? App.getSourceInfo() : { mode: "historical" };
        let note = "";

        if (src.mode === "future") {
            const ds = src.downscaling || "bcsd";
            const scen = src.scenario || "";
            const gcm = src.gcm || "";

            if (ds === "regcm4") {
                const rcp = scen === "rcp45" ? "RCP 4.5" : "RCP 8.5";
                note = `Modeled: GCM ensemble → RegCM4 dynamical RCM (18 km). ${rcp}. Source: GLARM-Proj1.`;
            } else if (ds === "wrf") {
                const ssp = scen === "ssp245" ? "SSP2-4.5" : "SSP5-8.5";
                note = `Modeled: ${gcm} → WRF dynamical RCM (12 km). ${ssp}. Source: Argonne ClimRR.`;
            } else {
                const ssp = scen === "ssp245" ? "SSP2-4.5" : "SSP5-8.5";
                note = `Modeled: ${gcm} → BCSD statistical (0.25°). ${ssp}. Source: NASA NEX-GDDP-CMIP6.`;
            }
        } else {
            // Historical AORC — provenance varies by data era
            if (y < 1995) note = "Observed + reanalysis: Stage II + CMORPH satellite precip. GDAS/MERRA2 non-precip fields.";
            else if (y < 2002) note = "Observed + reanalysis: NEXRAD Stage II hourly precip. GDAS/MERRA2 non-precip fields.";
            else if (y < 2016) note = "Observed + reanalysis: Stage IV gauge-calibrated NEXRAD precip. GDAS/MERRA2 non-precip.";
            else if (y < 2018) note = "Observed + reanalysis: Stage IV precip. NLDAS-2 to URMA transition blend.";
            else note = "Observed + reanalysis: Stage IV gauge-calibrated NEXRAD precip. URMA reanalysis (2.5 km).";
        }
        document.getElementById("provenance-note").textContent = note;
    },
};
