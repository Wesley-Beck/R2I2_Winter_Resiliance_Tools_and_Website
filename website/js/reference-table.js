/**
 * Reference tab — FDI dataset capability table.
 *
 * Populates the table from the same HISTORICAL / DOWNSCALING metadata
 * used by the explorer, plus projection entries. Supports filtering
 * by category and FDI capability.
 */

const ReferenceTable = {

    /** Full dataset list for the reference table. */
    _datasets: null,

    init() {
        this._datasets = this._buildDatasetList();
        this._render();
        this._wireFilters();
        this._wireTabs();
    },

    /** Build a flat array of dataset descriptors from app metadata. */
    _buildDatasetList() {
        const datasets = [];

        // Historical datasets
        const categories = {
            aorc: "Reanalysis", nldas2: "Reanalysis", era5: "Reanalysis",
            era5land: "Reanalysis", narr: "Reanalysis", hrrr: "Reanalysis",
            rtma: "Reanalysis",
            prism: "Gridded Obs", daymet: "Gridded Obs", gridmet: "Gridded Obs",
            livneh: "Gridded Obs",
            mrms: "Radar/Satellite", cpc: "Gridded Obs",
        };

        for (const [key, meta] of Object.entries(HISTORICAL)) {
            const vars = meta.hasVars || [];
            datasets.push({
                name: meta.source.split("(")[0].trim(),
                key,
                category: categories[key] || "Other",
                catFilter: categories[key] === "Radar/Satellite" ? "radar"
                    : categories[key] === "Gridded Obs" ? "gridded" : "reanalysis",
                spatial: meta.spatial.split("(")[0].trim(),
                temporal: meta.temporal,
                period: meta.period,
                hasT: vars.includes("T"),
                hasRH: vars.includes("RH"),
                hasWind: vars.includes("wind"),
                hasPrecip: vars.includes("precip"),
                hasRad: vars.includes("radiation"),
                hasPres: vars.includes("pressure"),
                canFWI: vars.includes("T") && vars.includes("RH") && vars.includes("wind") && vars.includes("precip"),
                canNFDRS: vars.includes("T") && vars.includes("RH") && vars.includes("wind") && vars.includes("precip"),
                canFPI: vars.includes("T") && vars.includes("RH"),
                notes: meta.access || "",
            });
        }

        // Projection datasets
        const projections = [
            {
                name: "NEX-GDDP-CMIP6",
                key: "nex-gddp",
                category: "Projection (BCSD)",
                catFilter: "projection",
                spatial: "25 km",
                temporal: "Daily",
                period: "2015-2100",
                hasT: true, hasRH: true, hasWind: true, hasPrecip: true,
                hasRad: false, hasPres: false,
                canFWI: true, canNFDRS: true, canFPI: true,
                notes: "27 GCMs. SSP2-4.5 / SSP5-8.5.",
            },
            {
                name: "ClimRR / Argonne",
                key: "climrr",
                category: "Projection (WRF)",
                catFilter: "projection",
                spatial: "12 km",
                temporal: "Daily",
                period: "1995-2094",
                hasT: true, hasRH: true, hasWind: true, hasPrecip: true,
                hasRad: false, hasPres: false,
                canFWI: true, canNFDRS: true, canFPI: true,
                notes: "CESM2 via WRF. SSP2-4.5 / SSP5-8.5.",
            },
            {
                name: "GLARM / Michigan Tech",
                key: "glarm",
                category: "Projection (RegCM4)",
                catFilter: "projection",
                spatial: "18 km",
                temporal: "Daily",
                period: "1981-2099",
                hasT: true, hasRH: true, hasWind: true, hasPrecip: true,
                hasRad: true, hasPres: false,
                canFWI: true, canNFDRS: true, canFPI: true,
                notes: "RegCM4 ensemble. RCP 4.5 / 8.5.",
            },
        ];

        return datasets.concat(projections);
    },

    /** Render table rows for the given (or all) datasets. */
    _render(filteredList) {
        const list = filteredList || this._datasets;
        const tbody = document.getElementById("fdi-table-body");
        tbody.innerHTML = "";

        for (const ds of list) {
            const tr = document.createElement("tr");

            const yesCell = (val) => {
                const td = document.createElement("td");
                td.className = val ? "cell-yes" : "cell-no";
                td.textContent = val ? "\u2713" : "\u2717";
                return td;
            };

            const fdiCell = (val) => {
                const td = document.createElement("td");
                td.className = val ? "cell-fdi-yes" : "cell-fdi-no";
                td.textContent = val ? "\u2713" : "\u2014";
                return td;
            };

            const textCell = (text, cls) => {
                const td = document.createElement("td");
                td.textContent = text;
                if (cls) td.className = cls;
                return td;
            };

            tr.appendChild(textCell(ds.name, "cell-name"));
            tr.appendChild(textCell(ds.category, "cell-cat"));
            tr.appendChild(textCell(ds.spatial));
            tr.appendChild(textCell(ds.period));
            tr.appendChild(yesCell(ds.hasT));
            tr.appendChild(yesCell(ds.hasRH));
            tr.appendChild(yesCell(ds.hasWind));
            tr.appendChild(yesCell(ds.hasPrecip));
            tr.appendChild(yesCell(ds.hasRad));
            tr.appendChild(yesCell(ds.hasPres));
            tr.appendChild(fdiCell(ds.canFWI));
            tr.appendChild(fdiCell(ds.canNFDRS));
            tr.appendChild(fdiCell(ds.canFPI));

            tbody.appendChild(tr);
        }
    },

    /** Wire up filter dropdowns. */
    _wireFilters() {
        const catFilter = document.getElementById("ref-filter-category");
        const fdiFilter = document.getElementById("ref-filter-fdi");

        const applyFilters = () => {
            const cat = catFilter.value;
            const fdi = fdiFilter.value;

            let filtered = this._datasets;
            if (cat !== "all") {
                filtered = filtered.filter(d => d.catFilter === cat);
            }
            if (fdi === "cfwi") filtered = filtered.filter(d => d.canFWI);
            else if (fdi === "nfdrs") filtered = filtered.filter(d => d.canNFDRS);
            else if (fdi === "fpi") filtered = filtered.filter(d => d.canFPI);
            else if (fdi === "none") filtered = filtered.filter(d => !d.canFWI && !d.canNFDRS && !d.canFPI);

            this._render(filtered);
        };

        catFilter.addEventListener("change", applyFilters);
        fdiFilter.addEventListener("change", applyFilters);
    },

    /** Wire tab navigation buttons. */
    _wireTabs() {
        document.querySelectorAll(".tab-btn").forEach(btn => {
            btn.addEventListener("click", () => {
                const tab = btn.dataset.tab;

                // Update button active state
                document.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
                btn.classList.add("active");

                // Show/hide tab content
                document.querySelectorAll(".tab-content").forEach(tc => {
                    tc.style.display = "none";
                    tc.classList.remove("active");
                });
                const target = document.getElementById(`tab-${tab}`);
                if (target) {
                    target.style.display = "";
                    target.classList.add("active");
                }

                // Invalidate map size when switching back to explorer
                if (tab === "explorer" && typeof MapLayer !== "undefined" && MapLayer.map) {
                    setTimeout(() => MapLayer.map.invalidateSize(), 100);
                }
            });
        });
    },
};

document.addEventListener("DOMContentLoaded", () => ReferenceTable.init());
