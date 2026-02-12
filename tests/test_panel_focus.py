"""Tests for panel focus navigation (Tab/Shift+Tab)."""

import pytest


class TestPanelFocusBindings:
    """Test panel focus keybindings are defined."""

    def test_tab_binding_exists(self):
        """Tab key should be bound for next panel."""
        from openclaw_dash.app import DashboardApp

        bindings = {b[0]: b[1] for b in DashboardApp.BINDINGS}
        assert "tab" in bindings
        assert bindings["tab"] == "focus_next_panel"

    def test_shift_tab_binding_exists(self):
        """Shift+Tab should be bound for previous panel."""
        from openclaw_dash.app import DashboardApp

        bindings = {b[0]: b[1] for b in DashboardApp.BINDINGS}
        assert "shift+tab" in bindings
        assert bindings["shift+tab"] == "focus_prev_panel"


class TestPanelFocusActions:
    """Test panel focus action methods exist and are callable."""

    def test_focus_next_panel_action_exists(self):
        """action_focus_next_panel method should exist."""
        from openclaw_dash.app import DashboardApp

        assert hasattr(DashboardApp, "action_focus_next_panel")
        assert callable(getattr(DashboardApp, "action_focus_next_panel"))

    def test_focus_prev_panel_action_exists(self):
        """action_focus_prev_panel method should exist."""
        from openclaw_dash.app import DashboardApp

        assert hasattr(DashboardApp, "action_focus_prev_panel")
        assert callable(getattr(DashboardApp, "action_focus_prev_panel"))

    def test_focus_panel_action_exists(self):
        """action_focus_panel method should exist."""
        from openclaw_dash.app import DashboardApp

        assert hasattr(DashboardApp, "action_focus_panel")
        assert callable(getattr(DashboardApp, "action_focus_panel"))


class TestPanelOrder:
    """Test PANEL_ORDER is defined correctly."""

    def test_panel_order_exists(self):
        """PANEL_ORDER should be defined."""
        from openclaw_dash.app import DashboardApp

        assert hasattr(DashboardApp, "PANEL_ORDER")
        assert isinstance(DashboardApp.PANEL_ORDER, list)

    def test_panel_order_not_empty(self):
        """PANEL_ORDER should contain panel IDs."""
        from openclaw_dash.app import DashboardApp

        assert len(DashboardApp.PANEL_ORDER) > 0

    def test_panel_ids_end_with_panel_or_group(self):
        """All PANEL_ORDER entries should end with '-panel' or '-group'."""
        from openclaw_dash.app import DashboardApp

        for panel_id in DashboardApp.PANEL_ORDER:
            assert panel_id.endswith("-panel") or panel_id.endswith(
                "-group"
            ), f"{panel_id} should end with '-panel' or '-group'"


class TestHelpPanelFocusDocs:
    """Test panel focus keys are documented in help panel (optional)."""

    def test_help_shortcuts_exist(self):
        """Help shortcuts should be defined."""
        from openclaw_dash.widgets.help_panel import STATIC_SHORTCUTS

        assert STATIC_SHORTCUTS is not None
        assert isinstance(STATIC_SHORTCUTS, list)
        assert len(STATIC_SHORTCUTS) > 0
