"""Tests for vim-style keyboard navigation."""

import pytest


class TestVimKeyBindings:
    """Test vim-style keybindings are defined."""

    def test_j_binding_exists(self):
        """j key should be bound for scroll down."""
        from openclaw_dash.app import DashboardApp

        bindings = {b[0]: b[1] for b in DashboardApp.BINDINGS}
        assert "j" in bindings
        assert bindings["j"] == "scroll_down"

    def test_k_binding_exists(self):
        """k key should be bound for scroll up."""
        from openclaw_dash.app import DashboardApp

        bindings = {b[0]: b[1] for b in DashboardApp.BINDINGS}
        assert "k" in bindings
        assert bindings["k"] == "scroll_up"

    def test_G_binding_exists(self):
        """G (shift+g) should be bound for scroll to end."""
        from openclaw_dash.app import DashboardApp

        bindings = {b[0]: b[1] for b in DashboardApp.BINDINGS}
        assert "G" in bindings
        assert bindings["G"] == "scroll_end"

    def test_home_binding_exists(self):
        """Home key should be bound for scroll to top."""
        from openclaw_dash.app import DashboardApp

        bindings = {b[0]: b[1] for b in DashboardApp.BINDINGS}
        assert "home" in bindings
        assert bindings["home"] == "scroll_home"


class TestVimScrollActions:
    """Test vim scroll action methods exist."""

    def test_scroll_down_action_exists(self):
        """action_scroll_down method should exist."""
        from openclaw_dash.app import DashboardApp

        assert hasattr(DashboardApp, "action_scroll_down")
        assert callable(getattr(DashboardApp, "action_scroll_down"))

    def test_scroll_up_action_exists(self):
        """action_scroll_up method should exist."""
        from openclaw_dash.app import DashboardApp

        assert hasattr(DashboardApp, "action_scroll_up")
        assert callable(getattr(DashboardApp, "action_scroll_up"))

    def test_scroll_end_action_exists(self):
        """action_scroll_end method should exist."""
        from openclaw_dash.app import DashboardApp

        assert hasattr(DashboardApp, "action_scroll_end")
        assert callable(getattr(DashboardApp, "action_scroll_end"))

    def test_scroll_home_action_exists(self):
        """action_scroll_home method should exist."""
        from openclaw_dash.app import DashboardApp

        assert hasattr(DashboardApp, "action_scroll_home")
        assert callable(getattr(DashboardApp, "action_scroll_home"))


class TestHelpPanelVimDocs:
    """Test vim keys are documented in help panel."""

    def test_vim_navigation_section_exists(self):
        """Vim Navigation section should exist in help."""
        from openclaw_dash.widgets.help_panel import STATIC_SHORTCUTS

        section_names = [section[0] for section in STATIC_SHORTCUTS]
        assert "Vim Navigation" in section_names

    def test_jk_documented(self):
        """j/k scroll should be documented."""
        from openclaw_dash.widgets.help_panel import STATIC_SHORTCUTS

        vim_section = next(s for s in STATIC_SHORTCUTS if s[0] == "Vim Navigation")
        keys = [k[0] for k in vim_section[1]]
        assert "j/k" in keys

    def test_G_documented(self):
        """G (scroll to bottom) should be documented."""
        from openclaw_dash.widgets.help_panel import STATIC_SHORTCUTS

        vim_section = next(s for s in STATIC_SHORTCUTS if s[0] == "Vim Navigation")
        keys = [k[0] for k in vim_section[1]]
        assert "G" in keys

    def test_home_documented(self):
        """Home (scroll to top) should be documented."""
        from openclaw_dash.widgets.help_panel import STATIC_SHORTCUTS

        vim_section = next(s for s in STATIC_SHORTCUTS if s[0] == "Vim Navigation")
        keys = [k[0] for k in vim_section[1]]
        assert "Home" in keys
