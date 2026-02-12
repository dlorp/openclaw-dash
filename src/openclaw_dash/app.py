"""Main TUI application."""

from typing import Any

from textual.app import App, ComposeResult
from textual.containers import Container
from textual.widget import Widget
from textual.widgets import Collapsible, DataTable, Footer, Header, Static

from openclaw_dash.collectors import activity, cron, gateway, repos, sessions
from openclaw_dash.commands import DashboardCommands
from openclaw_dash.config import Config, load_config
from openclaw_dash.themes import THEMES, next_theme
from openclaw_dash.version import get_version_info
from openclaw_dash.widgets.agents import AgentsPanel
from openclaw_dash.widgets.alerts import AlertsPanel
from openclaw_dash.widgets.ascii_art import (
    STATUS_SYMBOLS,
    mini_bar,
    progress_bar,
    separator,
    status_indicator,
)
from openclaw_dash.widgets.channels import ChannelsPanel
from openclaw_dash.widgets.connection_warning import ConnectionWarningBanner
from openclaw_dash.widgets.help_panel import HelpScreen
from openclaw_dash.widgets.input_pane import CommandSent, InputPane
from openclaw_dash.widgets.logs import LogsPanel
from openclaw_dash.widgets.metric_boxes import MetricBoxesBar
from openclaw_dash.widgets.metrics import MetricsPanel
from openclaw_dash.widgets.notifications import (
    notify_panel_error,
    notify_refresh,
)
from openclaw_dash.widgets.resources import ResourcesPanel
from openclaw_dash.widgets.security import SecurityPanel
from openclaw_dash.widgets.tabbed_groups import (  # noqa: F401 - exported for external use
    CodeTabGroup,
    RuntimeTabGroup,
)

# Responsive breakpoints (width thresholds)
COMPACT_WIDTH = 100  # Hide less-critical panels below this
MINIMUM_WIDTH = 80  # Minimum supported terminal width


def build_jump_labels(panel_ids: list[str]) -> dict[str, str]:
    """Build a mapping of single letter keys to panel IDs for jump mode.

    Args:
        panel_ids: List of panel ID strings.

    Returns:
        Dict mapping single letters (a-z) to panel IDs.
    """
    keys = "asdfghjklqwertyuiopzxcvbnm"  # Home row first for ergonomics
    return {keys[i]: panel_id for i, panel_id in enumerate(panel_ids) if i < len(keys)}


class GatewayPanel(Static):
    """Gateway status panel."""

    def compose(self) -> ComposeResult:
        yield Static("Loading...", id="gw-content")

    def refresh_data(self) -> None:
        data = gateway.collect()
        content = self.query_one("#gw-content", Static)
        if data.get("healthy"):
            ctx = data.get("context_pct", 0)
            ctx_bar = progress_bar(ctx / 100, width=12, show_percent=False, style="smooth")
            content.update(
                f"{status_indicator('ok', 'ONLINE')}\n"
                f"{separator(18, 'dotted')}\n"
                f"Context: {ctx:.0f}%\n{ctx_bar}\n"
                f"Uptime: {data.get('uptime', '?')}"
            )
        else:
            content.update(
                f"{status_indicator('error', 'OFFLINE')}\n"
                f"{separator(18, 'dotted')}\n"
                f"{data.get('error', '')}"
            )


class CurrentTaskPanel(Static):
    """Current task display."""

    def compose(self) -> ComposeResult:
        yield Static("No active task", id="task-content")

    def refresh_data(self) -> None:
        data = activity.collect()
        content = self.query_one("#task-content", Static)
        if data.get("current_task"):
            content.update(
                f"{STATUS_SYMBOLS['triangle_right']} [bold cyan]{data['current_task']}[/]"
            )
        else:
            content.update(f"{STATUS_SYMBOLS['circle_empty']} [dim]No active task[/]")


