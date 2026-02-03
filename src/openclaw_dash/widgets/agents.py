"""Agents panel widget for displaying active sub-agents and their status."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.widgets import Static

from openclaw_dash.collectors import agents
from openclaw_dash.widgets.ascii_art import mini_bar, separator


class AgentsPanel(Static):
    """Panel displaying active sub-agents and their coordination status."""

    def compose(self) -> ComposeResult:
        yield Static("Loading...", id="agents-content")

    def refresh_data(self) -> None:
        """Refresh sub-agent data from collector."""
        data = agents.collect()
        content = self.query_one("#agents-content", Static)

        agent_list = data.get("agents", [])
        active = data.get("active", 0)
        total = data.get("total", 0)

        if not agent_list:
            content.update("[dim]No sub-agents running[/]")
            return

        lines: list[str] = []

        # Header with count and ratio bar
        ratio = active / total if total > 0 else 0
        bar = mini_bar(ratio, width=8)
        lines.append(f"[bold]{active}[/]/{total} active {bar}")
        lines.append(separator(28, "dotted"))

        # Display each agent (limit to first 6 for space)
        for agent in agent_list[:6]:
            status = agent.get("status", "unknown")
            label = agent.get("label", "unnamed")[:14]
            running_time = agent.get("running_time", "?")
            task_summary = agent.get("task_summary", "")[:25]
            context_pct = agent.get("context_pct", 0)

            # Status icon and color
            icon = agents.get_status_icon(status)
            color = agents.get_status_color(status)

            # Context usage mini bar
            ctx_bar = mini_bar(context_pct / 100, width=4)

            # Build agent line
            lines.append(f"  [{color}]{icon}[/] [bold]{label}[/] {ctx_bar}")
            lines.append(f"    [dim]{task_summary}[/]")
            lines.append(f"    [dim]⏱ {running_time}[/]")

        # Show overflow indicator
        remaining = total - 6
        if remaining > 0:
            lines.append(f"   [dim]... and {remaining} more[/]")

        content.update("\n".join(lines))


class AgentsSummaryPanel(Static):
    """Compact agents summary for metric boxes or header display."""

    def compose(self) -> ComposeResult:
        yield Static("", id="agents-summary")

    def refresh_data(self) -> None:
        """Refresh agent summary."""
        data = agents.collect()
        content = self.query_one("#agents-summary", Static)

        total = data.get("total", 0)

        if total == 0:
            content.update("[dim]No agents[/]")
            return

        # Count by status
        agent_list = data.get("agents", [])
        status_counts: dict[str, int] = {}
        for agent in agent_list:
            status = agent.get("status", "unknown")
            status_counts[status] = status_counts.get(status, 0) + 1

        parts = []
        if status_counts.get("active", 0):
            parts.append(f"[green]● {status_counts['active']}[/]")
        if status_counts.get("idle", 0):
            parts.append(f"[yellow]◐ {status_counts['idle']}[/]")
        if status_counts.get("error", 0):
            parts.append(f"[red]✗ {status_counts['error']}[/]")

        if parts:
            content.update(" ".join(parts))
        else:
            content.update(f"[dim]{total} agents[/]")
