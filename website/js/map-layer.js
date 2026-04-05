/**
 * Map layer management — renders points as colored CircleMarkers on a Leaflet map.
 */

const MapLayer = {
    map: null,
    markers: [],              // Array of L.circleMarker instances
    markersByPointId: {},     // point_id → marker reference
    currentLayer: null,       // Current variable path
    currentData: null,        // Current parsed CSV data
    currentTimestamp: null,

    /**
     * Initialize the Leaflet map centered on the WUP.
     */
    initMap() {
        this.map = L.map("map", {
            center: [47.1, -89.0],
            zoom: 8,
            zoomControl: true,
            preferCanvas: true,     // Better performance for many markers
        });

        // Dark-themed basemap (CartoDB Dark Matter)
        L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png", {
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a> &copy; <a href="https://carto.com/">CARTO</a>',
            subdomains: "abcd",
            maxZoom: 19,
        }).addTo(this.map);

        return this.map;
    },

    /**
     * Plot all points from the point index as gray CircleMarkers.
     */
    plotPoints(pointIndex) {
        // Clear existing
        this.clearMarkers();

        for (const pt of pointIndex) {
            const marker = L.circleMarker([pt.latitude, pt.longitude], {
                radius: 3,
                fillColor: "rgba(128,128,128,0.4)",
                fillOpacity: 0.8,
                stroke: false,
                weight: 0,
            });

            marker.pointId = pt.point_id;
            marker.pointLat = pt.latitude;
            marker.pointLon = pt.longitude;

            marker.on("click", (e) => {
                this._onPointClick(e.target);
            });

            marker.addTo(this.map);
            this.markers.push(marker);
            this.markersByPointId[pt.point_id] = marker;
        }

        console.log(`Plotted ${this.markers.length} point markers`);
    },

    /**
     * Update marker colors based on data values at the current timestamp.
     */
    updateColors(variablePath, values) {
        for (const marker of this.markers) {
            const pid = marker.pointId;
            const val = values[pid];
            const color = getColor(variablePath, val);
            marker.setStyle({ fillColor: color, fillOpacity: 0.85 });
        }
    },

    /**
     * Reset all markers to gray (no data).
     */
    resetColors() {
        for (const marker of this.markers) {
            marker.setStyle({
                fillColor: "rgba(128,128,128,0.4)",
                fillOpacity: 0.6,
            });
        }
    },

    /**
     * Clear all markers from the map.
     */
    clearMarkers() {
        for (const marker of this.markers) {
            marker.remove();
        }
        this.markers = [];
        this.markersByPointId = {};
    },

    /**
     * Handle point click — show info panel.
     */
    _onPointClick(marker) {
        const pid = marker.pointId;
        const lat = marker.pointLat;
        const lon = marker.pointLon;

        let html = `<div class="info-row"><span class="info-label">Point ID</span><span class="info-value">${pid}</span></div>`;
        html += `<div class="info-row"><span class="info-label">Latitude</span><span class="info-value">${lat.toFixed(4)}</span></div>`;
        html += `<div class="info-row"><span class="info-label">Longitude</span><span class="info-value">${lon.toFixed(4)}</span></div>`;

        // Show value for current layer
        if (this.currentData && this.currentTimestamp && this.currentLayer) {
            const tsData = this.currentData.byPointId[pid];
            if (tsData) {
                const val = tsData[this.currentTimestamp];
                const config = VariableConfig[this.currentLayer];
                if (val != null && config) {
                    html += `<div class="info-header">${config.label}</div>`;
                    html += `<div class="info-row"><span class="info-label">${this.currentTimestamp}</span><span class="info-value">${val.toFixed(2)} ${config.units}</span></div>`;
                }
            }
        }

        const infoPanel = document.getElementById("info-panel");
        const pointInfo = document.getElementById("point-info");
        pointInfo.innerHTML = html;
        infoPanel.style.display = "block";
    },

    /**
     * Show a loading indicator on the map.
     */
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

    /**
     * Hide the loading indicator.
     */
    hideLoading() {
        const overlay = document.querySelector(".loading-overlay");
        if (overlay) overlay.style.display = "none";
    },
};