class ActivityPanel(Static):
    """Recent activity log."""

    def compose(self) -> ComposeResult:
        yield Static("", id="activity-content")

    def refresh_data(self) -> None:
        data = activity.collect()
        content = self.query_one("#activity-content", Static)
        lines = []
        for item in data.get("recent", [])[-8:]:
            lines.append(
                f"{STATUS_SYMBOLS['bullet']} [dim]{item.get('time', '?')}[/] {item.get('action', '?')}"
            )
        content.update(
            "\n".join(lines)
            if lines
            else f"{STATUS_SYMBOLS['circle_empty']} [dim]No recent activity[/]"
        )


class ReposPanel(Static):
    """Repository status panel."""

    def compose(self) -> ComposeResult:
        table: DataTable[str] = DataTable(id="repos-table", zebra_stripes=True)
        table.add_columns("Repo", "Health", "PRs", "Last Commit")
        yield table

    def refresh_data(self) -> None:
        data = repos.collect()
        table: DataTable[str] = self.query_one("#repos-table", DataTable)
        table.clear()
        for r in data.get("repos", []):
            table.add_row(
                r.get("name", "?"),
                r.get("health", "?"),
                str(r.get("open_prs", 0)),
                r.get("last_commit", "?"),
            )


class CronPanel(Static):
    """Cron jobs panel."""

    def compose(self) -> ComposeResult:
        yield Static("", id="cron-content")

    def refresh_data(self) -> None:
        data = cron.collect()
        content = self.query_one("#cron-content", Static)
        enabled = data.get("enabled", 0)
        total = data.get("total", 0)
        ratio = enabled / total if total > 0 else 0
        bar = mini_bar(ratio, width=8)

        lines = [f"[bold]{enabled}[/]/{total} enabled {bar}"]
        lines.append(separator(22, "dotted"))
        for job in data.get("jobs", [])[:5]:
            icon = (
                STATUS_SYMBOLS["triangle_right"]
                if job.get("enabled")
                else STATUS_SYMBOLS["circle_empty"]
            )
            color = "" if job.get("enabled") else "[dim]"
            end_color = "[/]" if not job.get("enabled") else ""
            name = job.get("name", "?")[:18]
            lines.append(f"  {color}{icon} {name}{end_color}")
        content.update("\n".join(lines))


class SessionsPanel(Static):
    """Sessions panel."""

    def compose(self) -> ComposeResult:
        yield Static("", id="sessions-content")

    def refresh_data(self) -> None:
        data = sessions.collect()
        content = self.query_one("#sessions-content", Static)
        active = data.get("active", 0)
        total = data.get("total", 0)
        ratio = active / total if total > 0 else 0
        bar = mini_bar(ratio, width=8)

        lines = [f"[bold]{active}[/]/{total} active {bar}"]
        lines.append(separator(25, "dotted"))
        for s in data.get("sessions", [])[:6]:
            if s.get("active"):
                icon = f"[green]{STATUS_SYMBOLS['circle_full']}[/]"
            else:
                icon = f"[dim]{STATUS_SYMBOLS['circle_empty']}[/]"
            key = s.get("key", "?")[:12]
            ctx = s.get("context_pct", 0)
            ctx_bar = mini_bar(ctx / 100, width=5)
            lines.append(f"  {icon} {key} {ctx_bar}")
        content.update("\n".join(lines))


