"""Collapsible panel wrapper for dashboard panels."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from textual.app import ComposeResult
from textual.containers import Container
from textual.message import Message
from textual.widgets import Collapsible, Static

if TYPE_CHECKING:
    from textual.widget import Widget


class CollapsiblePanel(Container):
    """A panel that can be collapsed/expanded.

    Wraps content in a Textual Collapsible widget with a summary line
    visible when collapsed.
    """

    DEFAULT_CSS = """
    CollapsiblePanel {
        height: auto;
    }

    CollapsiblePanel > Collapsible {
        padding: 0;
        margin: 0;
        border: none;
        background: transparent;
    }

    CollapsiblePanel > Collapsible > CollapsibleTitle {
        padding: 0 1;
        background: transparent;
    }

    CollapsiblePanel > Collapsible > Contents {
        padding: 0;
    }

    CollapsiblePanel .summary {
        padding: 0 1;
        color: $text-muted;
        display: none;
    }

    CollapsiblePanel.-collapsed .summary {
        display: block;
    }
    """

    class Collapsed(Message):
        """Posted when panel is collapsed."""

        def __init__(self, panel_id: str, collapsed: bool) -> None:
            super().__init__()
            self.panel_id = panel_id
            self.collapsed = collapsed

    def __init__(
        self,
        *children: Widget,
        title: str,
        panel_id: str,
        collapsed: bool = False,
        summary_fn: Callable[[], str] | None = None,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        """Initialize a collapsible panel.

        Args:
            *children: Content widgets to display when expanded.
            title: Panel title shown in the collapsible header.
            panel_id: Unique identifier for this panel (used for persistence).
            collapsed: Whether the panel starts collapsed.
            summary_fn: Optional function that returns a summary string for collapsed state.
            name: Widget name.
            id: Widget ID.
            classes: CSS classes.
        """
        super().__init__(name=name, id=id, classes=classes)
        self._title = title
        self._panel_id = panel_id
        self._collapsed = collapsed
        self._summary_fn = summary_fn
        self._children = children

    @property
    def panel_id(self) -> str:
        """Return the panel identifier."""
        return self._panel_id

    @property
    def collapsed(self) -> bool:
        """Return whether the panel is collapsed."""
        return self._collapsed

    @collapsed.setter
    def collapsed(self, value: bool) -> None:
        """Set the collapsed state."""
        self._collapsed = value
        try:
            collapsible = self.query_one(Collapsible)
            collapsible.collapsed = value
        except Exception:
            pass
        self._update_classes()

    def compose(self) -> ComposeResult:
        with Collapsible(
            title=self._title,
            collapsed=self._collapsed,
            collapsed_symbol="▸",
            expanded_symbol="▾",
        ):
            yield from self._children

        # Summary line shown when collapsed
        summary_text = self._get_summary()
        yield Static(summary_text, classes="summary", id=f"{self._panel_id}-summary")

        self._update_classes()

    def _get_summary(self) -> str:
        """Get the summary text for collapsed state."""
        if self._summary_fn:
            try:
                return self._summary_fn()
            except Exception:
                return "[dim]...[/]"
        return "[dim]...[/]"

    def _update_classes(self) -> None:
        """Update CSS classes based on collapsed state."""
        if self._collapsed:
            self.add_class("-collapsed")
        else:
            self.remove_class("-collapsed")

    def update_summary(self) -> None:
        """Update the summary text."""
        try:
            summary = self.query_one(f"#{self._panel_id}-summary", Static)
            summary.update(self._get_summary())
        except Exception:
            pass

    def on_collapsible_collapsed(self, event: Collapsible.Collapsed) -> None:
        """Handle collapsible state change."""
        self._collapsed = event.collapsible.collapsed
        self._update_classes()
        self.update_summary()
        self.post_message(self.Collapsed(self._panel_id, self._collapsed))
        event.stop()

    def on_collapsible_expanded(self, event: Collapsible.Expanded) -> None:
        """Handle collapsible state change."""
        self._collapsed = not event.collapsible.collapsed
        self._update_classes()
        self.post_message(self.Collapsed(self._panel_id, self._collapsed))
        event.stop()

    def toggle(self) -> None:
        """Toggle the collapsed state."""
        self.collapsed = not self._collapsed

    def expand(self) -> None:
        """Expand the panel."""
        self.collapsed = False

    def collapse(self) -> None:
        """Collapse the panel."""
        self.collapsed = True
