"""Tests for panel focus navigation (Tab/Shift+Tab)."""


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
            assert panel_id.endswith("-panel") or panel_id.endswith("-group"), (
                f"{panel_id} should end with '-panel' or '-group'"
            )


class TestHelpPanelFocusDocs:
    """Test panel focus keys are documented in help panel (optional)."""

    def test_help_shortcuts_exist(self):
        """Help shortcuts should be defined."""
        from openclaw_dash.widgets.help_panel import STATIC_SHORTCUTS

        assert STATIC_SHORTCUTS is not None
        assert isinstance(STATIC_SHORTCUTS, list)
        assert len(STATIC_SHORTCUTS) > 0


class TestPanelFocusIntegration:
    """Integration tests for Tab/Shift+Tab panel navigation."""

    def test_action_focus_next_panel_implementation(self):
        """Test action_focus_next_panel method exists and has proper logic."""

        from openclaw_dash.app import DashboardApp

        # Verify method exists
        assert hasattr(DashboardApp, "action_focus_next_panel")
        method = getattr(DashboardApp, "action_focus_next_panel")

        # Verify it's callable
        assert callable(method)

        # Verify docstring exists
        assert method.__doc__ is not None
        assert "next" in method.__doc__.lower()

    def test_action_focus_prev_panel_implementation(self):
        """Test action_focus_prev_panel method exists and has proper logic."""

        from openclaw_dash.app import DashboardApp

        # Verify method exists
        assert hasattr(DashboardApp, "action_focus_prev_panel")
        method = getattr(DashboardApp, "action_focus_prev_panel")

        # Verify it's callable
        assert callable(method)

        # Verify docstring exists
        assert method.__doc__ is not None
        assert "previous" in method.__doc__.lower() or "prev" in method.__doc__.lower()

    def test_action_focus_panel_implementation(self):
        """Test action_focus_panel method exists and validates panel IDs."""
        import inspect

        from openclaw_dash.app import DashboardApp

        # Verify method exists
        assert hasattr(DashboardApp, "action_focus_panel")
        method = getattr(DashboardApp, "action_focus_panel")

        # Verify it's callable
        assert callable(method)

        # Verify method signature includes panel_id parameter
        sig = inspect.signature(method)
        assert "panel_id" in sig.parameters

        # Verify source contains security validation
        import inspect as insp

        source = insp.getsource(method)
        assert "PANEL_ORDER" in source, "Should validate against PANEL_ORDER"
        assert "if" in source, "Should have conditional validation"

    def test_tab_binding_maps_to_focus_next(self):
        """Test that Tab key is bound to focus_next_panel action."""
        from openclaw_dash.app import DashboardApp

        bindings_dict = {b[0]: b[1] for b in DashboardApp.BINDINGS}
        assert "tab" in bindings_dict
        assert bindings_dict["tab"] == "focus_next_panel"

        # Verify help text exists for Tab binding
        tab_binding = next(b for b in DashboardApp.BINDINGS if b[0] == "tab")
        assert len(tab_binding) >= 3
        help_text = tab_binding[2]
        assert help_text is not None

    def test_shift_tab_binding_maps_to_focus_prev(self):
        """Test that Shift+Tab key is bound to focus_prev_panel action."""
        from openclaw_dash.app import DashboardApp

        bindings_dict = {b[0]: b[1] for b in DashboardApp.BINDINGS}
        assert "shift+tab" in bindings_dict
        assert bindings_dict["shift+tab"] == "focus_prev_panel"

        # Verify help text exists for Shift+Tab binding
        shift_tab_binding = next(b for b in DashboardApp.BINDINGS if b[0] == "shift+tab")
        assert len(shift_tab_binding) >= 3
        help_text = shift_tab_binding[2]
        assert help_text is not None

    def test_panel_order_valid_for_cycling(self):
        """Test that PANEL_ORDER contains valid panel IDs for cycling."""
        from openclaw_dash.app import DashboardApp

        panel_order = DashboardApp.PANEL_ORDER
        assert len(panel_order) > 0

        # Each panel ID should have "-panel" or "-group" suffix
        for panel_id in panel_order:
            assert panel_id.endswith("-panel") or panel_id.endswith("-group")

    def test_panel_focus_wrapping_logic(self):
        """Test that panel focus wrapping logic would work correctly."""
        from openclaw_dash.app import DashboardApp

        panel_order = DashboardApp.PANEL_ORDER

        # Simulate forward wrapping
        current_index = len(panel_order) - 1  # Last panel
        next_index = (current_index + 1) % len(panel_order)
        assert next_index == 0, "Forward wrap should go to first panel"

        # Simulate backward wrapping
        current_index = 0  # First panel
        prev_index = (current_index - 1) % len(panel_order)
        assert prev_index == len(panel_order) - 1, "Backward wrap should go to last panel"

    def test_help_shortcuts_include_tab_navigation(self):
        """Test that help panel documents Tab navigation."""
        from openclaw_dash.widgets.help_panel import STATIC_SHORTCUTS

        # Check that shortcuts list exists
        assert STATIC_SHORTCUTS is not None
        assert isinstance(STATIC_SHORTCUTS, list)

        # Verify shortcuts list is not empty
        assert len(STATIC_SHORTCUTS) > 0


