"""Comprehensive tests for the LogsPanel and LogsSummaryPanel widgets."""

from unittest.mock import patch

import pytest
from textual.app import App, ComposeResult
from textual.widgets import Static

from openclaw_dash.widgets.logs import LogsPanel, LogsSummaryPanel


class LogsPanelTestApp(App):
    """Test app for mounting LogsPanel."""

    def compose(self) -> ComposeResult:
        yield LogsPanel(id="test-logs", n_lines=10)


class LogsSummaryTestApp(App):
    """Test app for mounting LogsSummaryPanel."""

    def compose(self) -> ComposeResult:
        yield LogsSummaryPanel(id="test-logs-summary")


class TestLogsPanelWidget:
    """Tests for LogsPanel widget class."""

    def test_is_static_subclass(self):
        """LogsPanel should inherit from Static."""
        assert issubclass(LogsPanel, Static)

    def test_has_refresh_data_method(self):
        """LogsPanel should have refresh_data method."""
        assert hasattr(LogsPanel, "refresh_data")
        assert callable(getattr(LogsPanel, "refresh_data"))

    def test_has_compose_method(self):
        """LogsPanel should have compose method."""
        assert hasattr(LogsPanel, "compose")
        assert callable(getattr(LogsPanel, "compose"))

    def test_accepts_n_lines_parameter(self):
        """LogsPanel should accept n_lines parameter."""
        panel = LogsPanel(n_lines=25)
        assert panel.n_lines == 25

    def test_default_n_lines(self):
        """LogsPanel should have default n_lines of 15."""
        panel = LogsPanel()
        assert panel.n_lines == 15

    @pytest.mark.asyncio
    async def test_panel_compose_yields_static(self):
        """Test that compose yields a Static widget."""
        panel = LogsPanel()
        children = list(panel.compose())
        assert len(children) >= 1
        assert isinstance(children[0], Static)

    @pytest.mark.asyncio
    async def test_panel_content_has_id(self):
        """Test that the content widget has correct ID."""
        panel = LogsPanel()
        children = list(panel.compose())
        content = children[0]
        assert content.id == "logs-content"


class TestLogsPanelFormatTime:
    """Tests for LogsPanel._format_time method."""

    def test_format_time_iso_with_z(self):
        """Test formatting ISO timestamp with Z suffix."""
        panel = LogsPanel()
        result = panel._format_time("2026-02-01T08:09:41.294Z")
        assert result == "08:09:41"

    def test_format_time_iso_with_offset(self):
        """Test formatting ISO timestamp with timezone offset."""
        panel = LogsPanel()
        result = panel._format_time("2026-02-01T08:09:41.294+00:00")
        assert result == "08:09:41"

    def test_format_time_empty_string(self):
        """Test formatting empty timestamp."""
        panel = LogsPanel()
        result = panel._format_time("")
        assert result == "??:??"

    def test_format_time_invalid(self):
        """Test formatting invalid timestamp."""
        panel = LogsPanel()
        result = panel._format_time("not-a-timestamp")
        # Should return fallback (first 8 chars)
        assert result == "not-a-ti"

    def test_format_time_with_t_separator(self):
        """Test formatting timestamp with T separator but invalid format."""
        panel = LogsPanel()
        result = panel._format_time("2026-02-01Tinvalid")
        # Should extract time portion after T
        assert result == "invalid"[:8]


