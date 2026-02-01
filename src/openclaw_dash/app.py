"""Main TUI application."""

from textual.app import App, ComposeResult
from textual.containers import Container
from textual.widgets import DataTable, Footer, Header, Static

from openclaw_dash.collectors import activity, cron, gateway, repos, sessions
from openclaw_dash.commands import DashboardCommands
from openclaw_dash.config import Config, load_config
from openclaw_dash.themes import THEMES, next_theme
from openclaw_dash.widgets.alerts import AlertsPanel
from openclaw_dash.widgets.ascii_art import (
    STATUS_SYMBOLS,
    mini_bar,
    progress_bar,
    separator,
    status_indicator,
)
from openclaw_dash.widgets.channels import ChannelsPanel
from openclaw_dash.widgets.help_panel import HelpScreen
from openclaw_dash.widgets.metrics import MetricsPanel
from openclaw_dash.widgets.notifications import (
    notify_panel_error,
    notify_refresh,
)
from openclaw_dash.widgets.security import SecurityPanel


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
        table = DataTable(id="repos-table", zebra_stripes=True)
        table.add_columns("Repo", "Health", "PRs", "Last Commit")
        yield table

    def refresh_data(self) -> None:
        data = repos.collect()
        table = self.query_one("#repos-table", DataTable)
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


class DashboardApp(App):
    """Lorp's system dashboard."""

    COMMANDS = {DashboardCommands}

    WATCH_REFRESH_INTERVAL = 5

    config: Config
    watch_mode: bool = False

    def __init__(self, watch_mode: bool = False) -> None:
        """Initialize the dashboard app.

        Args:
            watch_mode: If True, uses aggressive 5s refresh interval.
        """
        super().__init__()
        self.watch_mode = watch_mode

    CSS = """
    Screen {
        layout: grid;
        grid-size: 3 5;
        grid-gutter: 1;
        padding: 1;
    }

    .panel {
        border: round $primary;
        padding: 1;
    }

    #gateway-panel { row-span: 1; }
    #task-panel { column-span: 2; }
    #alerts-panel { column-span: 2; row-span: 1; }
    #repos-panel { column-span: 2; row-span: 1; }
    #activity-panel { row-span: 2; }
    #cron-panel { }
    #sessions-panel { }
    #metrics-panel { column-span: 2; }
    #security-panel { column-span: 2; row-span: 1; }

    DataTable { height: auto; }
    """

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("r", "refresh", "Refresh"),
        ("t", "cycle_theme", "Theme"),
        ("h", "help", "Help"),
        ("question_mark", "help", "Help"),
        ("g", "focus_panel('gateway-panel')", "Gateway"),
        ("s", "focus_panel('security-panel')", "Security"),
        ("m", "focus_panel('metrics-panel')", "Metrics"),
        ("a", "focus_panel('alerts-panel')", "Alerts"),
        ("c", "focus_panel('cron-panel')", "Cron"),
        ("p", "focus_panel('repos-panel')", "Repos"),
    ]

    _mounted: bool = False  # Track if initial mount is complete (for notifications)

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)

        with Container(id="gateway-panel", classes="panel"):
            yield Static("[bold]Gateway[/]")
            yield GatewayPanel()

        with Container(id="task-panel", classes="panel"):
            yield Static("[bold]Current Task[/]")
            yield CurrentTaskPanel()

        with Container(id="alerts-panel", classes="panel"):
            yield Static("[bold]⚠️ Alerts[/]")
            yield AlertsPanel()

        with Container(id="repos-panel", classes="panel"):
            yield Static("[bold]Repositories[/]")
            yield ReposPanel()

        with Container(id="activity-panel", classes="panel"):
            yield Static("[bold]Activity[/]")
            yield ActivityPanel()

        with Container(id="cron-panel", classes="panel"):
            yield Static("[bold]Cron[/]")
            yield CronPanel()

        with Container(id="sessions-panel", classes="panel"):
            yield Static("[bold]Sessions[/]")
            yield SessionsPanel()

        with Container(id="channels-panel", classes="panel"):
            yield Static("[bold]Channels[/]")
            yield ChannelsPanel()

        with Container(id="metrics-panel", classes="panel"):
            yield Static("[bold]📊 Metrics[/]")
            yield MetricsPanel()

        with Container(id="security-panel", classes="panel"):
            yield Static("[bold]🔒 Security[/]")
            yield SecurityPanel()

        yield Footer()

    def on_mount(self) -> None:
        # Load user config
        self.config = load_config()

        # Register custom themes
        for theme in THEMES:
            self.register_theme(theme)

        # Apply saved theme (or default)
        self.theme = self.config.theme

        self.action_refresh()
        self._mounted = True  # Enable notifications after initial load
        interval = self.WATCH_REFRESH_INTERVAL if self.watch_mode else self.config.refresh_interval
        self.set_interval(interval, self._auto_refresh)

    def _auto_refresh(self) -> None:
        """Auto-refresh without notification (for timer-based refresh)."""
        for panel_cls in [
            GatewayPanel,
            CurrentTaskPanel,
            AlertsPanel,
            ActivityPanel,
            ReposPanel,
            CronPanel,
            SessionsPanel,
            ChannelsPanel,
            MetricsPanel,
            SecurityPanel,
        ]:
            try:
                panel = self.query_one(panel_cls)
                panel.refresh_data()
            except Exception:
                pass

    def action_cycle_theme(self) -> None:
        """Cycle through available themes and save preference."""
        self.theme = next_theme(self.theme)
        self.config.update(theme=self.theme)
        self.notify(f"Theme: {self.theme}", timeout=1.5)

    def action_refresh(self) -> None:
        """Refresh all panels and show notification."""
        panels = [
            GatewayPanel,
            CurrentTaskPanel,
            AlertsPanel,
            ActivityPanel,
            ReposPanel,
            CronPanel,
            SessionsPanel,
            ChannelsPanel,
            MetricsPanel,
            SecurityPanel,
        ]
        refreshed = 0
        errors = []
        for panel_cls in panels:
            try:
                panel = self.query_one(panel_cls)
                panel.refresh_data()
                refreshed += 1
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
