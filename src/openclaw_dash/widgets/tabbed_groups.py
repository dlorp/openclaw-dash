"""Tabbed panel groups for the dashboard.

Groups related panels into TabbedContent widgets for better organization:
- Runtime tab: Sessions + Cron + Channels
- Code tab: Repos + Activity
"""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Container
from textual.widgets import Static, TabbedContent, TabPane


class RuntimeTabGroup(Container):
    """Tabbed group containing runtime-related panels.
    
    Contains:
    - Sessions panel
    - Cron panel  
    - Channels panel
    """

    DEFAULT_CSS = """
    RuntimeTabGroup {
        height: auto;
    }
    
    RuntimeTabGroup TabbedContent {
        height: auto;
    }
    
    RuntimeTabGroup TabPane {
        height: auto;
        padding: 0;
    }
    
    RuntimeTabGroup Tabs {
        background: $surface;
    }
    
    RuntimeTabGroup Tab {
        background: $surface;
        color: $text-muted;
        padding: 0 2;
    }
    
    RuntimeTabGroup Tab:hover {
        background: $panel;
        color: $primary;
    }
    
    RuntimeTabGroup Tab.-active {
        background: $primary 15%;
        color: $primary;
        text-style: bold;
    }
    
    RuntimeTabGroup Underline {
        background: $primary;
    }
    """

    def __init__(
        self,
        sessions_panel: Static,
        cron_panel: Static,
        channels_panel: Static,
        **kwargs,
    ) -> None:
        """Initialize with the panel widgets.
        
        Args:
            sessions_panel: The sessions panel widget.
            cron_panel: The cron panel widget.
            channels_panel: The channels panel widget.
        """
        super().__init__(**kwargs)
        self._sessions_panel = sessions_panel
        self._cron_panel = cron_panel
        self._channels_panel = channels_panel

    def compose(self) -> ComposeResult:
        with TabbedContent(id="runtime-tabs"):
            with TabPane("Sessions", id="tab-sessions"):
                yield self._sessions_panel
            with TabPane("Cron", id="tab-cron"):
                yield self._cron_panel
            with TabPane("Channels", id="tab-channels"):
                yield self._channels_panel


class CodeTabGroup(Container):
    """Tabbed group containing code-related panels.
    
    Contains:
    - Repos panel
    - Activity panel
    """

    DEFAULT_CSS = """
    CodeTabGroup {
        height: auto;
    }
    
    CodeTabGroup TabbedContent {
        height: auto;
    }
    
    CodeTabGroup TabPane {
        height: auto;
        padding: 0;
    }
    
    CodeTabGroup Tabs {
        background: $surface;
    }
    
    CodeTabGroup Tab {
        background: $surface;
        color: $text-muted;
        padding: 0 2;
    }
    
    CodeTabGroup Tab:hover {
        background: $panel;
        color: $secondary;
    }
    
    CodeTabGroup Tab.-active {
        background: $secondary 15%;
        color: $secondary;
        text-style: bold;
    }
    
    CodeTabGroup Underline {
        background: $secondary;
    }
    """

    def __init__(
        self,
        repos_panel: Static,
        activity_panel: Static,
        **kwargs,
    ) -> None:
        """Initialize with the panel widgets.
        
        Args:
            repos_panel: The repos panel widget.
            activity_panel: The activity panel widget.
        """
        super().__init__(**kwargs)
        self._repos_panel = repos_panel
        self._activity_panel = activity_panel

    def compose(self) -> ComposeResult:
        with TabbedContent(id="code-tabs"):
            with TabPane("Repos", id="tab-repos"):
                yield self._repos_panel
            with TabPane("Activity", id="tab-activity"):
                yield self._activity_panel


def switch_tab(tabbed_content: TabbedContent, tab_id: str) -> None:
    """Switch to a specific tab within a TabbedContent.
    
    Args:
        tabbed_content: The TabbedContent widget.
        tab_id: The ID of the tab pane to activate.
    """
    tabbed_content.active = tab_id


def next_tab(tabbed_content: TabbedContent) -> None:
    """Switch to the next tab in a TabbedContent.
    
    Args:
        tabbed_content: The TabbedContent widget.
    """
    # Get current active and all pane IDs
    current = tabbed_content.active
    pane_ids = [pane.id for pane in tabbed_content.query("TabPane") if pane.id]
    
    if not pane_ids:
        return
    
    try:
        idx = pane_ids.index(current)
        next_idx = (idx + 1) % len(pane_ids)
        tabbed_content.active = pane_ids[next_idx]
    except ValueError:
        # Current not found, go to first
        tabbed_content.active = pane_ids[0]


def prev_tab(tabbed_content: TabbedContent) -> None:
    """Switch to the previous tab in a TabbedContent.
    
    Args:
        tabbed_content: The TabbedContent widget.
    """
    current = tabbed_content.active
    pane_ids = [pane.id for pane in tabbed_content.query("TabPane") if pane.id]
    
    if not pane_ids:
        return
    
    try:
        idx = pane_ids.index(current)
        prev_idx = (idx - 1) % len(pane_ids)
        tabbed_content.active = pane_ids[prev_idx]
    except ValueError:
        tabbed_content.active = pane_ids[-1]
