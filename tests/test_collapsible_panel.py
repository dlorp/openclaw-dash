"""Tests for CollapsiblePanel widget."""

from unittest.mock import MagicMock, patch

import pytest
from textual.app import App, ComposeResult
from textual.containers import Container
from textual.message import Message
from textual.widgets import Static

from openclaw_dash.widgets.collapsible_panel import CollapsiblePanel


class TestCollapsiblePanelBasics:
    """Basic tests for CollapsiblePanel class structure."""

    def test_is_container_subclass(self):
        """CollapsiblePanel should inherit from Container."""
        assert issubclass(CollapsiblePanel, Container)

    def test_has_collapsed_message_class(self):
        """CollapsiblePanel should have a Collapsed message class."""
        assert hasattr(CollapsiblePanel, "Collapsed")
        assert issubclass(CollapsiblePanel.Collapsed, Message)

    def test_has_required_methods(self):
        """CollapsiblePanel should have all expected methods."""
        expected_methods = [
            "compose",
            "toggle",
            "expand",
            "collapse",
            "update_summary",
        ]
        for method in expected_methods:
            assert hasattr(CollapsiblePanel, method)
            assert callable(getattr(CollapsiblePanel, method))

    def test_has_required_properties(self):
        """CollapsiblePanel should have expected properties."""
        expected_properties = ["panel_id", "collapsed"]
        for prop in expected_properties:
            assert hasattr(CollapsiblePanel, prop)


class TestCollapsiblePanelInit:
    """Tests for CollapsiblePanel initialization."""

    def test_basic_init(self):
        """Test basic initialization with required args."""
        panel = CollapsiblePanel(
            Static("content"),
            title="Test Panel",
            panel_id="test-panel",
        )
        assert panel._title == "Test Panel"
        assert panel._panel_id == "test-panel"
        assert panel._collapsed is False
        assert panel._summary_fn is None

    def test_init_with_collapsed(self):
        """Test initialization with collapsed=True."""
        panel = CollapsiblePanel(
            Static("content"),
            title="Test Panel",
            panel_id="test-panel",
            collapsed=True,
        )
        assert panel._collapsed is True

    def test_init_with_summary_fn(self):
        """Test initialization with summary function."""
        summary_fn = lambda: "Summary text"
        panel = CollapsiblePanel(
            Static("content"),
            title="Test Panel",
            panel_id="test-panel",
            summary_fn=summary_fn,
        )
        assert panel._summary_fn is summary_fn

    def test_init_with_multiple_children(self):
        """Test initialization with multiple child widgets."""
        child1 = Static("child 1")
        child2 = Static("child 2")
        panel = CollapsiblePanel(
            child1,
            child2,
            title="Multi-child Panel",
            panel_id="multi-panel",
        )
        assert len(panel._children) == 2

    def test_init_with_optional_args(self):
        """Test initialization with name, id, and classes."""
        panel = CollapsiblePanel(
            Static("content"),
            title="Test Panel",
            panel_id="test-panel",
            name="my-panel",
            id="panel-widget",
            classes="custom-class",
        )
        # These are passed to parent Container
        assert panel.name == "my-panel"


class TestCollapsiblePanelProperties:
    """Tests for CollapsiblePanel properties."""

    def test_panel_id_property(self):
        """Test panel_id property returns correct value."""
        panel = CollapsiblePanel(
            Static("content"),
            title="Test Panel",
            panel_id="my-test-id",
        )
        assert panel.panel_id == "my-test-id"

    def test_collapsed_property_getter(self):
        """Test collapsed property getter."""
        panel = CollapsiblePanel(
            Static("content"),
            title="Test Panel",
            panel_id="test-panel",
            collapsed=True,
        )
        assert panel.collapsed is True

    def test_collapsed_property_setter(self):
        """Test collapsed property setter updates internal state."""
        panel = CollapsiblePanel(
            Static("content"),
            title="Test Panel",
            panel_id="test-panel",
            collapsed=False,
        )
        panel.collapsed = True
        assert panel._collapsed is True


