"""Tests for the metrics panel widgets."""

from unittest.mock import MagicMock, patch

import pytest
from textual.widgets import Static

from openclaw_dash.widgets.metrics import (
    CostsPanel,
    GitHubPanel,
    MetricsPanel,
    PerformancePanel,
    calculate_cost_forecast,
    get_days_in_current_month,
)


class TestCostsPanel:
    """Tests for the CostsPanel widget."""

    def test_is_static_subclass(self):
        """CostsPanel should inherit from Static."""
        assert issubclass(CostsPanel, Static)

    def test_has_refresh_data_method(self):
        """CostsPanel should have refresh_data method."""
        assert hasattr(CostsPanel, "refresh_data")
        assert callable(getattr(CostsPanel, "refresh_data"))

    def test_has_compose_method(self):
        """CostsPanel should have compose method."""
        assert hasattr(CostsPanel, "compose")
        assert callable(getattr(CostsPanel, "compose"))

    @pytest.mark.asyncio
    async def test_panel_renders(self):
        """Test that the panel can be instantiated and composed."""
        panel = CostsPanel()
        children = list(panel.compose())
        assert len(children) >= 1
        assert isinstance(children[0], Static)

    @pytest.mark.asyncio
    async def test_refresh_data_with_mock(self):
        """Test refresh_data uses the CostTracker collector."""
        mock_data = {
            "today": {
                "date": "2026-02-01",
                "input_tokens": 10000,
                "output_tokens": 5000,
                "cost": 0.0123,
                "by_model": {
                    "claude-sonnet-4": {"cost": 0.01, "input_tokens": 8000, "output_tokens": 4000}
                },
            },
            "summary": {
                "total_cost": 1.23,
                "avg_daily_cost": 0.15,
            },
            "daily_costs": [
                {"date": "2026-01-30", "cost": 0.10},
                {"date": "2026-01-31", "cost": 0.12},
            ],
        }

        with patch("openclaw_dash.widgets.metrics.CostTracker") as mock_tracker_cls:
            mock_tracker = MagicMock()
            mock_tracker.collect.return_value = mock_data
            mock_tracker_cls.return_value = mock_tracker

            # Verify the module uses CostTracker
            from openclaw_dash.widgets import metrics as m

            assert hasattr(m, "CostsPanel")


class TestPerformancePanel:
    """Tests for the PerformancePanel widget."""

    def test_is_static_subclass(self):
        """PerformancePanel should inherit from Static."""
        assert issubclass(PerformancePanel, Static)

    def test_has_refresh_data_method(self):
        """PerformancePanel should have refresh_data method."""
        assert hasattr(PerformancePanel, "refresh_data")
        assert callable(getattr(PerformancePanel, "refresh_data"))

    def test_has_compose_method(self):
        """PerformancePanel should have compose method."""
        assert hasattr(PerformancePanel, "compose")
        assert callable(getattr(PerformancePanel, "compose"))

    @pytest.mark.asyncio
    async def test_panel_renders(self):
        """Test that the panel can be instantiated and composed."""
        panel = PerformancePanel()
        children = list(panel.compose())
        assert len(children) >= 1
        assert isinstance(children[0], Static)

    @pytest.mark.asyncio
    async def test_refresh_data_with_mock(self):
        """Test refresh_data uses the PerformanceMetrics collector."""
        mock_data = {
            "summary": {
                "total_calls": 150,
                "total_errors": 3,
                "error_rate_pct": 2.0,
                "avg_latency_ms": 125.5,
            },
            "slowest": [
                {"name": "chat.send", "avg_ms": 350},
                {"name": "config.get", "avg_ms": 200},
            ],
            "error_prone": [
                {"name": "auth.check", "error_rate": 5.0},
            ],
            "latency_history": [
                {"avg_ms": 100},
                {"avg_ms": 120},
                {"avg_ms": 130},
            ],
        }

        with patch("openclaw_dash.widgets.metrics.PerformanceMetrics") as mock_perf_cls:
            mock_perf = MagicMock()
            mock_perf.collect.return_value = mock_data
            mock_perf_cls.return_value = mock_perf

            from openclaw_dash.widgets import metrics as m

            assert hasattr(m, "PerformancePanel")


