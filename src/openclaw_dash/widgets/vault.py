"""Vault metrics panel widget.

Displays HDLS knowledge vault metrics: entry count, domain count,
research queue depth, and agent pipeline status.
"""

from __future__ import annotations

from textual.app import ComposeResult
from textual.widgets import Static

from openclaw_dash.collectors import vault
from openclaw_dash.widgets.ascii_art import mini_bar, separator, status_indicator


class VaultPanel(Static):
    """Knowledge vault metrics panel.

    Shows:
    - Total vault entries
    - Domain count
    - Research queue depth (pending / total)
    - Pipeline status (ready / running / blocked)
    """

    def compose(self) -> ComposeResult:
        yield Static("Loading...", id="vault-content")

    def refresh_data(self) -> None:
        data = vault.collect()
        content = self.query_one("#vault-content", Static)

        if not data.get("available"):
            content.update(
                f"{status_indicator('error', 'UNAVAILABLE')}\\n"
                f"{separator(22, 'dotted')}\\n"
                f"{data.get('error', 'Vault not found')}"
            )
            return

        entries = data.get("entries", 0)
        domains = data.get("domains", 0)
        rq = data.get("research_queue", {})
        pipeline = data.get("pipeline", {})

        # Research queue depth
        rq_pending = rq.get("pending", 0)
        rq_total = rq.get("total", 0)
        rq_ratio = rq_pending / rq_total if rq_total > 0 else 0
        rq_bar = mini_bar(rq_ratio, width=6)

        # Pipeline health
        ready = pipeline.get("ready", 0)
        running = pipeline.get("running", 0)
        blocked = pipeline.get("blocked", 0)

        lines = [
            f"{status_indicator('ok', 'ONLINE')}",
            separator(22, "dotted"),
            f"Entries: [bold]{entries:,}[/]",
            f"Domains: [bold]{domains}[/]",
            separator(22, "dotted"),
            f"Research: [bold]{rq_pending}[/] pending {rq_bar}",
            f"Pipeline: [green]{ready}[/] ready / [cyan]{running}[/] running",
        ]

        if blocked > 0:
            lines.append(f"          [red]{blocked}[/] blocked")

        content.update("\n".join(lines))