class TestCollapsiblePanelMethods:
    """Tests for CollapsiblePanel methods."""

    def test_toggle_from_expanded(self):
        """Test toggle from expanded state."""
        panel = CollapsiblePanel(
            Static("content"),
            title="Test Panel",
            panel_id="test-panel",
            collapsed=False,
        )
        panel.toggle()
        assert panel._collapsed is True

    def test_toggle_from_collapsed(self):
        """Test toggle from collapsed state."""
        panel = CollapsiblePanel(
            Static("content"),
            title="Test Panel",
            panel_id="test-panel",
            collapsed=True,
        )
        panel.toggle()
        assert panel._collapsed is False

    def test_expand_when_collapsed(self):
        """Test expand when panel is collapsed."""
        panel = CollapsiblePanel(
            Static("content"),
            title="Test Panel",
            panel_id="test-panel",
            collapsed=True,
        )
        panel.expand()
        assert panel._collapsed is False

    def test_expand_when_expanded(self):
        """Test expand when panel is already expanded (no-op)."""
        panel = CollapsiblePanel(
            Static("content"),
            title="Test Panel",
            panel_id="test-panel",
            collapsed=False,
        )
        panel.expand()
        assert panel._collapsed is False

    def test_collapse_when_expanded(self):
        """Test collapse when panel is expanded."""
        panel = CollapsiblePanel(
            Static("content"),
            title="Test Panel",
            panel_id="test-panel",
            collapsed=False,
        )
        panel.collapse()
        assert panel._collapsed is True

    def test_collapse_when_collapsed(self):
        """Test collapse when panel is already collapsed (no-op)."""
        panel = CollapsiblePanel(
            Static("content"),
            title="Test Panel",
            panel_id="test-panel",
            collapsed=True,
        )
        panel.collapse()
        assert panel._collapsed is True

    def test_get_summary_with_function(self):
        """Test _get_summary returns result from summary_fn."""
        panel = CollapsiblePanel(
            Static("content"),
            title="Test Panel",
            panel_id="test-panel",
            summary_fn=lambda: "Custom summary",
        )
        assert panel._get_summary() == "Custom summary"

    def test_get_summary_without_function(self):
        """Test _get_summary returns default when no summary_fn."""
        panel = CollapsiblePanel(
            Static("content"),
            title="Test Panel",
            panel_id="test-panel",
        )
        assert panel._get_summary() == "[dim]...[/]"

    def test_get_summary_handles_exception(self):
        """Test _get_summary returns default on exception."""
        def failing_summary():
            raise ValueError("Oops")

        panel = CollapsiblePanel(
            Static("content"),
            title="Test Panel",
            panel_id="test-panel",
            summary_fn=failing_summary,
        )
        assert panel._get_summary() == "[dim]...[/]"

    def test_update_classes_collapsed(self):
        """Test _update_classes adds -collapsed class when collapsed."""
        panel = CollapsiblePanel(
            Static("content"),
            title="Test Panel",
            panel_id="test-panel",
            collapsed=True,
        )
        panel._update_classes()
        assert "-collapsed" in panel.classes

    def test_update_classes_expanded(self):
        """Test _update_classes removes -collapsed class when expanded."""
        panel = CollapsiblePanel(
            Static("content"),
            title="Test Panel",
            panel_id="test-panel",
            collapsed=False,
        )
        panel.add_class("-collapsed")
        panel._update_classes()
        assert "-collapsed" not in panel.classes


class TestCollapsiblePanelMessages:
    """Tests for CollapsiblePanel.Collapsed message class."""

    def test_collapsed_message_init(self):
        """Test Collapsed message initialization."""
        msg = CollapsiblePanel.Collapsed("test-panel", True)
        assert msg.panel_id == "test-panel"
        assert msg.collapsed is True

    def test_collapsed_message_expanded(self):
        """Test Collapsed message with collapsed=False."""
        msg = CollapsiblePanel.Collapsed("other-panel", False)
        assert msg.panel_id == "other-panel"
        assert msg.collapsed is False


class TestCollapsiblePanelCompose:
    """Tests for CollapsiblePanel composition."""

    @pytest.mark.asyncio
    async def test_compose_yields_widgets(self):
        """Test that compose yields expected widgets when mounted."""

        class TestApp(App):
            def compose(self) -> ComposeResult:
                yield CollapsiblePanel(
                    Static("Test content"),
                    title="Test Panel",
                    panel_id="test-panel",
                )

        async with TestApp().run_test() as pilot:
            panel = pilot.app.query_one(CollapsiblePanel)
            # Panel should contain a Collapsible and a Static (summary)
            from textual.widgets import Collapsible

            collapsibles = panel.query(Collapsible)
            assert len(collapsibles) == 1
            # Should also have a summary Static
            summary = panel.query_one("#test-panel-summary", Static)
            assert summary is not None

    @pytest.mark.asyncio
    async def test_compose_creates_summary_with_correct_id(self):
        """Test that compose creates summary Static with correct ID."""

        class TestApp(App):
            def compose(self) -> ComposeResult:
                yield CollapsiblePanel(
                    Static("content"),
                    title="Test Panel",
                    panel_id="my-panel",
                )

        async with TestApp().run_test() as pilot:
            panel = pilot.app.query_one(CollapsiblePanel)
            summary = panel.query_one("#my-panel-summary", Static)
            assert summary is not None
            assert summary.id == "my-panel-summary"


