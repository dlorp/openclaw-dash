"""Tests for the billing collector."""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from openclaw_dash.collectors.billing import (
    AnthropicBilling,
    BillingCollector,
    BillingResult,
    OpenAIBilling,
    collect,
)


class TestBillingResult:
    """Tests for the BillingResult dataclass."""

    def test_basic_creation(self):
        """Test creating a BillingResult."""
        now = datetime.now()
        result = BillingResult(
            provider="openai",
            source="api",
            cost_usd=1.23,
            input_tokens=1000,
            output_tokens=500,
            period_start=now,
            period_end=now,
        )
        assert result.provider == "openai"
        assert result.source == "api"
        assert result.cost_usd == 1.23
        assert result.input_tokens == 1000
        assert result.output_tokens == 500

    def test_with_error(self):
        """Test BillingResult with error."""
        now = datetime.now()
        result = BillingResult(
            provider="openai",
            source="estimated",
            cost_usd=0.0,
            input_tokens=0,
            output_tokens=0,
            period_start=now,
            period_end=now,
            error="API timeout",
        )
        assert result.error == "API timeout"
        assert result.source == "estimated"


class TestOpenAIBilling:
    """Tests for OpenAI billing collector."""

    def test_is_available_without_key(self):
        """Test that OpenAI billing is not available without admin key."""
        with patch.dict("os.environ", {}, clear=True):
            billing = OpenAIBilling(admin_key=None)
            # Clear any cached key
            billing.admin_key = None
            assert billing.is_available() is False

    def test_is_available_with_key(self):
        """Test that OpenAI billing is available with admin key."""
        billing = OpenAIBilling(admin_key="test-admin-key")
        assert billing.is_available() is True

    def test_get_usage_without_key(self):
        """Test that get_usage returns error without key."""
        billing = OpenAIBilling(admin_key=None)
        billing.admin_key = None
        result = billing.get_usage()
        assert result.source == "estimated"
        assert result.error == "OPENAI_ADMIN_KEY not set"

    @patch("openclaw_dash.collectors.billing.httpx.get")
    def test_get_usage_success(self, mock_get):
        """Test successful usage API call."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [
                {
                    "results": [
                        {
                            "model": "gpt-4o",
                            "input_tokens": 1000,
                            "output_tokens": 500,
                        }
                    ]
                }
            ]
        }
        mock_get.return_value = mock_response

        billing = OpenAIBilling(admin_key="test-key")
        result = billing.get_usage()

        assert result.source == "api"
        assert result.input_tokens == 1000
        assert result.output_tokens == 500
        assert result.error is None

    @patch("openclaw_dash.collectors.billing.httpx.get")
    def test_get_usage_auth_error(self, mock_get):
        """Test handling of authentication error."""
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_get.return_value = mock_response

        billing = OpenAIBilling(admin_key="invalid-key")
        result = billing.get_usage()

        assert result.source == "estimated"
        assert result.error == "Invalid OPENAI_ADMIN_KEY"

    @patch("openclaw_dash.collectors.billing.httpx.get")
    def test_get_usage_api_error(self, mock_get):
        """Test handling of API error."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_get.return_value = mock_response

        billing = OpenAIBilling(admin_key="test-key")
        result = billing.get_usage()

        assert result.source == "estimated"
        assert "API error: 500" in result.error

    @patch("openclaw_dash.collectors.billing.httpx.get")
    def test_get_costs_success(self, mock_get):
        """Test successful costs API call."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [
                {
                    "results": [
                        {
                            "line_item": "GPT-4 Turbo",
                            "amount": {"value": 2.50},
                        }
                    ]
                }
            ]
        }
        mock_get.return_value = mock_response

        billing = OpenAIBilling(admin_key="test-key")
        result = billing.get_costs()

        assert result.source == "api"
        assert result.cost_usd == 2.50
        assert result.error is None

    def test_calculate_cost(self):
        """Test cost calculation from token counts."""
        billing = OpenAIBilling(admin_key="test-key")
        breakdown = {
            "gpt-4o": {"input_tokens": 1_000_000, "output_tokens": 500_000},
        }
        cost = billing._calculate_cost(breakdown)
        # gpt-4o: $2.50/1M input + $10.00/1M output
        # 1M input = $2.50, 0.5M output = $5.00, total = $7.50
        assert cost == 7.5


class TestAnthropicBilling:
    """Tests for Anthropic billing collector."""

    def test_is_available_always_false(self):
        """Test that Anthropic billing API is never available."""
        billing = AnthropicBilling(api_key="test-key")
        assert billing.is_available() is False

    def test_get_usage_returns_estimation(self):
        """Test that get_usage returns estimation notice."""
        billing = AnthropicBilling()
        result = billing.get_usage()

        assert result.provider == "anthropic"
        assert result.source == "estimated"
        assert "does not provide a billing API" in result.error


class TestBillingCollector:
    """Tests for the unified billing collector."""

    def test_collect_returns_dict(self):
        """Test that collect returns expected structure."""
        collector = BillingCollector()
        result = collector.collect()

        assert isinstance(result, dict)
        assert "providers" in result
        assert "total_api_cost" in result
        assert "has_api_data" in result
        assert "api_available" in result
        assert "collected_at" in result

    def test_collect_includes_anthropic(self):
        """Test that collect includes Anthropic (estimated)."""
        collector = BillingCollector()
        result = collector.collect()

        assert "anthropic" in result["providers"]
        assert result["providers"]["anthropic"]["source"] == "estimated"

    @patch("openclaw_dash.collectors.billing.is_demo_mode", return_value=False)
    @patch.object(OpenAIBilling, "is_available", return_value=True)
    @patch.object(OpenAIBilling, "get_costs")
    def test_collect_with_openai_api(self, mock_get_costs, mock_is_available, mock_demo):
        """Test collect when OpenAI API is available."""
        now = datetime.now()
        mock_get_costs.return_value = BillingResult(
            provider="openai",
            source="api",
            cost_usd=5.67,
            input_tokens=10000,
            output_tokens=5000,
            period_start=now,
            period_end=now,
        )

        collector = BillingCollector()
        result = collector.collect()

        assert "openai" in result["providers"]
        assert result["providers"]["openai"]["source"] == "api"
        assert result["total_api_cost"] == 5.67
        assert result["has_api_data"] is True

    def test_get_daily_costs(self):
        """Test fetching daily cost breakdown."""
        collector = BillingCollector()
        result = collector.get_daily_costs(days=3)

        assert isinstance(result, list)
        assert len(result) <= 3
        for day in result:
            assert "date" in day
            assert "api_cost" in day
            assert "has_api_data" in day

    @patch("openclaw_dash.collectors.billing.is_demo_mode", return_value=True)
    def test_demo_mode_returns_mock_data(self, mock_demo):
        """Test that demo mode returns mock data."""
        collector = BillingCollector()
        result = collector.collect()

        assert result["has_api_data"] is True
        assert result["total_api_cost"] == 1.23
        assert "openai" in result["providers"]
        assert result["providers"]["openai"]["source"] == "api"

    @patch("openclaw_dash.collectors.billing.is_demo_mode", return_value=True)
    def test_demo_mode_daily_costs(self, mock_demo):
        """Test that demo mode returns mock daily costs."""
        collector = BillingCollector()
        result = collector.get_daily_costs(days=5)

        assert len(result) == 5
        assert all(day["has_api_data"] for day in result)


class TestCollectFunction:
    """Tests for the convenience collect function."""

    def test_collect_function_returns_dict(self):
        """Test that the collect() convenience function works."""
        result = collect()
        assert isinstance(result, dict)
        assert "providers" in result
        assert "collected_at" in result


class TestOpenAIPricing:
    """Tests for OpenAI pricing calculations."""

    def test_gpt4o_pricing(self):
        """Test GPT-4o pricing calculation."""
        billing = OpenAIBilling(admin_key="test")
        breakdown = {"gpt-4o": {"input_tokens": 1_000_000, "output_tokens": 1_000_000}}
        cost = billing._calculate_cost(breakdown)
        # $2.50/1M input + $10.00/1M output = $12.50
        assert cost == 12.5

    def test_gpt4o_mini_pricing(self):
        """Test GPT-4o-mini pricing calculation."""
        billing = OpenAIBilling(admin_key="test")
        breakdown = {"gpt-4o-mini": {"input_tokens": 1_000_000, "output_tokens": 1_000_000}}
        cost = billing._calculate_cost(breakdown)
        # $0.15/1M input + $0.60/1M output = $0.75
        assert cost == 0.75

    def test_unknown_model_uses_default(self):
        """Test that unknown models use default pricing."""
        billing = OpenAIBilling(admin_key="test")
        breakdown = {"unknown-model": {"input_tokens": 1_000_000, "output_tokens": 1_000_000}}
        cost = billing._calculate_cost(breakdown)
        # Default: $2.50/1M input + $10.00/1M output = $12.50
        assert cost == 12.5

    def test_multiple_models(self):
        """Test cost calculation with multiple models."""
        billing = OpenAIBilling(admin_key="test")
        breakdown = {
            "gpt-4o": {"input_tokens": 500_000, "output_tokens": 250_000},
            "gpt-4o-mini": {"input_tokens": 500_000, "output_tokens": 250_000},
        }
        cost = billing._calculate_cost(breakdown)
        # gpt-4o: 0.5M * $2.50 + 0.25M * $10.00 = $1.25 + $2.50 = $3.75
        # gpt-4o-mini: 0.5M * $0.15 + 0.25M * $0.60 = $0.075 + $0.15 = $0.225
        # Total: $3.975
        assert cost == pytest.approx(3.975, rel=0.01)
