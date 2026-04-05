/**
 * Color scale definitions for different variable types.
 * Each scale has: stops (array of [position, color]), min, max, label, units.
 */

const ColorScales = {
    // Fire danger: green → gold → orange → red
    fire: {
        stops: [
            [0.0,  [43, 92, 63]],    // #2b5c3f forest green
            [0.2,  [74, 140, 63]],   // #4a8c3f green
            [0.4,  [165, 196, 78]],  // #a5c44e yellow-green
            [0.5,  [245, 211, 110]], // #f5d36e gold
            [0.7,  [232, 149, 48]],  // #e89530 orange
            [0.85, [200, 78, 29]],   // #c84e1d burnt orange
            [1.0,  [122, 26, 15]],   // #7a1a0f deep red
        ],
        gradient: "linear-gradient(to right, #2b5c3f, #4a8c3f, #a5c44e, #f5d36e, #e89530, #c84e1d, #7a1a0f)",
    },

    // Temperature: blue → white → red
    temperature: {
        stops: [
            [0.0,  [44, 62, 148]],   // cold blue
            [0.25, [100, 140, 200]], // light blue
            [0.5,  [240, 240, 240]], // white
            [0.75, [220, 120, 60]],  // warm orange
            [1.0,  [170, 30, 20]],   // hot red
        ],
        gradient: "linear-gradient(to right, #2c3e94, #648cc8, #f0f0f0, #dc783c, #aa1e14)",
    },

    // Humidity: brown (dry) → blue (humid)
    humidity: {
        stops: [
            [0.0,  [140, 90, 50]],   // dry brown
            [0.3,  [180, 160, 100]], // tan
            [0.5,  [160, 200, 170]], // pale green
            [0.7,  [100, 160, 200]], // light blue
            [1.0,  [30, 80, 160]],   // deep blue
        ],
        gradient: "linear-gradient(to right, #8c5a32, #b4a064, #a0c8aa, #64a0c8, #1e50a0)",
    },

    // Precipitation: white → deep blue
    precipitation: {
        stops: [
            [0.0,  [240, 240, 240]], // near-white
            [0.3,  [170, 210, 230]], // light blue
            [0.6,  [80, 150, 200]],  // medium blue
            [0.8,  [30, 90, 160]],   // dark blue
            [1.0,  [10, 40, 100]],   // deep blue
        ],
        gradient: "linear-gradient(to right, #f0f0f0, #aad2e6, #5096c8, #1e5aa0, #0a2864)",
    },

    // Wind: calm green → strong purple
    wind: {
        stops: [
            [0.0,  [60, 140, 80]],   // calm green
            [0.3,  [200, 200, 80]],  // yellow
            [0.6,  [220, 130, 40]],  // orange
            [0.8,  [180, 50, 50]],   // red
            [1.0,  [130, 40, 130]],  // purple
        ],
        gradient: "linear-gradient(to right, #3c8c50, #c8c850, #dc8228, #b43232, #822882)",
    },

    // Fuel moisture: red (dry/dangerous) → green (wet/safe)
    moisture: {
        stops: [
            [0.0,  [170, 30, 20]],   // very dry - red
            [0.25, [220, 120, 40]],  // dry - orange
            [0.5,  [220, 200, 80]],  // moderate - yellow
            [0.75, [100, 170, 100]], // moist - green
            [1.0,  [30, 100, 60]],   // wet - deep green
        ],
        gradient: "linear-gradient(to right, #aa1e14, #dc7828, #dcc850, #64aa64, #1e643c)",
    },
};

