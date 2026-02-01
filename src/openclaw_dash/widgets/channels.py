"""Channels panel widget for displaying messaging channel status."""

from textual.app import ComposeResult
from textual.widgets import Static

from openclaw_dash.collectors import channels


class ChannelsPanel(Static):
    """Panel displaying connected messaging channels and their status."""

    def compose(self) -> ComposeResult:
        yield Static("", id="channels-content")

    def refresh_data(self) -> None:
        """Refresh channel status data."""
        data = channels.collect()
        content = self.query_one("#channels-content", Static)

        connected = data.get("connected", 0)
        total = data.get("total", 0)

        lines = [f"[bold]{connected}[/]/{total} connected"]

        for ch in data.get("channels", [])[:6]:
            ch_type = ch.get("type", "unknown")
            status = ch.get("status", "unknown")

            icon = channels.get_channel_icon(ch_type)
            status_icon = channels.get_status_icon(status)

            # Color based on status
            if status == "connected":
                status_fmt = f"[green]{status_icon}[/]"
            elif status == "configured":
                status_fmt = f"[yellow]{status_icon}[/]"
            elif status == "disabled":
                status_fmt = f"[dim]{status_icon}[/]"
            else:
                status_fmt = f"[red]{status_icon}[/]"

            name = ch_type.capitalize()
            lines.append(f"  {icon} {name} {status_fmt}")

        if not data.get("channels"):
            lines.append("  [dim]No channels configured[/]")

        content.update("\n".join(lines))
