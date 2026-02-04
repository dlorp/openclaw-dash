"""Tests for CLI."""

from unittest.mock import MagicMock, patch

import pytest

from openclaw_dash.cli import get_status, main, run_tui


class TestCLI:
    def test_get_status_returns_dict(self):
        result = get_status()
        assert isinstance(result, dict)
        assert "gateway" in result
        assert "sessions" in result
        assert "repos" in result
        assert "activity" in result

    @patch("sys.argv", ["openclaw-dash", "--version"])
    def test_version_flag(self):
        with pytest.raises(SystemExit) as exc:
            main()
        assert exc.value.code == 0

    @patch("openclaw_dash.cli.with_gateway_timeout")
    @patch("sys.argv", ["openclaw-dash", "--status", "--json"])
    def test_json_output(self, mock_timeout, capsys):
        mock_timeout.return_value = {
            "gateway": {"status": "connected"},
            "sessions": [],
            "repos": [],
            "activity": [],
        }
        result = main()
        assert result == 0
        import json

        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert "gateway" in data

    @patch("openclaw_dash.cli.run_tui")
    @patch("sys.argv", ["openclaw-dash", "--watch"])
    def test_watch_flag_long(self, mock_run_tui):
        """Test that --watch sets 5s refresh interval."""
        main()
        mock_run_tui.assert_called_once_with(refresh_interval=5)

    @patch("openclaw_dash.cli.run_tui")
    @patch("sys.argv", ["openclaw-dash", "-w"])
    def test_watch_flag_short(self, mock_run_tui):
        """Test that -w flag also works."""
        main()
        mock_run_tui.assert_called_once_with(refresh_interval=5)

    @patch("openclaw_dash.cli.run_tui")
    @patch("sys.argv", ["openclaw-dash"])
    def test_default_refresh_interval(self, mock_run_tui):
        """Test that default refresh interval is None (uses config)."""
        main()
        mock_run_tui.assert_called_once_with(refresh_interval=None)


class TestRunTui:
    @patch("openclaw_dash.app.DashboardApp")
    def test_run_tui_default_interval(self, mock_app_class):
        """Test run_tui passes None by default."""
        mock_app = MagicMock()
        mock_app_class.return_value = mock_app
        run_tui()
        mock_app_class.assert_called_once_with(refresh_interval=None)
        mock_app.run.assert_called_once()

    @patch("openclaw_dash.app.DashboardApp")
    def test_run_tui_watch_mode_interval(self, mock_app_class):
        """Test run_tui passes 5s for watch mode."""
        mock_app = MagicMock()
        mock_app_class.return_value = mock_app
        run_tui(refresh_interval=5)
        mock_app_class.assert_called_once_with(refresh_interval=5)
        mock_app.run.assert_called_once()