// Map variable paths to scale types and default ranges
const VariableConfig = {
    // Weather
    "converted/temperature_c":     { scale: "temperature",   min: -30, max: 40,   label: "Temperature", units: "\u00b0C" },
    "converted/temperature_f":     { scale: "temperature",   min: -20, max: 105,  label: "Temperature", units: "\u00b0F" },
    "converted/relative_humidity": { scale: "humidity",       min: 0,   max: 100,  label: "Relative Humidity", units: "%" },
    "converted/wind_speed_kph":    { scale: "wind",           min: 0,   max: 80,   label: "Wind Speed", units: "km/h" },
    "converted/wind_speed_mph":    { scale: "wind",           min: 0,   max: 50,   label: "Wind Speed", units: "mph" },
    "converted/precipitation_mm":  { scale: "precipitation",  min: 0,   max: 20,   label: "Precipitation", units: "mm" },

    // CFWI
    "cfwi/FFMC": { scale: "fire", min: 0,  max: 101, label: "FFMC", units: "" },
    "cfwi/DMC":  { scale: "fire", min: 0,  max: 150, label: "DMC",  units: "" },
    "cfwi/DC":   { scale: "fire", min: 0,  max: 500, label: "DC",   units: "" },
    "cfwi/ISI":  { scale: "fire", min: 0,  max: 30,  label: "ISI",  units: "" },
    "cfwi/BUI":  { scale: "fire", min: 0,  max: 150, label: "BUI",  units: "" },
    "cfwi/FWI":  { scale: "fire", min: 0,  max: 50,  label: "FWI",  units: "" },

    // NFDRS
    "nfdrs/FM1":    { scale: "moisture", min: 0,   max: 40,  label: "1-hr Fuel Moisture", units: "%" },
    "nfdrs/FM10":   { scale: "moisture", min: 0,   max: 40,  label: "10-hr Fuel Moisture", units: "%" },
    "nfdrs/FM100":  { scale: "moisture", min: 0,   max: 40,  label: "100-hr Fuel Moisture", units: "%" },
    "nfdrs/FM1000": { scale: "moisture", min: 0,   max: 40,  label: "1000-hr Fuel Moisture", units: "%" },
    "nfdrs/SC":     { scale: "fire",     min: 0,   max: 100, label: "Spread Component", units: "ft/min" },
    "nfdrs/ERC":    { scale: "fire",     min: 0,   max: 100, label: "Energy Release Component", units: "BTU/ft\u00b2" },
    "nfdrs/BI":     { scale: "fire",     min: 0,   max: 150, label: "Burning Index", units: "" },

    // FPI
    "fpi/RG":  { scale: "fire", min: 0, max: 1,   label: "Relative Greenness", units: "" },
    "fpi/EMC": { scale: "moisture", min: 0, max: 40, label: "EMC", units: "%" },
    "fpi/FPI": { scale: "fire", min: 0, max: 100, label: "Fire Potential Index", units: "" },
};

/**
 * Interpolate a color from a scale at a normalized position (0-1).
 * Returns [r, g, b] array.
 */
function interpolateColor(scale, t) {
    t = Math.max(0, Math.min(1, t));
    const stops = scale.stops;

    // Find surrounding stops
    for (let i = 0; i < stops.length - 1; i++) {
        if (t >= stops[i][0] && t <= stops[i + 1][0]) {
            const range = stops[i + 1][0] - stops[i][0];
            const local_t = range > 0 ? (t - stops[i][0]) / range : 0;
            const c0 = stops[i][1];
            const c1 = stops[i + 1][1];
            return [
                Math.round(c0[0] + (c1[0] - c0[0]) * local_t),
                Math.round(c0[1] + (c1[1] - c0[1]) * local_t),
                Math.round(c0[2] + (c1[2] - c0[2]) * local_t),
            ];
        }
    }
    return stops[stops.length - 1][1];
}

/**
 * Get an RGB color string for a value given a variable path.
 */
function getColor(variablePath, value) {
    const config = VariableConfig[variablePath];
    if (!config || value == null || isNaN(value)) return "rgba(128,128,128,0.4)";

    const scale = ColorScales[config.scale];
    const t = (value - config.min) / (config.max - config.min);
    const [r, g, b] = interpolateColor(scale, t);
    return `rgb(${r},${g},${b})`;
}