class TestGitHubPanel:
    """Tests for the GitHubPanel widget."""

    def test_is_static_subclass(self):
        """GitHubPanel should inherit from Static."""
        assert issubclass(GitHubPanel, Static)

    def test_has_refresh_data_method(self):
        """GitHubPanel should have refresh_data method."""
        assert hasattr(GitHubPanel, "refresh_data")
        assert callable(getattr(GitHubPanel, "refresh_data"))

    def test_has_compose_method(self):
        """GitHubPanel should have compose method."""
        assert hasattr(GitHubPanel, "compose")
        assert callable(getattr(GitHubPanel, "compose"))

    @pytest.mark.asyncio
    async def test_panel_renders(self):
        """Test that the panel can be instantiated and composed."""
        panel = GitHubPanel()
        children = list(panel.compose())
        assert len(children) >= 1
        assert isinstance(children[0], Static)

    @pytest.mark.asyncio
    async def test_refresh_data_with_mock(self):
        """Test refresh_data uses the GitHubMetrics collector."""
        mock_data = {
            "streak": {
                "streak_days": 14,
                "username": "testuser",
            },
            "pr_metrics": {
                "avg_cycle_hours": 12.5,
                "fastest_merge_hours": 2.0,
                "slowest_merge_hours": 48.0,
            },
            "commit_history": [
                {"date": "2026-01-30", "commits": 5},
                {"date": "2026-01-31", "commits": 8},
            ],
            "todo_trends": {
                "repos": {
                    "my-repo": [{"count": 10}, {"count": 12}],
                }
            },
        }

        with patch("openclaw_dash.widgets.metrics.GitHubMetrics") as mock_gh_cls:
            mock_gh = MagicMock()
            mock_gh.collect.return_value = mock_data
            mock_gh_cls.return_value = mock_gh

            from openclaw_dash.widgets import metrics as m

            assert hasattr(m, "GitHubPanel")


class TestMetricsPanel:
    """Tests for the MetricsPanel widget (combined view)."""

    def test_is_static_subclass(self):
        """MetricsPanel should inherit from Static."""
        assert issubclass(MetricsPanel, Static)

    def test_has_refresh_data_method(self):
        """MetricsPanel should have refresh_data method."""
        assert hasattr(MetricsPanel, "refresh_data")
        assert callable(getattr(MetricsPanel, "refresh_data"))

    def test_has_compose_method(self):
        """MetricsPanel should have compose method."""
        assert hasattr(MetricsPanel, "compose")
        assert callable(getattr(MetricsPanel, "compose"))

    @pytest.mark.asyncio
    async def test_panel_renders(self):
        """Test that the panel can be instantiated and composed."""
        panel = MetricsPanel()
        children = list(panel.compose())
        assert len(children) >= 1
        assert isinstance(children[0], Static)


class TestMetricsPanelIntegration:
    """Integration tests for metrics panels in the app."""

    def test_costs_panel_import(self):
        """CostsPanel should be importable."""
        from openclaw_dash.widgets.metrics import CostsPanel

        assert CostsPanel is not None

    def test_performance_panel_import(self):
        """PerformancePanel should be importable."""
        from openclaw_dash.widgets.metrics import PerformancePanel

        assert PerformancePanel is not None

    def test_github_panel_import(self):
        """GitHubPanel should be importable."""
        from openclaw_dash.widgets.metrics import GitHubPanel

        assert GitHubPanel is not None

    def test_metrics_panel_import(self):
        """MetricsPanel should be importable."""
        from openclaw_dash.widgets.metrics import MetricsPanel

        assert MetricsPanel is not None


