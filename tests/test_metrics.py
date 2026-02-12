"""Tests for metrics collectors."""

from unittest.mock import patch

from openclaw_dash import demo
from openclaw_dash.metrics import CostTracker


class TestCostTracker:
    """Tests for CostTracker."""

    def test_collect_returns_dict(self, tmp_path):
        tracker = CostTracker(metrics_dir=tmp_path)
        result = tracker.collect()
        assert isinstance(result, dict)
        assert "today" in result
        assert "summary" in result
        assert "trend" in result
        assert "collected_at" in result

    def test_today_structure(self, tmp_path):
        tracker = CostTracker(metrics_dir=tmp_path)
        result = tracker.collect()
        today = result["today"]
        assert "date" in today
        assert "input_tokens" in today
        assert "output_tokens" in today
        assert "cost" in today

    def test_calculate_cost_opus(self):
        # Test opus pricing: $15/1M input, $75/1M output
        input_cost, output_cost, total = CostTracker.calculate_cost(
            "claude-opus-4-5",
            input_tokens=1_000_000,
            output_tokens=100_000,
        )
        assert input_cost == 15.00
        assert output_cost == 7.50
        assert total == 22.50

    def test_calculate_cost_sonnet(self):
        # Test sonnet pricing: $3/1M input, $15/1M output
        input_cost, output_cost, total = CostTracker.calculate_cost(
            "claude-sonnet-4",
            input_tokens=1_000_000,
            output_tokens=1_000_000,
        )
        assert input_cost == 3.00
        assert output_cost == 15.00
        assert total == 18.00

    def test_calculate_cost_unknown_model(self):
        # Unknown models should use sonnet pricing as fallback
        input_cost, output_cost, total = CostTracker.calculate_cost(
            "unknown-model",
            input_tokens=1_000_000,
            output_tokens=1_000_000,
        )
        assert total > 0  # Should get some value, not crash

    def test_history_persistence(self, tmp_path):
        demo.disable_demo_mode()  # Disable demo mode to test real code path
        tracker = CostTracker(metrics_dir=tmp_path)

        # First collection creates daily entry even if no sessions
        tracker.collect()

        # History is saved internally, verify by loading
        history = tracker._load_history()
        assert "daily" in history
        assert "sessions" in history

        # Today's date should be in daily
        from datetime import date

        today = date.today().isoformat()
        assert today in history["daily"]

    def test_get_history(self, tmp_path):
        tracker = CostTracker(metrics_dir=tmp_path)
        tracker.collect()

        history = tracker.get_history(days=30)
        assert isinstance(history, list)

    def test_sessions_data_from_collector(self, tmp_path):
        with patch("openclaw_dash.collectors.sessions.collect") as mock_collect:
            mock_collect.return_value = {
                "sessions": [
                    {
                        "key": "test-session",
                        "model": "claude-sonnet-4",
                        "inputTokens": 1000,
                        "outputTokens": 500,
                        "totalTokens": 1500,
                    }
                ]
            }

            tracker = CostTracker(metrics_dir=tmp_path)
            sessions = tracker.get_sessions_data()
            assert isinstance(sessions, list)
            assert len(sessions) == 1
            assert sessions[0]["key"] == "test-session"
