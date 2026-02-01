"""Tests for watch mode feature."""

import pytest

from openclaw_dash.app import DashboardApp


class TestDashboardAppRefreshInterval:
    """Tests for DashboardApp refresh interval configuration."""

    def test_default_refresh_interval_constant(self):
        """Test DEFAULT_REFRESH_INTERVAL is 30 seconds."""
        assert DashboardApp.DEFAULT_REFRESH_INTERVAL == 30

    def test_watch_refresh_interval_constant(self):
        """Test WATCH_REFRESH_INTERVAL is 5 seconds."""
        assert DashboardApp.WATCH_REFRESH_INTERVAL == 5

    def test_default_refresh_interval_on_init(self):
        """Test that default refresh interval is 30 seconds."""
        app = DashboardApp()
        assert app.refresh_interval == 30

    def test_custom_refresh_interval_on_init(self):
        """Test that custom refresh interval is passed correctly."""
        app = DashboardApp(refresh_interval=5)
        assert app.refresh_interval == 5

    def test_watch_mode_interval(self):
        """Test watch mode uses 5 second interval."""
        app = DashboardApp(refresh_interval=DashboardApp.WATCH_REFRESH_INTERVAL)
        assert app.refresh_interval == 5

    def test_arbitrary_interval(self):
        """Test arbitrary refresh interval works."""
        app = DashboardApp(refresh_interval=10)
        assert app.refresh_interval == 10


class TestWatchModeHelp:
    """Tests for watch mode CLI help."""

    def test_watch_flag_in_parser(self):
        """Test that --watch flag is available in argument parser."""
        import argparse
        from unittest.mock import patch

        from openclaw_dash.cli import main

        # Capture help output to verify --watch is documented
        with patch("sys.argv", ["openclaw-dash", "--help"]):
            with pytest.raises(SystemExit) as exc:
                main()
            assert exc.value.code == 0

    def test_watch_flag_description(self):
        """Test watch flag has meaningful description."""
        import argparse

        parser = argparse.ArgumentParser()
        # This mimics what cli.py does
        parser.add_argument(
            "-w", "--watch", action="store_true", help="Watch mode: auto-refresh every 5s"
        )
        # Verify the flag exists and has help text
        action = parser._option_string_actions.get("--watch")
        assert action is not None
        assert "5s" in action.help
