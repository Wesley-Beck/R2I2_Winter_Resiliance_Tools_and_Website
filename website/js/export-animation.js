/**
 * Export & Animation module — captures map frames and exports as:
 *   - Individual PNG images (ZIP download)
 *   - Animated GIF
 *   - WebM video
 *
 * Works by rendering the Leaflet map + data layer + overlays onto an
 * offscreen canvas for each frame in the selected date range, then
 * encoding the result into the chosen format.
 *
 * Uses:
 *   - html-to-image (via canvas snapshot of the map container)
 *   - GIF.js for animated GIF encoding
 *   - MediaRecorder API for WebM video
 *   - JSZip for multi-frame PNG download
 */

const ExportAnimation = {
    _exporting: false,
    _cancelled: false,
    _totalFrames: 0,
    _currentFrame: 0,

    // Offscreen canvas for rendering
    _canvas: null,
    _ctx: null,

    /**
     * Initialize the export panel event listeners.
     */
    init() {
        document.getElementById("export-btn").addEventListener("click", () => {
            this.startExport();
        });
        document.getElementById("export-cancel-btn").addEventListener("click", () => {
            this._cancelled = true;
        });

        // Wire format selector to show/hide relevant options
        const fmt = document.getElementById("export-format");
        if (fmt) {
            fmt.addEventListener("change", () => this._updateFormatOptions());
        }

        // Default: use current layer's date range
        this._syncFromUI();
    },

    /**
     * Sync export settings from the main UI controls.
     */
    _syncFromUI() {
        const el = document.getElementById("export-start-date");
        if (el) {
            const y = UIControls.currentYear;
            const m = String(UIControls.currentMonth).padStart(2, "0");
            const ds = String(UIControls.rangeStart).padStart(2, "0");
            const de = String(UIControls.rangeEnd).padStart(2, "0");
            document.getElementById("export-start-date").value = `${y}-${m}-${ds}`;
            document.getElementById("export-end-date").value = `${y}-${m}-${de}`;
        }
    },

    _updateFormatOptions() {
        const fmt = document.getElementById("export-format").value;
        const gifOpts = document.getElementById("gif-options");
        const vidOpts = document.getElementById("video-options");
        if (gifOpts) gifOpts.style.display = (fmt === "gif") ? "" : "none";
        if (vidOpts) vidOpts.style.display = (fmt === "video") ? "" : "none";
    },

    /**
     * Main export entry point.
     */
    async startExport() {
        if (this._exporting) return;
        this._exporting = true;
        this._cancelled = false;

        const progressBar = document.getElementById("export-progress");
        const progressText = document.getElementById("export-progress-text");
        const exportBtn = document.getElementById("export-btn");
        const cancelBtn = document.getElementById("export-cancel-btn");

        exportBtn.disabled = true;
        cancelBtn.style.display = "inline-block";
        progressBar.style.display = "block";

        try {
            const format = document.getElementById("export-format").value;
            const startDate = document.getElementById("export-start-date").value;
            const endDate = document.getElementById("export-end-date").value;
            const hourStep = parseInt(document.getElementById("export-hour-step").value) || 1;
            const includeWildfires = document.getElementById("export-wildfires").checked;
            const includeOverlay = document.getElementById("export-overlay").checked;
            const fireProgression = document.getElementById("export-fire-progression").checked;

            // Parse date range
            const frames = this._buildFrameList(startDate, endDate, hourStep);
            this._totalFrames = frames.length;
            this._currentFrame = 0;

            if (frames.length === 0) {
                progressText.textContent = "No frames in range";
                return;
            }

            progressText.textContent = `Preparing ${frames.length} frames...`;

            // Ensure wildfire overlay is loaded if requested
            if (includeWildfires && !document.getElementById("wildfire-toggle").checked) {
                document.getElementById("wildfire-toggle").checked = true;
                await WildfireOverlay.load(UIControls.currentYear);
            }

            // Load fire progression data if requested
            this._progressionFires = null;
            if (fireProgression) {
                progressText.textContent = "Loading wildfire progression data...";
                this._progressionFires = await this.loadFireProgression(startDate, endDate);
                progressText.textContent = `Found ${this._progressionFires.length} fires for progression`;
            }

            // Capture all frames
            const capturedFrames = [];
            for (let i = 0; i < frames.length; i++) {
                if (this._cancelled) {
                    progressText.textContent = "Export cancelled";
                    break;
                }

                this._currentFrame = i;
                const pct = ((i + 1) / frames.length * 100).toFixed(0);
                progressText.textContent = `Capturing frame ${i + 1}/${frames.length} (${pct}%)`;
                progressBar.value = pct;

                // Set the map to this frame's state
                await this._setFrame(frames[i]);

                // Brief pause for render
                await this._sleep(80);

                // Capture the map
                const blob = await this._captureMapCanvas(includeOverlay);
                capturedFrames.push({
                    blob,
                    timestamp: frames[i].label,
                    index: i,
                });
            }

            if (this._cancelled) {
                this._exporting = false;
                cancelBtn.style.display = "none";
                exportBtn.disabled = false;
                return;
            }

            // Encode to chosen format
            progressText.textContent = `Encoding ${format}...`;

            if (format === "png-zip") {
                await this._exportPngZip(capturedFrames, progressText);
            } else if (format === "gif") {
                await this._exportGif(capturedFrames, progressText);
            } else if (format === "video") {
                await this._exportVideo(capturedFrames, progressText);
            } else if (format === "png-single") {
                await this._exportSinglePng(progressText);
            }

        } catch (err) {
            console.error("Export error:", err);
            progressText.textContent = `Export failed: ${err.message}`;
        } finally {
            this._exporting = false;
            this._clearProgressionLayers();
            this._progressionFires = null;
            cancelBtn.style.display = "none";
            exportBtn.disabled = false;
            progressBar.style.display = "block";
        }
    },

    // ------------------------------------------------------------------
    // Frame building
    // ------------------------------------------------------------------

    /**
     * Build list of {year, month, day, hour, label} for the export range.
     */
    _buildFrameList(startStr, endStr, hourStep) {
        const frames = [];
        const start = new Date(startStr + "T00:00:00");
        const end = new Date(endStr + "T23:59:59");

        if (isNaN(start) || isNaN(end) || start > end) return frames;

        const cursor = new Date(start);
        while (cursor <= end) {
            const y = cursor.getFullYear();
            const m = cursor.getMonth() + 1;
            const d = cursor.getDate();

            for (let h = 0; h < 24; h += hourStep) {
                frames.push({
                    year: y,
                    month: m,
                    day: d,
                    hour: h,
                    label: `${y}-${String(m).padStart(2, "0")}-${String(d).padStart(2, "0")} ${String(h).padStart(2, "0")}:00`,
                });
            }

            cursor.setDate(cursor.getDate() + 1);
        }

        return frames;
    },

    /**
     * Set the viewer to display a specific frame.
     */
    async _setFrame(frame) {
        const needsLoad = (
            frame.year !== UIControls.currentYear ||
            frame.month !== UIControls.currentMonth ||
            !MapLayer.currentData
        );

        if (needsLoad) {
            UIControls.currentYear = frame.year;
            UIControls.currentMonth = frame.month;
            document.getElementById("year-select").value = frame.year;
            document.getElementById("month-select").value = frame.month;

            // Load data for this month
            const layerPath = UIControls.currentLayerPath;
            if (layerPath) {
                try {
                    const data = await DataLoader.loadMonthlyData(
                        frame.year, frame.month, layerPath
                    );
                    MapLayer.currentData = data;
                    MapLayer.currentLayer = layerPath;
                } catch (e) {
                    console.warn("Failed to load data for frame:", frame.label, e);
                    return;
                }
            }
        }

        UIControls.currentDay = frame.day;
        UIControls.currentHour = frame.hour;

        // Update hour slider
        document.getElementById("hour-slider").value = frame.hour;
        document.getElementById("hour-display").textContent =
            UIControls._formatHourAmPm(frame.hour);

        UIControls._updateTimeDisplay();

        // Display the frame's data on the map
        const targetTs = UIControls.getCurrentTimestamp();
        const hourIdx = DataLoader.findClosestTimestampIndex(
            MapLayer.currentData.timestamps, targetTs
        );
        if (hourIdx >= 0) {
            MapLayer.currentHourIndex = hourIdx;
            const values = DataLoader.getValuesAtHourIndex(MapLayer.currentData, hourIdx);
            if (values) {
                MapLayer.updateColors(UIControls.currentLayerPath, values);
            }
        }

        // Progressive fire overlay: show fires discovered up to this timestamp
        if (this._progressionFires && this._progressionFires.length > 0) {
            await this.showFiresUpTo(frame.label, this._progressionFires);
        }
    },

    // ------------------------------------------------------------------
    // Map capture
    // ------------------------------------------------------------------

    /**
     * Capture the current map view as a PNG Blob.
     *
     * Uses leaflet-image-like approach: renders the Leaflet container
     * (canvas renderer + tiles) to an offscreen canvas.
     */
    async _captureMapCanvas(includeOverlay) {
        const mapContainer = document.getElementById("map");
        const rect = mapContainer.getBoundingClientRect();
        const width = rect.width;
        const height = rect.height;
        const dpr = window.devicePixelRatio || 1;

        // Create or resize offscreen canvas
        if (!this._canvas || this._canvas.width !== width * dpr) {
            this._canvas = document.createElement("canvas");
            this._canvas.width = width * dpr;
            this._canvas.height = height * dpr;
            this._ctx = this._canvas.getContext("2d");
        }

        const ctx = this._ctx;
        const canvas = this._canvas;
        ctx.scale(dpr, dpr);

        // Clear
        ctx.clearRect(0, 0, width, height);

        // 1. Draw basemap tiles
        const tilePane = mapContainer.querySelector(".leaflet-tile-pane");
        if (tilePane) {
            const tiles = tilePane.querySelectorAll("img.leaflet-tile");
            for (const tile of tiles) {
                try {
                    const tileRect = tile.getBoundingClientRect();
                    const x = tileRect.left - rect.left;
                    const y = tileRect.top - rect.top;
                    ctx.drawImage(tile, x, y, tileRect.width, tileRect.height);
                } catch (e) {
                    // CORS tile — skip
                }
            }
        }

        // 2. Draw Leaflet canvas renderer (data points)
        const canvasPane = mapContainer.querySelector(".leaflet-canvas-icon-overlay, canvas.leaflet-zoom-animated");
        // Try finding the Leaflet renderer canvas
        const allCanvases = mapContainer.querySelectorAll("canvas");
        for (const c of allCanvases) {
            try {
                const cr = c.getBoundingClientRect();
                const x = cr.left - rect.left;
                const y = cr.top - rect.top;
                ctx.drawImage(c, x, y, cr.width, cr.height);
            } catch (e) {
                // tainted canvas
            }
        }

        // 3. Draw SVG overlays (fire perimeters, if any)
        if (includeOverlay) {
            const svgPanes = mapContainer.querySelectorAll(".leaflet-overlay-pane svg");
            for (const svg of svgPanes) {
                try {
                    const svgData = new XMLSerializer().serializeToString(svg);
                    const svgBlob = new Blob([svgData], { type: "image/svg+xml;charset=utf-8" });
                    const url = URL.createObjectURL(svgBlob);
                    const img = await this._loadImage(url);
                    const sr = svg.getBoundingClientRect();
                    ctx.drawImage(img, sr.left - rect.left, sr.top - rect.top, sr.width, sr.height);
                    URL.revokeObjectURL(url);
                } catch (e) {
                    // SVG render failed
                }
            }
        }

        // 4. Draw timestamp + legend overlay
        this._drawOverlayText(ctx, width, height);

        // Reset scale for next capture
        ctx.setTransform(1, 0, 0, 1, 0, 0);

        // Convert to blob
        return new Promise(resolve => {
            canvas.toBlob(blob => resolve(blob), "image/png");
        });
    },

    /**
     * Draw timestamp, variable name, and legend onto the capture canvas.
     */
    _drawOverlayText(ctx, width, height) {
        const config = VariableConfig[UIControls.currentLayerPath];
        const label = config ? config.label : UIControls.currentLayerPath;
        const units = config ? config.units : "";
        const timestamp = UIControls.getCurrentTimestamp();

        // Semi-transparent background box (top-left)
        const text = `${label}${units ? " (" + units + ")" : ""}  |  ${timestamp}`;
        ctx.font = "bold 14px monospace";
        const metrics = ctx.measureText(text);
        const pad = 8;
        const boxW = metrics.width + pad * 2;
        const boxH = 24;

        ctx.fillStyle = "rgba(0,0,0,0.7)";
        ctx.fillRect(0, 0, boxW, boxH);
        ctx.fillStyle = "#e8d5c4";
        ctx.fillText(text, pad, 17);

        // Mini legend bar (bottom-right)
        if (config) {
            const barW = 180;
            const barH = 14;
            const barX = width - barW - 12;
            const barY = height - barH - 30;

            // Background
            ctx.fillStyle = "rgba(0,0,0,0.7)";
            ctx.fillRect(barX - 4, barY - 4, barW + 8, barH + 26);

            // Gradient bar
            const scale = ColorScales[config.scale];
            if (scale && scale.stops) {
                for (let px = 0; px < barW; px++) {
                    const t = px / barW;
                    const rgb = this._interpolateStops(scale.stops, t);
                    ctx.fillStyle = `rgb(${rgb[0]},${rgb[1]},${rgb[2]})`;
                    ctx.fillRect(barX + px, barY, 1, barH);
                }
            }

            // Min/max labels
            ctx.font = "10px monospace";
            ctx.fillStyle = "#e8d5c4";
            ctx.fillText(String(config.min), barX, barY + barH + 12);
            const maxText = String(config.max);
            const maxW = ctx.measureText(maxText).width;
            ctx.fillText(maxText, barX + barW - maxW, barY + barH + 12);

            // Center label
            const legendLabel = label;
            const lblW = ctx.measureText(legendLabel).width;
            ctx.fillText(legendLabel, barX + (barW - lblW) / 2, barY + barH + 12);
        }
    },

    /**
     * Interpolate color from scale stops at position t (0-1).
     */
    _interpolateStops(stops, t) {
        t = Math.max(0, Math.min(1, t));
        let i = 0;
        while (i < stops.length - 1 && stops[i + 1][0] < t) i++;
        if (i >= stops.length - 1) return stops[stops.length - 1][1];

        const [t0, c0] = stops[i];
        const [t1, c1] = stops[i + 1];
        const f = (t - t0) / (t1 - t0 || 1);

        return [
            Math.round(c0[0] + (c1[0] - c0[0]) * f),
            Math.round(c0[1] + (c1[1] - c0[1]) * f),
            Math.round(c0[2] + (c1[2] - c0[2]) * f),
        ];
    },

    // ------------------------------------------------------------------
    // Export formats
    // ------------------------------------------------------------------

    /**
     * Export frames as a ZIP of numbered PNG files.
     */
    async _exportPngZip(frames, progressText) {
        // Dynamically load JSZip
        await this._loadScript("https://unpkg.com/jszip@3.10.1/dist/jszip.min.js");

        const zip = new JSZip();
        const folder = zip.folder("frames");

        for (let i = 0; i < frames.length; i++) {
            const name = `frame_${String(i).padStart(5, "0")}_${frames[i].timestamp.replace(/[: ]/g, "_")}.png`;
            folder.file(name, frames[i].blob);
        }

        progressText.textContent = "Compressing ZIP...";
        const content = await zip.generateAsync({
            type: "blob",
            compression: "DEFLATE",
            compressionOptions: { level: 6 },
        }, (meta) => {
            progressText.textContent = `Compressing... ${meta.percent.toFixed(0)}%`;
        });

        this._downloadBlob(content, this._exportFilename("frames", "zip"));
        progressText.textContent = `Exported ${frames.length} frames as ZIP`;
    },

    /**
     * Export frames as animated GIF using gif.js.
     */
    async _exportGif(frames, progressText) {
        // Load gif.js from CDN
        await this._loadScript("https://unpkg.com/gif.js@0.2.0/dist/gif.js");

        const delay = parseInt(document.getElementById("export-gif-delay")?.value) || 200;

        const gif = new GIF({
            workers: 2,
            quality: 10,
            width: this._canvas.width / (window.devicePixelRatio || 1),
            height: this._canvas.height / (window.devicePixelRatio || 1),
            workerScript: "https://unpkg.com/gif.js@0.2.0/dist/gif.worker.js",
        });

        // Add each frame
        for (let i = 0; i < frames.length; i++) {
            const img = await this._blobToImage(frames[i].blob);
            gif.addFrame(img, { delay, copy: true });
        }

        progressText.textContent = "Encoding GIF...";

        return new Promise((resolve) => {
            gif.on("finished", (blob) => {
                this._downloadBlob(blob, this._exportFilename("animation", "gif"));
                progressText.textContent = `Exported ${frames.length}-frame GIF (${(blob.size / 1024 / 1024).toFixed(1)} MB)`;
                resolve();
            });
            gif.on("progress", (p) => {
                progressText.textContent = `Encoding GIF... ${(p * 100).toFixed(0)}%`;
            });
            gif.render();
        });
    },

    /**
     * Export frames as WebM video using MediaRecorder + Canvas.
     */
    async _exportVideo(frames, progressText) {
        const width = this._canvas.width / (window.devicePixelRatio || 1);
        const height = this._canvas.height / (window.devicePixelRatio || 1);
        const fps = parseInt(document.getElementById("export-video-fps")?.value) || 10;
        const frameDelay = 1000 / fps;

        // Create a playback canvas
        const playCanvas = document.createElement("canvas");
        playCanvas.width = width;
        playCanvas.height = height;
        const playCtx = playCanvas.getContext("2d");

        const stream = playCanvas.captureStream(0); // manual frame push
        const recorder = new MediaRecorder(stream, {
            mimeType: "video/webm;codecs=vp9",
            videoBitsPerSecond: 5000000,
        });

        const chunks = [];
        recorder.ondataavailable = (e) => {
            if (e.data.size > 0) chunks.push(e.data);
        };

        return new Promise((resolve) => {
            recorder.onstop = () => {
                const blob = new Blob(chunks, { type: "video/webm" });
                this._downloadBlob(blob, this._exportFilename("animation", "webm"));
                progressText.textContent = `Exported ${frames.length}-frame video (${(blob.size / 1024 / 1024).toFixed(1)} MB)`;
                resolve();
            };

            recorder.start();

            const drawFrames = async () => {
                for (let i = 0; i < frames.length; i++) {
                    if (this._cancelled) break;
                    progressText.textContent = `Encoding video frame ${i + 1}/${frames.length}`;

                    const img = await this._blobToImage(frames[i].blob);
                    playCtx.clearRect(0, 0, width, height);
                    playCtx.drawImage(img, 0, 0, width, height);

                    // Request a frame from the stream
                    const track = stream.getVideoTracks()[0];
                    if (track.requestFrame) track.requestFrame();

                    await this._sleep(frameDelay);
                }
                recorder.stop();
            };

            drawFrames();
        });
    },

    /**
     * Export current single frame as PNG.
     */
    async _exportSinglePng(progressText) {
        const blob = await this._captureMapCanvas(true);
        this._downloadBlob(blob, this._exportFilename("frame", "png"));
        progressText.textContent = "Exported current frame as PNG";
    },

    // ------------------------------------------------------------------
    // Wildfire progression
    // ------------------------------------------------------------------

    /**
     * Load wildfire progression data between two dates.
     * Shows fire perimeters that were active during the export period,
     * with progressive reveal based on discovery date.
     *
     * @param {string} startDate - YYYY-MM-DD
     * @param {string} endDate - YYYY-MM-DD
     * @returns {Array} fires sorted by discovery date
     */
    async loadFireProgression(startDate, endDate) {
        const year = parseInt(startDate.substring(0, 4));
        const endYear = parseInt(endDate.substring(0, 4));

        const fires = [];
        for (let y = year; y <= endYear; y++) {
            try {
                let geojson = WildfireOverlay.cache[y];
                if (!geojson) {
                    geojson = await WildfireOverlay._fetchPerimeters(y);
                    WildfireOverlay.cache[y] = geojson;
                }
                if (geojson && geojson.features) {
                    fires.push(...geojson.features);
                }
            } catch (e) {
                console.warn(`Failed to load fires for ${y}:`, e);
            }
        }

        // Sort by discovery date and filter to range
        const startTs = new Date(startDate + "T00:00:00").getTime();
        const endTs = new Date(endDate + "T23:59:59").getTime();

        return fires
            .map(f => {
                const dateRaw = f.properties.irwin_FireDiscoveryDateTime ||
                                f.properties.FireDiscoveryDateTime;
                const ts = dateRaw ? new Date(dateRaw).getTime() : null;
                return { feature: f, discoveryTs: ts };
            })
            .filter(f => f.discoveryTs && f.discoveryTs >= startTs && f.discoveryTs <= endTs)
            .sort((a, b) => a.discoveryTs - b.discoveryTs);
    },

    /**
     * Progressive fire layers — used during export to show fires
     * appearing as they were discovered during the animation period.
     */
    _progressionLayers: [],

    async showFiresUpTo(timestamp, fires) {
        // Remove previous progression layers
        this._clearProgressionLayers();

        const ts = new Date(timestamp).getTime();

        for (const fire of fires) {
            if (fire.discoveryTs <= ts) {
                const layer = L.geoJSON(fire.feature, {
                    style: {
                        color: "#ff4444",
                        weight: 2,
                        fillColor: "#ff6600",
                        fillOpacity: 0.35,
                    },
                });
                layer.addTo(MapLayer.map);
                this._progressionLayers.push(layer);
            }
        }
    },

    _clearProgressionLayers() {
        for (const layer of this._progressionLayers) {
            layer.remove();
        }
        this._progressionLayers = [];
    },

    /**
     * Export with wildfire progression — fires appear as they were discovered.
     */
    async startExportWithProgression() {
        if (this._exporting) return;

        const startDate = document.getElementById("export-start-date").value;
        const endDate = document.getElementById("export-end-date").value;

        if (!startDate || !endDate) return;

        // Load fire progression data
        const progressText = document.getElementById("export-progress-text");
        progressText.textContent = "Loading wildfire progression data...";

        const fires = await this.loadFireProgression(startDate, endDate);
        if (fires.length > 0) {
            progressText.textContent = `Found ${fires.length} fires in range. Starting export...`;
        }

        // Store fires for use during frame capture
        this._progressionFires = fires;

        // Start normal export (frames will include progression)
        await this.startExport();

        // Cleanup
        this._clearProgressionLayers();
        this._progressionFires = null;
    },

    // ------------------------------------------------------------------
    // Utilities
    // ------------------------------------------------------------------

    _loadImage(url) {
        return new Promise((resolve, reject) => {
            const img = new Image();
            img.crossOrigin = "anonymous";
            img.onload = () => resolve(img);
            img.onerror = reject;
            img.src = url;
        });
    },

    _blobToImage(blob) {
        return new Promise((resolve, reject) => {
            const url = URL.createObjectURL(blob);
            const img = new Image();
            img.onload = () => {
                URL.revokeObjectURL(url);
                resolve(img);
            };
            img.onerror = reject;
            img.src = url;
        });
    },

    _sleep(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    },

    _downloadBlob(blob, filename) {
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    },

    _exportFilename(prefix, ext) {
        const layer = UIControls.currentLayerPath || "data";
        const safe = layer.replace(/\//g, "_");
        const start = document.getElementById("export-start-date").value;
        const end = document.getElementById("export-end-date").value;
        return `wup_${safe}_${start}_${end}.${ext}`;
    },

    async _loadScript(src) {
        // Skip if already loaded
        if (document.querySelector(`script[src="${src}"]`)) return;

        return new Promise((resolve, reject) => {
            const script = document.createElement("script");
            script.src = src;
            script.onload = resolve;
            script.onerror = () => reject(new Error(`Failed to load ${src}`));
            document.head.appendChild(script);
        });
    },
};