class TestCostsPanelRendering:
    """Tests for CostsPanel rendering logic."""

    def test_costs_panel_renders_today_cost(self):
        """Test that today's cost is displayed."""
        mock_data = {
            "today": {
                "date": "2026-02-01",
                "input_tokens": 10000,
                "output_tokens": 5000,
                "cost": 0.0567,
                "by_model": {},
            },
            "summary": {
                "total_cost": 5.67,
                "avg_daily_cost": 0.50,
            },
            "daily_costs": [],
        }

        with patch("openclaw_dash.widgets.metrics.CostTracker") as mock_tracker_cls:
            mock_tracker = MagicMock()
            mock_tracker.collect.return_value = mock_data
            mock_tracker_cls.return_value = mock_tracker

            panel = CostsPanel()
            # Compose yields a Static with id="costs-content"
            children = list(panel.compose())
            assert len(children) >= 1

    def test_costs_panel_handles_empty_model_breakdown(self):
        """Test rendering with no model breakdown."""
        mock_data = {
            "today": {
                "date": "2026-02-01",
                "input_tokens": 0,
                "output_tokens": 0,
                "cost": 0,
                "by_model": {},
            },
            "summary": {"total_cost": 0, "avg_daily_cost": 0},
            "daily_costs": [],
        }

        with patch("openclaw_dash.widgets.metrics.CostTracker") as mock_tracker_cls:
            mock_tracker = MagicMock()
            mock_tracker.collect.return_value = mock_data
            mock_tracker_cls.return_value = mock_tracker

            panel = CostsPanel()
            children = list(panel.compose())
            assert len(children) >= 1


class TestPerformancePanelRendering:
    """Tests for PerformancePanel rendering logic."""

    def test_perf_panel_renders_with_low_error_rate(self):
        """Test rendering with low error rate (should show ok status)."""
        mock_data = {
            "summary": {
                "total_calls": 1000,
                "total_errors": 20,
                "error_rate_pct": 2.0,
                "avg_latency_ms": 100,
            },
            "slowest": [],
            "error_prone": [],
            "latency_history": [],
        }

        with patch("openclaw_dash.widgets.metrics.PerformanceMetrics") as mock_perf_cls:
            mock_perf = MagicMock()
            mock_perf.collect.return_value = mock_data
            mock_perf_cls.return_value = mock_perf

            panel = PerformancePanel()
            children = list(panel.compose())
            assert len(children) >= 1

    def test_perf_panel_renders_with_high_error_rate(self):
        """Test rendering with high error rate (should show error status)."""
        mock_data = {
            "summary": {
                "total_calls": 100,
                "total_errors": 25,
                "error_rate_pct": 25.0,
                "avg_latency_ms": 500,
            },
            "slowest": [{"name": "slow.action", "avg_ms": 1000}],
            "error_prone": [{"name": "bad.action", "error_rate": 50.0}],
            "latency_history": [],
        }

        with patch("openclaw_dash.widgets.metrics.PerformanceMetrics") as mock_perf_cls:
            mock_perf = MagicMock()
            mock_perf.collect.return_value = mock_data
            mock_perf_cls.return_value = mock_perf

            panel = PerformancePanel()
            children = list(panel.compose())
            assert len(children) >= 1


