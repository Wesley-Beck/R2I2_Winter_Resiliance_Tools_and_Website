"""Tests for the multi-model climate projection system.

Tests:
- ClimateModelAdapter interface and factory
- NexGddpCmip6Adapter initialization and validation
- GLARMAdapter initialization
- ProjectionMirror local caching
- CLIMATE_MODEL_REGISTRY completeness
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest


# ==================================================================
# Climate Model Adapter Tests
# ==================================================================

class TestClimateModelRegistry:
    def test_registry_has_all_sources(self):
        from aorc_tools.climate_model_adapter import CLIMATE_MODEL_REGISTRY
        assert "aorc" in CLIMATE_MODEL_REGISTRY
        assert "nex-gddp-cmip6" in CLIMATE_MODEL_REGISTRY
        assert "glarm" in CLIMATE_MODEL_REGISTRY
        assert "climrr" in CLIMATE_MODEL_REGISTRY

    def test_registry_entries_have_required_fields(self):
        from aorc_tools.climate_model_adapter import CLIMATE_MODEL_REGISTRY
        required = {"name", "type", "period", "resolution", "variables", "source"}
        for key, entry in CLIMATE_MODEL_REGISTRY.items():
            missing = required - set(entry.keys())
            assert not missing, f"Registry entry '{key}' missing: {missing}"

    def test_list_models(self):
        from aorc_tools.climate_model_adapter import list_models
        models = list_models()
        assert isinstance(models, dict)
        assert len(models) >= 4


class TestGetAdapter:
    def test_nex_gddp_adapter(self):
        from aorc_tools.climate_model_adapter import get_adapter
        adapter = get_adapter("nex-gddp-cmip6", gcm="MIROC6", scenario="ssp245")
        assert "MIROC6" in adapter.name
        assert "ssp245" in adapter.name

    def test_nex_gddp_invalid_gcm(self):
        from aorc_tools.climate_model_adapter import get_adapter
        with pytest.raises(ValueError, match="Unknown GCM"):
            get_adapter("nex-gddp-cmip6", gcm="FAKE-MODEL", scenario="ssp585")

    def test_nex_gddp_invalid_scenario(self):
        from aorc_tools.climate_model_adapter import get_adapter
        with pytest.raises(ValueError, match="Unknown scenario"):
            get_adapter("nex-gddp-cmip6", gcm="ACCESS-CM2", scenario="rcp85")

    def test_glarm_adapter(self):
        from aorc_tools.climate_model_adapter import get_adapter
        with tempfile.TemporaryDirectory() as td:
            adapter = get_adapter("glarm", data_path=td, scenario="rcp45")
            assert "rcp45" in adapter.name.lower()

    def test_unknown_source_raises(self):
        from aorc_tools.climate_model_adapter import get_adapter
        with pytest.raises(ValueError, match="Unknown data source"):
            get_adapter("nonexistent-model")

    def test_config_file_adapter(self):
        from aorc_tools.climate_model_adapter import get_adapter
        with tempfile.TemporaryDirectory() as td:
            config = {"type": "nex-gddp-cmip6", "gcm": "EC-Earth3", "scenario": "ssp585"}
            config_path = Path(td) / "config.json"
            with open(config_path, "w") as f:
                json.dump(config, f)
            adapter = get_adapter(str(config_path))
            assert "EC-Earth3" in adapter.name


class TestNexGddpCmip6Adapter:
    def test_properties(self):
        from aorc_tools.climate_model_adapter import NexGddpCmip6Adapter
        adapter = NexGddpCmip6Adapter(gcm="GFDL-ESM4", scenario="ssp245")
        assert adapter.name == "NEX-GDDP-CMIP6 GFDL-ESM4 (ssp245)"

    def test_time_range_historical(self):
        from aorc_tools.climate_model_adapter import NexGddpCmip6Adapter
        adapter = NexGddpCmip6Adapter(gcm="ACCESS-CM2", scenario="historical")
        start, end = adapter.get_time_range()
        assert start == 1950
        assert end == 2014

    def test_time_range_ssp(self):
        from aorc_tools.climate_model_adapter import NexGddpCmip6Adapter
        adapter = NexGddpCmip6Adapter(gcm="ACCESS-CM2", scenario="ssp585")
        start, end = adapter.get_time_range()
        assert start == 2015
        assert end == 2100

    def test_available_variables(self):
        from aorc_tools.climate_model_adapter import NexGddpCmip6Adapter, REQUIRED_VARIABLES
        adapter = NexGddpCmip6Adapter()
        vars = adapter.get_available_variables()
        for v in REQUIRED_VARIABLES:
            assert v in vars

    def test_no_missing_variables(self):
        from aorc_tools.climate_model_adapter import NexGddpCmip6Adapter
        adapter = NexGddpCmip6Adapter()
        assert adapter.get_missing_variables() == []

    def test_info(self):
        from aorc_tools.climate_model_adapter import NexGddpCmip6Adapter
        adapter = NexGddpCmip6Adapter()
        info = adapter.info()
        assert info["ready"] is True
        assert info["start_year"] == 2015
        assert info["end_year"] == 2100

    def test_coordinates(self):
        from aorc_tools.climate_model_adapter import NexGddpCmip6Adapter
        adapter = NexGddpCmip6Adapter()
        lats, lons = adapter.get_coordinates()
        assert len(lats) > 0
        assert len(lons) > 0
        assert lats[0] < lats[-1]  # sorted ascending

    def test_all_27_gcms_available(self):
        from aorc_tools.climate_model_adapter import NEX_GDDP_GCMS
        assert len(NEX_GDDP_GCMS) == 27
        assert "ACCESS-CM2" in NEX_GDDP_GCMS
        assert "UKESM1-0-LL" in NEX_GDDP_GCMS


class TestClimRRAdapter:
    def test_init(self):
        from aorc_tools.climate_model_adapter import ClimRRAdapter
        adapter = ClimRRAdapter(scenario="ssp245", period="midcentury")
        assert "SSP245" in adapter.name
        assert "midcentury" in adapter.name

    def test_invalid_period(self):
        from aorc_tools.climate_model_adapter import ClimRRAdapter
        with pytest.raises(ValueError, match="Unknown period"):
            ClimRRAdapter(period="farfuture")

    def test_time_range(self):
        from aorc_tools.climate_model_adapter import ClimRRAdapter
        adapter = ClimRRAdapter(period="midcentury")
        start, end = adapter.get_time_range()
        assert start == 2045
        assert end == 2064

    def test_time_range_historical(self):
        from aorc_tools.climate_model_adapter import ClimRRAdapter
        adapter = ClimRRAdapter(period="historical")
        start, end = adapter.get_time_range()
        assert start == 1995
        assert end == 2014

    def test_available_variables(self):
        from aorc_tools.climate_model_adapter import ClimRRAdapter, REQUIRED_VARIABLES
        adapter = ClimRRAdapter()
        vars = adapter.get_available_variables()
        for v in REQUIRED_VARIABLES:
            assert v in vars

    def test_no_missing_variables(self):
        from aorc_tools.climate_model_adapter import ClimRRAdapter
        adapter = ClimRRAdapter()
        assert adapter.get_missing_variables() == []

    def test_daily_point_values_structure(self):
        from aorc_tools.climate_model_adapter import ClimRRAdapter
        adapter = ClimRRAdapter(period="midcentury")
        # With no data source, should return NaN-filled arrays
        result = adapter.get_daily_point_values(
            2050, 7, 15,
            np.array([50, 51, 52]),
            np.array([100, 101, 102]),
            (46.0, 47.0), (-90.0, -88.0),
        )
        assert "hours" in result
        assert "timestamps" in result
        assert len(result["hours"]) == 24
        assert result["TMP_2maboveground"].shape == (24, 3)
        assert result["PRES_surface"].shape == (24, 3)

    def test_info(self):
        from aorc_tools.climate_model_adapter import ClimRRAdapter
        adapter = ClimRRAdapter(scenario="ssp585", period="endcentury")
        info = adapter.info()
        assert info["ready"] is True
        assert info["scenario"] == "ssp585"
        assert info["period"] == "endcentury"
        assert info["period_years"] == (2075, 2094)

    def test_factory_climrr(self):
        from aorc_tools.climate_model_adapter import get_adapter
        adapter = get_adapter("climrr", scenario="ssp245", period="midcentury")
        assert "ClimRR" in adapter.name

    def test_factory_argonne_alias(self):
        from aorc_tools.climate_model_adapter import get_adapter
        adapter = get_adapter("argonne", scenario="ssp585")
        assert "ClimRR" in adapter.name

    def test_local_data_path(self):
        from aorc_tools.climate_model_adapter import ClimRRAdapter
        with tempfile.TemporaryDirectory() as td:
            adapter = ClimRRAdapter(data_path=td)
            info = adapter.info()
            assert info["data_source"] == "local"

    def test_no_data_path(self):
        from aorc_tools.climate_model_adapter import ClimRRAdapter
        adapter = ClimRRAdapter()
        info = adapter.info()
        assert info["data_source"] == "ArcGIS Feature Service"


class TestGLARMAdapter:
    def test_init(self):
        from aorc_tools.climate_model_adapter import GLARMAdapter
        with tempfile.TemporaryDirectory() as td:
            adapter = GLARMAdapter(td, scenario="rcp45")
            assert "RCP45" in adapter.name

    def test_time_range(self):
        from aorc_tools.climate_model_adapter import GLARMAdapter
        with tempfile.TemporaryDirectory() as td:
            adapter = GLARMAdapter(td)
            start, end = adapter.get_time_range()
            assert start == 1981
            assert end == 2099

    def test_variable_map(self):
        from aorc_tools.climate_model_adapter import GLARMAdapter
        with tempfile.TemporaryDirectory() as td:
            adapter = GLARMAdapter(td)
            assert "T2" in adapter.variable_map
            assert adapter.variable_map["T2"] == "TMP_2maboveground"


# ==================================================================
# ProjectionMirror Tests
# ==================================================================

class TestProjectionMirror:
    @pytest.fixture
    def mock_adapter(self):
        adapter = MagicMock()
        adapter.name = "TestAdapter"
        adapter.get_daily_point_values.return_value = {
            "hours": list(range(24)),
            "timestamps": [f"2050-07-01 {h:02d}:00" for h in range(24)],
            "TMP_2maboveground": np.random.rand(24, 5).astype(np.float32),
            "APCP_surface": np.random.rand(24, 5).astype(np.float32),
        }
        return adapter

    @pytest.fixture
    def mock_points_df(self):
        import pandas as pd
        return pd.DataFrame({
            "point_id": [f"P{i}" for i in range(5)],
            "latitude": [46.5, 46.6, 46.7, 46.8, 46.9],
            "longitude": [-89.0, -89.1, -89.2, -89.3, -89.4],
            "lat_idx": [100, 101, 102, 103, 104],
            "lon_idx": [200, 201, 202, 203, 204],
        })

    def test_init(self, mock_adapter, mock_points_df):
        from aorc_tools.projection_mirror import ProjectionMirror
        with tempfile.TemporaryDirectory() as td:
            mirror = ProjectionMirror(td, "test/source", mock_adapter, mock_points_df)
            assert mirror.n_points == 5
            assert not mirror.is_downloaded(2050, 7)

    def test_manifest_roundtrip(self, mock_adapter, mock_points_df):
        from aorc_tools.projection_mirror import ProjectionMirror
        with tempfile.TemporaryDirectory() as td:
            mirror = ProjectionMirror(td, "test/source", mock_adapter, mock_points_df)
            mirror._save_manifest()

            # Reload
            mirror2 = ProjectionMirror(td, "test/source", mock_adapter, mock_points_df)
            assert mirror2._manifest["source"] == "test/source"
            assert mirror2._manifest["n_points"] == 5

    def test_download_month(self, mock_adapter, mock_points_df):
        from aorc_tools.projection_mirror import ProjectionMirror
        with tempfile.TemporaryDirectory() as td:
            mirror = ProjectionMirror(td, "test/source", mock_adapter, mock_points_df)
            path = mirror.download_month(2050, 7)

            assert path is not None
            assert path.exists()
            assert mirror.is_downloaded(2050, 7)

            # Verify npz contents
            data = np.load(path, allow_pickle=True)
            assert "timestamps" in data.files
            assert "TMP_2maboveground" in data.files

    def test_download_month_skip_existing(self, mock_adapter, mock_points_df):
        from aorc_tools.projection_mirror import ProjectionMirror
        with tempfile.TemporaryDirectory() as td:
            mirror = ProjectionMirror(td, "test/source", mock_adapter, mock_points_df)
            mirror.download_month(2050, 7)
            assert mock_adapter.get_daily_point_values.call_count == 31  # July has 31 days

            # Second call should skip
            mock_adapter.get_daily_point_values.reset_mock()
            mirror.download_month(2050, 7)
            assert mock_adapter.get_daily_point_values.call_count == 0

    def test_download_month_force(self, mock_adapter, mock_points_df):
        from aorc_tools.projection_mirror import ProjectionMirror
        with tempfile.TemporaryDirectory() as td:
            mirror = ProjectionMirror(td, "test/source", mock_adapter, mock_points_df)
            mirror.download_month(2050, 7)
            mock_adapter.get_daily_point_values.reset_mock()

            mirror.download_month(2050, 7, force=True)
            assert mock_adapter.get_daily_point_values.call_count == 31

    def test_load_month(self, mock_adapter, mock_points_df):
        from aorc_tools.projection_mirror import ProjectionMirror
        with tempfile.TemporaryDirectory() as td:
            mirror = ProjectionMirror(td, "test/source", mock_adapter, mock_points_df)
            mirror.download_month(2050, 7)

            result = mirror.load_month(2050, 7)
            assert isinstance(result, dict)
            # Should have day entries
            assert len(result) > 0

    def test_status(self, mock_adapter, mock_points_df):
        from aorc_tools.projection_mirror import ProjectionMirror
        with tempfile.TemporaryDirectory() as td:
            mirror = ProjectionMirror(td, "test/source", mock_adapter, mock_points_df)
            mirror.download_month(2050, 7)

            status = mirror.status()
            assert status["months_downloaded"] == 1
            assert status["n_points"] == 5
            assert 2050 in status["years_covered"]

    def test_download_range(self, mock_adapter, mock_points_df):
        from aorc_tools.projection_mirror import ProjectionMirror
        with tempfile.TemporaryDirectory() as td:
            mirror = ProjectionMirror(td, "test/source", mock_adapter, mock_points_df)
            count = mirror.download_range(2050, 2050, start_month=6, end_month=7)
            assert count == 2
            assert mirror.is_downloaded(2050, 6)
            assert mirror.is_downloaded(2050, 7)

    def test_is_month_available(self, mock_adapter, mock_points_df):
        from aorc_tools.projection_mirror import ProjectionMirror
        with tempfile.TemporaryDirectory() as td:
            mirror = ProjectionMirror(td, "test/source", mock_adapter, mock_points_df)
            assert not mirror.is_month_available(2050, 7)
            mirror.download_month(2050, 7)
            assert mirror.is_month_available(2050, 7)
