"""
Dead fuel moisture calculations for NFDRS.

Provides two approaches:
1. EMC approximation — simple, no carry-forward state needed.
   Matches how Argonne derived fuel moisture from GRIDMET.
2. Nelson model — carry-forward timelag model, more accurate for hourly data.

Both produce 1-hr, 10-hr, 100-hr, and 1000-hr dead fuel moisture values
needed by the NFDRS ERC/BI/SC calculation chain.

References:
    - Simard 1968: EMC equations (3-range piecewise)
    - Nelson 2000: Dead fuel moisture timelag model
    - Bradshaw et al. 1984: NFDRS fuel moisture timelag equations
    - Argonne (Yu/Feng): Used GRIDMET pre-computed FM via EMC approach
"""

import numpy as np

from aorc_tools.climate_convert import equilibrium_moisture_content


def emc_fuel_moisture(temp_f, rh):
    """Compute dead fuel moisture using EMC approximation (no state).

    Simple approach matching Argonne's GRIDMET-derived fuel moisture.
    No carry-forward state needed — each timestep is independent.

    Args:
        temp_f: Temperature in °F (scalar or array).
        rh: Relative humidity in % (scalar or array).

    Returns:
        dict with keys: fm1, fm10, fm100, fm1000 (all as % moisture content).
    """
    emc = equilibrium_moisture_content(temp_f, rh)

    # Standard NFDRS timelag multipliers from EMC
    # 1-hr fuel moisture ≈ EMC (responds immediately)
    # 10-hr = EMC × 1.28 (Argonne FPI code uses this)
    # 100-hr and 1000-hr use larger multipliers for slower response
    return {
        "fm1": emc,
        "fm10": emc * 1.28,
        "fm100": emc * 1.5,
        "fm1000": emc * 1.8,
    }


class NelsonFuelMoisture:
    """Dead fuel moisture model with carry-forward timelag state.

    Implements the NFDRS fuel moisture stick equations for 1-hr through
    1000-hr timelag classes. Each class responds to weather changes at
    a rate proportional to its timelag period.

    More accurate than EMC approximation for hourly data because it
    models the lag between weather changes and fuel moisture response.

    References:
        - Nelson 2000, "Prediction of diurnal change in 10-h fuel stick
          moisture content"
        - Bradshaw et al. 1984, Chapter 6 (fuel moisture calculations)
    """

    # Timelag periods in hours
    TIMELAGS = {
        "fm1": 1.0,
        "fm10": 10.0,
        "fm100": 100.0,
        "fm1000": 1000.0,
    }

    # Response rate per hour: 1 - exp(-1/timelag)
    # For 1-hr: responds ~63% in 1 hour
    # For 10-hr: responds ~10% in 1 hour
    # For 1000-hr: responds ~0.1% in 1 hour

    def __init__(self, n_points, initial_fm=None):
        """Initialize fuel moisture state for a set of points.

        Args:
            n_points: Number of spatial points to track.
            initial_fm: Optional dict with fm1/fm10/fm100/fm1000 arrays.
                If None, initializes to reasonable defaults.
        """
        self.n_points = n_points

        if initial_fm is not None:
            self.state = {k: np.array(v, dtype=np.float64)
                          for k, v in initial_fm.items()}
        else:
            # Default initial values (moderate moisture)
            self.state = {
                "fm1": np.full(n_points, 8.0),
                "fm10": np.full(n_points, 10.0),
                "fm100": np.full(n_points, 12.0),
                "fm1000": np.full(n_points, 15.0),
            }

    def update(self, temp_f, rh, precip_mm=None, time_step_hr=1.0):
        """Advance fuel moisture state by one timestep.

        Args:
            temp_f: Temperature in °F (array of n_points).
            rh: Relative humidity in % (array of n_points).
            precip_mm: Precipitation in mm (array, optional).
            time_step_hr: Duration of this timestep in hours (default 1.0).

        Returns:
            dict with fm1, fm10, fm100, fm1000 arrays (current moisture %).
        """
        emc = equilibrium_moisture_content(temp_f, rh)

        for key, timelag in self.TIMELAGS.items():
            # Exponential approach to equilibrium
            rate = 1.0 - np.exp(-time_step_hr / timelag)
            self.state[key] += rate * (emc - self.state[key])

            # Rain wetting effect (simple addition proportional to precip)
            if precip_mm is not None:
                precip = np.asarray(precip_mm)
                rain_mask = precip > 0
                if rain_mask.any():
                    # Wetting rate depends on timelag class
                    wetting = precip * (1.0 - np.exp(-1.0 / timelag))
                    self.state[key] = np.where(
                        rain_mask,
                        self.state[key] + wetting,
                        self.state[key],
                    )

            # Clamp to physical range
            self.state[key] = np.clip(self.state[key], 1.0, 250.0)

        return {k: v.copy() for k, v in self.state.items()}

    def get_state(self):
        """Return current fuel moisture state (for serialization)."""
        return {k: v.copy() for k, v in self.state.items()}

    def set_state(self, state_dict):
        """Restore fuel moisture state (from deserialization)."""
        for k, v in state_dict.items():
            if k in self.state:
                self.state[k] = np.array(v, dtype=np.float64)