class TestLogsPanelIntegration:
    """Integration tests for LogsPanel in an app context."""

    @pytest.mark.asyncio
    async def test_panel_mounts_correctly(self):
        """Test that panel mounts without errors."""
        app = LogsPanelTestApp()
        async with app.run_test():
            panel = app.query_one(LogsPanel)
            assert panel is not None

    @pytest.mark.asyncio
    async def test_refresh_with_error(self):
        """Test refresh_data with error response."""
        mock_data = {
            "entries": [],
            "error": "Log file not found",
            "collected_at": "2026-02-01T12:00:00",
            "total": 0,
            "levels": {},
        }

        app = LogsPanelTestApp()
        async with app.run_test():
            with patch(
                "openclaw_dash.widgets.logs.logs.collect",
                return_value=mock_data,
            ) as mock_collect:
                panel = app.query_one(LogsPanel)
                panel.refresh_data()
                mock_collect.assert_called_once()

    @pytest.mark.asyncio
    async def test_refresh_with_no_entries(self):
        """Test refresh_data with no log entries."""
        mock_data = {
            "entries": [],
            "collected_at": "2026-02-01T12:00:00",
            "total": 0,
            "levels": {},
        }

        app = LogsPanelTestApp()
        async with app.run_test():
            with patch(
                "openclaw_dash.widgets.logs.logs.collect",
                return_value=mock_data,
            ) as mock_collect:
                panel = app.query_one(LogsPanel)
                panel.refresh_data()
                mock_collect.assert_called_once()

    @pytest.mark.asyncio
    async def test_refresh_with_log_entries(self):
        """Test refresh_data with log entries."""
        mock_data = {
            "entries": [
                {
                    "timestamp": "2026-02-01T08:09:41.294Z",
                    "tag": "gateway",
                    "message": "Service started",
                    "level": "info",
                },
                {
                    "timestamp": "2026-02-01T08:09:42.000Z",
                    "tag": "discord",
                    "message": "Connected to server",
                    "level": "info",
                },
            ],
            "collected_at": "2026-02-01T12:00:00",
            "total": 2,
            "levels": {"info": 2},
        }

        app = LogsPanelTestApp()
        async with app.run_test():
            with patch(
                "openclaw_dash.widgets.logs.logs.collect",
                return_value=mock_data,
            ) as mock_collect:
                panel = app.query_one(LogsPanel)
                panel.refresh_data()
                mock_collect.assert_called_once()

    @pytest.mark.asyncio
    async def test_refresh_with_level_summary(self):
        """Test refresh_data with errors/warnings shows level summary."""
        mock_data = {
            "entries": [
                {
                    "timestamp": "2026-02-01T08:09:41.294Z",
                    "tag": "gateway",
                    "message": "Error occurred",
                    "level": "error",
                },
                {
                    "timestamp": "2026-02-01T08:09:42.000Z",
                    "tag": "discord",
                    "message": "Warning message",
                    "level": "warning",
                },
            ],
            "collected_at": "2026-02-01T12:00:00",
            "total": 2,
            "levels": {"error": 1, "warning": 1},
        }

        app = LogsPanelTestApp()
        async with app.run_test():
            with patch(
                "openclaw_dash.widgets.logs.logs.collect",
                return_value=mock_data,
            ) as mock_collect:
                panel = app.query_one(LogsPanel)
                panel.refresh_data()
                mock_collect.assert_called_once()

    @pytest.mark.asyncio
    async def test_refresh_handles_long_messages(self):
        """Test that refresh_data handles long messages (truncation)."""
        long_message = "A" * 100  # Message longer than 50 chars

        mock_data = {
            "entries": [
                {
                    "timestamp": "2026-02-01T08:09:41.294Z",
                    "tag": "gateway",
                    "message": long_message,
                    "level": "info",
                },
            ],
            "collected_at": "2026-02-01T12:00:00",
            "total": 1,
            "levels": {"info": 1},
        }

        app = LogsPanelTestApp()
        async with app.run_test():
            with patch(
                "openclaw_dash.widgets.logs.logs.collect",
                return_value=mock_data,
            ) as mock_collect:
                panel = app.query_one(LogsPanel)
                # Should not raise even with long message
                panel.refresh_data()
                mock_collect.assert_called_once()

    @pytest.mark.asyncio
    async def test_refresh_handles_all_levels(self):
        """Test that refresh_data handles all log levels."""
        mock_data = {
            "entries": [
                {
                    "timestamp": "2026-02-01T08:09:41.000Z",
                    "tag": "a",
                    "message": "m",
                    "level": "error",
                },
                {
                    "timestamp": "2026-02-01T08:09:42.000Z",
                    "tag": "b",
                    "message": "m",
                    "level": "warning",
                },
                {
                    "timestamp": "2026-02-01T08:09:43.000Z",
                    "tag": "c",
                    "message": "m",
                    "level": "info",
                },
                {
                    "timestamp": "2026-02-01T08:09:44.000Z",
                    "tag": "d",
                    "message": "m",
                    "level": "debug",
                },
            ],
            "collected_at": "2026-02-01T12:00:00",
            "total": 4,
            "levels": {"error": 1, "warning": 1, "info": 1, "debug": 1},
        }

        app = LogsPanelTestApp()
        async with app.run_test():
            with patch(
                "openclaw_dash.widgets.logs.logs.collect",
                return_value=mock_data,
            ) as mock_collect:
                panel = app.query_one(LogsPanel)
                panel.refresh_data()
                mock_collect.assert_called_once()


class TestLogsSummaryPanelWidget:
    """Tests for LogsSummaryPanel widget class."""

    def test_is_static_subclass(self):
        """LogsSummaryPanel should inherit from Static."""
        assert issubclass(LogsSummaryPanel, Static)

    def test_has_refresh_data_method(self):
        """LogsSummaryPanel should have refresh_data method."""
        assert hasattr(LogsSummaryPanel, "refresh_data")
        assert callable(getattr(LogsSummaryPanel, "refresh_data"))

    @pytest.mark.asyncio
    async def test_panel_compose_yields_static(self):
        """Test that compose yields a Static widget."""
        panel = LogsSummaryPanel()
        children = list(panel.compose())
        assert len(children) >= 1
        assert isinstance(children[0], Static)

    @pytest.mark.asyncio
    async def test_panel_content_has_id(self):
        """Test that the content widget has correct ID."""
        panel = LogsSummaryPanel()
        children = list(panel.compose())
        content = children[0]
        assert content.id == "logs-summary"