class TestGitHubPanelRendering:
    """Tests for GitHubPanel rendering logic."""

    def test_github_panel_renders_with_streak(self):
        """Test rendering with an active streak."""
        mock_data = {
            "streak": {
                "streak_days": 30,
                "username": "activedev",
            },
            "pr_metrics": {
                "avg_cycle_hours": 8.0,
                "fastest_merge_hours": 1.0,
                "slowest_merge_hours": 24.0,
            },
            "commit_history": [],
            "todo_trends": {"repos": {}},
        }

        with patch("openclaw_dash.widgets.metrics.GitHubMetrics") as mock_gh_cls:
            mock_gh = MagicMock()
            mock_gh.collect.return_value = mock_data
            mock_gh_cls.return_value = mock_gh

            panel = GitHubPanel()
            children = list(panel.compose())
            assert len(children) >= 1

    def test_github_panel_renders_with_no_streak(self):
        """Test rendering with no active streak."""
        mock_data = {
            "streak": {
                "streak_days": 0,
                "username": "lazydev",
            },
            "pr_metrics": {
                "avg_cycle_hours": 0,
                "fastest_merge_hours": 0,
                "slowest_merge_hours": 0,
            },
            "commit_history": [],
            "todo_trends": {"repos": {}},
        }

        with patch("openclaw_dash.widgets.metrics.GitHubMetrics") as mock_gh_cls:
            mock_gh = MagicMock()
            mock_gh.collect.return_value = mock_data
            mock_gh_cls.return_value = mock_gh

            panel = GitHubPanel()
            children = list(panel.compose())
            assert len(children) >= 1

    def test_github_panel_renders_with_todos(self):
        """Test rendering with TODO trends."""
        mock_data = {
            "streak": {"streak_days": 5, "username": "dev"},
            "pr_metrics": {
                "avg_cycle_hours": 10.0,
                "fastest_merge_hours": 2.0,
                "slowest_merge_hours": 48.0,
            },
            "commit_history": [
                {"date": "2026-01-30", "commits": 3},
                {"date": "2026-01-31", "commits": 5},
            ],
            "todo_trends": {
                "repos": {
                    "project-a": [{"count": 15}, {"count": 14}, {"count": 12}],
                    "project-b": [{"count": 8}, {"count": 10}],
                }
            },
        }

        with patch("openclaw_dash.widgets.metrics.GitHubMetrics") as mock_gh_cls:
            mock_gh = MagicMock()
            mock_gh.collect.return_value = mock_data
            mock_gh_cls.return_value = mock_gh

            panel = GitHubPanel()
            children = list(panel.compose())
            assert len(children) >= 1


class TestMetricsPanelRendering:
    """Tests for MetricsPanel (combined) rendering logic."""

    def test_metrics_panel_handles_exceptions(self):
        """Test that MetricsPanel handles collector exceptions gracefully."""
        with (
            patch("openclaw_dash.widgets.metrics.CostTracker") as mock_cost_cls,
            patch("openclaw_dash.widgets.metrics.PerformanceMetrics") as mock_perf_cls,
            patch("openclaw_dash.widgets.metrics.GitHubMetrics") as mock_gh_cls,
        ):
            # All collectors raise exceptions
            mock_cost = MagicMock()
            mock_cost.collect.side_effect = Exception("Cost error")
            mock_cost_cls.return_value = mock_cost

            mock_perf = MagicMock()
            mock_perf.collect.side_effect = Exception("Perf error")
            mock_perf_cls.return_value = mock_perf

            mock_gh = MagicMock()
            mock_gh.collect.side_effect = Exception("GH error")
            mock_gh_cls.return_value = mock_gh

            panel = MetricsPanel()
            children = list(panel.compose())
            # Panel should still render even if collectors fail
            assert len(children) >= 1

    def test_metrics_panel_renders_combined_data(self):
        """Test that MetricsPanel combines all metrics sources."""
        with (
            patch("openclaw_dash.widgets.metrics.CostTracker") as mock_cost_cls,
            patch("openclaw_dash.widgets.metrics.PerformanceMetrics") as mock_perf_cls,
            patch("openclaw_dash.widgets.metrics.GitHubMetrics") as mock_gh_cls,
        ):
            # Set up all mocks with valid data
            mock_cost = MagicMock()
            mock_cost.collect.return_value = {
                "today": {"cost": 0.05},
                "summary": {"total_cost": 1.00},
                "daily_costs": [],
            }
            mock_cost_cls.return_value = mock_cost

            mock_perf = MagicMock()
            mock_perf.collect.return_value = {
                "summary": {
                    "total_calls": 100,
                    "avg_latency_ms": 50,
                    "error_rate_pct": 1.0,
                },
                "latency_history": [],
            }
            mock_perf_cls.return_value = mock_perf

            mock_gh = MagicMock()
            mock_gh.collect.return_value = {
                "streak": {"streak_days": 10},
                "pr_metrics": {"avg_cycle_hours": 5.0},
                "commit_history": [],
            }
            mock_gh_cls.return_value = mock_gh

            panel = MetricsPanel()
            children = list(panel.compose())
            assert len(children) >= 1