class TestCollapsiblePanelCSS:
    """Tests for CollapsiblePanel CSS."""

    def test_has_default_css(self):
        """Test that DEFAULT_CSS is defined."""
        assert hasattr(CollapsiblePanel, "DEFAULT_CSS")
        assert isinstance(CollapsiblePanel.DEFAULT_CSS, str)
        assert len(CollapsiblePanel.DEFAULT_CSS) > 0

    def test_css_contains_collapsed_rules(self):
        """Test that CSS contains rules for collapsed state."""
        css = CollapsiblePanel.DEFAULT_CSS
        assert "-collapsed" in css
        assert ".summary" in css

    def test_css_no_unsupported_pseudo_classes(self):
        """Test that CSS doesn't use unsupported pseudo-classes like :not()."""
        css = CollapsiblePanel.DEFAULT_CSS
        # :not() is not supported in Textual CSS
        assert ":not(" not in css, "CSS contains unsupported :not() pseudo-class"


class TestCollapsiblePanelIntegration:
    """Integration tests for CollapsiblePanel with Textual app."""

    @pytest.mark.asyncio
    async def test_panel_mounts_in_app(self):
        """Test that CollapsiblePanel can be mounted in an app."""

        class TestApp(App):
            def compose(self) -> ComposeResult:
                yield CollapsiblePanel(
                    Static("Test content"),
                    title="Test Panel",
                    panel_id="test-panel",
                )

        async with TestApp().run_test() as pilot:
            app = pilot.app
            panels = app.query(CollapsiblePanel)
            assert len(panels) == 1

    @pytest.mark.asyncio
    async def test_collapsed_panel_shows_summary(self):
        """Test that collapsed panel shows summary."""

        class TestApp(App):
            def compose(self) -> ComposeResult:
                yield CollapsiblePanel(
                    Static("Full content here"),
                    title="Test Panel",
                    panel_id="test-panel",
                    collapsed=True,
                    summary_fn=lambda: "Brief summary",
                )

        async with TestApp().run_test() as pilot:
            panel = pilot.app.query_one(CollapsiblePanel)
            assert panel.collapsed is True

    @pytest.mark.asyncio
    async def test_toggle_via_method(self):
        """Test toggling panel state via toggle() method."""

        class TestApp(App):
            def compose(self) -> ComposeResult:
                yield CollapsiblePanel(
                    Static("Content"),
                    title="Test Panel",
                    panel_id="test-panel",
                    collapsed=True,  # Start collapsed
                )

        async with TestApp().run_test() as pilot:
            panel = pilot.app.query_one(CollapsiblePanel)
            initial_state = panel.collapsed
            panel.toggle()
            # State should flip
            assert panel._collapsed is not initial_state

    @pytest.mark.asyncio
    async def test_expand_collapse_methods(self):
        """Test expand() and collapse() methods."""

        class TestApp(App):
            def compose(self) -> ComposeResult:
                yield CollapsiblePanel(
                    Static("Content"),
                    title="Test Panel",
                    panel_id="test-panel",
                    collapsed=True,  # Start collapsed
                )

        async with TestApp().run_test() as pilot:
            panel = pilot.app.query_one(CollapsiblePanel)

            # Start collapsed
            assert panel.collapsed is True

            # Expand
            panel.expand()
            assert panel._collapsed is False

            # Collapse
            panel.collapse()
            assert panel._collapsed is True


class TestCollapsiblePanelEdgeCases:
    """Edge case tests for CollapsiblePanel."""

    def test_empty_panel_id(self):
        """Test panel with empty panel_id."""
        panel = CollapsiblePanel(
            Static("content"),
            title="Test Panel",
            panel_id="",
        )
        assert panel.panel_id == ""

    def test_special_characters_in_panel_id(self):
        """Test panel_id with special characters."""
        panel = CollapsiblePanel(
            Static("content"),
            title="Test Panel",
            panel_id="panel-with-special_chars.123",
        )
        assert panel.panel_id == "panel-with-special_chars.123"

    def test_no_children(self):
        """Test panel with no children."""
        panel = CollapsiblePanel(
            title="Empty Panel",
            panel_id="empty",
        )
        assert len(panel._children) == 0

    def test_summary_fn_returns_empty_string(self):
        """Test summary_fn that returns empty string."""
        panel = CollapsiblePanel(
            Static("content"),
            title="Test Panel",
            panel_id="test-panel",
            summary_fn=lambda: "",
        )
        assert panel._get_summary() == ""

    def test_summary_fn_returns_rich_markup(self):
        """Test summary_fn that returns Rich markup."""
        panel = CollapsiblePanel(
            Static("content"),
            title="Test Panel",
            panel_id="test-panel",
            summary_fn=lambda: "[bold green]Status OK[/]",
        )
        assert panel._get_summary() == "[bold green]Status OK[/]"


class TestCollapsiblePanelUpdateSummary:
    """Tests for update_summary method."""

    def test_update_summary_handles_missing_widget(self):
        """Test update_summary handles case where summary widget not found."""
        panel = CollapsiblePanel(
            Static("content"),
            title="Test Panel",
            panel_id="test-panel",
        )
        # Should not raise - widget not composed yet
        panel.update_summary()
