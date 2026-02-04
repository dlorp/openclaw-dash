"""Tests for the settings screen with Models tab."""

from pathlib import Path

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
                family="qwen",
                path=Path("/models/qwen2.5-coder-7b-q4_k_m.gguf"),
                size_billions=7.0,
                quantization="q4_k_m",
                tier=ModelTier.FAST,
                is_instruct=True,
                is_coder=True,
                is_reasoning=False,
                source="huggingface",
                file_size_gb=4.2,
            ),
            ModelInfo(
                name="Llama3 14B",
                family="llama",
                path=Path("/models/llama3-14b-q4_k_m.gguf"),
                size_billions=14.0,
                quantization="q4_k_m",
                tier=ModelTier.BALANCED,
                is_instruct=True,
                is_coder=False,
                is_reasoning=False,
                source="huggingface",
                file_size_gb=8.1,
            ),
            ModelInfo(
                name="DeepSeek R1 70B",
                family="deepseek",
                path=Path("/models/deepseek-r1-70b-q4_k_m.gguf"),
                size_billions=70.0,
                quantization="q4_k_m",
                tier=ModelTier.POWERFUL,
                is_instruct=True,
                is_coder=False,
                is_reasoning=True,
                source="custom",
                file_size_gb=40.5,
            ),
        ]
        result = DiscoveryResult(
            models=models,
            scan_paths=[Path.home() / ".cache" / "huggingface" / "hub"],
            ollama_running=False,
            llamacpp_running=False,
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

    def test_discovery_result_total_size(self, mock_discovery_result):
        """Test DiscoveryResult.total_size_gb property."""
        total = mock_discovery_result.total_size_gb
        assert total == pytest.approx(4.2 + 8.1 + 40.5, rel=0.01)

    def test_model_info_display_name(self):
        """Test ModelInfo.display_name property."""
        model = ModelInfo(
            name="Test Model",
            family="qwen",
            path=Path("/test.gguf"),
            size_billions=14.0,
            quantization="q4_k_m",
            tier=ModelTier.BALANCED,
            version="2.5",
            variant="coder",
        )
        assert "Qwen2.5" in model.display_name
        assert "CODER" in model.display_name
        assert "14B" in model.display_name

    def test_model_info_tier_emoji(self):
        """Test ModelInfo.tier_emoji property."""
        fast_model = ModelInfo(
            name="Fast",
            family="test",
            path=Path("/test.gguf"),
            size_billions=7.0,
            quantization="q4_k_m",
            tier=ModelTier.FAST,
        )
        balanced_model = ModelInfo(
            name="Balanced",
            family="test",
            path=Path("/test.gguf"),
            size_billions=14.0,
            quantization="q4_k_m",
            tier=ModelTier.BALANCED,
        )
        powerful_model = ModelInfo(
            name="Powerful",
            family="test",
            path=Path("/test.gguf"),
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
