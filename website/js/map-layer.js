/**
 * Map layer management — renders points as colored CircleMarkers on a Leaflet map.
 *
 * Optimized: updateColors takes a Float32Array directly (no object allocation),
 * and uses indexed access instead of property lookups for 28K+ markers.
 */

const MapLayer = {
    map: null,
    markers: [],              // Array of L.circleMarker instances (ordered by point index)
    currentLayer: null,       // Current variable path
    currentData: null,        // Current parsed CSV data
    currentHourIndex: -1,     // Current hour index into data arrays

    /**
     * Initialize the Leaflet map centered on the WUP.
     */
    initMap() {
        this.map = L.map("map", {
            center: [47.1, -89.0],
            zoom: 8,
            zoomControl: true,
            preferCanvas: true,
        });

        L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png", {
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a> &copy; <a href="https://carto.com/">CARTO</a>',
            subdomains: "abcd",
            maxZoom: 19,
        }).addTo(this.map);

        return this.map;
    },

    /**
     * Plot all points from the point index as gray CircleMarkers.
     * Markers are stored in point index order for direct array indexing.
     */
    plotPoints(pointIndex) {
        this.clearMarkers();

        for (let i = 0; i < pointIndex.length; i++) {
            const pt = pointIndex[i];
            const marker = L.circleMarker([pt.latitude, pt.longitude], {
                radius: 3,
                fillColor: "rgba(128,128,128,0.4)",
                fillOpacity: 0.8,
                stroke: false,
                weight: 0,
            });

            marker._ptIdx = i;
            marker._ptId = pt.point_id;
            marker._ptLat = pt.latitude;
            marker._ptLon = pt.longitude;

            marker.on("click", (e) => {
                this._onPointClick(e.target);
            });

            marker.addTo(this.map);
            this.markers.push(marker);
        }

        console.log(`Plotted ${this.markers.length} point markers`);
    },

    /**
     * Update marker colors from a Float32Array (indexed by point order).
     * No object allocation — direct array access for all 28K markers.
     */
    updateColorsFromArray(variablePath, valuesArray) {
        const config = VariableConfig[variablePath];
        if (!config) return;

        const scale = ColorScales[config.scale];
        const min = config.min;
        const range = config.max - min;

        for (let i = 0; i < this.markers.length; i++) {
            const val = valuesArray[i];
            let color;

            if (isNaN(val)) {
                color = "rgba(128,128,128,0.4)";
            } else {
                // Inline color interpolation to avoid function call overhead for 28K markers
                const t = Math.max(0, Math.min(1, (val - min) / range));
                color = scale.interpolate ? scale.interpolate(t) : getColor(variablePath, val);
            }

            this.markers[i].setStyle({ fillColor: color, fillOpacity: 0.85 });
        }
    },

    /**
     * Legacy updateColors — kept for compatibility, delegates to array version.
     */
    updateColors(variablePath, values) {
        // If values is a Float32Array, use direct path
        if (values instanceof Float32Array) {
            this.updateColorsFromArray(variablePath, values);
            return;
        }
        // Object-based fallback
        for (const marker of this.markers) {
            const pid = marker._ptId;
            const val = values[pid];
            const color = getColor(variablePath, val);
            marker.setStyle({ fillColor: color, fillOpacity: 0.85 });
        }
    },

    resetColors() {
        for (const marker of this.markers) {
            marker.setStyle({
                fillColor: "rgba(128,128,128,0.4)",
                fillOpacity: 0.6,
            });
        }
    },

    clearMarkers() {
        for (const marker of this.markers) {
            marker.remove();
        }
        this.markers = [];
    },

    _onPointClick(marker) {
        const pid = marker._ptId;
        const lat = marker._ptLat;
        const lon = marker._ptLon;

        let html = `<div class="info-row"><span class="info-label">Point ID</span><span class="info-value">${pid}</span></div>`;
        html += `<div class="info-row"><span class="info-label">Latitude</span><span class="info-value">${lat.toFixed(4)}</span></div>`;
        html += `<div class="info-row"><span class="info-label">Longitude</span><span class="info-value">${lon.toFixed(4)}</span></div>`;

        if (this.currentData && this.currentHourIndex >= 0 && this.currentLayer) {
            const val = DataLoader.getValueForPoint(this.currentData, this.currentHourIndex, pid);
            const config = VariableConfig[this.currentLayer];
            if (val != null && config) {
                const ts = this.currentData.timestamps[this.currentHourIndex];
                html += `<div class="info-header">${config.label}</div>`;
                html += `<div class="info-row"><span class="info-label">${ts}</span><span class="info-value">${val.toFixed(2)} ${config.units}</span></div>`;
            }
        }

        const infoPanel = document.getElementById("info-panel");
        document.getElementById("point-info").innerHTML = html;
        infoPanel.style.display = "block";
    },

    showLoading(message) {
        let overlay = document.querySelector(".loading-overlay");
        if (!overlay) {
            overlay = document.createElement("div");
            overlay.className = "loading-overlay";
            document.getElementById("map").appendChild(overlay);
        }
        overlay.textContent = message || "Loading...";
        overlay.style.display = "block";
    },

    hideLoading() {
        const overlay = document.querySelector(".loading-overlay");
        if (overlay) overlay.style.display = "none";
    },
};
