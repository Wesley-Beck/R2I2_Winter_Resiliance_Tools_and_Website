"""
Unit tests for climate_convert.py — known-value checks.

Each test verifies conversions against hand-calculated or reference values.
"""

import numpy as np
import pytest

from aorc_tools.climate_convert import (
    kelvin_to_celsius,
    celsius_to_fahrenheit,
    kelvin_to_fahrenheit,
    wind_components_to_speed,
    ms_to_kph,
    ms_to_mph,
    specific_to_relative_humidity,
    equilibrium_moisture_content,
)


class TestTemperature:
    def test_kelvin_to_celsius_freezing(self):
        assert kelvin_to_celsius(273.15) == pytest.approx(0.0, abs=1e-10)

    def test_kelvin_to_celsius_boiling(self):
        assert kelvin_to_celsius(373.15) == pytest.approx(100.0, abs=1e-10)

    def test_celsius_to_fahrenheit_freezing(self):
        assert celsius_to_fahrenheit(0.0) == pytest.approx(32.0, abs=1e-10)

    def test_celsius_to_fahrenheit_boiling(self):
        assert celsius_to_fahrenheit(100.0) == pytest.approx(212.0, abs=1e-10)

    def test_kelvin_to_fahrenheit(self):
        assert kelvin_to_fahrenheit(293.15) == pytest.approx(68.0, abs=0.1)

    def test_array_input(self):
        t_k = np.array([273.15, 283.15, 293.15])
        t_c = kelvin_to_celsius(t_k)
        np.testing.assert_allclose(t_c, [0.0, 10.0, 20.0])


class TestWind:
    def test_vector_magnitude(self):
        assert wind_components_to_speed(3.0, 4.0) == pytest.approx(5.0)

    def test_ms_to_kph(self):
        assert ms_to_kph(1.0) == pytest.approx(3.6)

    def test_ms_to_mph(self):
        assert ms_to_mph(1.0) == pytest.approx(2.23694, abs=1e-4)

    def test_wind_array(self):
        u = np.array([3.0, 0.0])
        v = np.array([4.0, 5.0])
        ws = wind_components_to_speed(u, v)
        np.testing.assert_allclose(ws, [5.0, 5.0])


class TestRelativeHumidity:
    def test_standard_conditions(self):
        """At 20°C, 101325 Pa, q=0.008 kg/kg → RH ≈ 54%."""
        rh = specific_to_relative_humidity(0.008, 293.15, 101325.0)
        assert 50.0 < rh < 60.0  # Approximate check

    def test_saturated(self):
        """Very high specific humidity → RH should be clipped to 100."""
        rh = specific_to_relative_humidity(0.05, 293.15, 101325.0)
        assert rh == 100.0

    def test_dry(self):
        """Very low specific humidity → RH near 0."""
        rh = specific_to_relative_humidity(0.0001, 293.15, 101325.0)
        assert rh < 5.0

    def test_array(self):
        q = np.array([0.004, 0.008, 0.012])
        rh = specific_to_relative_humidity(q, 293.15, 101325.0)
        assert rh.shape == (3,)
        assert np.all(rh >= 0) and np.all(rh <= 100)


class TestEMC:
    def test_low_rh(self):
        """RH < 10%: EMC should be very low."""
        emc = equilibrium_moisture_content(80.0, 5.0)
        assert 0 < emc < 5.0

    def test_mid_rh(self):
        """10% ≤ RH < 50%: EMC in moderate range."""
        emc = equilibrium_moisture_content(70.0, 30.0)
        assert 3.0 < emc < 15.0

    def test_high_rh(self):
        """RH ≥ 50%: EMC higher."""
        emc = equilibrium_moisture_content(70.0, 80.0)
        assert 5.0 < emc < 30.0

    def test_array(self):
        t = np.array([70.0, 80.0, 90.0])
        rh = np.array([20.0, 50.0, 80.0])
        emc = equilibrium_moisture_content(t, rh)
        assert emc.shape == (3,)
        assert np.all(emc >= 0)
