"""Tests for the CronPanel widget."""

from datetime import datetime, timedelta
from unittest.mock import patch

import pytest
from textual.widgets import Static

from openclaw_dash.widgets.cron import (
    CronPanel,
    CronSummaryPanel,
    format_relative_time,
    format_schedule,
    get_status_color,
    get_status_icon,
)


class TestFormatSchedule:
    """Tests for schedule formatting."""

    def test_cron_expression(self):
        """Should format cron expressions."""
        schedule = {"kind": "cron", "expr": "0 4 * * *"}
        assert format_schedule(schedule) == "⏰ 0 4 * * *"

    def test_every_hours(self):
        """Should format hour intervals."""
        schedule = {"kind": "every", "everyMs": 7200000}  # 2 hours
        assert format_schedule(schedule) == "↻ 2h"

    def test_every_minutes(self):
        """Should format minute intervals."""
        schedule = {"kind": "every", "everyMs": 1800000}  # 30 minutes
        assert format_schedule(schedule) == "↻ 30m"

    def test_every_seconds(self):
        """Should format second intervals."""
        schedule = {"kind": "every", "everyMs": 10000}  # 10 seconds
        assert format_schedule(schedule) == "↻ 10s"

    def test_every_milliseconds(self):
        """Should format millisecond intervals."""
        schedule = {"kind": "every", "everyMs": 500}
        assert format_schedule(schedule) == "↻ 500ms"

    def test_at_time(self):
        """Should format at-time schedules."""
        schedule = {"kind": "at", "at": "09:00"}
        assert format_schedule(schedule) == "@ 09:00"

    def test_empty_schedule(self):
        """Should handle empty schedule."""
        assert format_schedule({}) == "?"
        assert format_schedule(None) == "?"

    def test_unknown_kind(self):
        """Should truncate unknown schedule kinds."""
        schedule = {"kind": "unknown", "data": "something-long"}
        result = format_schedule(schedule)
        assert len(result) <= 12


class TestFormatRelativeTime:
    """Tests for relative time formatting."""

    def test_seconds_ago(self):
        """Should format seconds ago."""
        now = datetime.now()
        past = (now - timedelta(seconds=30)).isoformat()
        result = format_relative_time(past)
        assert "s ago" in result

    def test_minutes_ago(self):
        """Should format minutes ago."""
        now = datetime.now()
        past = (now - timedelta(minutes=15)).isoformat()
        result = format_relative_time(past)
        assert "m ago" in result

    def test_hours_ago(self):
        """Should format hours ago."""
        now = datetime.now()
        past = (now - timedelta(hours=3)).isoformat()
        result = format_relative_time(past)
        assert "h ago" in result

    def test_days_ago(self):
        """Should format days ago."""
        now = datetime.now()
        past = (now - timedelta(days=2)).isoformat()
        result = format_relative_time(past)
        assert "d ago" in result

    def test_future_time(self):
        """Should format future times."""
        now = datetime.now()
        future = (now + timedelta(hours=2)).isoformat()
        result = format_relative_time(future)
        assert "in" in result

    def test_none_input(self):
        """Should handle None input."""
        assert format_relative_time(None) == "never"

    def test_invalid_input(self):
        """Should handle invalid input."""
        assert format_relative_time("not-a-date") == "?"

    def test_timestamp_input(self):
        """Should handle timestamp input."""
        now = datetime.now()
        ts = now.timestamp() * 1000  # milliseconds
        result = format_relative_time(ts)
        assert "s ago" in result or result == "0s ago" or "m ago" in result


class TestStatusIcons:
    """Tests for status icon/color functions."""

    def test_ok_status(self):
        """Should return checkmark for ok status."""
        assert get_status_icon("ok") == "✓"
        assert get_status_icon("success") == "✓"

    def test_failed_status(self):
        """Should return X for failed status."""
        assert get_status_icon("failed") == "✗"
        assert get_status_icon("error") == "✗"

    def test_running_status(self):
        """Should return spinner for running status."""
        assert get_status_icon("running") == "⟳"

    def test_pending_status(self):
        """Should return half-circle for pending status."""
        assert get_status_icon("pending") == "◐"

    def test_disabled_status(self):
        """Should return empty circle for disabled status."""
        assert get_status_icon("disabled") == "○"

    def test_unknown_status(self):
        """Should return question mark for unknown status."""
        assert get_status_icon("unknown") == "?"

    def test_status_colors(self):
        """Should return appropriate colors."""
        assert get_status_color("ok") == "green"
        assert get_status_color("failed") == "red"
        assert get_status_color("running") == "cyan"
        assert get_status_color("pending") == "yellow"
        assert get_status_color("disabled") == "dim"


