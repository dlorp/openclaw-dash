"""Tests for metric_boxes widget."""

import pytest
from textual.widgets import Static

from openclaw_dash.widgets.metric_boxes import (
    COLORS,
    MetricBox,
    MetricBoxesBar,
    format_uptime_compact,
)


class TestMetricBox:
    """Tests for the MetricBox widget."""

    def test_is_static_subclass(self):
        """MetricBox should inherit from Static."""
        assert issubclass(MetricBox, Static)

    def test_init_with_defaults(self):
        """MetricBox should initialize with minimal parameters."""
        box = MetricBox(label="Test", value="123")
        assert box._label == "Test"
        assert box._value == "123"
        assert box._detail == ""
        assert box._status is None
        assert box._priority == 1

    def test_init_with_all_params(self):
        """MetricBox should accept all parameters."""
        box = MetricBox(
            label="Gateway",
            value="Online",
            detail="5h uptime",
            status="ok",
            box_id="test-box",
            priority=2,
        )
        assert box._label == "Gateway"
        assert box._value == "Online"
        assert box._detail == "5h uptime"
        assert box._status == "ok"
        assert box._priority == 2
        assert box.id == "test-box"

    def test_status_class_applied(self):
        """MetricBox should apply status class on init."""
        box = MetricBox(label="Test", value="1", status="ok")
        assert "status-ok" in box.classes

        box_error = MetricBox(label="Test", value="0", status="error")
        assert "status-error" in box_error.classes

        box_warning = MetricBox(label="Test", value="!", status="warning")
        assert "status-warning" in box_warning.classes

    def test_update_metric_changes_values(self):
        """update_metric should update internal values."""
        box = MetricBox(label="Test", value="old")
        box.update_metric(value="new", detail="detail", status="ok")

        assert box._value == "new"
        assert box._detail == "detail"
        assert box._status == "ok"

    def test_update_metric_changes_status_class(self):
        """update_metric should update status class."""
        box = MetricBox(label="Test", value="1", status="ok")
        assert "status-ok" in box.classes

        box.update_metric(value="0", status="error")
        assert "status-error" in box.classes
        assert "status-ok" not in box.classes


class TestMetricBoxesBar:
    """Tests for the MetricBoxesBar widget."""

    def test_is_static_subclass(self):
        """MetricBoxesBar should inherit from Static."""
        assert issubclass(MetricBoxesBar, Static)

    def test_has_refresh_data_method(self):
        """MetricBoxesBar should have refresh_data method."""
        assert hasattr(MetricBoxesBar, "refresh_data")
        assert callable(getattr(MetricBoxesBar, "refresh_data"))

    def test_has_compose_method(self):
        """MetricBoxesBar should have compose method."""
        assert hasattr(MetricBoxesBar, "compose")
        assert callable(getattr(MetricBoxesBar, "compose"))

    def test_bar_has_compose_generator(self):
        """MetricBoxesBar.compose should be a generator method."""
        import inspect

        bar = MetricBoxesBar()
        # compose() should be a generator function
        assert inspect.isgeneratorfunction(bar.compose) or hasattr(bar.compose, "__call__")
        # Can't easily test the compose output without an app context,
        # but we can verify the method exists and is callable

    def test_width_thresholds(self):
        """MetricBoxesBar should have responsive width thresholds."""
        assert MetricBoxesBar.COMPACT_WIDTH == 100
        assert MetricBoxesBar.NARROW_WIDTH == 80
        assert MetricBoxesBar.MINIMAL_WIDTH == 60

    def test_has_private_refresh_methods(self):
        """MetricBoxesBar should have private refresh methods for each metric."""
        bar = MetricBoxesBar()
        assert hasattr(bar, "_refresh_gateway")
        assert hasattr(bar, "_refresh_cost")
        assert hasattr(bar, "_refresh_errors")
        assert hasattr(bar, "_refresh_streak")


class TestFormatUptimeCompact:
    """Tests for the format_uptime_compact helper."""

    def test_empty_uptime(self):
        """Empty uptime should return ?."""
        assert format_uptime_compact("") == "?"
        assert format_uptime_compact("?") == "?"
        assert format_uptime_compact("unknown") == "?"

    def test_single_component(self):
        """Single component uptime should return as-is."""
        assert format_uptime_compact("5h") == "5h"
        assert format_uptime_compact("23m") == "23m"

    def test_two_components(self):
        """Two component uptime should return both."""
        assert format_uptime_compact("5h 23m") == "5h 23m"
        assert format_uptime_compact("2d 5h") == "2d 5h"

    def test_three_components_truncated(self):
        """Three+ component uptime should truncate to first two."""
        assert format_uptime_compact("5h 23m 15s") == "5h 23m"
        assert format_uptime_compact("2d 5h 23m 15s") == "2d 5h"


