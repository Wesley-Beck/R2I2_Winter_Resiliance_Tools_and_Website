/**
 * Data loading module — loads point index and monthly CSV files via PapaParse.
 *
 * CSV format: rows indexed by point_id, columns are datetime strings "YYYY-MM-DD HH:MM".
 * Points index: point_id, latitude, longitude, lat_idx, lon_idx.
 */

const DataLoader = {
    basePath: "../data/output",
    pointIndex: null,          // Array of { point_id, latitude, longitude }
    cache: {},                 // key: "year/month/subfolder/variable" → parsed data

    /**
     * Set the base data path.
     */
    setBasePath(path) {
        this.basePath = path.replace(/\/+$/, "");
        this.cache = {};
    },

    /**
     * Load the points index CSV.
     * Returns a Promise resolving to an array of point objects.
     */
    loadPointIndex() {
        return new Promise((resolve, reject) => {
            const url = `${this.basePath}/points_index.csv`;
            Papa.parse(url, {
                download: true,
                header: true,
                dynamicTyping: true,
                skipEmptyLines: true,
                complete: (results) => {
                    if (results.errors.length > 0) {
                        console.warn("Point index parse warnings:", results.errors);
                    }
                    this.pointIndex = results.data.map(row => ({
                        point_id: row.point_id,
                        latitude: row.latitude,
                        longitude: row.longitude,
                    }));
                    console.log(`Loaded ${this.pointIndex.length} points`);
                    resolve(this.pointIndex);
                },
                error: (err) => {
                    reject(new Error(`Failed to load points index: ${err.message}`));
                },
            });
        });
    },

    /**
     * Load a monthly data CSV.
     *
     * @param {number} year - e.g., 2020
     * @param {number} month - 1-12
     * @param {string} layerPath - e.g., "cfwi/FWI" or "converted/temperature_c"
     * @returns {Promise<Object>} { timestamps: string[], byPointId: { [pointId]: { [timestamp]: number } } }
     */
    loadMonthlyCSV(year, month, layerPath) {
        const monthStr = String(month).padStart(2, "0");
        const parts = layerPath.split("/");
        const subfolder = parts[0];
        const variable = parts[1];
        const filename = `${year}_${monthStr}_${variable}.csv`;
        const cacheKey = `${year}/${monthStr}/${layerPath}`;

        if (this.cache[cacheKey]) {
            return Promise.resolve(this.cache[cacheKey]);
        }

        const url = `${this.basePath}/${year}/${monthStr}/${subfolder}/${filename}`;

        return new Promise((resolve, reject) => {
            Papa.parse(url, {
                download: true,
                header: true,
                dynamicTyping: true,
                skipEmptyLines: true,
                complete: (results) => {
                    if (results.data.length === 0) {
                        reject(new Error(`No data in ${url}`));
                        return;
                    }

                    // Get column names (first is point_id or index, rest are timestamps)
                    const fields = results.meta.fields;
                    const idField = fields[0]; // Usually "point_id" or ""
                    const timestamps = fields.slice(1);

                    // Build lookup: point_id → { timestamp: value }
                    const byPointId = {};
                    for (const row of results.data) {
                        const pid = row[idField];
                        if (pid == null) continue;
                        byPointId[pid] = {};
                        for (const ts of timestamps) {
                            byPointId[pid][ts] = row[ts];
                        }
                    }

                    const parsed = { timestamps, byPointId };
                    this.cache[cacheKey] = parsed;
                    console.log(`Loaded ${url}: ${Object.keys(byPointId).length} points, ${timestamps.length} hours`);
                    resolve(parsed);
                },
                error: (err) => {
                    reject(new Error(`No data available for this period`));
                },
            });
        });
    },

    /**
     * Get all point values for a single timestamp.
     *
     * @param {Object} parsedData - from loadMonthlyCSV
     * @param {string} timestamp - e.g., "2020-07-15 12:00"
     * @returns {Object} { [pointId]: number }
     */
    getValuesAtTime(parsedData, timestamp) {
        const result = {};
        for (const [pid, tsMap] of Object.entries(parsedData.byPointId)) {
            const val = tsMap[timestamp];
            if (val != null && !isNaN(val)) {
                result[pid] = val;
            }
        }
        return result;
    },

    /**
     * Find the closest available timestamp to a target.
     */
    findClosestTimestamp(timestamps, target) {
        if (!timestamps || timestamps.length === 0) return null;
        if (timestamps.includes(target)) return target;

        // Try to find by date/hour match
        let best = timestamps[0];
        let bestDiff = Infinity;
        const targetDate = new Date(target.replace(" ", "T") + ":00");

        for (const ts of timestamps) {
            const d = new Date(ts.replace(" ", "T") + ":00");
            const diff = Math.abs(d - targetDate);
            if (diff < bestDiff) {
                bestDiff = diff;
                best = ts;
            }
        }
        return best;
    },
};