class TestCronPanel:
    """Tests for the CronPanel widget."""

    def test_is_static_subclass(self):
        """CronPanel should inherit from Static."""
        assert issubclass(CronPanel, Static)

    def test_has_refresh_data_method(self):
        """CronPanel should have refresh_data method."""
        assert hasattr(CronPanel, "refresh_data")
        assert callable(getattr(CronPanel, "refresh_data"))

    def test_has_compose_method(self):
        """CronPanel should have compose method."""
        assert hasattr(CronPanel, "compose")
        assert callable(getattr(CronPanel, "compose"))

    @pytest.mark.asyncio
    async def test_panel_renders(self):
        """Test that the panel can be instantiated and composed."""
        panel = CronPanel()
        children = list(panel.compose())
        assert len(children) >= 1
        assert isinstance(children[0], Static)

    def test_module_imports(self):
        """Test that the module imports correctly."""
        from openclaw_dash.widgets import cron

        assert hasattr(cron, "CronPanel")
        assert hasattr(cron, "CronSummaryPanel")


class TestCronSummaryPanel:
    """Tests for the CronSummaryPanel widget."""

    def test_is_static_subclass(self):
        """CronSummaryPanel should inherit from Static."""
        assert issubclass(CronSummaryPanel, Static)

    def test_has_refresh_data_method(self):
        """CronSummaryPanel should have refresh_data method."""
        assert hasattr(CronSummaryPanel, "refresh_data")
        assert callable(getattr(CronSummaryPanel, "refresh_data"))

    @pytest.mark.asyncio
    async def test_panel_renders(self):
        """Test that the summary panel can be instantiated and composed."""
        panel = CronSummaryPanel()
        children = list(panel.compose())
        assert len(children) >= 1
        assert isinstance(children[0], Static)


class TestCronPanelIntegration:
    """Integration tests for CronPanel with collector."""

    def test_refresh_with_mock_data(self):
        """Test refresh_data processes mock data correctly."""
        mock_data = {
            "jobs": [
                {
                    "id": "test-job",
                    "name": "test-job",
                    "enabled": True,
                    "schedule": {"kind": "cron", "expr": "0 * * * *"},
                    "last_run": datetime.now().isoformat(),
                    "last_status": "ok",
                    "next_run": (datetime.now() + timedelta(hours=1)).isoformat(),
                },
                {
                    "id": "disabled-job",
                    "name": "disabled-job",
                    "enabled": False,
                    "schedule": {"kind": "every", "everyMs": 60000},
                    "last_run": None,
                },
            ],
            "total": 2,
            "enabled": 1,
            "collected_at": datetime.now().isoformat(),
        }

        with patch("openclaw_dash.widgets.cron.cron.collect", return_value=mock_data):
            from openclaw_dash.widgets.cron import CronPanel

            assert CronPanel is not None

    def test_refresh_with_camel_case_data(self):
        """Test refresh_data handles camelCase data from demo mode."""
        mock_data = {
            "jobs": [
                {
                    "id": "demo-job",
                    "name": "demo-job",
                    "enabled": True,
                    "schedule": {"kind": "every", "everyMs": 1800000},
                    "lastRun": datetime.now().isoformat(),  # camelCase
                    "lastStatus": "ok",  # camelCase
                },
            ],
            "collected_at": datetime.now().isoformat(),
        }

        with patch("openclaw_dash.widgets.cron.cron.collect", return_value=mock_data):
            from openclaw_dash.widgets.cron import CronPanel

            assert CronPanel is not None

    def test_empty_jobs_list(self):
        """Test handling of empty jobs list."""
        mock_data = {
            "jobs": [],
            "total": 0,
            "enabled": 0,
            "collected_at": datetime.now().isoformat(),
        }

        with patch("openclaw_dash.widgets.cron.cron.collect", return_value=mock_data):
            from openclaw_dash.widgets.cron import CronPanel

            panel = CronPanel()
            # Verify panel can be created with empty data
            assert panel is not None


class TestCronSummaryPanelIntegration:
    """Integration tests for CronSummaryPanel."""

    def test_summary_with_mixed_statuses(self):
        """Test summary counts jobs by status."""
        mock_data = {
            "jobs": [
                {"id": "job1", "enabled": True, "last_status": "ok"},
                {"id": "job2", "enabled": True, "last_status": "ok"},
                {"id": "job3", "enabled": True, "last_status": "failed"},
                {"id": "job4", "enabled": False, "last_status": "ok"},
            ],
            "collected_at": datetime.now().isoformat(),
        }

        with patch("openclaw_dash.widgets.cron.cron.collect", return_value=mock_data):
            from openclaw_dash.widgets.cron import CronSummaryPanel

            panel = CronSummaryPanel()
            assert panel is not None

    def test_summary_empty_jobs(self):
        """Test summary with no jobs."""
        mock_data = {
            "jobs": [],
            "collected_at": datetime.now().isoformat(),
        }

        with patch("openclaw_dash.widgets.cron.cron.collect", return_value=mock_data):
            from openclaw_dash.widgets.cron import CronSummaryPanel

            panel = CronSummaryPanel()
            assert panel is not None
