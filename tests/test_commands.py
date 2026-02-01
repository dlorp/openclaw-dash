"""Tests for the command palette."""

import pytest

from openclaw_dash.commands import DashboardCommands
from openclaw_dash.themes import THEME_NAMES


class TestDashboardCommandsClass:
    """Test DashboardCommands provider class."""

    def test_class_exists(self):
        """DashboardCommands class should exist."""
        assert DashboardCommands is not None

    def test_inherits_from_provider(self):
        """Should inherit from textual Provider."""
        from textual.command import Provider

        assert issubclass(DashboardCommands, Provider)

    def test_has_discover_method(self):
        """Should have discover method for default commands."""
        assert hasattr(DashboardCommands, "discover")
        assert callable(getattr(DashboardCommands, "discover"))

    def test_has_search_method(self):
        """Should have search method for filtering commands."""
        assert hasattr(DashboardCommands, "search")
        assert callable(getattr(DashboardCommands, "search"))


class TestAppIntegration:
    """Test that commands are integrated into the app."""

    def test_app_has_commands(self):
        """DashboardApp should have COMMANDS set."""
        from openclaw_dash.app import DashboardApp

        assert hasattr(DashboardApp, "COMMANDS")
        assert DashboardCommands in DashboardApp.COMMANDS

    def test_command_palette_enabled(self):
        """Command palette should be enabled by default."""
        from openclaw_dash.app import DashboardApp

        # ENABLE_COMMAND_PALETTE defaults to True in Textual
        assert DashboardApp.ENABLE_COMMAND_PALETTE is True

    def test_command_palette_binding(self):
        """Command palette should be accessible via Ctrl+P."""
        from openclaw_dash.app import DashboardApp

        assert DashboardApp.COMMAND_PALETTE_BINDING == "ctrl+p"


class TestThemeCommands:
    """Test theme-related commands."""

    def test_all_themes_available(self):
        """All themes should be available in commands."""
        # Verify themes are defined for command generation
        assert "dark" in THEME_NAMES
        assert "light" in THEME_NAMES
        assert "hacker" in THEME_NAMES


class TestPanelCommands:
    """Test panel focus commands."""

    def test_expected_panels_in_commands(self):
        """Expected panels should be defined in the commands module."""
        # Check that command module references the panel IDs
        import inspect

        source = inspect.getsource(DashboardCommands)

        # Core panels that should have focus commands
        expected_panels = [
            "gateway-panel",
            "security-panel",
            "metrics-panel",
            "alerts-panel",
            "cron-panel",
            "repos-panel",
        ]
        for panel_id in expected_panels:
            assert panel_id in source, f"Panel {panel_id} not found in commands"


class TestExportFunctionality:
    """Test export data functionality."""

    def test_export_method_exists(self):
        """Export method should be defined."""
        assert hasattr(DashboardCommands, "_export_data")

    def test_set_theme_method_exists(self):
        """Set theme method should be defined."""
        assert hasattr(DashboardCommands, "_set_theme")


@pytest.mark.asyncio
async def test_command_palette_bindings():
    """Test that command palette keybinding is configured."""
    from textual.app import App

    # Verify default Textual behavior
    assert App.COMMAND_PALETTE_BINDING == "ctrl+p"
    assert App.ENABLE_COMMAND_PALETTE is True
