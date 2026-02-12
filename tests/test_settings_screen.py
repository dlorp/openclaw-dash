"""Tests for the settings screen with Models tab."""

import pytest

from openclaw_dash.screens.settings_screen import (
    PortNumber,
    PositiveInteger,
    SettingsScreen,
)
from openclaw_dash.services.model_discovery import (
    DiscoveryResult,
    ModelInfo,
    ModelTier,
)


class TestValidators:
    """Test validators used in settings screen."""

    def test_positive_integer_valid(self):
        """Test PositiveInteger validator with valid input."""
        validator = PositiveInteger()
        result = validator.validate("42")
        assert result.is_valid

    def test_positive_integer_empty(self):
        """Test PositiveInteger validator with empty input."""
        validator = PositiveInteger()
        result = validator.validate("")
        assert result.is_valid

    def test_positive_integer_zero(self):
        """Test PositiveInteger validator with zero."""
        validator = PositiveInteger()
        result = validator.validate("0")
        assert not result.is_valid

    def test_positive_integer_negative(self):
        """Test PositiveInteger validator with negative number."""
        validator = PositiveInteger()
        result = validator.validate("-5")
        assert not result.is_valid

    def test_positive_integer_non_number(self):
        """Test PositiveInteger validator with non-numeric input."""
        validator = PositiveInteger()
        result = validator.validate("abc")
        assert not result.is_valid

    def test_port_number_valid(self):
        """Test PortNumber validator with valid port."""
        validator = PortNumber()
        result = validator.validate("8080")
        assert result.is_valid

    def test_port_number_min(self):
        """Test PortNumber validator with minimum port."""
        validator = PortNumber()
        result = validator.validate("1")
        assert result.is_valid

    def test_port_number_max(self):
        """Test PortNumber validator with maximum port."""
        validator = PortNumber()
        result = validator.validate("65535")
        assert result.is_valid

    def test_port_number_zero(self):
        """Test PortNumber validator with zero."""
        validator = PortNumber()
        result = validator.validate("0")
        assert not result.is_valid

    def test_port_number_too_high(self):
        """Test PortNumber validator with port above max."""
        validator = PortNumber()
        result = validator.validate("65536")
        assert not result.is_valid

    def test_port_number_empty(self):
        """Test PortNumber validator with empty input."""
        validator = PortNumber()
        result = validator.validate("")
        assert result.is_valid


class TestSettingsScreen:
    """Test SettingsScreen functionality."""

    @pytest.fixture
    def mock_discovery_result(self):
        """Create a mock DiscoveryResult for testing."""
        models = [
            ModelInfo(
                name="Qwen2.5 Coder 7B",
                provider="ollama",
                family="qwen",
                size_billions=7.0,
                quantization="q4_k_m",
                tier=ModelTier.FAST,
                is_instruct=True,
                is_coder=True,
                is_reasoning=False,
            ),
            ModelInfo(
                name="Llama3 14B",
                provider="ollama",
                family="llama",
                size_billions=14.0,
                quantization="q4_k_m",
                tier=ModelTier.BALANCED,
                is_instruct=True,
                is_coder=False,
                is_reasoning=False,
            ),
            ModelInfo(
                name="DeepSeek R1 70B",
                provider="ollama",
                family="deepseek",
                size_billions=70.0,
                quantization="q4_k_m",
                tier=ModelTier.POWERFUL,
                is_instruct=True,
                is_coder=False,
                is_reasoning=True,
            ),
        ]
        result = DiscoveryResult(
            models=models,
            gateway_connected=False,
        )
        return result

    def test_settings_screen_has_models_tab_binding(self):
        """Test that settings screen has binding for models tab."""
        screen = SettingsScreen()
        bindings = {b.key: b.action for b in screen.BINDINGS}
        assert "5" in bindings
        assert bindings["5"] == "tab_models"

    def test_settings_screen_has_all_tab_bindings(self):
        """Test that settings screen has all tab bindings."""
        screen = SettingsScreen()
        bindings = {b.key: b.action for b in screen.BINDINGS}
        assert bindings.get("1") == "tab_general"
        assert bindings.get("2") == "tab_tools"
        assert bindings.get("3") == "tab_appearance"
        assert bindings.get("4") == "tab_keybinds"
        assert bindings.get("5") == "tab_models"

    def test_discovery_result_by_tier(self, mock_discovery_result):
        """Test DiscoveryResult.by_tier property."""
        by_tier = mock_discovery_result.by_tier
        assert len(by_tier[ModelTier.FAST]) == 1
        assert len(by_tier[ModelTier.BALANCED]) == 1
        assert len(by_tier[ModelTier.POWERFUL]) == 1

    def test_model_info_display_name(self):
        """Test ModelInfo.display_name property."""
        model = ModelInfo(
            name="Test Model",
            provider="ollama",
            family="qwen",
            size_billions=14.0,
            quantization="q4_k_m",
            tier=ModelTier.BALANCED,
            version="2.5",
            variant="coder",
        )
        # display_name uses family + variant when both present
        assert "Qwen" in model.display_name
        assert "Coder" in model.display_name

    def test_model_info_tier_emoji(self):
        """Test ModelInfo.tier_emoji property."""
        fast_model = ModelInfo(
            name="Fast",
            provider="ollama",
            family="test",
            size_billions=7.0,
            quantization="q4_k_m",
            tier=ModelTier.FAST,
        )
        balanced_model = ModelInfo(
            name="Balanced",
            provider="ollama",
            family="test",
            size_billions=14.0,
            quantization="q4_k_m",
            tier=ModelTier.BALANCED,
        )
        powerful_model = ModelInfo(
            name="Powerful",
            provider="ollama",
            family="test",
            size_billions=70.0,
            quantization="q4_k_m",
            tier=ModelTier.POWERFUL,
        )

        assert fast_model.tier_emoji == "▸"
        assert balanced_model.tier_emoji == "◉"
        assert powerful_model.tier_emoji == "★"