class StatusFooter(Static):
    """Footer widget showing focused panel, mode, and version info."""

    DEFAULT_CSS = """
    StatusFooter {
        dock: bottom;
        height: 1;
        background: $surface;
        color: $text-muted;
        padding: 0 1;
    }
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._focused_panel: str = ""
        self._mode: str = "normal"

    def on_mount(self) -> None:
        """Update with initial status on mount."""
        self._update_display()

    def set_focused_panel(self, panel_name: str) -> None:
        """Update the focused panel display."""
        self._focused_panel = panel_name
        self._update_display()

    def set_mode(self, mode: str) -> None:
        """Update the current mode display."""
        self._mode = mode
        self._update_display()

    def _update_display(self) -> None:
        """Rebuild the status display."""
        info = get_version_info()
        parts = []

        if self._focused_panel:
            parts.append(f"[bold $primary]{self._focused_panel}[/]")

        if self._mode and self._mode != "normal":
            parts.append(f"[dim]({self._mode})[/]")

        left_side = " │ ".join(parts) if parts else ""
        right_side = f"[dim]{info.format_short()}[/]"

        if left_side:
            self.update(f"{left_side}  [dim]│[/]  {right_side}")
        else:
            self.update(right_side)


class DashboardApp(App):
    """Lorp's system dashboard."""

    COMMANDS = {DashboardCommands}

    DEFAULT_REFRESH_INTERVAL = 30
    WATCH_REFRESH_INTERVAL = 5

    # Panel IDs in tab-cycling order (most important first)
    PANEL_ORDER = [
        "gateway-panel",
        "alerts-panel",
        "repos-panel",
        "metrics-panel",
        "security-panel",
        "logs-panel",
        "resources-panel",
        "runtime-group",
        "code-group",
        "cron-panel",
        "sessions-panel",
        "agents-panel",
        "channels-panel",
        "activity-panel",
        "task-panel",
    ]

    # Less critical panels to hide in compact mode
    COLLAPSIBLE_PANELS = ["channels-panel", "activity-panel"]

    # Tab groups mapping group ID to contained panel IDs
    TAB_GROUPS = {
        "runtime-group": ["sessions-panel", "agents-panel", "cron-panel", "channels-panel"],
        "code-group": ["repos-panel", "activity-panel"],
    }

    config: Config
    refresh_interval: int
    _compact_mode: bool = False
    _jump_mode: bool = False
    _jump_key_mapping: dict[str, str] = {}

    def __init__(self, refresh_interval: int | None = None, watch_mode: bool = False) -> None:
        """Initialize the dashboard app.

        Args:
            refresh_interval: Custom refresh interval in seconds. If None, uses default (30s).
            watch_mode: If True and refresh_interval not set, uses aggressive 5s refresh.
        """
        super().__init__()
        if refresh_interval is not None:
            self.refresh_interval = refresh_interval
        elif watch_mode:
            self.refresh_interval = self.WATCH_REFRESH_INTERVAL
        else:
            self.refresh_interval = self.DEFAULT_REFRESH_INTERVAL

    CSS = """
    /* =================================================================
       OpenClaw Dashboard - Brand Styling
       -----------------------------------------------------------------
       Brand Colors:
         #636764 Granite Gray    - borders, muted elements
         #FB8B24 Dark Orange     - warnings, important actions
         #F4E409 Titanium Yellow - highlights, focus states
         #50D8D7 Medium Turquoise - success, online status
         #3B60E4 Royal Blue Light - primary, links
       ================================================================= */

    Screen {
        layout: grid;
        grid-size: 3 6;
        grid-gutter: 1;
        padding: 1;
    }

    /* Panel base styling with consistent borders */
    .panel {
        border: round #636764;  /* Granite Gray - consistent border color */
        padding: 1 2;  /* Consistent: 1 vertical, 2 horizontal */
    }

    .panel:focus-within {
        border: round #F4E409;  /* Titanium Yellow - focus highlight */
    }

    .panel.collapsed {
        display: none;
    }

    /* Panel title styling for consistency */
    .panel > Static:first-child {
        margin-bottom: 1;
    }

    /* =================================================================
       Panel Layout Grid
       ================================================================= */

    #gateway-panel { row-span: 1; }
    #task-panel { column-span: 2; }
    #alerts-panel { column-span: 2; row-span: 1; }
    #repos-panel { column-span: 2; row-span: 1; }
    #activity-panel { row-span: 2; }
    #cron-panel { }
    #sessions-panel { }
    #agents-panel { }
    #metrics-panel { column-span: 2; }
    #security-panel { column-span: 2; row-span: 1; }
    #logs-panel { column-span: 3; row-span: 1; }
    #resources-panel { column-span: 3; row-span: 1; }
    #resources-panel.hidden { display: none; }

    /* =================================================================
       Widget Styling
       ================================================================= */

    DataTable { height: auto; }

    /* Jump mode label styling - use brand Royal Blue */
    .jump-label {
        background: #3B60E4;  /* Royal Blue Light */
        color: #ffffff;
        text-style: bold;
        padding: 0 1;
        dock: top;
        width: auto;
        height: 1;
        offset-x: 1;
        offset-y: 0;
    }
    """

    BINDINGS = [
        ("ctrl+p", "command_palette", "Commands"),
        ("q", "quit", "Quit"),
        ("r", "refresh", "Refresh"),
        ("t", "cycle_theme", "Theme"),
        ("h", "help", "Help"),
        ("question_mark", "help", "Help"),
        # Vim-style scrolling
        ("j", "scroll_down", "↓"),
        ("k", "scroll_up", "↑"),
        ("G", "scroll_end", "End"),
        ("home", "scroll_home", "Top"),
        # Tab navigation
        ("tab", "focus_next_panel", "Next"),
        ("shift+tab", "focus_prev_panel", "Prev"),
        # Panel focus shortcuts
        ("g", "focus_panel('gateway-panel')", "Gateway"),
        ("s", "focus_panel('security-panel')", "Security"),
        ("m", "focus_panel('metrics-panel')", "Metrics"),
        ("a", "focus_panel('alerts-panel')", "Alerts"),
        ("c", "focus_panel('cron-panel')", "Cron"),
        ("p", "focus_panel('repos-panel')", "Repos"),
        ("l", "focus_panel('logs-panel')", "Logs"),
        ("n", "focus_panel('agents-panel')", "Agents"),
        ("x", "toggle_resources", "Resources"),
        # Jump mode
        ("f", "enter_jump_mode", "Jump"),
        ("slash", "enter_jump_mode", "Jump"),
        # Collapse/expand controls
        ("enter", "toggle_focused_collapse", "Toggle"),
        ("ctrl+left_square_bracket", "collapse_all", "Collapse All"),
        ("ctrl+right_square_bracket", "expand_all", "Expand All"),
        # Tab group navigation
        ("1", "focus_tab_group('runtime-group')", "Runtime"),
        ("2", "focus_tab_group('code-group')", "Code"),
        ("bracketleft", "prev_tab_in_group", "["),
        ("bracketright", "next_tab_in_group", "]"),
        # Input pane
        ("colon", "focus_input", "Input"),
        ("i", "focus_input", "Input"),
    ]

    _mounted: bool = False  # Track if initial mount is complete (for notifications)

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield ConnectionWarningBanner(id="connection-warning")
        yield MetricBoxesBar(id="metric-boxes")

        with Container(id="gateway-panel", classes="panel"):
            with Collapsible(
                title="Gateway",
                collapsed=False,
                collapsed_symbol="▸",
                expanded_symbol="▾",
                id="gateway-panel-collapsible",
            ):
                yield GatewayPanel()

        with Container(id="task-panel", classes="panel"):
            with Collapsible(
                title="Current Task",
                collapsed=False,
                collapsed_symbol="▸",
                expanded_symbol="▾",
                id="task-panel-collapsible",
            ):
                yield CurrentTaskPanel()

        with Container(id="alerts-panel", classes="panel"):
            with Collapsible(
                title=" Alerts",
                collapsed=False,
                collapsed_symbol="▸",
                expanded_symbol="▾",
                id="alerts-panel-collapsible",
            ):
                yield AlertsPanel()

        with Container(id="repos-panel", classes="panel"):
            with Collapsible(
                title="Repositories",
                collapsed=False,
                collapsed_symbol="▸",
                expanded_symbol="▾",
                id="repos-panel-collapsible",
            ):
                yield ReposPanel()

        with Container(id="activity-panel", classes="panel"):
            with Collapsible(
                title="Activity",
                collapsed=False,
                collapsed_symbol="▸",
                expanded_symbol="▾",
                id="activity-panel-collapsible",
            ):
                yield ActivityPanel()

        with Container(id="cron-panel", classes="panel"):
            with Collapsible(
                title="Cron",
                collapsed=False,
                collapsed_symbol="▸",
                expanded_symbol="▾",
                id="cron-panel-collapsible",
            ):
                yield CronPanel()

        with Container(id="sessions-panel", classes="panel"):
            with Collapsible(
                title="Sessions",
                collapsed=False,
                collapsed_symbol="▸",
                expanded_symbol="▾",
                id="sessions-panel-collapsible",
            ):
                yield SessionsPanel()

        with Container(id="agents-panel", classes="panel"):
            with Collapsible(
                title=" Agents",
                collapsed=False,
                collapsed_symbol="▸",
                expanded_symbol="▾",
                id="agents-panel-collapsible",
            ):
                yield AgentsPanel()

        with Container(id="channels-panel", classes="panel"):
            with Collapsible(
                title="Channels",
                collapsed=False,
                collapsed_symbol="▸",
                expanded_symbol="▾",
                id="channels-panel-collapsible",
            ):
                yield ChannelsPanel()

        with Container(id="metrics-panel", classes="panel"):
            with Collapsible(
                title=" Metrics",
                collapsed=False,
                collapsed_symbol="▸",
                expanded_symbol="▾",
                id="metrics-panel-collapsible",
            ):
                yield MetricsPanel()

        with Container(id="security-panel", classes="panel"):
            with Collapsible(
                title=" Security",
                collapsed=False,
                collapsed_symbol="▸",
                expanded_symbol="▾",
                id="security-panel-collapsible",
            ):
                yield SecurityPanel()

        with Container(id="logs-panel", classes="panel"):
            with Collapsible(
                title="Logs Logs",
                collapsed=False,
                collapsed_symbol="▸",
                expanded_symbol="▾",
                id="logs-panel-collapsible",
            ):
                yield LogsPanel(n_lines=12)

        with Container(id="resources-panel", classes="panel"):
            with Collapsible(
                title=" Resources",
                collapsed=False,
                collapsed_symbol="▸",
                expanded_symbol="▾",
                id="resources-panel-collapsible",
            ):
                yield ResourcesPanel()

        yield InputPane(id="input-pane")
        yield Footer()
        yield StatusFooter(id="status-footer")

    def on_mount(self) -> None:
        # Load user config
        self.config = load_config()

        # Register custom themes
        for theme in THEMES:
            self.register_theme(theme)

        # Apply saved theme (or default)
        self.theme = self.config.theme

        # Apply resources panel visibility
        if not self.config.show_resources:
            try:
                panel = self.query_one("#resources-panel")
                panel.add_class("hidden")
            except Exception:
                pass

        # Apply saved collapsed states
        for panel_id in self.config.collapsed_panels:
            try:
                collapsible = self.query_one(f"#{panel_id}-collapsible", Collapsible)
                collapsible.collapsed = True
            except Exception:
                pass

        # Apply initial responsive layout
        self._apply_responsive_layout(self.size.width, self.size.height)

        self.action_refresh()
        self._mounted = True  # Enable notifications after initial load
        self.set_interval(self.refresh_interval, self._do_auto_refresh)

    def _apply_responsive_layout(self, width: int, height: int) -> None:
        """Apply responsive layout based on terminal size."""
        # Hide less critical panels when terminal is narrow
        hide_threshold = 100  # Minimum width for full layout
        panels_to_hide = ["channels-panel", "security-panel", "metrics-panel"]

        for panel_id in panels_to_hide:
            try:
                panel = self.query_one(f"#{panel_id}")
                if width < hide_threshold:
                    panel.add_class("hidden")
                else:
                    panel.remove_class("hidden")
            except Exception:
                pass

    def on_resize(self, event: Any) -> None:
        """Handle terminal resize."""
        self._apply_responsive_layout(event.size.width, event.size.height)

    def _do_auto_refresh(self) -> None:
        """Auto-refresh without notification (for timer-based refresh)."""
        # Refresh connection warning banner
        try:
            warning_banner = self.query_one(ConnectionWarningBanner)
            warning_banner.check_and_update()
        except Exception:
            pass
            # Refresh metric boxes bar
        try:
            metric_boxes = self.query_one(MetricBoxesBar)
            metric_boxes.refresh_data()
        except Exception:
            pass

        for panel_cls in [
            GatewayPanel,
            CurrentTaskPanel,
            AlertsPanel,
            ActivityPanel,
            ReposPanel,
            CronPanel,
            SessionsPanel,
            AgentsPanel,
            ChannelsPanel,
            MetricsPanel,
            SecurityPanel,
            LogsPanel,
            ResourcesPanel,
        ]:
            try:
                # Skip resources panel if disabled
                if panel_cls == ResourcesPanel and not self.config.show_resources:
                    continue
                auto_refresh_panel: Static = self.query_one(panel_cls)  # type: ignore[arg-type]
                auto_refresh_panel.refresh_data()  # type: ignore[attr-defined]
            except Exception:
                pass

    def action_cycle_theme(self) -> None:
        """Cycle through available themes and save preference."""
        self.theme = next_theme(self.theme)
        self.config.update(theme=self.theme)
        self.notify(f"Theme: {self.theme}", timeout=1.5)

    def action_refresh(self) -> None:
        """Refresh all panels and show notification."""
        # Refresh connection warning banner
        try:
            warning_banner = self.query_one(ConnectionWarningBanner)
            warning_banner.check_and_update()
        except Exception:
            pass
            # Refresh metric boxes bar
        try:
            metric_boxes = self.query_one(MetricBoxesBar)
            metric_boxes.refresh_data()
        except Exception:
            pass

        panels = [
            GatewayPanel,
            CurrentTaskPanel,
            AlertsPanel,
            ActivityPanel,
            ReposPanel,
            CronPanel,
            SessionsPanel,
            AgentsPanel,
            ChannelsPanel,
            MetricsPanel,
            SecurityPanel,
            LogsPanel,
            ResourcesPanel,
        ]
        refreshed = 0
        errors = []
        for panel_cls in panels:
            try:
                # Skip resources panel if disabled
                if panel_cls == ResourcesPanel and not self.config.show_resources:
                    continue
                try:
                    refresh_panel: Static = self.query_one(panel_cls)  # type: ignore[arg-type]
                    refresh_panel.refresh_data()  # type: ignore[attr-defined]
                    refreshed += 1
                except Exception:
                    pass
            except Exception as e:
                errors.append((panel_cls.__name__, str(e)))

        # Show notification for manual refresh (not auto-refresh on mount)
        if self._mounted:
            if errors:
                for panel_name, error in errors[:2]:  # Limit error notifications
                    notify_panel_error(self, panel_name, error)
            else:
                notify_refresh(self, refreshed)

    def action_help(self) -> None:
        """Show the help panel with keyboard shortcuts."""
        self.push_screen(HelpScreen())

    def action_focus_panel(self, panel_id: str) -> None:
        """Focus a specific panel by ID."""
        try:
            panel = self.query_one(f"#{panel_id}")
            panel.focus()
        except Exception:
            pass

    def action_scroll_down(self) -> None:
        """Scroll the focused panel down (vim j key)."""
        focused = self.focused
        if focused is not None:
            # Find scrollable parent or use focused widget
            widget: Widget | None = focused
            while widget is not None:
                if hasattr(widget, "scroll_down"):
                    widget.scroll_down()
                    return
                widget = widget.parent if isinstance(widget.parent, Widget) else None

    def action_scroll_up(self) -> None:
        """Scroll the focused panel up (vim k key)."""
        focused = self.focused
        if focused is not None:
            widget: Widget | None = focused
            while widget is not None:
                if hasattr(widget, "scroll_up"):
                    widget.scroll_up()
                    return
                widget = widget.parent if isinstance(widget.parent, Widget) else None

    def action_scroll_end(self) -> None:
        """Scroll to the bottom of focused panel (vim G key)."""
        focused = self.focused
        if focused is not None:
            widget: Widget | None = focused
            while widget is not None:
                if hasattr(widget, "scroll_end"):
                    widget.scroll_end()
                    return
                widget = widget.parent if isinstance(widget.parent, Widget) else None

    def action_scroll_home(self) -> None:
        """Scroll to the top of focused panel (vim gg / Home key)."""
        focused = self.focused
        if focused is not None:
            widget: Widget | None = focused
            while widget is not None:
                if hasattr(widget, "scroll_home"):
                    widget.scroll_home()
                    return
                widget = widget.parent if isinstance(widget.parent, Widget) else None

    def action_toggle_resources(self) -> None:
        """Toggle the resources panel visibility and save preference."""
        try:
            panel = self.query_one("#resources-panel")
            self.config.show_resources = not self.config.show_resources
            self.config.save()

            if self.config.show_resources:
                panel.remove_class("hidden")
                # Refresh the panel when shown
                try:
                    resources_widget = self.query_one(ResourcesPanel)
                    resources_widget.refresh_data()
                except Exception:
                    pass
                self.notify("Resources panel: ON", timeout=1.5)
            else:
                panel.add_class("hidden")
                self.notify("Resources panel: OFF", timeout=1.5)
        except Exception:
            pass

    def action_toggle_focused_collapse(self) -> None:
        """Toggle collapse state of the focused panel."""
        focused = self.focused
        if focused is None:
            return

        # Find the collapsible in the focused widget's hierarchy
        widget: Widget | None = focused
        while widget is not None:
            # Check if we're inside a panel container
            if hasattr(widget, "id") and widget.id and widget.id.endswith("-panel"):
                panel_id = widget.id
                try:
                    collapsible = self.query_one(f"#{panel_id}-collapsible", Collapsible)
                    collapsible.collapsed = not collapsible.collapsed
                    self._save_collapsed_state(panel_id, collapsible.collapsed)
                except Exception:
                    pass
                return
            widget = widget.parent if isinstance(widget.parent, Widget) else None

    def action_collapse_all(self) -> None:
        """Collapse all panels."""
        collapsed_ids = []
        for panel_id in self.PANEL_ORDER:
            try:
                collapsible = self.query_one(f"#{panel_id}-collapsible", Collapsible)
                collapsible.collapsed = True
                collapsed_ids.append(panel_id)
            except Exception:
                pass

        # Save all collapsed states
        self.config.collapsed_panels = collapsed_ids
        self.config.save()
        self.notify("All panels collapsed", timeout=1.5)

    def action_expand_all(self) -> None:
        """Expand all panels."""
        for panel_id in self.PANEL_ORDER:
            try:
                collapsible = self.query_one(f"#{panel_id}-collapsible", Collapsible)
                collapsible.collapsed = False
            except Exception:
                pass

        # Clear collapsed states
        self.config.collapsed_panels = []
        self.config.save()
        self.notify("All panels expanded", timeout=1.5)

    def _save_collapsed_state(self, panel_id: str, collapsed: bool) -> None:
        """Save a panel's collapsed state to config."""
        if collapsed:
            if panel_id not in self.config.collapsed_panels:
                self.config.collapsed_panels.append(panel_id)
        else:
            if panel_id in self.config.collapsed_panels:
                self.config.collapsed_panels.remove(panel_id)
        self.config.save()

    def on_collapsible_collapsed(self, event: Collapsible.Collapsed) -> None:
        """Handle collapsible collapse event."""
        collapsible = event.collapsible
        if collapsible.id and collapsible.id.endswith("-collapsible"):
            panel_id = collapsible.id.replace("-collapsible", "")
            self._save_collapsed_state(panel_id, True)

    def on_collapsible_expanded(self, event: Collapsible.Expanded) -> None:
        """Handle collapsible expand event."""
        collapsible = event.collapsible
        if collapsible.id and collapsible.id.endswith("-collapsible"):
            panel_id = collapsible.id.replace("-collapsible", "")
            self._save_collapsed_state(panel_id, False)

    def action_focus_tab_group(self, group_id: str) -> None:
        """Focus a specific tab group by ID."""
        try:
            group = self.query_one(f"#{group_id}")
            group.focus()
        except Exception:
            pass

    def action_next_tab_in_group(self) -> None:
        """Switch to the next tab in the focused tab group."""
        try:
            from textual.widgets import TabbedContent

            focused = self.focused
            if focused:
                # Find parent TabbedContent
                parent = focused.parent
                while parent and not isinstance(parent, TabbedContent):
                    parent = parent.parent
                if parent and isinstance(parent, TabbedContent):
                    # Get current tab index and switch to next
                    tabs = list(parent.query("TabPane"))
                    if tabs:
                        current_idx = 0
                        for i, tab in enumerate(tabs):
                            if tab.has_focus or tab.has_focus_within:
                                current_idx = i
                                break
                        next_idx = (current_idx + 1) % len(tabs)
                        parent.active = tabs[next_idx].id or ""
        except Exception:
            pass

    def action_prev_tab_in_group(self) -> None:
        """Switch to the previous tab in the focused tab group."""
        try:
            from textual.widgets import TabbedContent

            focused = self.focused
            if focused:
                # Find parent TabbedContent
                parent = focused.parent
                while parent and not isinstance(parent, TabbedContent):
                    parent = parent.parent
                if parent and isinstance(parent, TabbedContent):
                    # Get current tab index and switch to previous
                    tabs = list(parent.query("TabPane"))
                    if tabs:
                        current_idx = 0
                        for i, tab in enumerate(tabs):
                            if tab.has_focus or tab.has_focus_within:
                                current_idx = i
                                break
                        prev_idx = (current_idx - 1) % len(tabs)
                        parent.active = tabs[prev_idx].id or ""
        except Exception:
            pass

    def action_enter_jump_mode(self) -> None:
        """Enter jump mode for quick panel navigation."""
        if self._jump_mode:
            return  # Already in jump mode

        self._jump_mode = True
        self._jump_key_mapping = build_jump_labels(self.PANEL_ORDER)

        # Show jump labels on each panel
        for key, panel_id in self._jump_key_mapping.items():
            try:
                panel = self.query_one(f"#{panel_id}")
                label = Static(f"[{key}]", classes="jump-label")
                label.id = f"jump-label-{panel_id}"
                panel.mount(label)
            except Exception:
                pass

        # Update status footer to show jump mode
        try:
            footer = self.query_one("#status-footer", StatusFooter)
            footer.set_mode("jump")
        except Exception:
            pass

    def _exit_jump_mode(self) -> None:
        """Exit jump mode and remove labels."""
        if not self._jump_mode:
            return

        self._jump_mode = False

        # Remove all jump labels
        for panel_id in self.PANEL_ORDER:
            try:
                label = self.query_one(f"#jump-label-{panel_id}")
                label.remove()
            except Exception:
                pass

        # Reset status footer
        try:
            footer = self.query_one("#status-footer", StatusFooter)
            footer.set_mode("normal")
        except Exception:
            pass

    def on_key(self, event) -> None:
        """Handle key presses, including jump mode navigation."""
        if not self._jump_mode:
            return

        key = event.key.lower() if hasattr(event, "key") else str(event).lower()

        # Escape exits jump mode without action
        if key == "escape":
            self._exit_jump_mode()
            event.stop()
            return

        # Check if it's a valid jump key
        if key in self._jump_key_mapping:
            panel_id = self._jump_key_mapping[key]
            self._exit_jump_mode()
            self.action_focus_panel(panel_id)
            event.stop()
            return

        # Any other key exits jump mode
        self._exit_jump_mode()
        event.stop()

    def action_focus_input(self) -> None:
        """Focus the command input pane."""
        try:
            input_pane = self.query_one(InputPane)
            input_pane.focus_input()
        except Exception:
            pass

    def on_command_sent(self, event: CommandSent) -> None:
        """Handle command sent events from the input pane."""
        if event.success:
            # Show brief success notification
            self.notify(
                f"Command sent: {event.command[:30]}{'...' if len(event.command) > 30 else ''}",
                timeout=2.0,
            )
        else:
            # Show error notification
            self.notify(
                f"Error: {event.response[:50]}{'...' if len(event.response) > 50 else ''}",
                severity="error",
                timeout=4.0,
            )
