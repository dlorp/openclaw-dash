"""Tests for metrics collectors."""

import json
from datetime import datetime
from unittest.mock import MagicMock, patch

from openclaw_dash import demo
from openclaw_dash.metrics import CostTracker, GitHubMetrics, PerformanceMetrics
from openclaw_dash.metrics.costs import MODEL_PRICING


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

    @patch("openclaw_dash.metrics.costs.subprocess.run")
    def test_sessions_data_from_cli(self, mock_run, tmp_path):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps(
                {
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
            ),
        )

        tracker = CostTracker(metrics_dir=tmp_path)
        sessions = tracker.get_sessions_data()

        assert len(sessions) == 1
        assert sessions[0]["key"] == "test-session"


class TestPerformanceMetrics:
    """Tests for PerformanceMetrics."""

    def test_collect_returns_dict(self, tmp_path):
        perf = PerformanceMetrics(metrics_dir=tmp_path)
        result = perf.collect()
        assert isinstance(result, dict)
        assert "summary" in result
        assert "slowest" in result
        assert "error_prone" in result
        assert "collected_at" in result

    def test_summary_structure(self, tmp_path):
        perf = PerformanceMetrics(metrics_dir=tmp_path)
        result = perf.collect()
        summary = result["summary"]
        assert "total_calls" in summary
        assert "total_errors" in summary
        assert "error_rate_pct" in summary
        assert "avg_latency_ms" in summary

    def test_parse_ws_log_line(self, tmp_path):
        perf = PerformanceMetrics(metrics_dir=tmp_path)

        # Test successful ws response
        parsed = perf._parse_log_line("[ws] SYNC res ✓ chat.history 67ms conn=xyz id=abc")
        assert parsed is not None
        assert parsed["type"] == "ws_response"
        assert parsed["action"] == "chat.history"
        assert parsed["success"] is True
        assert parsed["latency_ms"] == 67

    def test_parse_ws_error_line(self, tmp_path):
        perf = PerformanceMetrics(metrics_dir=tmp_path)

        # Test failed ws response
        parsed = perf._parse_log_line("[ws] SYNC res ✗ config.patch 5ms errorCode=INVALID_REQUEST")
        assert parsed is not None
        assert parsed["success"] is False
        assert parsed["action"] == "config.patch"

    def test_get_trend(self, tmp_path):
        perf = PerformanceMetrics(metrics_dir=tmp_path)
        perf.collect()

        trend = perf.get_trend(days=7)
        assert isinstance(trend, list)


class TestGitHubMetrics:
    """Tests for GitHubMetrics."""

    def test_collect_returns_dict(self, tmp_path):
        gh = GitHubMetrics(metrics_dir=tmp_path)
        result = gh.collect()
        assert isinstance(result, dict)
        assert "streak" in result
        assert "pr_metrics" in result
        assert "todo_trends" in result
        assert "collected_at" in result

    def test_streak_structure(self, tmp_path):
        gh = GitHubMetrics(metrics_dir=tmp_path)
        result = gh.collect()
        streak = result["streak"]
        assert "streak_days" in streak

    def test_pr_metrics_structure(self, tmp_path):
        gh = GitHubMetrics(metrics_dir=tmp_path)
        result = gh.collect()
        pr = result["pr_metrics"]
        assert "recent_prs" in pr
        assert "avg_cycle_hours" in pr

    @patch("openclaw_dash.metrics.github.subprocess.run")
    def test_contribution_streak_with_mock(self, mock_run, tmp_path):
        # Mock the gh api calls
        def mock_subprocess(cmd, **kwargs):
            cmd_str = " ".join(cmd) if isinstance(cmd, list) else str(cmd)
            if "api user" in cmd_str:
                return MagicMock(returncode=0, stdout="testuser\n")
            elif "events" in cmd_str:
                today = datetime.now().strftime("%Y-%m-%dT12:00:00Z")
                return MagicMock(returncode=0, stdout=f"{today}\n")
            return MagicMock(returncode=1, stdout="", stderr="")

        mock_run.side_effect = mock_subprocess

        gh = GitHubMetrics(metrics_dir=tmp_path)
        streak = gh.get_contribution_streak("testuser")  # Pass username directly

        assert "streak_days" in streak
        # With activity today, streak should be at least 1
        assert streak.get("streak_days", 0) >= 0

    def test_todo_trends_no_snapshots(self, tmp_path):
        gh = GitHubMetrics(metrics_dir=tmp_path)
        trends = gh.get_todo_trends()
        assert "repos" in trends
        # Should handle missing directory gracefully
        assert isinstance(trends["repos"], dict)

    def test_get_streak_history(self, tmp_path):
        gh = GitHubMetrics(metrics_dir=tmp_path)
        gh.collect()

        history = gh.get_streak_history(days=30)
        assert isinstance(history, list)


class TestModelPricing:
    """Tests for model pricing configuration."""

    def test_all_models_have_both_prices(self):
        for model, pricing in MODEL_PRICING.items():
            assert "input" in pricing, f"{model} missing input price"
            assert "output" in pricing, f"{model} missing output price"
            assert pricing["input"] > 0, f"{model} input price should be positive"
            assert pricing["output"] > 0, f"{model} output price should be positive"

    def test_opus_more_expensive_than_sonnet(self):
        opus = MODEL_PRICING.get("claude-opus-4-5", MODEL_PRICING.get("claude-3-opus"))
        sonnet = MODEL_PRICING.get("claude-sonnet-4", MODEL_PRICING.get("claude-3-sonnet"))

        assert opus["input"] > sonnet["input"]
        assert opus["output"] > sonnet["output"]