class TestLogsSummaryPanelIntegration:
    """Integration tests for LogsSummaryPanel."""

    @pytest.mark.asyncio
    async def test_panel_mounts_correctly(self):
        """Test that panel mounts without errors."""
        app = LogsSummaryTestApp()
        async with app.run_test():
            panel = app.query_one(LogsSummaryPanel)
            assert panel is not None

    @pytest.mark.asyncio
    async def test_refresh_with_error(self):
        """Test refresh_data with error response."""
        mock_data = {
            "entries": [],
            "error": "Log file not found",
            "collected_at": "2026-02-01T12:00:00",
            "total": 0,
            "levels": {},
        }

        app = LogsSummaryTestApp()
        async with app.run_test():
            with patch(
                "openclaw_dash.widgets.logs.logs.collect",
                return_value=mock_data,
            ) as mock_collect:
                panel = app.query_one(LogsSummaryPanel)
                panel.refresh_data()
                mock_collect.assert_called_once()

    @pytest.mark.asyncio
    async def test_refresh_no_issues(self):
        """Test refresh_data with no errors or warnings."""
        mock_data = {
            "entries": [],
            "collected_at": "2026-02-01T12:00:00",
            "total": 5,
            "levels": {"info": 3, "debug": 2},
        }

        app = LogsSummaryTestApp()
        async with app.run_test():
            with patch(
                "openclaw_dash.widgets.logs.logs.collect",
                return_value=mock_data,
            ) as mock_collect:
                panel = app.query_one(LogsSummaryPanel)
                panel.refresh_data()
                mock_collect.assert_called_once()

    @pytest.mark.asyncio
    async def test_refresh_with_errors(self):
        """Test refresh_data with errors."""
        mock_data = {
            "entries": [
                {
                    "timestamp": "2026-02-01T08:09:41.294Z",
                    "tag": "gateway",
                    "message": "Critical failure",
                    "level": "error",
                },
            ],
            "collected_at": "2026-02-01T12:00:00",
            "total": 1,
            "levels": {"error": 3},
        }

        app = LogsSummaryTestApp()
        async with app.run_test():
            with patch(
                "openclaw_dash.widgets.logs.logs.collect",
                return_value=mock_data,
            ) as mock_collect:
                panel = app.query_one(LogsSummaryPanel)
                panel.refresh_data()
                mock_collect.assert_called_once()

    @pytest.mark.asyncio
    async def test_refresh_with_warnings(self):
        """Test refresh_data with warnings."""
        mock_data = {
            "entries": [
                {
                    "timestamp": "2026-02-01T08:09:41.294Z",
                    "tag": "gateway",
                    "message": "Low memory",
                    "level": "warning",
                },
            ],
            "collected_at": "2026-02-01T12:00:00",
            "total": 1,
            "levels": {"warning": 2},
        }

        app = LogsSummaryTestApp()
        async with app.run_test():
            with patch(
                "openclaw_dash.widgets.logs.logs.collect",
                return_value=mock_data,
            ) as mock_collect:
                panel = app.query_one(LogsSummaryPanel)
                panel.refresh_data()
                mock_collect.assert_called_once()

    @pytest.mark.asyncio
    async def test_refresh_with_errors_and_warnings(self):
        """Test refresh_data with both errors and warnings."""
        mock_data = {
            "entries": [
                {
                    "timestamp": "2026-02-01T08:09:41.000Z",
                    "tag": "a",
                    "message": "err",
                    "level": "error",
                },
                {
                    "timestamp": "2026-02-01T08:09:42.000Z",
                    "tag": "b",
                    "message": "warn",
                    "level": "warning",
                },
            ],
            "collected_at": "2026-02-01T12:00:00",
            "total": 2,
            "levels": {"error": 5, "warning": 3},
        }

        app = LogsSummaryTestApp()
        async with app.run_test():
            with patch(
                "openclaw_dash.widgets.logs.logs.collect",
                return_value=mock_data,
            ) as mock_collect:
                panel = app.query_one(LogsSummaryPanel)
                panel.refresh_data()
                mock_collect.assert_called_once()


class TestLogsPanelAppIntegration:
    """Tests for LogsPanel integration with DashboardApp."""

    def test_import_from_app(self):
        """LogsPanel should be importable from app module."""
        from openclaw_dash.app import LogsPanel as AppLogsPanel

        assert AppLogsPanel is not None
        assert AppLogsPanel is LogsPanel

    def test_app_has_logs_keybinding(self):
        """DashboardApp should have 'l' keybinding for logs."""
        from openclaw_dash.app import DashboardApp

        binding_keys = [b[0] for b in DashboardApp.BINDINGS]
        assert "l" in binding_keys

    def test_app_has_logs_in_refresh_list(self):
        """DashboardApp should refresh LogsPanel."""
        import inspect

        from openclaw_dash.app import DashboardApp

        source = inspect.getsource(DashboardApp.action_refresh)
        assert "LogsPanel" in source

    def test_app_has_logs_in_auto_refresh(self):
        """DashboardApp should auto-refresh LogsPanel."""
        import inspect

        from openclaw_dash.app import DashboardApp

        source = inspect.getsource(DashboardApp._do_auto_refresh)
        assert "LogsPanel" in source

    def test_logs_panel_in_compose(self):
        """DashboardApp compose should include logs-panel."""
        import inspect

        from openclaw_dash.app import DashboardApp

        source = inspect.getsource(DashboardApp.compose)
        assert "logs-panel" in source