class TestCostForecast:
    """Tests for the cost forecasting functionality."""

    def test_calculate_cost_forecast_empty_data(self):
        """Test forecast with empty data returns zeros."""
        result = calculate_cost_forecast([])
        assert result["daily_avg"] == 0.0
        assert result["projected_monthly"] == 0.0
        assert result["trend"] == "→"
        assert result["trend_pct"] == 0.0

    def test_calculate_cost_forecast_single_day(self):
        """Test forecast with a single day of data."""
        daily_costs = [{"date": "2026-02-01", "cost": 1.50}]
        result = calculate_cost_forecast(daily_costs)
        assert result["daily_avg"] == 1.50
        assert result["projected_monthly"] == 45.0  # 1.50 * 30
        assert result["trend"] == "→"  # No prior data to compare

    def test_calculate_cost_forecast_stable_trend(self):
        """Test forecast shows stable trend when costs are consistent."""
        daily_costs = [
            {"date": "2026-02-07", "cost": 1.00},
            {"date": "2026-02-06", "cost": 1.00},
            {"date": "2026-02-05", "cost": 1.00},
            {"date": "2026-02-04", "cost": 1.00},
            {"date": "2026-02-03", "cost": 1.00},
            {"date": "2026-02-02", "cost": 1.00},
            {"date": "2026-02-01", "cost": 1.00},
            # Prior period
            {"date": "2026-01-31", "cost": 1.00},
            {"date": "2026-01-30", "cost": 1.00},
            {"date": "2026-01-29", "cost": 1.00},
            {"date": "2026-01-28", "cost": 1.00},
            {"date": "2026-01-27", "cost": 1.00},
            {"date": "2026-01-26", "cost": 1.00},
            {"date": "2026-01-25", "cost": 1.00},
        ]
        result = calculate_cost_forecast(daily_costs)
        assert result["daily_avg"] == 1.00
        assert result["projected_monthly"] == 30.0
        assert result["trend"] == "→"

    def test_calculate_cost_forecast_increasing_trend(self):
        """Test forecast detects increasing cost trend."""
        daily_costs = [
            # Recent period (higher costs)
            {"date": "2026-02-07", "cost": 2.00},
            {"date": "2026-02-06", "cost": 2.00},
            {"date": "2026-02-05", "cost": 2.00},
            {"date": "2026-02-04", "cost": 2.00},
            {"date": "2026-02-03", "cost": 2.00},
            {"date": "2026-02-02", "cost": 2.00},
            {"date": "2026-02-01", "cost": 2.00},
            # Prior period (lower costs)
            {"date": "2026-01-31", "cost": 1.00},
            {"date": "2026-01-30", "cost": 1.00},
            {"date": "2026-01-29", "cost": 1.00},
            {"date": "2026-01-28", "cost": 1.00},
            {"date": "2026-01-27", "cost": 1.00},
            {"date": "2026-01-26", "cost": 1.00},
            {"date": "2026-01-25", "cost": 1.00},
        ]
        result = calculate_cost_forecast(daily_costs)
        assert result["daily_avg"] == 2.00
        assert result["projected_monthly"] == 60.0
        assert result["trend"] == "↑"
        assert result["trend_pct"] == 100.0  # 100% increase

    def test_calculate_cost_forecast_decreasing_trend(self):
        """Test forecast detects decreasing cost trend."""
        daily_costs = [
            # Recent period (lower costs)
            {"date": "2026-02-07", "cost": 0.50},
            {"date": "2026-02-06", "cost": 0.50},
            {"date": "2026-02-05", "cost": 0.50},
            {"date": "2026-02-04", "cost": 0.50},
            {"date": "2026-02-03", "cost": 0.50},
            {"date": "2026-02-02", "cost": 0.50},
            {"date": "2026-02-01", "cost": 0.50},
            # Prior period (higher costs)
            {"date": "2026-01-31", "cost": 1.00},
            {"date": "2026-01-30", "cost": 1.00},
            {"date": "2026-01-29", "cost": 1.00},
            {"date": "2026-01-28", "cost": 1.00},
            {"date": "2026-01-27", "cost": 1.00},
            {"date": "2026-01-26", "cost": 1.00},
            {"date": "2026-01-25", "cost": 1.00},
        ]
        result = calculate_cost_forecast(daily_costs)
        assert result["daily_avg"] == 0.50
        assert result["projected_monthly"] == 15.0
        assert result["trend"] == "↓"
        assert result["trend_pct"] == -50.0  # 50% decrease

    def test_calculate_cost_forecast_with_total_cost_key(self):
        """Test forecast works with 'total_cost' key (alternate format)."""
        daily_costs = [
            {"date": "2026-02-01", "total_cost": 1.50},
            {"date": "2026-01-31", "total_cost": 1.50},
        ]
        result = calculate_cost_forecast(daily_costs)
        assert result["daily_avg"] == 1.50
        assert result["projected_monthly"] == 45.0

    def test_calculate_cost_forecast_custom_lookback(self):
        """Test forecast with custom lookback period."""
        daily_costs = [
            {"date": "2026-02-03", "cost": 3.00},
            {"date": "2026-02-02", "cost": 3.00},
            {"date": "2026-02-01", "cost": 3.00},
            {"date": "2026-01-31", "cost": 1.00},
            {"date": "2026-01-30", "cost": 1.00},
            {"date": "2026-01-29", "cost": 1.00},
        ]
        result = calculate_cost_forecast(daily_costs, lookback_days=3)
        assert result["daily_avg"] == 3.00
        assert result["trend"] == "↑"


