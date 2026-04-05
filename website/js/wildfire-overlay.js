/**
 * Wildfire perimeter overlay — loads historical fire perimeters from NIFC
 * ArcGIS REST API and displays them as GeoJSON polygons on the Leaflet map.
 *
 * Enhanced with:
 * - Clickable fire list panel sorted by acreage
 * - Click-to-zoom on individual fires
 * - Calendar integration (fire discovery day markers)
 */

const WildfireOverlay = {
    layer: null,
    currentYear: null,
    cache: {},  // year → GeoJSON data
    _highlightedLayer: null,

    // WUP bounding box for spatial query
    BBOX: {
        xmin: -90.5,
        ymin: 45.9,
        xmax: -87.4,
        ymax: 48.3,
    },

    // NIFC Interagency Fire Perimeters — historical archive
    HISTORICAL_URL: "https://services3.arcgis.com/T4QMspbfLg3qTGWY/arcgis/rest/services/InteragencyFirePerimeterHistory_All_Years_View/FeatureServer/0/query",

    /**
     * Load and display wildfire perimeters for a given year.
     */
    async load(year) {
        if (this.currentYear === year && this.layer) return;
        this.currentYear = year;

        // Remove existing layer
        this.hide();

        const infoEl = document.getElementById("wildfire-info");
        infoEl.textContent = `Loading ${year} fires...`;

        try {
            let geojson = this.cache[year];
            if (!geojson) {
                geojson = await this._fetchPerimeters(year);
                this.cache[year] = geojson;
            }

            if (!geojson || !geojson.features || geojson.features.length === 0) {
                infoEl.textContent = `No recorded fires in WUP for ${year}`;
                this._clearFireList();
                UIControls.setFireDates(new Set());
                return;
            }

            this.layer = L.geoJSON(geojson, {
                style: {
                    color: "#ff4444",
                    weight: 2,
                    fillColor: "#ff6600",
                    fillOpacity: 0.25,
                },
                onEachFeature: (feature, layer) => {
                    layer.bindPopup(this._buildPopup(feature.properties));
                },
            });

            this.layer.addTo(MapLayer.map);

            const count = geojson.features.length;
            const totalAcres = this._totalAcres(geojson.features);
            infoEl.textContent = `${count} fire${count !== 1 ? "s" : ""} in WUP for ${year}` +
                (totalAcres > 0 ? ` (${totalAcres.toLocaleString()} acres)` : "");

            // Build fire list and calendar markers
            this._buildFireList(geojson.features);
            this._updateFireCalendar(geojson.features);

        } catch (err) {
            console.error("Wildfire load error:", err);
            infoEl.textContent = `Failed to load fire data: ${err.message}`;
        }
    },

    /**
     * Hide the wildfire perimeter layer.
     */
    hide() {
        if (this.layer) {
            this.layer.remove();
            this.layer = null;
        }
        this._clearHighlight();
        this._clearFireList();
        UIControls.setFireDates(new Set());
    },

    /**
     * Build the fire list panel with clickable entries sorted by acreage.
     */
    _buildFireList(features) {
        const listEl = document.getElementById("fire-list");
        if (!listEl) return;
        listEl.innerHTML = "";

        // Sort by acreage (largest first)
        const sorted = [...features].sort((a, b) => {
            return this._getAcres(b.properties) - this._getAcres(a.properties);
        });

        for (const feature of sorted) {
            const p = feature.properties;
            const name = p.poly_IncidentName || p.irwin_IncidentName || p.IncidentName || "Unknown";
            const acres = this._getAcres(p);
            const dateStr = this._getDateStr(p);

            const item = document.createElement("div");
            item.className = "fire-list-item";
            item.innerHTML = `
                <span class="fire-name">${name}</span>
                <span class="fire-detail">${acres > 0 ? acres.toLocaleString() + " ac" : ""}${dateStr ? " &middot; " + dateStr : ""}</span>
            `;
            item.addEventListener("click", () => this._zoomToFire(feature));
            listEl.appendChild(item);
        }
    },

    /**
     * Zoom to a specific fire and highlight it.
     */
    _zoomToFire(feature) {
        this._clearHighlight();

        // Create a temporary highlight layer
        this._highlightedLayer = L.geoJSON(feature, {
            style: {
                color: "#ffff00",
                weight: 4,
                fillColor: "#ffcc00",
                fillOpacity: 0.4,
            },
        });
        this._highlightedLayer.addTo(MapLayer.map);

        // Zoom to bounds
        const bounds = this._highlightedLayer.getBounds();
        if (bounds.isValid()) {
            MapLayer.map.fitBounds(bounds, { padding: [40, 40], maxZoom: 12 });
        }

        // Open popup
        this._highlightedLayer.eachLayer(layer => {
            layer.bindPopup(this._buildPopup(feature.properties)).openPopup();
        });

        // Auto-clear highlight after 8 seconds
        setTimeout(() => this._clearHighlight(), 8000);
    },

    _clearHighlight() {
        if (this._highlightedLayer) {
            this._highlightedLayer.remove();
            this._highlightedLayer = null;
        }
    },

    /**
     * Update calendar with fire discovery date markers.
     */
    _updateFireCalendar(features) {
        const fireDays = new Set();
        const currentMonth = UIControls.currentMonth;

        for (const feature of features) {
            const date = this._getFireDate(feature.properties);
            if (date && date.getMonth() + 1 === currentMonth) {
                fireDays.add(date.getDate());
            }
        }

        UIControls.setFireDates(fireDays);
    },

    _clearFireList() {
        const listEl = document.getElementById("fire-list");
        if (listEl) listEl.innerHTML = "";
    },

    _buildPopup(p) {
        const name = p.poly_IncidentName || p.irwin_IncidentName || p.IncidentName || "Unknown";
        const acres = this._getAcres(p);
        const cause = p.irwin_FireCause || p.FireCause || "";
        const dateStr = this._getDateStr(p);
        const acresStr = acres > 0 ? `${acres.toLocaleString()} acres` : "Size unknown";

        return `<div style="font-size: 0.85rem;">` +
            `<strong>${name}</strong><br>` +
            `${acresStr}<br>` +
            (dateStr ? `Discovered: ${dateStr}<br>` : "") +
            (cause ? `Cause: ${cause}` : "") +
            `</div>`;
    },

    _getAcres(p) {
        const raw = p.poly_GISAcres || p.GISAcres || p.irwin_CalculatedAcres || 0;
        return typeof raw === "number" ? Math.round(raw) : 0;
    },

    _totalAcres(features) {
        return features.reduce((sum, f) => sum + this._getAcres(f.properties), 0);
    },

    _getFireDate(p) {
        const raw = p.irwin_FireDiscoveryDateTime || p.FireDiscoveryDateTime || "";
        if (!raw) return null;
        const d = new Date(raw);
        return isNaN(d) ? null : d;
    },

    _getDateStr(p) {
        const d = this._getFireDate(p);
        return d ? d.toLocaleDateString() : "";
    },

    /**
     * Fetch fire perimeters from NIFC ArcGIS REST API.
     */
    async _fetchPerimeters(year) {
        const bbox = this.BBOX;
        const params = new URLSearchParams({
            where: `FireDiscoveryDateTime >= '${year}-01-01' AND FireDiscoveryDateTime <= '${year}-12-31'`,
            geometry: `${bbox.xmin},${bbox.ymin},${bbox.xmax},${bbox.ymax}`,
            geometryType: "esriGeometryEnvelope",
            inSR: "4326",
            spatialRel: "esriSpatialRelIntersects",
            outFields: "*",
            returnGeometry: "true",
            outSR: "4326",
            f: "geojson",
        });

        const url = `${this.HISTORICAL_URL}?${params}`;
        const response = await fetch(url);

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        return await response.json();
    },
};
