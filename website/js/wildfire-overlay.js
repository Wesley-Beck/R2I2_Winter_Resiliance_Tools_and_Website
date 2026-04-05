/**
 * Wildfire perimeter overlay — loads historical fire perimeters from NIFC
 * ArcGIS REST API and displays them as GeoJSON polygons on the Leaflet map.
 */

const WildfireOverlay = {
    layer: null,
    currentYear: null,
    cache: {},  // year → GeoJSON data

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
                    const p = feature.properties;
                    const name = p.poly_IncidentName || p.irwin_IncidentName || p.IncidentName || "Unknown";
                    const acres = p.poly_GISAcres || p.GISAcres || p.irwin_CalculatedAcres || "N/A";
                    const cause = p.irwin_FireCause || p.FireCause || "";
                    const date = p.irwin_FireDiscoveryDateTime || p.FireDiscoveryDateTime || "";

                    let dateStr = "";
                    if (date) {
                        const d = new Date(date);
                        if (!isNaN(d)) dateStr = d.toLocaleDateString();
                    }

                    const acresStr = typeof acres === "number" ? acres.toFixed(0) : acres;

                    layer.bindPopup(
                        `<div style="font-size: 0.85rem;">` +
                        `<strong>${name}</strong><br>` +
                        `${acresStr} acres<br>` +
                        (dateStr ? `Discovered: ${dateStr}<br>` : "") +
                        (cause ? `Cause: ${cause}` : "") +
                        `</div>`
                    );
                },
            });

            this.layer.addTo(MapLayer.map);

            const count = geojson.features.length;
            infoEl.textContent = `${count} fire${count !== 1 ? "s" : ""} in WUP for ${year}`;

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
