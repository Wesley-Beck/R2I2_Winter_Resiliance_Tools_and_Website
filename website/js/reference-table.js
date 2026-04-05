/**
 * Reference page — FDI dataset capability table.
 *
 * Self-contained: includes all dataset metadata so this script works
 * on the standalone reference.html page without loading app.js.
 * Supports filtering by category and FDI capability.
 */

const ReferenceTable = {

    _datasets: null,

    init() {
        this._datasets = this._buildDatasetList();
        this._render();
        this._wireFilters();
    },

    /** Self-contained dataset definitions (mirrors app.js HISTORICAL + projections). */
    _buildDatasetList() {
        return [
            // --- Reanalysis ---
            { name: "NOAA AORC v1.1", category: "Reanalysis", catFilter: "reanalysis",
              spatial: "~800 m", temporal: "Hourly", period: "1979 \u2013 present",
              hasT: true, hasRH: true, hasWind: true, hasPrecip: true, hasRad: true, hasPres: true,
              canFWI: true, canNFDRS: true, canFPI: true },
            { name: "NASA NLDAS-2", category: "Reanalysis", catFilter: "reanalysis",
              spatial: "12 km", temporal: "Hourly", period: "1979 \u2013 present",
              hasT: true, hasRH: true, hasWind: true, hasPrecip: true, hasRad: true, hasPres: true,
              canFWI: true, canNFDRS: true, canFPI: true },
            { name: "ECMWF ERA5", category: "Reanalysis", catFilter: "reanalysis",
              spatial: "31 km", temporal: "Hourly", period: "1940 \u2013 present",
              hasT: true, hasRH: true, hasWind: true, hasPrecip: true, hasRad: true, hasPres: true,
              canFWI: true, canNFDRS: true, canFPI: true },
            { name: "ECMWF ERA5-Land", category: "Reanalysis", catFilter: "reanalysis",
              spatial: "9 km", temporal: "Hourly", period: "1950 \u2013 present",
              hasT: true, hasRH: true, hasWind: true, hasPrecip: true, hasRad: false, hasPres: false,
              canFWI: true, canNFDRS: true, canFPI: true },
            { name: "NCEP NARR", category: "Reanalysis", catFilter: "reanalysis",
              spatial: "32 km", temporal: "3-hourly", period: "1979 \u2013 2024",
              hasT: true, hasRH: true, hasWind: true, hasPrecip: true, hasRad: true, hasPres: true,
              canFWI: true, canNFDRS: true, canFPI: true },
            { name: "NOAA HRRR", category: "Reanalysis / NWP", catFilter: "reanalysis",
              spatial: "3 km", temporal: "Hourly", period: "2014 \u2013 present",
              hasT: true, hasRH: true, hasWind: true, hasPrecip: true, hasRad: true, hasPres: false,
              canFWI: true, canNFDRS: true, canFPI: true },
            { name: "NOAA RTMA/URMA", category: "Reanalysis", catFilter: "reanalysis",
              spatial: "2.5 km", temporal: "Hourly", period: "2011 \u2013 present",
              hasT: true, hasRH: true, hasWind: true, hasPrecip: true, hasRad: false, hasPres: true,
              canFWI: true, canNFDRS: true, canFPI: true },

            // --- Gridded Observations ---
            { name: "PRISM", category: "Gridded Obs", catFilter: "gridded",
              spatial: "800 m", temporal: "Daily", period: "1895 \u2013 present",
              hasT: true, hasRH: true, hasWind: false, hasPrecip: true, hasRad: false, hasPres: false,
              canFWI: false, canNFDRS: false, canFPI: true },
            { name: "Daymet v4", category: "Gridded Obs", catFilter: "gridded",
              spatial: "1 km", temporal: "Daily", period: "1980 \u2013 present",
              hasT: true, hasRH: true, hasWind: false, hasPrecip: true, hasRad: true, hasPres: false,
              canFWI: false, canNFDRS: false, canFPI: true },
            { name: "GridMET", category: "Gridded Obs", catFilter: "gridded",
              spatial: "4 km", temporal: "Daily", period: "1979 \u2013 present",
              hasT: true, hasRH: true, hasWind: true, hasPrecip: true, hasRad: true, hasPres: false,
              canFWI: true, canNFDRS: true, canFPI: true },
            { name: "Livneh", category: "Gridded Obs", catFilter: "gridded",
              spatial: "6 km", temporal: "Daily", period: "1915 \u2013 2015",
              hasT: true, hasRH: false, hasWind: true, hasPrecip: true, hasRad: false, hasPres: false,
              canFWI: false, canNFDRS: false, canFPI: false },

            // --- Radar / Satellite ---
            { name: "NOAA MRMS", category: "Radar/Satellite", catFilter: "radar",
              spatial: "1 km", temporal: "2-minute", period: "2014 \u2013 present",
              hasT: false, hasRH: false, hasWind: false, hasPrecip: true, hasRad: false, hasPres: false,
              canFWI: false, canNFDRS: false, canFPI: false },
            { name: "NOAA CPC Unified", category: "Gridded Obs", catFilter: "gridded",
              spatial: "25 km", temporal: "Daily", period: "1948 \u2013 present",
              hasT: true, hasRH: false, hasWind: false, hasPrecip: true, hasRad: false, hasPres: false,
              canFWI: false, canNFDRS: false, canFPI: false },

            // --- Climate Projections ---
            { name: "NEX-GDDP-CMIP6 (27 GCMs)", category: "Projection (BCSD)", catFilter: "projection",
              spatial: "25 km", temporal: "Daily", period: "2015 \u2013 2100",
              hasT: true, hasRH: true, hasWind: true, hasPrecip: true, hasRad: false, hasPres: false,
              canFWI: true, canNFDRS: true, canFPI: true },
            { name: "ClimRR / Argonne (CESM2+WRF)", category: "Projection (WRF)", catFilter: "projection",
              spatial: "12 km", temporal: "Daily", period: "1995 \u2013 2094",
              hasT: true, hasRH: true, hasWind: true, hasPrecip: true, hasRad: false, hasPres: false,
              canFWI: true, canNFDRS: true, canFPI: true },
            { name: "GLARM / Michigan Tech (RegCM4)", category: "Projection (RegCM4)", catFilter: "projection",
              spatial: "18 km", temporal: "Daily", period: "1981 \u2013 2099",
              hasT: true, hasRH: true, hasWind: true, hasPrecip: true, hasRad: true, hasPres: false,
              canFWI: true, canNFDRS: true, canFPI: true },
        ];
    },

    /** Render table rows. */
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
            tr.appendChild(textCell(ds.temporal));
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
};

document.addEventListener("DOMContentLoaded", () => ReferenceTable.init());
