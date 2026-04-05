/**
 * Main application — initializes map, loads point index, wires up UI.
 */

const App = {
    async init() {
        const status = document.getElementById("status-text");
        status.textContent = "Initializing map...";

        // Initialize map
        MapLayer.initMap();

        // Initialize UI controls
        UIControls.init();

        // Data source selector
        const sourceSelect = document.getElementById("data-source-select");
        if (sourceSelect) {
            sourceSelect.addEventListener("change", (e) => {
                DataLoader.setBasePath(e.target.value);
                this.loadPoints();
            });
        }

        // Try to load point index
        await this.loadPoints();
    },

    async loadPoints() {
        const status = document.getElementById("status-text");

        try {
            status.textContent = "Loading point index...";
            MapLayer.showLoading("Loading point index...");

            const points = await DataLoader.loadPointIndex();
            MapLayer.plotPoints(points);

            // Fit map to points
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
            status.textContent = "No data loaded — use controls to set data path";
            MapLayer.hideLoading();

            // Show helpful message
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
                    <li>Set the <strong>Data Directory</strong> above to your output path</li>
                    <li>Click <strong>Load</strong></li>
                </ol>
                <p style="margin-top: 8px; color: #a08060;">
                    See USAGE.md for detailed instructions.
                </p>
            </div>
        `;
        document.getElementById("info-panel").style.display = "block";
    },
};

// Start the application when the page loads
document.addEventListener("DOMContentLoaded", () => {
    App.init();
});
