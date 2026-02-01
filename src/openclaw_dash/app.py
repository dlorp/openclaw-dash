"""Main TUI application."""

from textual.app import App, ComposeResult
from textual.containers import Container
from textual.widgets import DataTable, Footer, Header, Static

from openclaw_dash.collectors import activity, cron, gateway, repos, sessions
from openclaw_dash.widgets.channels import ChannelsPanel


class GatewayPanel(Static):
    """Gateway status panel."""

    def compose(self) -> ComposeResult:
        yield Static("Loading...", id="gw-content")

    def refresh_data(self) -> None:
        data = gateway.collect()
        content = self.query_one("#gw-content", Static)
        if data.get("healthy"):
            ctx = data.get("context_pct", 0)
            content.update(
                f"[green]✓ ONLINE[/]\nContext: {ctx:.0f}%\nUptime: {data.get('uptime', '?')}"
            )
        else:
            content.update(f"[red]✗ OFFLINE[/]\n{data.get('error', '')}")


class CurrentTaskPanel(Static):
    """Current task display."""

    def compose(self) -> ComposeResult:
        yield Static("No active task", id="task-content")

    def refresh_data(self) -> None:
        data = activity.collect()
        content = self.query_one("#task-content", Static)
        if data.get("current_task"):
            content.update(f"[bold cyan]{data['current_task']}[/]")
        else:
            content.update("[dim]No active task[/]")


class ActivityPanel(Static):
    """Recent activity log."""

    def compose(self) -> ComposeResult:
        yield Static("", id="activity-content")

    def refresh_data(self) -> None:
        data = activity.collect()
        content = self.query_one("#activity-content", Static)
        lines = []
        for item in data.get("recent", [])[-8:]:
            lines.append(f"[dim]{item.get('time', '?')}[/] {item.get('action', '?')}")
        content.update("\n".join(lines) if lines else "[dim]No recent activity[/]")


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
        lines = [f"[bold]{data.get('enabled', 0)}[/]/{data.get('total', 0)} enabled"]
        for job in data.get("jobs", [])[:5]:
            icon = "▸" if job.get("enabled") else "▹"
            name = job.get("name", "?")[:20]
            lines.append(f"  {icon} {name}")
        content.update("\n".join(lines))


class SessionsPanel(Static):
    """Sessions panel."""

    def compose(self) -> ComposeResult:
        yield Static("", id="sessions-content")

    def refresh_data(self) -> None:
        data = sessions.collect()
        content = self.query_one("#sessions-content", Static)
        lines = [f"[bold]{data.get('active', 0)}[/]/{data.get('total', 0)} active"]
        for s in data.get("sessions", [])[:6]:
            icon = "[green]●[/]" if s.get("active") else "[dim]○[/]"
            key = s.get("key", "?")[:15]
            ctx = s.get("context_pct", 0)
            lines.append(f"  {icon} {key} [{ctx:.0f}%]")
        content.update("\n".join(lines))


class DashboardApp(App):
    """Lorp's system dashboard."""

    CSS = """
    Screen {
        layout: grid;
        grid-size: 3 3;
        grid-gutter: 1;
        padding: 1;
    }

    .panel {
        border: round $primary;
        padding: 1;
    }

    #gateway-panel { row-span: 1; }
    #task-panel { column-span: 2; }
    #repos-panel { column-span: 2; row-span: 1; }
    #activity-panel { row-span: 2; }
    #cron-panel { }
    #sessions-panel { }

    DataTable { height: auto; }
    """

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("r", "refresh", "Refresh"),
    ]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)

        with Container(id="gateway-panel", classes="panel"):
            yield Static("[bold]Gateway[/]")
            yield GatewayPanel()

        with Container(id="task-panel", classes="panel"):
            yield Static("[bold]Current Task[/]")
            yield CurrentTaskPanel()

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

        yield Footer()

    def on_mount(self) -> None:
        self.action_refresh()
        self.set_interval(30, self.action_refresh)

    def action_refresh(self) -> None:
        for panel_cls in [
            GatewayPanel,
            CurrentTaskPanel,
            ActivityPanel,
            ReposPanel,
            CronPanel,
            SessionsPanel,
            ChannelsPanel,
        ]:
            try:
                panel = self.query_one(panel_cls)
                panel.refresh_data()
            except Exception:
                pass
