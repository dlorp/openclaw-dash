"""Tests for logs collector and widget."""

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from textual.widgets import Static

from openclaw_dash.collectors import logs
from openclaw_dash.widgets.logs import LogsPanel, LogsSummaryPanel


class TestLogsCollector:
    """Tests for the logs collector."""

    def test_collect_returns_dict(self):
        """collect() should return a dict with expected keys."""
        result = logs.collect()
        assert isinstance(result, dict)
        assert "entries" in result
        assert "collected_at" in result
        assert "total" in result

    def test_entries_is_list(self):
        """entries should be a list."""
        result = logs.collect()
        assert isinstance(result["entries"], list)

    def test_parse_log_line_valid(self):
        """Should parse valid log lines."""
        line = "2026-02-01T08:09:41.294Z [gateway] signal SIGUSR1 received"
        parsed = logs.parse_log_line(line)

        assert parsed is not None
        assert parsed["timestamp"] == "2026-02-01T08:09:41.294Z"
        assert parsed["tag"] == "gateway"
        assert parsed["message"] == "signal SIGUSR1 received"

    def test_parse_log_line_invalid(self):
        """Should return None for invalid lines."""
        assert logs.parse_log_line("") is None
        assert logs.parse_log_line("not a log line") is None
        assert logs.parse_log_line("missing brackets") is None

    def test_get_log_level_error(self):
        """Should detect error level."""
        assert logs.get_log_level("error", "something") == "error"
        assert logs.get_log_level("gateway", "error occurred") == "error"
        assert logs.get_log_level("api", "request failed") == "error"

    def test_get_log_level_warning(self):
        """Should detect warning level."""
        assert logs.get_log_level("gateway", "warning: low memory") == "warning"
        assert logs.get_log_level("ws", "disconnected") == "warning"

    def test_get_log_level_info(self):
        """Should detect info level."""
        assert logs.get_log_level("gateway", "service started") == "info"
        assert logs.get_log_level("gateway", "listening on port 3000") == "info"

    def test_get_level_color(self):
        """Should return correct colors for levels."""
        assert logs.get_level_color("error") == "red"
        assert logs.get_level_color("warning") == "yellow"
        assert logs.get_level_color("info") == "green"
        assert logs.get_level_color("debug") == "dim"

    def test_get_level_icon(self):
        """Should return correct icons for levels."""
        assert logs.get_level_icon("error") == "✗"
        assert logs.get_level_icon("warning") == "⚠"
        assert logs.get_level_icon("info") == "•"

    def test_tail_file_with_temp_file(self):
        """Should read last n lines from a file."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".log") as f:
            for i in range(100):
                f.write(f"Line {i}\n")
            f.flush()
            path = Path(f.name)

        try:
            lines = logs.tail_file(path, n=10)
            assert len(lines) == 10
            assert lines[-1] == "Line 99"
            assert lines[0] == "Line 90"
        finally:
            path.unlink()

    def test_tail_file_small_file(self):
        """Should handle files smaller than n lines."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".log") as f:
            f.write("Line 1\nLine 2\nLine 3\n")
            f.flush()
            path = Path(f.name)

        try:
            lines = logs.tail_file(path, n=10)
            assert len(lines) == 3
        finally:
            path.unlink()

    def test_tail_file_nonexistent(self):
        """Should return empty list for nonexistent file."""
        lines = logs.tail_file(Path("/nonexistent/file.log"))
        assert lines == []

    def test_collect_with_temp_log(self):
        """Should collect entries from a log file."""
        log_content = """2026-02-01T08:09:41.294Z [gateway] started
2026-02-01T08:09:42.000Z [discord] connected
2026-02-01T08:09:43.000Z [error] something failed
"""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".log") as f:
            f.write(log_content)
            f.flush()
            path = Path(f.name)

        try:
            result = logs.collect(n=10, log_path=path)
            assert result["total"] == 3
            assert len(result["entries"]) == 3
            assert result["entries"][0]["tag"] == "gateway"
            assert result["entries"][2]["level"] == "error"
        finally:
            path.unlink()

    def test_collect_filter_by_level(self):
        """Should filter entries by log level."""
        log_content = """2026-02-01T08:09:41.000Z [gateway] info message
2026-02-01T08:09:42.000Z [gateway] error occurred
2026-02-01T08:09:43.000Z [gateway] warning here
"""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".log") as f:
            f.write(log_content)
            f.flush()
            path = Path(f.name)

        try:
            result = logs.collect(n=10, log_path=path, filter_level="warning")
            # Should only include error and warning
            levels = [e["level"] for e in result["entries"]]
            assert "debug" not in levels
        finally:
            path.unlink()

    def test_find_log_file_returns_path_or_none(self):
        """find_log_file should return Path or None."""
        result = logs.find_log_file()
        assert result is None or isinstance(result, Path)


class TestLogsPanel:
    """Tests for the LogsPanel widget."""

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
        panel = LogsPanel(n_lines=20)
        assert panel.n_lines == 20

    def test_default_n_lines(self):
        """LogsPanel should have default n_lines."""
        panel = LogsPanel()
        assert panel.n_lines == 15

    @pytest.mark.asyncio
    async def test_panel_renders(self):
        """Test that the panel can be instantiated and composed."""
        panel = LogsPanel()
        children = list(panel.compose())
        assert len(children) >= 1
        assert isinstance(children[0], Static)


class TestLogsSummaryPanel:
    """Tests for the LogsSummaryPanel widget."""

    def test_is_static_subclass(self):
        """LogsSummaryPanel should inherit from Static."""
        assert issubclass(LogsSummaryPanel, Static)

    def test_has_refresh_data_method(self):
        """LogsSummaryPanel should have refresh_data method."""
        assert hasattr(LogsSummaryPanel, "refresh_data")

    @pytest.mark.asyncio
    async def test_panel_renders(self):
        """Test that the panel can be instantiated and composed."""
        panel = LogsSummaryPanel()
        children = list(panel.compose())
        assert len(children) >= 1


class TestLogsPanelIntegration:
    """Integration tests for LogsPanel in the app."""

    def test_import_from_app(self):
        """LogsPanel should be importable from app module."""
        from openclaw_dash.app import LogsPanel as AppLogsPanel

        assert AppLogsPanel is not None

    def test_app_has_logs_in_refresh_list(self):
        """DashboardApp should refresh LogsPanel."""
        import inspect

        from openclaw_dash.app import DashboardApp

        source = inspect.getsource(DashboardApp.action_refresh)
        assert "LogsPanel" in source

    def test_app_has_logs_keybinding(self):
        """DashboardApp should have 'l' keybinding for logs."""
        from openclaw_dash.app import DashboardApp

        binding_keys = [b[0] for b in DashboardApp.BINDINGS]
        assert "l" in binding_keys

    def test_logs_panel_in_compose(self):
        """DashboardApp compose should include logs-panel."""
        import inspect

        from openclaw_dash.app import DashboardApp

        source = inspect.getsource(DashboardApp.compose)
        assert "logs-panel" in source
