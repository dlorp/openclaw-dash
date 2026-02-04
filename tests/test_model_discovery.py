"""Tests for model discovery service."""

from unittest.mock import MagicMock

import pytest

from openclaw_dash.services import (
    DiscoveryResult,
    GatewayClient,
    ModelDiscoveryService,
    ModelInfo,
    ModelTier,
)


class TestModelTier:
    """Tests for ModelTier enum."""

    def test_tier_values(self):
        assert ModelTier.FAST.value == "fast"
        assert ModelTier.BALANCED.value == "balanced"
        assert ModelTier.POWERFUL.value == "powerful"

    def test_tier_is_string(self):
        assert isinstance(ModelTier.FAST, str)
        assert ModelTier.FAST == "fast"


class TestModelInfo:
    """Tests for ModelInfo dataclass."""

    def test_basic_creation(self):
        model = ModelInfo(
            name="anthropic/claude-sonnet-4-20250514",
            family="claude",
            tier=ModelTier.BALANCED,
        )
        assert model.name == "anthropic/claude-sonnet-4-20250514"
        assert model.family == "claude"
        assert model.tier == ModelTier.BALANCED

    def test_defaults(self):
        model = ModelInfo(name="test", family="test", tier=ModelTier.FAST)
        assert model.size_billions is None
        assert model.quantization is None
        assert model.is_instruct is True
        assert model.is_coder is False
        assert model.is_reasoning is False

    def test_tier_emoji(self):
        assert ModelInfo(name="a", family="a", tier=ModelTier.FAST).tier_emoji == "⚡"
        assert ModelInfo(name="a", family="a", tier=ModelTier.BALANCED).tier_emoji == "⚖️"
        assert ModelInfo(name="a", family="a", tier=ModelTier.POWERFUL).tier_emoji == "🧠"

    def test_display_name_with_variant(self):
        model = ModelInfo(
            name="anthropic/claude-sonnet-4",
            family="claude",
            tier=ModelTier.BALANCED,
            variant="sonnet",
        )
        assert model.display_name == "Claude Sonnet"

    def test_display_name_without_variant(self):
        model = ModelInfo(name="openai/gpt-4", family="gpt", tier=ModelTier.POWERFUL)
        assert model.display_name == "Gpt"


class TestDiscoveryResult:
    """Tests for DiscoveryResult dataclass."""

    def test_empty_result(self):
        result = DiscoveryResult()
        assert result.models == []
        assert result.gateway_connected is False

    def test_by_tier_grouping(self):
        result = DiscoveryResult(
            models=[
                ModelInfo(name="fast1", family="a", tier=ModelTier.FAST),
                ModelInfo(name="powerful1", family="b", tier=ModelTier.POWERFUL),
                ModelInfo(name="fast2", family="c", tier=ModelTier.FAST),
                ModelInfo(name="balanced1", family="d", tier=ModelTier.BALANCED),
            ],
            gateway_connected=True,
        )

        by_tier = result.by_tier
        assert len(by_tier[ModelTier.FAST]) == 2
        assert len(by_tier[ModelTier.BALANCED]) == 1
        assert len(by_tier[ModelTier.POWERFUL]) == 1


class TestModelDiscoveryService:
    """Tests for ModelDiscoveryService."""

    @pytest.fixture
    def mock_client(self):
        return MagicMock(spec=GatewayClient)

    def test_init_with_client(self, mock_client):
        service = ModelDiscoveryService(mock_client)
        assert service.client is mock_client
        assert service.fast_threshold == 8.0
        assert service.powerful_threshold == 30.0

    def test_init_custom_thresholds(self, mock_client):
        service = ModelDiscoveryService(mock_client, fast_threshold=4.0, powerful_threshold=20.0)
        assert service.fast_threshold == 4.0
        assert service.powerful_threshold == 20.0

    def test_discover_returns_models(self, mock_client):
        mock_client.get_available_models.return_value = [
            "anthropic/claude-sonnet-4-20250514",
            "openai/gpt-4o",
            "google/gemini-2.0-flash",
        ]

        service = ModelDiscoveryService(mock_client)
        result = service.discover()

        assert result.gateway_connected is True
        assert len(result.models) == 3

    def test_discover_gateway_offline(self, mock_client):
        mock_client.get_available_models.side_effect = Exception("Connection refused")

        service = ModelDiscoveryService(mock_client)
        result = service.discover()

        assert result.gateway_connected is False
        assert len(result.models) == 0

    def test_discover_sorts_by_tier(self, mock_client):
        mock_client.get_available_models.return_value = [
            "google/gemini-2.0-flash",  # FAST
            "anthropic/claude-opus-4",  # POWERFUL (reasoning)
            "anthropic/claude-sonnet-4",  # BALANCED
        ]

        service = ModelDiscoveryService(mock_client)
        result = service.discover()

        # POWERFUL should come first
        assert result.models[0].tier == ModelTier.POWERFUL
        # Then BALANCED
        assert result.models[1].tier == ModelTier.BALANCED
        # Then FAST
        assert result.models[2].tier == ModelTier.FAST

    def test_parse_anthropic_model(self, mock_client):
        service = ModelDiscoveryService(mock_client)
        model = service._parse_model_name("anthropic/claude-sonnet-4-20250514")

        assert model.name == "anthropic/claude-sonnet-4-20250514"
        assert model.family == "claude"
        assert model.provider == "anthropic"
        assert model.variant == "sonnet"
        assert model.tier == ModelTier.BALANCED

    def test_parse_openai_model(self, mock_client):
        service = ModelDiscoveryService(mock_client)
        model = service._parse_model_name("openai/gpt-4o")

        assert model.provider == "openai"
        assert model.family == "gpt"
        assert model.tier == ModelTier.POWERFUL

    def test_parse_reasoning_model(self, mock_client):
        service = ModelDiscoveryService(mock_client)

        # Claude Opus is reasoning
        model = service._parse_model_name("anthropic/claude-opus-4")
        assert model.is_reasoning is True
        assert model.tier == ModelTier.POWERFUL

        # o1 is reasoning
        model = service._parse_model_name("openai/o1")
        assert model.is_reasoning is True
        assert model.tier == ModelTier.POWERFUL

    def test_parse_coder_model(self, mock_client):
        service = ModelDiscoveryService(mock_client)
        model = service._parse_model_name("deepseek/deepseek-coder-33b")

        assert model.is_coder is True

    def test_parse_fast_tier_models(self, mock_client):
        service = ModelDiscoveryService(mock_client)

        # Flash variant
        model = service._parse_model_name("google/gemini-2.0-flash")
        assert model.tier == ModelTier.FAST
        assert model.variant == "flash"

        # Mini variant
        model = service._parse_model_name("openai/gpt-4o-mini")
        assert model.tier == ModelTier.FAST

        # Haiku variant
        model = service._parse_model_name("anthropic/claude-3-haiku")
        assert model.tier == ModelTier.FAST
        assert model.variant == "haiku"

    def test_parse_powerful_tier_models(self, mock_client):
        service = ModelDiscoveryService(mock_client)

        # Pro variant
        model = service._parse_model_name("google/gemini-pro")
        assert model.tier == ModelTier.POWERFUL
        assert model.variant == "pro"

        # Ultra variant
        model = service._parse_model_name("google/gemini-ultra")
        assert model.tier == ModelTier.POWERFUL

    def test_parse_model_without_provider(self, mock_client):
        service = ModelDiscoveryService(mock_client)
        model = service._parse_model_name("llama-3-70b")

        assert model.provider is None
        assert model.family == "llama-3-70b"
