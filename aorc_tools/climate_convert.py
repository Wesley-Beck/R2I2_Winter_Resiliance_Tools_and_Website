"""
Unit conversion functions for AORC climate data.

All functions accept and return numpy arrays or scalars.
Each function documents input/output units.

The RH calculation uses the existing Magnus formula approach from
aorc_data_loader.py, cleaned up to avoid double-conversion.
"""

import numpy as np


def kelvin_to_celsius(t_k):
    """Convert temperature from Kelvin to Celsius.

    Args:
        t_k: Temperature in Kelvin (scalar or array).

    Returns:
        Temperature in °C.
    """
    return t_k - 273.15


def celsius_to_fahrenheit(t_c):
    """Convert temperature from Celsius to Fahrenheit.

    Args:
        t_c: Temperature in °C (scalar or array).

    Returns:
        Temperature in °F.
    """
    return t_c * 9.0 / 5.0 + 32.0


def kelvin_to_fahrenheit(t_k):
    """Convert temperature from Kelvin to Fahrenheit.

    Args:
        t_k: Temperature in Kelvin (scalar or array).

    Returns:
        Temperature in °F.
    """
    return celsius_to_fahrenheit(kelvin_to_celsius(t_k))


def wind_components_to_speed(u, v):
    """Compute wind speed from U and V components.

    Args:
        u: U-component of wind (m/s).
        v: V-component of wind (m/s).

    Returns:
        Wind speed in m/s.
    """
    return np.sqrt(u ** 2 + v ** 2)


def ms_to_kph(ws_ms):
    """Convert wind speed from m/s to km/h.

    Args:
        ws_ms: Wind speed in m/s.

    Returns:
        Wind speed in km/h.
    """
    return ws_ms * 3.6


def ms_to_mph(ws_ms):
    """Convert wind speed from m/s to mph.

    Args:
        ws_ms: Wind speed in m/s.

    Returns:
        Wind speed in mph.
    """
    return ws_ms * 2.23694


def specific_to_relative_humidity(q, t_k, p_pa):
    """Convert specific humidity to relative humidity.

    Uses the Magnus formula for saturation vapor pressure, ported from
    the existing calculate_relative_humidity() in aorc_data_loader.py
    but without the double-conversion issue.

    Args:
        q: Specific humidity in kg/kg (dimensionless mass ratio).
           AORC SPFH_2maboveground is stored in kg/kg.
        t_k: Temperature in Kelvin.
        p_pa: Surface pressure in Pascals.

    Returns:
        Relative humidity in % [0, 100].
    """
    t_c = kelvin_to_celsius(t_k)

    # Saturation vapor pressure (hPa) via Magnus formula
    es = 6.112 * np.exp(17.67 * t_c / (t_c + 243.5))

    # Mixing ratio from specific humidity
    w = q / (1.0 - q)

    # Actual vapor pressure (hPa)
    p_hpa = p_pa / 100.0
    e = w * p_hpa / (0.622 + w)

    # Relative humidity (%)
    rh = 100.0 * e / es

    return np.clip(rh, 0.0, 100.0)


def equilibrium_moisture_content(t_f, rh):
    """Compute Equilibrium Moisture Content (EMC) using Simard 1968 equations.

    This is the EMC calculation used by both the existing calculate_fpi()
    (now correctly identified as part of the FPI chain) and by Argonne's
    FPI code. Three piecewise ranges based on RH.

    Args:
        t_f: Temperature in °F (scalar or array).
        rh: Relative humidity in % (scalar or array).

    Returns:
        EMC as fraction (e.g., 0.08 = 8% moisture content).
    """
    rh = np.asarray(rh, dtype=np.float64)
    t_f = np.asarray(t_f, dtype=np.float64)

    emc = np.zeros_like(rh)

    # Range 1: RH < 10%
    mask1 = rh < 10
    emc[mask1] = (0.03229 + 0.281073 * rh[mask1]
                  - 0.000578 * t_f[mask1] * rh[mask1])

    # Range 2: 10% ≤ RH < 50%
    mask2 = (rh >= 10) & (rh < 50)
    emc[mask2] = (2.22749 + 0.160107 * rh[mask2]
                  - 0.014784 * t_f[mask2])

    # Range 3: RH ≥ 50%
    mask3 = rh >= 50
    emc[mask3] = (21.0606 + 0.005565 * rh[mask3] ** 2
                  - 0.00035 * rh[mask3] * t_f[mask3]
                  - 0.483199 * rh[mask3])

    emc = np.maximum(emc, 0.0)
    return emc
