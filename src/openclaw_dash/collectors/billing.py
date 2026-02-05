"""Billing collector for fetching real costs from provider APIs.

Supports:
- OpenAI: Uses the Organization Usage/Costs API (requires OPENAI_ADMIN_KEY)
- Anthropic: Falls back to local estimation (no public billing API)
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

import httpx

from openclaw_dash.demo import is_demo_mode


@dataclass
class BillingResult:
    """Result from a billing API call."""

    provider: str
    source: str  # "api" or "estimated"
    cost_usd: float
    input_tokens: int
    output_tokens: int
    period_start: datetime
    period_end: datetime
    breakdown: dict[str, Any] | None = None
    error: str | None = None


class OpenAIBilling:
    """Fetch billing data from OpenAI's Usage API.

    Requires OPENAI_ADMIN_KEY environment variable.
    See: https://platform.openai.com/docs/api-reference/usage
    """

    BASE_URL = "https://api.openai.com/v1/organization"

    def __init__(self, admin_key: str | None = None):
        self.admin_key = admin_key or os.environ.get("OPENAI_ADMIN_KEY")

    def is_available(self) -> bool:
        """Check if OpenAI billing API is available."""
        return bool(self.admin_key)

    def get_usage(
        self,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        bucket_width: str = "1d",
    ) -> BillingResult:
        """Fetch usage data from OpenAI API.

        Args:
            start_time: Start of period (defaults to start of today)
            end_time: End of period (defaults to now)
            bucket_width: Bucket width ("1m", "1h", "1d")

        Returns:
            BillingResult with usage data
        """
        if not self.admin_key:
            return BillingResult(
                provider="openai",
                source="estimated",
                cost_usd=0.0,
                input_tokens=0,
                output_tokens=0,
                period_start=start_time or datetime.now().replace(hour=0, minute=0, second=0),
                period_end=end_time or datetime.now(),
                error="OPENAI_ADMIN_KEY not set",
            )

        # Default to today
        if not start_time:
            start_time = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        if not end_time:
            end_time = datetime.now()

        try:
            # Fetch completions usage (the main cost driver)
            response = httpx.get(
                f"{self.BASE_URL}/usage/completions",
                params={
                    "start_time": int(start_time.timestamp()),
                    "end_time": int(end_time.timestamp()),
                    "bucket_width": bucket_width,
                    "group_by": ["model"],
                },
                headers={
                    "Authorization": f"Bearer {self.admin_key}",
                    "Content-Type": "application/json",
                },
                timeout=5,
            )

            if response.status_code == 401:
                return BillingResult(
                    provider="openai",
                    source="estimated",
                    cost_usd=0.0,
                    input_tokens=0,
                    output_tokens=0,
                    period_start=start_time,
                    period_end=end_time,
                    error="Invalid OPENAI_ADMIN_KEY",
                )

            if response.status_code != 200:
                return BillingResult(
                    provider="openai",
                    source="estimated",
                    cost_usd=0.0,
                    input_tokens=0,
                    output_tokens=0,
                    period_start=start_time,
                    period_end=end_time,
                    error=f"API error: {response.status_code}",
                )

            data = response.json()
            return self._parse_usage_response(data, start_time, end_time)

        except httpx.TimeoutException:
            return BillingResult(
                provider="openai",
                source="estimated",
                cost_usd=0.0,
                input_tokens=0,
                output_tokens=0,
                period_start=start_time,
                period_end=end_time,
                error="API timeout",
            )
        except Exception as e:
            return BillingResult(
                provider="openai",
                source="estimated",
                cost_usd=0.0,
                input_tokens=0,
                output_tokens=0,
                period_start=start_time,
                period_end=end_time,
                error=str(e),
            )

    def get_costs(
        self,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> BillingResult:
        """Fetch actual costs from OpenAI Costs API.

        This endpoint gives exact dollar amounts that reconcile with invoices.
        """
        if not self.admin_key:
            return BillingResult(
                provider="openai",
                source="estimated",
                cost_usd=0.0,
                input_tokens=0,
                output_tokens=0,
                period_start=start_time or datetime.now().replace(hour=0, minute=0, second=0),
                period_end=end_time or datetime.now(),
                error="OPENAI_ADMIN_KEY not set",
            )

        if not start_time:
            start_time = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        if not end_time:
            end_time = datetime.now()

        try:
            response = httpx.get(
                f"{self.BASE_URL}/costs",
                params={
                    "start_time": int(start_time.timestamp()),
                    "end_time": int(end_time.timestamp()),
                    "bucket_width": "1d",
                    "group_by": ["line_item"],
                },
                headers={
                    "Authorization": f"Bearer {self.admin_key}",
                    "Content-Type": "application/json",
                },
                timeout=5,
            )

            if response.status_code != 200:
                # Fall back to usage-based calculation
                return self.get_usage(start_time, end_time)

            data = response.json()
            return self._parse_costs_response(data, start_time, end_time)

        except Exception:
            # Fall back to usage-based calculation
            return self.get_usage(start_time, end_time)

    def _parse_usage_response(
        self, data: dict[str, Any], start_time: datetime, end_time: datetime
    ) -> BillingResult:
        """Parse usage API response into BillingResult."""
        total_input = 0
        total_output = 0
        breakdown: dict[str, dict[str, int]] = {}

        for bucket in data.get("data", []):
            for result in bucket.get("results", []):
                model = result.get("model", "unknown")
                input_tokens = result.get("input_tokens", 0)
                output_tokens = result.get("output_tokens", 0)

                total_input += input_tokens
                total_output += output_tokens

                if model not in breakdown:
                    breakdown[model] = {"input_tokens": 0, "output_tokens": 0}
                breakdown[model]["input_tokens"] += input_tokens
                breakdown[model]["output_tokens"] += output_tokens

        # Calculate cost using OpenAI pricing
        cost = self._calculate_cost(breakdown)

        return BillingResult(
            provider="openai",
            source="api",
            cost_usd=cost,
            input_tokens=total_input,
            output_tokens=total_output,
            period_start=start_time,
            period_end=end_time,
            breakdown=breakdown,
        )

    def _parse_costs_response(
        self, data: dict[str, Any], start_time: datetime, end_time: datetime
    ) -> BillingResult:
        """Parse costs API response into BillingResult."""
        total_cost = 0.0
        breakdown: dict[str, float] = {}

        for bucket in data.get("data", []):
            for result in bucket.get("results", []):
                amount = result.get("amount", {}).get("value", 0)
                line_item = result.get("line_item", "other")
                total_cost += amount
                breakdown[line_item] = breakdown.get(line_item, 0) + amount

        return BillingResult(
            provider="openai",
            source="api",
            cost_usd=total_cost,
            input_tokens=0,  # Costs API doesn't include token counts
            output_tokens=0,
            period_start=start_time,
            period_end=end_time,
            breakdown=breakdown,
        )

    def _calculate_cost(self, breakdown: dict[str, dict[str, int]]) -> float:
        """Calculate cost from token counts using OpenAI pricing."""
        # OpenAI pricing per 1M tokens (as of early 2025)
        # Order matters: more specific matches first
        pricing = [
            ("gpt-4o-mini", {"input": 0.15, "output": 0.60}),
            ("gpt-4o", {"input": 2.50, "output": 10.00}),
            ("gpt-4-turbo", {"input": 10.00, "output": 30.00}),
            ("gpt-4", {"input": 30.00, "output": 60.00}),
            ("gpt-3.5-turbo", {"input": 0.50, "output": 1.50}),
            ("o1-mini", {"input": 3.00, "output": 12.00}),
            ("o1", {"input": 15.00, "output": 60.00}),
        ]
        default_pricing = {"input": 2.50, "output": 10.00}

        total = 0.0
        for model, tokens in breakdown.items():
            # Find matching pricing (handle model variants)
            # More specific matches first due to ordering
            model_pricing = default_pricing
            model_lower = model.lower()
            for key, prices in pricing:
                if key in model_lower:
                    model_pricing = prices
                    break

            input_cost = (tokens["input_tokens"] / 1_000_000) * model_pricing["input"]
            output_cost = (tokens["output_tokens"] / 1_000_000) * model_pricing["output"]
            total += input_cost + output_cost

        return round(total, 6)


class AnthropicBilling:
    """Anthropic billing - currently estimation only.

    Anthropic does not have a public billing/usage API as of early 2025.
    We fall back to local token-based estimation.
    """

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")

    def is_available(self) -> bool:
        """Check if Anthropic billing is available (always False for real API)."""
        return False  # No billing API available

    def get_usage(
        self,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> BillingResult:
        """Get usage data - returns estimation notice.

        Anthropic doesn't have a billing API, so we can't fetch real costs.
        The CostTracker's local estimation should be used instead.
        """
        if not start_time:
            start_time = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        if not end_time:
            end_time = datetime.now()

        return BillingResult(
            provider="anthropic",
            source="estimated",
            cost_usd=0.0,
            input_tokens=0,
            output_tokens=0,
            period_start=start_time,
            period_end=end_time,
            error="Anthropic does not provide a billing API - using local estimation",
        )


class BillingCollector:
    """Unified billing collector that aggregates data from all providers."""

    def __init__(self):
        self.openai = OpenAIBilling()
        self.anthropic = AnthropicBilling()

    def collect(
        self,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> dict[str, Any]:
        """Collect billing data from all available providers.

        Returns:
            Dictionary with:
                - providers: Dict of provider -> BillingResult
                - total_cost: Sum of all provider costs
                - has_api_data: Whether any provider returned real API data
                - collected_at: Timestamp
        """
        if is_demo_mode():
            return self._mock_data()

        results: dict[str, BillingResult] = {}
        total_cost = 0.0
        has_api_data = False

        # OpenAI
        if self.openai.is_available():
            openai_result = self.openai.get_costs(start_time, end_time)
            results["openai"] = openai_result
            if openai_result.source == "api" and not openai_result.error:
                total_cost += openai_result.cost_usd
                has_api_data = True

        # Anthropic (always estimated)
        anthropic_result = self.anthropic.get_usage(start_time, end_time)
        results["anthropic"] = anthropic_result

        return {
            "providers": {
                name: {
                    "source": result.source,
                    "cost_usd": result.cost_usd,
                    "input_tokens": result.input_tokens,
                    "output_tokens": result.output_tokens,
                    "period_start": result.period_start.isoformat(),
                    "period_end": result.period_end.isoformat(),
                    "breakdown": result.breakdown,
                    "error": result.error,
                }
                for name, result in results.items()
            },
            "total_api_cost": total_cost,
            "has_api_data": has_api_data,
            "api_available": {
                "openai": self.openai.is_available(),
                "anthropic": self.anthropic.is_available(),
            },
            "collected_at": datetime.now().isoformat(),
        }

    def get_daily_costs(self, days: int = 7) -> list[dict[str, Any]]:
        """Get daily cost breakdown for the past N days.

        Returns list of daily cost records with API vs estimated breakdown.
        """
        if is_demo_mode():
            return self._mock_daily_costs(days)

        daily_costs = []
        end_time = datetime.now().replace(hour=23, minute=59, second=59, microsecond=0)

        for i in range(days):
            day_end = end_time - timedelta(days=i)
            day_start = day_end.replace(hour=0, minute=0, second=0, microsecond=0)

            result = self.collect(day_start, day_end)

            daily_costs.append(
                {
                    "date": day_start.strftime("%Y-%m-%d"),
                    "api_cost": result["total_api_cost"],
                    "has_api_data": result["has_api_data"],
                    "providers": result["providers"],
                }
            )

        return list(reversed(daily_costs))

    def _mock_data(self) -> dict[str, Any]:
        """Return mock data for demo mode."""
        now = datetime.now()
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)

        return {
            "providers": {
                "openai": {
                    "source": "api",
                    "cost_usd": 1.23,
                    "input_tokens": 50000,
                    "output_tokens": 12000,
                    "period_start": start.isoformat(),
                    "period_end": now.isoformat(),
                    "breakdown": {"gpt-4o": {"input_tokens": 40000, "output_tokens": 10000}},
                    "error": None,
                },
                "anthropic": {
                    "source": "estimated",
                    "cost_usd": 0.0,
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "period_start": start.isoformat(),
                    "period_end": now.isoformat(),
                    "breakdown": None,
                    "error": "Using local estimation",
                },
            },
            "total_api_cost": 1.23,
            "has_api_data": True,
            "api_available": {"openai": True, "anthropic": False},
            "collected_at": now.isoformat(),
        }

    def _mock_daily_costs(self, days: int) -> list[dict[str, Any]]:
        """Return mock daily costs for demo mode."""
        costs = []
        for i in range(days):
            date = datetime.now() - timedelta(days=days - 1 - i)
            costs.append(
                {
                    "date": date.strftime("%Y-%m-%d"),
                    "api_cost": 0.80 + (i * 0.15),
                    "has_api_data": True,
                    "providers": {},
                }
            )
        return costs


# Convenience function for collection
def collect() -> dict[str, Any]:
    """Collect billing data from all providers."""
    collector = BillingCollector()
    return collector.collect()