class TestModelTier:
    """Test ModelTier enum."""

    def test_model_tier_values(self):
        """Test ModelTier enum values."""
        assert ModelTier.FAST.value == "fast"
        assert ModelTier.BALANCED.value == "balanced"
        assert ModelTier.POWERFUL.value == "powerful"

    def test_model_tier_is_string_enum(self):
        """Test that ModelTier is a string enum."""
        assert isinstance(ModelTier.FAST, str)
        assert ModelTier.FAST == "fast"


class TestCustomPaths:
    """Test custom paths functionality."""

    def test_custom_paths_parsing_from_comma_separated_string(self):
        """Test parsing custom paths from comma-separated string."""
        custom_paths_str = "/path/to/models1,/path/to/models2,/path/to/models3"
        custom_paths = [p.strip() for p in custom_paths_str.split(",") if p.strip()]

        assert len(custom_paths) == 3
        assert custom_paths[0] == "/path/to/models1"
        assert custom_paths[1] == "/path/to/models2"
        assert custom_paths[2] == "/path/to/models3"

    def test_custom_paths_parsing_with_spaces(self):
        """Test parsing custom paths with extra spaces."""
        custom_paths_str = " /path/to/models1 , /path/to/models2 , /path/to/models3 "
        custom_paths = [p.strip() for p in custom_paths_str.split(",") if p.strip()]

        assert len(custom_paths) == 3
        assert custom_paths[0] == "/path/to/models1"
        assert custom_paths[1] == "/path/to/models2"
        assert custom_paths[2] == "/path/to/models3"

    def test_empty_custom_paths_handling(self):
        """Test handling of empty custom paths string."""
        custom_paths_str = ""
        custom_paths = [p.strip() for p in custom_paths_str.split(",") if p.strip()]

        assert len(custom_paths) == 0

    def test_custom_paths_with_empty_entries(self):
        """Test handling of empty entries in comma-separated string."""
        custom_paths_str = "/path/to/models1,,/path/to/models2,,"
        custom_paths = [p.strip() for p in custom_paths_str.split(",") if p.strip()]

        assert len(custom_paths) == 2
        assert custom_paths[0] == "/path/to/models1"
        assert custom_paths[1] == "/path/to/models2"

    def test_settings_persistence_round_trip(self):
        """Test that custom paths can be saved and loaded."""
        from pathlib import Path
        from tempfile import TemporaryDirectory

        from openclaw_dash.settings_manager import SettingsManager

        with TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.toml"
            settings = SettingsManager(config_path)

            # Set custom paths
            test_paths = ["/models/llama", "/models/mistral", "/models/qwen"]
            settings.set("models.custom_paths", ",".join(test_paths))
            settings.save()

            # Load in new instance
            settings2 = SettingsManager(config_path)
            loaded_value = settings2.get("models.custom_paths")

            # Parse the loaded value (it's stored as comma-separated string)
            if isinstance(loaded_value, str):
                loaded_paths = [p.strip() for p in loaded_value.split(",") if p.strip()]
            else:
                loaded_paths = loaded_value or []

            assert len(loaded_paths) == 3
            assert loaded_paths == test_paths
