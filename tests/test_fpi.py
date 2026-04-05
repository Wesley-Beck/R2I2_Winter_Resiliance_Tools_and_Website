"""
Tests for the Fire Potential Index (FPI) — Burgan 1998.

Validates the Argonne-ported FPI calculation against expected behavior.
"""

import numpy as np
import pytest

from aorc_tools.fire_indices.fpi import compute_fpi


class TestFPI:
    def test_basic_calculation(self):
        """FPI should produce values in [0, 100] range."""
        result = compute_fpi(
            nd0=np.array([0.6]),         # Current NDVI
            nd_min=np.array([0.1]),      # Historical min
            nd_max=np.array([0.8]),      # Historical max
            llfm=np.array([5.0]),        # Live fuel moisture loading
            dlfm=np.array([3.0]),        # Dead fuel moisture loading
            mxd=np.array([25.0]),        # Moisture of extinction
            tmax_f=np.array([85.0]),     # Max temp °F
            rh_min=np.array([25.0]),     # Min RH %
        )

        assert 0 <= result["FPI"][0] <= 100
        assert 0 <= result["RG"][0] <= 1
        assert result["FM10"][0] > 0

    def test_relative_greenness(self):
        """RG should scale linearly between NDVI min and max."""
        result = compute_fpi(
            nd0=np.array([0.5]),
            nd_min=np.array([0.2]),
            nd_max=np.array([0.8]),
            llfm=np.array([5.0]),
            dlfm=np.array([3.0]),
            mxd=np.array([25.0]),
            tmax_f=np.array([80.0]),
            rh_min=np.array([30.0]),
        )
        # RG = (0.5 - 0.2) / (0.8 - 0.2) = 0.5
        assert result["RG"][0] == pytest.approx(0.5, abs=0.01)

    def test_dry_hot_high_fire_potential(self):
        """Hot, dry conditions with low greenness → high FPI."""
        dry_hot = compute_fpi(
            nd0=np.array([0.15]),        # Low NDVI (brown)
            nd_min=np.array([0.1]),
            nd_max=np.array([0.8]),
            llfm=np.array([5.0]),
            dlfm=np.array([3.0]),
            mxd=np.array([25.0]),
            tmax_f=np.array([100.0]),    # Very hot
            rh_min=np.array([10.0]),     # Very dry
        )
        cool_wet = compute_fpi(
            nd0=np.array([0.7]),         # High NDVI (green)
            nd_min=np.array([0.1]),
            nd_max=np.array([0.8]),
            llfm=np.array([5.0]),
            dlfm=np.array([3.0]),
            mxd=np.array([25.0]),
            tmax_f=np.array([60.0]),     # Cool
            rh_min=np.array([70.0]),     # Humid
        )
        assert dry_hot["FPI"][0] > cool_wet["FPI"][0]

    def test_multiple_points(self):
        n = 5
        result = compute_fpi(
            nd0=np.linspace(0.2, 0.7, n),
            nd_min=np.full(n, 0.1),
            nd_max=np.full(n, 0.8),
            llfm=np.full(n, 5.0),
            dlfm=np.full(n, 3.0),
            mxd=np.full(n, 25.0),
            tmax_f=np.full(n, 80.0),
            rh_min=np.full(n, 30.0),
        )
        assert result["FPI"].shape == (n,)
        assert np.all(result["FPI"] >= 0)
        assert np.all(result["FPI"] <= 100)
