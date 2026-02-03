"""Agents panel widget for displaying active sub-agents and their status.

This module provides widgets for monitoring and displaying the status of
sub-agents running within the OpenClaw system, including their activity state,
context usage, and task summaries.
"""

from __future__ import annotations

from textual.app import ComposeResult
from textual.widgets import Static

from openclaw_dash.collectors import agents
from openclaw_dash.widgets.ascii_art import mini_bar, separator


class AgentsPanel(Static):
    """Panel displaying active sub-agents and their coordination status.

    Shows a list of currently running sub-agents with their:
    - Status (active, idle, error)
    - Label/name
    - Context window usage percentage
    - Current task summary
    - Running time
    """

    def compose(self) -> ComposeResult:
        """Compose the panel's child widgets.

        Yields:
            A Static widget for displaying agent content.
        """
        yield Static("Loading...", id="agents-content")

    def refresh_data(self) -> None:
        """Refresh sub-agent data from the collector.

        Fetches the latest agent data and updates the panel display
        with current status, context usage, and task information.
        """
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
    """Compact agents summary for metric boxes or header display.

    Provides a condensed view of agent status suitable for inclusion
    in dashboard headers or metric boxes, showing counts by status.
    """

    def compose(self) -> ComposeResult:
        """Compose the panel's child widgets.

        Yields:
            A Static widget for displaying the summary.
        """
        yield Static("", id="agents-summary")

    def refresh_data(self) -> None:
        """Refresh the agent summary display.

        Collects agent data and renders a compact summary showing
        counts of active, idle, and error state agents.
        """
        data = agents.collect()
        content = self.query_one("#agents-summary", Static)

        total = data.get("total", 0)

        if total == 0:
            content.update("[dim]No agents[/]")
            return

        # Count by status
        agent_list = data.get("agents", [])
        status_counts = {}
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