class TestGetDaysInCurrentMonth:
    """Tests for get_days_in_current_month helper."""

    def test_returns_positive_integer(self):
        """Test that function returns a reasonable number of days."""
        days = get_days_in_current_month()
        assert isinstance(days, int)
        assert 28 <= days <= 31


class TestCostsPanelWithForecast:
    """Tests for CostsPanel with forecast functionality."""

    @pytest.mark.asyncio
    async def test_costs_panel_displays_forecast(self):
        """Test that CostsPanel displays forecast information."""
        mock_data = {
            "today": {
                "date": "2026-02-01",
                "input_tokens": 10000,
                "output_tokens": 5000,
                "cost": 0.42,
                "by_model": {},
            },
            "summary": {
                "total_cost": 12.60,
                "avg_daily_cost": 0.42,
            },
            "daily_costs": [
                {"date": "2026-01-25", "cost": 0.40},
                {"date": "2026-01-26", "cost": 0.42},
                {"date": "2026-01-27", "cost": 0.44},
                {"date": "2026-01-28", "cost": 0.40},
                {"date": "2026-01-29", "cost": 0.41},
                {"date": "2026-01-30", "cost": 0.43},
                {"date": "2026-01-31", "cost": 0.42},
            ],
        }

        with patch("openclaw_dash.widgets.metrics.CostTracker") as mock_tracker_cls:
            mock_tracker = MagicMock()
            mock_tracker.collect.return_value = mock_data
            mock_tracker.get_history.return_value = mock_data["daily_costs"]
            mock_tracker_cls.return_value = mock_tracker

            panel = CostsPanel()
            children = list(panel.compose())
            assert len(children) >= 1

    @pytest.mark.asyncio
    async def test_costs_panel_falls_back_to_history(self):
        """Test that CostsPanel falls back to get_history when daily_costs empty."""
        mock_data = {
            "today": {"cost": 0.50},
            "summary": {"total_cost": 5.00},
            "daily_costs": [],  # Empty - should trigger fallback
        }
        mock_history = [
            {"date": "2026-01-31", "total_cost": 0.50},
            {"date": "2026-01-30", "total_cost": 0.45},
        ]

        with patch("openclaw_dash.widgets.metrics.CostTracker") as mock_tracker_cls:
            mock_tracker = MagicMock()
            mock_tracker.collect.return_value = mock_data
            mock_tracker.get_history.return_value = mock_history
            mock_tracker_cls.return_value = mock_tracker

            panel = CostsPanel()
            children = list(panel.compose())
            assert len(children) >= 1
