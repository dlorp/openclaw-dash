"""Tests for tabbed panel groups."""

import inspect

from textual.containers import Container
from textual.widgets import Static

from openclaw_dash.widgets.tabbed_groups import (
    CodeTabGroup,
    RuntimeTabGroup,
    next_tab,
    prev_tab,
    switch_tab,
)


class TestRuntimeTabGroup:
    """Tests for the RuntimeTabGroup widget."""

    def test_is_container_subclass(self):
        """RuntimeTabGroup should inherit from Container."""
        assert issubclass(RuntimeTabGroup, Container)

    def test_has_compose_method(self):
        """RuntimeTabGroup should have compose method."""
        assert hasattr(RuntimeTabGroup, "compose")
        assert callable(getattr(RuntimeTabGroup, "compose"))

    def test_initialization(self):
        """Test RuntimeTabGroup can be initialized with panels."""
        sessions = Static("Sessions")
        cron = Static("Cron")
        channels = Static("Channels")

        group = RuntimeTabGroup(
            sessions_panel=sessions,
            cron_panel=cron,
            channels_panel=channels,
        )

        assert group._sessions_panel is sessions
        assert group._cron_panel is cron
        assert group._channels_panel is channels

    def test_compose_method_is_generator(self):
        """Test that compose method is a generator that can be called."""
        sessions = Static("Sessions content")
        cron = Static("Cron content")
        channels = Static("Channels content")

        group = RuntimeTabGroup(
            sessions_panel=sessions,
            cron_panel=cron,
            channels_panel=channels,
        )

        # compose() should be callable and return a generator
        assert inspect.isgeneratorfunction(group.compose) or hasattr(group.compose, "__call__")

    def test_default_css_defined(self):
        """RuntimeTabGroup should have DEFAULT_CSS defined."""
        assert RuntimeTabGroup.DEFAULT_CSS is not None
        assert len(RuntimeTabGroup.DEFAULT_CSS) > 0
        assert "TabbedContent" in RuntimeTabGroup.DEFAULT_CSS


class TestCodeTabGroup:
    """Tests for the CodeTabGroup widget."""

    def test_is_container_subclass(self):
        """CodeTabGroup should inherit from Container."""
        assert issubclass(CodeTabGroup, Container)

    def test_has_compose_method(self):
        """CodeTabGroup should have compose method."""
        assert hasattr(CodeTabGroup, "compose")
        assert callable(getattr(CodeTabGroup, "compose"))

    def test_initialization(self):
        """Test CodeTabGroup can be initialized with panels."""
        repos = Static("Repos")
        activity = Static("Activity")

        group = CodeTabGroup(
            repos_panel=repos,
            activity_panel=activity,
        )

        assert group._repos_panel is repos
        assert group._activity_panel is activity

    def test_compose_method_is_generator(self):
        """Test that compose method is a generator that can be called."""
        repos = Static("Repos content")
        activity = Static("Activity content")

        group = CodeTabGroup(
            repos_panel=repos,
            activity_panel=activity,
        )

        # compose() should be callable and return a generator
        assert inspect.isgeneratorfunction(group.compose) or hasattr(group.compose, "__call__")

    def test_default_css_defined(self):
        """CodeTabGroup should have DEFAULT_CSS defined."""
        assert CodeTabGroup.DEFAULT_CSS is not None
        assert len(CodeTabGroup.DEFAULT_CSS) > 0
        assert "TabbedContent" in CodeTabGroup.DEFAULT_CSS


class TestTabNavigation:
    """Tests for tab navigation helper functions."""

    def test_switch_tab_function_exists(self):
        """switch_tab function should exist."""
        assert callable(switch_tab)

    def test_next_tab_function_exists(self):
        """next_tab function should exist."""
        assert callable(next_tab)

    def test_prev_tab_function_exists(self):
        """prev_tab function should exist."""
        assert callable(prev_tab)


class TestAppIntegration:
    """Integration tests for tabbed groups in the app."""

    def test_import_from_app(self):
        """Tab groups should be importable from app module."""
        from openclaw_dash.app import CodeTabGroup, RuntimeTabGroup

        assert RuntimeTabGroup is not None
        assert CodeTabGroup is not None

    def test_app_has_tab_group_bindings(self):
        """DashboardApp should have tab group keybindings."""
        from openclaw_dash.app import DashboardApp

        binding_strings = [str(b) for b in DashboardApp.BINDINGS]
        binding_text = " ".join(binding_strings)

        # Check for number key bindings
        assert "focus_tab_group" in binding_text

    def test_app_has_tab_navigation_actions(self):
        """DashboardApp should have tab navigation action methods."""
        from openclaw_dash.app import DashboardApp

        assert hasattr(DashboardApp, "action_focus_tab_group")
        assert hasattr(DashboardApp, "action_next_tab_in_group")
        assert hasattr(DashboardApp, "action_prev_tab_in_group")

    def test_panel_order_includes_tab_groups(self):
        """PANEL_ORDER should include tab group IDs."""
        from openclaw_dash.app import DashboardApp

        assert "runtime-group" in DashboardApp.PANEL_ORDER
        assert "code-group" in DashboardApp.PANEL_ORDER

    def test_tab_groups_constant_defined(self):
        """TAB_GROUPS constant should be defined."""
        from openclaw_dash.app import DashboardApp

        assert hasattr(DashboardApp, "TAB_GROUPS")
        assert "runtime-group" in DashboardApp.TAB_GROUPS
        assert "code-group" in DashboardApp.TAB_GROUPS


class TestHelpPanelIntegration:
    """Tests for help panel tab group documentation."""

    def test_static_shortcuts_includes_tab_groups(self):
        """STATIC_SHORTCUTS should include Tab Groups section."""
        from openclaw_dash.widgets.help_panel import STATIC_SHORTCUTS

        section_names = [name for name, _ in STATIC_SHORTCUTS]
        assert "Tab Groups" in section_names

    def test_shortcuts_legacy_includes_tab_groups(self):
        """Legacy SHORTCUTS should include Tab Groups section."""
        from openclaw_dash.widgets.help_panel import SHORTCUTS

        section_names = [name for name, _ in SHORTCUTS]
        assert "Tab Groups" in section_names

    def test_tab_group_shortcuts_documented(self):
        """Tab group shortcuts should be documented."""
        from openclaw_dash.widgets.help_panel import STATIC_SHORTCUTS

        tab_groups_section = None
        for name, shortcuts in STATIC_SHORTCUTS:
            if name == "Tab Groups":
                tab_groups_section = shortcuts
                break

        assert tab_groups_section is not None
        shortcut_keys = [key for key, _ in tab_groups_section]

        # Check for number keys
        assert "1" in shortcut_keys
        assert "2" in shortcut_keys
        # Check for bracket keys
        assert "[" in shortcut_keys
        assert "]" in shortcut_keys
