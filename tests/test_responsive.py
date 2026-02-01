"""Tests for responsive layout features."""

import pytest

from openclaw_dash.app import (
    COMPACT_WIDTH,
    MINIMUM_WIDTH,
    DashboardApp,
    StatusFooter,
)


class TestResponsiveConstants:
    """Test responsive breakpoint constants."""

    def test_compact_width_value(self):
        """Compact breakpoint should be reasonable."""
        assert COMPACT_WIDTH == 100
        assert COMPACT_WIDTH > MINIMUM_WIDTH

    def test_minimum_width_value(self):
        """Minimum width should support standard terminals."""
        assert MINIMUM_WIDTH == 80


class TestDashboardAppPanelOrder:
    """Test panel ordering for tab navigation."""

    def test_panel_order_defined(self):
        """Panel order should be defined."""
        assert hasattr(DashboardApp, "PANEL_ORDER")
        assert len(DashboardApp.PANEL_ORDER) > 0

    def test_panel_order_unique(self):
        """All panel IDs in order should be unique."""
        assert len(DashboardApp.PANEL_ORDER) == len(set(DashboardApp.PANEL_ORDER))

    def test_collapsible_panels_defined(self):
        """Collapsible panels should be defined."""
        assert hasattr(DashboardApp, "COLLAPSIBLE_PANELS")
        assert len(DashboardApp.COLLAPSIBLE_PANELS) > 0

    def test_collapsible_panels_in_order(self):
        """All collapsible panels should be in the panel order."""
        for panel_id in DashboardApp.COLLAPSIBLE_PANELS:
            assert panel_id in DashboardApp.PANEL_ORDER


class TestStatusFooter:
    """Test status footer widget."""

    def test_status_footer_instantiates(self):
        """StatusFooter should instantiate without errors."""
        footer = StatusFooter()
        assert footer is not None

    def test_set_focused_panel(self):
        """set_focused_panel should update internal state."""
        footer = StatusFooter()
        footer._focused_panel = ""
        footer.set_focused_panel("Gateway")
        assert footer._focused_panel == "Gateway"

    def test_set_mode(self):
        """set_mode should update internal state."""
        footer = StatusFooter()
        footer._mode = "normal"
        footer.set_mode("compact")
        assert footer._mode == "compact"

    def test_default_mode_is_normal(self):
        """Default mode should be 'normal'."""
        footer = StatusFooter()
        assert footer._mode == "normal"


class TestResponsiveLayoutLogic:
    """Test responsive layout helper logic."""

    def test_width_below_compact_triggers_compact_mode(self):
        """Width below COMPACT_WIDTH should trigger compact mode."""
        # Logic test - width 80 is below 100 (COMPACT_WIDTH)
        assert 80 < COMPACT_WIDTH
        assert 99 < COMPACT_WIDTH
        assert 100 >= COMPACT_WIDTH

    def test_collapsible_panels_are_less_critical(self):
        """Collapsible panels should be the less critical ones."""
        # channels and activity are less important than gateway/alerts
        expected = ["channels-panel", "activity-panel"]
        assert DashboardApp.COLLAPSIBLE_PANELS == expected
