"""Token and API cost tracking for OpenClaw sessions."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Any

from openclaw_dash.demo import is_demo_mode, mock_cost_data

# Token pricing per 1M tokens (as of early 2025)
MODEL_PRICING = {
    "claude-opus-4-5": {"input": 15.00, "output": 75.00},
    "claude-sonnet-4": {"input": 3.00, "output": 15.00},
    "claude-3-5-sonnet": {"input": 3.00, "output": 15.00},
    "claude-3-opus": {"input": 15.00, "output": 75.00},
    "claude-3-sonnet": {"input": 3.00, "output": 15.00},
    "claude-3-haiku": {"input": 0.25, "output": 1.25},
    "gpt-4o": {"input": 2.50, "output": 10.00},
    "gpt-4-turbo": {"input": 10.00, "output": 30.00},
    "gpt-4": {"input": 30.00, "output": 60.00},
    "gpt-3.5-turbo": {"input": 0.50, "output": 1.50},
}

DEFAULT_METRICS_DIR = Path.home() / ".openclaw" / "workspace" / "metrics"


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
        """Load cost history from disk."""
        if self.costs_file.exists():
            try:
                return json.loads(self.costs_file.read_text())
            except (OSError, json.JSONDecodeError):
                pass
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
        """
        pricing = MODEL_PRICING.get(
            model, MODEL_PRICING.get("claude-sonnet-4", {"input": 3.0, "output": 15.0})
        )
        input_cost = (input_tokens / 1_000_000) * pricing["input"]
        output_cost = (output_tokens / 1_000_000) * pricing["output"]
        return input_cost, output_cost, input_cost + output_cost

    def get_sessions_data(self) -> list[dict[str, Any]]:
        """Fetch current session data from the sessions collector.

        Uses the sessions collector which parses openclaw status output.
        Returns sessions with token usage data.
        """
        from openclaw_dash.collectors import sessions

        try:
            data = sessions.collect()
            return data.get("sessions", [])
        except Exception:
            # If collector fails, return empty list
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
            total_tokens = session.get("totalTokens", 0) or 0

            # Skip if no tokens used
            if total_tokens == 0:
                continue

            # Check if we've already recorded this session state
            session_record = history["sessions"].get(key, {})
            if session_record.get("total_tokens", 0) >= total_tokens:
                continue  # No new tokens

            # Calculate incremental tokens
            prev_total = session_record.get("total_tokens", 0)
            new_total = max(0, total_tokens - prev_total)

            if new_total == 0:
                continue

            # Estimate input/output split (60% input / 40% output is typical for AI conversations)
            # This is an approximation since the CLI doesn't expose the actual split
            new_input = int(new_total * 0.60)
            new_output = int(new_total * 0.40)

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

            # Update session record
            # Note: We only track total_tokens since that's what the CLI exposes
            # Input/output split is estimated during cost calculation
            history["sessions"][key] = {
                "total_tokens": total_tokens,
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