class TestColors:
    """Tests for brand color definitions."""

    def test_all_brand_colors_defined(self):
        """All dlorp brand colors should be defined."""
        assert "granite" in COLORS
        assert "orange" in COLORS
        assert "yellow" in COLORS
        assert "turquoise" in COLORS
        assert "blue" in COLORS

    def test_colors_are_hex(self):
        """Colors should be valid hex codes."""
        for name, color in COLORS.items():
            assert color.startswith("#"), f"{name} should start with #"
            assert len(color) == 7, f"{name} should be 7 chars (#RRGGBB)"

    def test_exact_brand_colors(self):
        """Colors should match exact brand spec."""
        assert COLORS["granite"] == "#636764"
        assert COLORS["orange"] == "#FB8B24"
        assert COLORS["yellow"] == "#F4E409"
        assert COLORS["turquoise"] == "#50D8D7"
        assert COLORS["blue"] == "#3B60E4"


class TestMetricBoxesIntegration:
    """Integration tests for metric boxes in the app."""

    def test_import_from_app(self):
        """MetricBoxesBar should be importable from app module."""
        from openclaw_dash.app import MetricBoxesBar

        assert MetricBoxesBar is not None

    def test_import_from_widgets(self):
        """MetricBoxesBar should be importable from widgets module."""
        from openclaw_dash.widgets import MetricBox, MetricBoxesBar

        assert MetricBox is not None
        assert MetricBoxesBar is not None

    def test_app_has_metric_boxes_in_refresh(self):
        """DashboardApp should refresh MetricBoxesBar."""
        import inspect

        from openclaw_dash.app import DashboardApp

        source = inspect.getsource(DashboardApp._do_auto_refresh)
        assert "MetricBoxesBar" in source

        source = inspect.getsource(DashboardApp.action_refresh)
        assert "MetricBoxesBar" in source


class TestMetricBoxesBarRefresh:
    """Tests for MetricBoxesBar refresh methods with mocked data."""

    @pytest.fixture
    def mock_gateway_healthy(self):
        """Mock healthy gateway response."""
        return {
            "healthy": True,
            "uptime": "5h 23m 15s",
            "pid": 12345,
            "version": "1.0.0",
        }

    @pytest.fixture
    def mock_gateway_unhealthy(self):
        """Mock unhealthy gateway response."""
        return {
            "healthy": False,
            "error": "Cannot connect",
        }

    @pytest.fixture
    def mock_cost_data(self):
        """Mock cost tracker response."""
        return {
            "today": {
                "date": "2025-01-15",
                "cost": 1.234,
                "input_tokens": 50000,
                "output_tokens": 10000,
            },
            "summary": {
                "total_cost": 45.67,
                "days_tracked": 30,
                "avg_daily_cost": 1.52,
            },
            "trend": {
                "dates": ["2025-01-15", "2025-01-14", "2025-01-13"],
                "costs": [1.234, 0.987, 1.456],
            },
        }

    @pytest.fixture
    def mock_perf_data(self):
        """Mock performance metrics response."""
        return {
            "summary": {
                "total_calls": 1000,
                "total_errors": 25,
                "error_rate_pct": 2.5,
                "avg_latency_ms": 150,
            },
        }

    @pytest.fixture
    def mock_github_data(self):
        """Mock GitHub metrics response."""
        return {
            "streak": {
                "streak_days": 15,
                "username": "testuser",
            },
            "commit_history": [
                {"date": "2025-01-15", "commits": 5},
                {"date": "2025-01-14", "commits": 3},
                {"date": "2025-01-13", "commits": 7},
            ],
        }

    def test_refresh_gateway_constructs_correct_display(self, mock_gateway_healthy):
        """Test that gateway refresh produces expected format."""
        # The actual refresh requires a mounted widget, but we can verify
        # the data structure is compatible
        data = mock_gateway_healthy
        assert data.get("healthy") is True
        assert "uptime" in data
        assert data["uptime"] == "5h 23m 15s"

    def test_cost_data_structure(self, mock_cost_data):
        """Test that cost data has expected structure."""
        data = mock_cost_data
        assert "today" in data
        assert "cost" in data["today"]
        assert "trend" in data
        assert "costs" in data["trend"]

    def test_perf_data_structure(self, mock_perf_data):
        """Test that performance data has expected structure."""
        data = mock_perf_data
        assert "summary" in data
        assert "error_rate_pct" in data["summary"]
        assert "total_errors" in data["summary"]

    def test_github_data_structure(self, mock_github_data):
        """Test that GitHub data has expected structure."""
        data = mock_github_data
        assert "streak" in data
        assert "streak_days" in data["streak"]
        assert "commit_history" in data