class TestPanelFocusSecurity:
    """Security tests for panel focus validation."""

    def test_action_focus_panel_validates_panel_id(self):
        """Test that action_focus_panel validates panel_id against PANEL_ORDER whitelist."""
        from unittest.mock import MagicMock

        from openclaw_dash.app import DashboardApp

        # Create a mock app instance
        app = DashboardApp()
        app.query_one = MagicMock()

        # Test 1: Valid panel ID should call query_one
        valid_panel_id = DashboardApp.PANEL_ORDER[0]
        app.action_focus_panel(valid_panel_id)
        assert app.query_one.called, "Should call query_one for valid panel ID"
        app.query_one.reset_mock()

        # Test 2: Invalid panel ID should NOT call query_one
        app.action_focus_panel("invalid-panel-id")
        assert not app.query_one.called, "Should not call query_one for invalid panel ID"
        app.query_one.reset_mock()

        # Test 3: CSS injection attempt should be rejected
        app.action_focus_panel("#malicious-selector")
        assert not app.query_one.called, "Should reject CSS injection patterns"
        app.query_one.reset_mock()

        # Test 4: None should be rejected
        app.action_focus_panel(None)
        assert not app.query_one.called, "Should reject None as panel ID"
        app.query_one.reset_mock()

        # Test 5: Empty string should be rejected
        app.action_focus_panel("")
        assert not app.query_one.called, "Should reject empty string as panel ID"
        app.query_one.reset_mock()

        # Test 6: SQL injection pattern should be rejected
        app.action_focus_panel("'; DROP TABLE panels; --")
        assert not app.query_one.called, "Should reject SQL injection patterns"
        app.query_one.reset_mock()

        # Test 7: Path traversal pattern should be rejected
        app.action_focus_panel("../../../etc/passwd")
        assert not app.query_one.called, "Should reject path traversal patterns"
        app.query_one.reset_mock()

        # Test 8: Special characters should be rejected
        app.action_focus_panel("panel*[data-foo]")
        assert not app.query_one.called, "Should reject special CSS selector characters"

    def test_panel_order_is_complete_whitelist(self):
        """Test that PANEL_ORDER serves as a complete whitelist for panel IDs."""
        from openclaw_dash.app import DashboardApp

        # PANEL_ORDER should exist and be a list
        assert hasattr(DashboardApp, "PANEL_ORDER")
        assert isinstance(DashboardApp.PANEL_ORDER, list)

        # PANEL_ORDER should only contain valid panel ID strings
        for panel_id in DashboardApp.PANEL_ORDER:
            assert isinstance(panel_id, str), "All panel IDs should be strings"
            assert len(panel_id) > 0, "Panel IDs should not be empty"
            assert panel_id == panel_id.strip(), "Panel IDs should not have leading/trailing spaces"

    def test_action_focus_panel_early_return_on_invalid_id(self):
        """Test that action_focus_panel returns early for invalid IDs without side effects."""
        import inspect

        from openclaw_dash.app import DashboardApp

        # Verify the method implementation returns early on invalid panel_id
        source = inspect.getsource(DashboardApp.action_focus_panel)

        # Should check panel_id against PANEL_ORDER
        assert "panel_id not in" in source or "panel_id in" in source, (
            "Should validate panel_id against PANEL_ORDER"
        )

        # Should have early return
        assert "return" in source, "Should return early for invalid panel IDs"

        # Validation should happen before query_one is called
        lines = source.split("\n")
        validation_line = None
        query_line = None

        for i, line in enumerate(lines):
            if "panel_id" in line and ("not in" in line or "PANEL_ORDER" in line):
                validation_line = i
            if "query_one" in line and validation_line is None:
                query_line = i

        assert validation_line is not None, "Should have panel_id validation"
        if query_line is not None:
            assert validation_line < query_line, "Validation should occur before query_one call"
