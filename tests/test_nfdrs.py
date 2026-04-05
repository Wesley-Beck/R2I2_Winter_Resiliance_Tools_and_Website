"""
Tests for NFDRS (ERC/SC/BI) calculations.

Validates against expected behavior from Argonne's code and the
NFDRS4-TechDoc reference implementation.
"""

import numpy as np
import pytest

from aorc_tools.fire_indices.nfdrs import compute_erc_bi, get_fuel_params


class TestFuelParams:
    def test_model_g_exists(self):
        fm = get_fuel_params("G")
        assert fm["sg1d"] == 2000
        assert fm["sg10d"] == 109
        assert fm["mxd"] == 25
        assert fm["depth"] == 1.0

    def test_loading_conversion(self):
        """Loadings should be converted from tons/acre to lbs/ft²."""
        fm = get_fuel_params("G")
        # L1=2.5 tons/acre × 0.046 = 0.115 lbs/ft²
        assert fm["w1"] == pytest.approx(2.5 * 0.046, abs=0.001)

    def test_all_models_valid(self):
        """All 22 fuel models should load without error."""
        from aorc_tools.config import NFDRS_FUEL_MODELS
        for code in NFDRS_FUEL_MODELS:
            fm = get_fuel_params(code)
            assert fm["sg1d"] > 0
            assert fm["depth"] > 0


class TestERCBI:
    def test_model_g_moderate_conditions(self):
        """Model G with moderate fuel moisture should produce reasonable ERC/BI."""
        result = compute_erc_bi(
            fm1=np.array([8.0]),
            fm10=np.array([10.0]),
            fm100=np.array([12.0]),
            fm1000=np.array([15.0]),
            mcherb=np.array([120.0]),
            mcwood=np.array([100.0]),
            ws_mph=np.array([10.0]),
            fuel_model="G",
        )

        assert "ERC" in result
        assert "SC" in result
        assert "BI" in result
        assert result["ERC"][0] > 0
        assert result["BI"][0] > 0
        assert not np.isnan(result["ERC"][0])
        assert not np.isnan(result["BI"][0])

    def test_dry_vs_wet(self):
        """Drier fuel should produce higher ERC."""
        dry = compute_erc_bi(
            fm1=np.array([4.0]), fm10=np.array([5.0]),
            fm100=np.array([6.0]), fm1000=np.array([8.0]),
            mcherb=np.array([50.0]), mcwood=np.array([60.0]),
            ws_mph=np.array([10.0]), fuel_model="G",
        )
        wet = compute_erc_bi(
            fm1=np.array([20.0]), fm10=np.array([25.0]),
            fm100=np.array([30.0]), fm1000=np.array([35.0]),
            mcherb=np.array([200.0]), mcwood=np.array([200.0]),
            ws_mph=np.array([10.0]), fuel_model="G",
        )
        assert dry["ERC"][0] > wet["ERC"][0]

    def test_wind_affects_bi(self):
        """Higher wind should increase BI (via SC)."""
        calm = compute_erc_bi(
            fm1=np.array([8.0]), fm10=np.array([10.0]),
            fm100=np.array([12.0]), fm1000=np.array([15.0]),
            mcherb=np.array([120.0]), mcwood=np.array([100.0]),
            ws_mph=np.array([2.0]), fuel_model="G",
        )
        windy = compute_erc_bi(
            fm1=np.array([8.0]), fm10=np.array([10.0]),
            fm100=np.array([12.0]), fm1000=np.array([15.0]),
            mcherb=np.array([120.0]), mcwood=np.array([100.0]),
            ws_mph=np.array([30.0]), fuel_model="G",
        )
        assert windy["BI"][0] > calm["BI"][0]

    def test_multiple_points(self):
        """Should handle array inputs for multiple points."""
        n = 10
        result = compute_erc_bi(
            fm1=np.full(n, 8.0),
            fm10=np.full(n, 10.0),
            fm100=np.full(n, 12.0),
            fm1000=np.full(n, 15.0),
            mcherb=np.full(n, 120.0),
            mcwood=np.full(n, 100.0),
            ws_mph=np.full(n, 10.0),
            fuel_model="G",
        )
        assert result["ERC"].shape == (n,)
        assert result["BI"].shape == (n,)

    def test_different_fuel_models(self):
        """Different fuel models should produce different ERC values."""
        kwargs = dict(
            fm1=np.array([8.0]), fm10=np.array([10.0]),
            fm100=np.array([12.0]), fm1000=np.array([15.0]),
            mcherb=np.array([120.0]), mcwood=np.array([100.0]),
            ws_mph=np.array([10.0]),
        )
        erc_g = compute_erc_bi(**kwargs, fuel_model="G")["ERC"][0]
        erc_a = compute_erc_bi(**kwargs, fuel_model="A")["ERC"][0]
        assert erc_g != erc_a
