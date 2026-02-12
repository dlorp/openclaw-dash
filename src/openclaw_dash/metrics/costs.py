"""Token and API cost tracking for OpenClaw sessions.

This module tracks the actual API costs based on real input/output token counts
from the OpenClaw gateway, rather than estimating token splits.

FUTURE ENHANCEMENT - Local Model Energy Tracking:
--------------------------------------------------
For local models (Ollama, local LLMs), costs are currently $0.00. A future enhancement
could track actual energy consumption:

1. Monitor GPU/CPU power draw during inference (using nvidia-smi, powermetrics, etc.)
2. Calculate kWh consumed per session
3. Apply local electricity rates (configurable per-user)
4. Track carbon footprint based on local grid mix
5. Compare cost/efficiency of local vs cloud models

This would provide true cost visibility including:
- Hardware costs (amortized)
- Energy costs
- Environmental impact
- Total cost of ownership comparisons

Implementation notes:
- Would require platform-specific power monitoring
- Need background sampling during model inference
- Store energy metrics alongside token counts
- Add config for electricity rate ($/kWh) and carbon intensity (gCO2/kWh)
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Any

from openclaw_dash.demo import is_demo_mode, mock_cost_data

logger = logging.getLogger(__name__)

# Security limits
MAX_TOKENS = 10_000_000  # 10M tokens - reasonable upper bound for a single session
MAX_COSTS_FILE_SIZE = 10 * 1024 * 1024  # 10MB limit for costs.json

# Token pricing per 1M tokens (as of Feb 2025)
# Prices are in USD per 1 million tokens
MODEL_PRICING = {
    # Claude 4.x series
    "claude-opus-4-5": {"input": 15.00, "output": 75.00},
    "claude-sonnet-4-5": {"input": 3.00, "output": 15.00},
    "claude-sonnet-4": {"input": 3.00, "output": 15.00},
    "claude-haiku-4-5": {"input": 0.25, "output": 1.25},
    "claude-haiku-4": {"input": 0.25, "output": 1.25},
    # Claude 3.x series
    "claude-3-opus": {"input": 15.00, "output": 75.00},
    "claude-3-5-sonnet": {"input": 3.00, "output": 15.00},
    "claude-3-sonnet": {"input": 3.00, "output": 15.00},
    "claude-3-haiku": {"input": 0.25, "output": 1.25},
    "claude-3-5-haiku": {"input": 0.25, "output": 1.25},
    # OpenAI GPT-4 series
    "gpt-4o": {"input": 2.50, "output": 10.00},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "gpt-4-turbo": {"input": 10.00, "output": 30.00},
    "gpt-4": {"input": 30.00, "output": 60.00},
    # OpenAI GPT-3.5 series
    "gpt-3.5-turbo": {"input": 0.50, "output": 1.50},
    # O-series (reasoning models)
    "o1": {"input": 15.00, "output": 60.00},
    "o1-mini": {"input": 3.00, "output": 12.00},
    "o3-mini": {"input": 1.10, "output": 4.40},
    # Codex/GitHub Copilot (approximations based on public info)
    "codex": {"input": 0.00, "output": 0.00},  # Usually bundled/free tier
    "copilot": {"input": 0.00, "output": 0.00},  # Subscription-based
    # Gemini series (Google)
    "gemini-1.5-pro": {"input": 1.25, "output": 5.00},
    "gemini-1.5-flash": {"input": 0.075, "output": 0.30},
    "gemini-2.0-flash": {"input": 0.10, "output": 0.40},
    # Default fallback (use Sonnet pricing as conservative estimate)
    "default": {"input": 3.00, "output": 15.00},
}

DEFAULT_METRICS_DIR = Path.home() / ".openclaw" / "workspace" / "metrics"


def _validate_token_count(value: Any, field_name: str) -> int:
    """Validate and sanitize a token count value.

    Args:
        value: The value to validate (should be an int or coercible to int)
        field_name: Name of the field for logging

    Returns:
        Validated integer token count, clamped to [0, MAX_TOKENS]

    Raises:
        TypeError: If value cannot be coerced to int
    """
    try:
        count = int(value)
    except (TypeError, ValueError) as e:
        logger.warning(
            f"Invalid token count for {field_name}: {value!r} (type={type(value).__name__}). "
            f"Error: {e}. Defaulting to 0."
        )
        return 0

    # Clamp to valid range
    if count < 0:
        logger.warning(f"Negative token count for {field_name}: {count}. Clamping to 0.")
        return 0

    if count > MAX_TOKENS:
        logger.warning(
            f"Token count for {field_name} exceeds maximum ({count:,} > {MAX_TOKENS:,}). "
            f"Clamping to {MAX_TOKENS:,}."
        )
        return MAX_TOKENS

    return count


@dataclass
class SessionCost:
    """Cost data for a single session."""

    session_key: str
    model: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    input_cost: float
    output_cost: float
    total_cost: float
    timestamp: str


@dataclass
class DailyCosts:
    """Aggregated costs for a day."""

    date: str
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_cost: float = 0.0
    by_model: dict[str, dict[str, Any]] = field(default_factory=dict)
    session_count: int = 0


class CostTracker:
    """Track and persist token/API costs over time."""

    def __init__(self, metrics_dir: Path | None = None):
        self.metrics_dir = metrics_dir or DEFAULT_METRICS_DIR
        self.metrics_dir.mkdir(parents=True, exist_ok=True)
        self.costs_file = self.metrics_dir / "costs.json"

    def _load_history(self) -> dict[str, Any]:
        """Load cost history from disk with security checks."""
        if not self.costs_file.exists():
            return {"daily": {}, "sessions": {}}

        try:
            # Check file size before loading (DoS protection)
            file_size = self.costs_file.stat().st_size
            if file_size > MAX_COSTS_FILE_SIZE:
                logger.error(
                    f"costs.json file too large ({file_size:,} bytes > {MAX_COSTS_FILE_SIZE:,} bytes). "
                    f"Skipping load to prevent DoS. File: {self.costs_file}"
                )
                return {"daily": {}, "sessions": {}}

            content = self.costs_file.read_text()
            return json.loads(content)

        except RecursionError as e:
            logger.error(
                f"Recursion limit exceeded while parsing costs.json (possible deeply nested JSON). "
                f"Error: {e}. File: {self.costs_file}"
            )
            return {"daily": {}, "sessions": {}}

        except json.JSONDecodeError as e:
            logger.error(
                f"Failed to parse costs.json as valid JSON. Error: {e}. File: {self.costs_file}"
            )
            return {"daily": {}, "sessions": {}}

        except OSError as e:
            logger.error(f"Failed to read costs.json. Error: {e}. File: {self.costs_file}")
            return {"daily": {}, "sessions": {}}

    def _save_history(self, data: dict[str, Any]) -> None:
        """Save cost history to disk."""
        self.costs_file.write_text(json.dumps(data, indent=2, default=str))

    @staticmethod
    def calculate_cost(
        model: str, input_tokens: int, output_tokens: int
    ) -> tuple[float, float, float]:
        """Calculate costs for given token counts.

        Returns: (input_cost, output_cost, total_cost) in USD

        Note: For local models (Ollama, etc.), this returns $0.00.
        Future enhancement: Track energy consumption for local models.
        """
        # Check if this looks like a local model (no cost)
        local_indicators = ["ollama", "local", "llama", "mistral"]
        if any(indicator in model.lower() for indicator in local_indicators):
            return 0.0, 0.0, 0.0

        # Get pricing for the model (with fallback to default)
        pricing = MODEL_PRICING.get(
            model, MODEL_PRICING.get("default", {"input": 3.0, "output": 15.0})
        )

        input_cost = (input_tokens / 1_000_000) * pricing["input"]
        output_cost = (output_tokens / 1_000_000) * pricing["output"]
        return input_cost, output_cost, input_cost + output_cost

    def get_sessions_data(self) -> list[dict[str, Any]]:
        """Fetch current session data from the sessions collector.

        Uses the sessions collector which parses openclaw status output.
        Returns sessions with token usage data including input/output split.
        """
        from openclaw_dash.collectors import sessions

        try:
            data = sessions.collect()
            return data.get("sessions", [])
        except Exception as e:
            # If collector fails, return empty list
            logger.error(f"Failed to collect session data from sessions collector: {e}")
            return []

    def collect(self) -> dict[str, Any]:
        """Collect current cost metrics."""
        # Return mock data in demo mode
        if is_demo_mode():
            mock_data = mock_cost_data()
            return {
                "today": {
                    "date": date.today().isoformat(),
                    "input_tokens": 50000,
                    "output_tokens": 12000,
                    "cost": mock_data["today"]["total"],
                    "by_model": {
                        "claude-sonnet-4": {
                            "input_tokens": 50000,
                            "output_tokens": 12000,
                            "cost": mock_data["today"]["total"],
                        }
                    },
                },
                "summary": {
                    "total_cost": 12.50,
                    "days_tracked": mock_data["streak"],
                    "avg_daily_cost": 1.04,
                },
                "trend": {
                    "dates": [date.today().isoformat()],
                    "costs": mock_data["trend"]["values"],
                },
                "collected_at": datetime.now().isoformat(),
            }

        sessions = self.get_sessions_data()
        history = self._load_history()
        today = date.today().isoformat()

        # Initialize today's data if needed
        if today not in history["daily"]:
            history["daily"][today] = asdict(DailyCosts(date=today))

        today_data = history["daily"][today]

        for session in sessions:
            key = session.get("key", session.get("sessionKey", ""))
            if not key:
                continue

            model = session.get("model", "unknown")

            # Validate and sanitize token counts (security: type confusion + overflow protection)
            total_tokens = _validate_token_count(
                session.get("totalTokens", 0) or 0, f"{key}.totalTokens"
            )
            current_input = _validate_token_count(
                session.get("inputTokens", 0) or 0, f"{key}.inputTokens"
            )
            current_output = _validate_token_count(
                session.get("outputTokens", 0) or 0, f"{key}.outputTokens"
            )

            # Skip if no tokens used
            if total_tokens == 0:
                continue

            # Check if we've already recorded this session state
            session_record = history["sessions"].get(key, {})
            prev_input = session_record.get("input_tokens", 0)
            prev_output = session_record.get("output_tokens", 0)

            # Calculate incremental tokens since last check
            new_input = max(0, current_input - prev_input)
            new_output = max(0, current_output - prev_output)

            # If no actual input/output data available, fall back to estimation
            # This handles older gateway versions or sessions without detailed tracking
            if new_input == 0 and new_output == 0 and total_tokens > 0:
                prev_total = session_record.get("total_tokens", 0)
                new_total = max(0, total_tokens - prev_total)
                if new_total > 0:
                    # Estimate 60% input / 40% output as fallback
                    new_input = int(new_total * 0.60)
                    new_output = int(new_total * 0.40)

            if new_input == 0 and new_output == 0:
                continue

            input_cost, output_cost, total_cost = self.calculate_cost(model, new_input, new_output)

            # Update today's totals
            today_data["total_input_tokens"] += new_input
            today_data["total_output_tokens"] += new_output
            today_data["total_cost"] += total_cost
            today_data["session_count"] += 1

            # Update model breakdown
            if model not in today_data["by_model"]:
                today_data["by_model"][model] = {"input_tokens": 0, "output_tokens": 0, "cost": 0.0}
            today_data["by_model"][model]["input_tokens"] += new_input
            today_data["by_model"][model]["output_tokens"] += new_output
            today_data["by_model"][model]["cost"] += total_cost

            # Update session record with actual token counts
            history["sessions"][key] = {
                "total_tokens": total_tokens,
                "input_tokens": current_input,
                "output_tokens": current_output,
                "model": model,
                "last_updated": datetime.now().isoformat(),
            }

        # Always save to ensure daily entry exists
        self._save_history(history)

        # Calculate summary stats
        total_all_time = sum(d.get("total_cost", 0) for d in history["daily"].values())
        days_tracked = len(history["daily"])
        avg_daily = total_all_time / days_tracked if days_tracked > 0 else 0

        # Get last 7 days trend
        recent_dates = sorted(history["daily"].keys(), reverse=True)[:7]
        recent_costs = [history["daily"][d].get("total_cost", 0) for d in recent_dates]

        return {
            "today": {
                "date": today,
                "input_tokens": today_data["total_input_tokens"],
                "output_tokens": today_data["total_output_tokens"],
                "cost": round(today_data["total_cost"], 4),
                "by_model": today_data["by_model"],
            },
            "summary": {
                "total_cost": round(total_all_time, 2),
                "days_tracked": days_tracked,
                "avg_daily_cost": round(avg_daily, 2),
            },
            "trend": {
                "dates": recent_dates,
                "costs": [round(c, 4) for c in recent_costs],
            },
            "collected_at": datetime.now().isoformat(),
        }

    def get_history(self, days: int = 30) -> list[dict[str, Any]]:
        """Get daily cost history."""
        history = self._load_history()
        dates = sorted(history["daily"].keys(), reverse=True)[:days]
        return [
            {
                "date": d,
                **history["daily"][d],
            }
            for d in dates
        ]
