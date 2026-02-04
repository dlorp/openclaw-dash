"""Sessions panel widget with DataTable display and phosphor amber aesthetic.

Lists active sessions from OpenClaw gateway with token-based highlighting.
"""

from __future__ import annotations

from textual.app import ComposeResult
from textual.message import Message
from textual.widgets import DataTable, Static

from openclaw_dash.collectors import sessions
from openclaw_dash.themes import DARK_ORANGE, MEDIUM_TURQUOISE, TITANIUM_YELLOW

# Token thresholds for highlighting
WARN_TOKEN_THRESHOLD = 50_000  # Yellow warning
CRITICAL_TOKEN_THRESHOLD = 100_000  # Red critical

# Phosphor-style glyphs
GLYPH_BULLET = "●"
GLYPH_WARN = "▲"
GLYPH_CRITICAL = "◆"
GLYPH_ELLIPSIS = "…"
GLYPH_BAR_FULL = "█"
GLYPH_BAR_EMPTY = "░"


def parse_channel_from_key(key: str) -> str:
    """Extract channel from session key.

    Session keys follow patterns like:
    - agent:main:discord:channel:1234567890
    - agent:florp:subagent:abc123

    Args:
        key: Session key string.

    Returns:
        Channel name or "-" if not found.
    """
    if not key:
        return "-"

    parts = key.split(":")
    channels = {"discord", "telegram", "slack", "whatsapp", "signal", "cli", "web"}

    for part in parts:
        if part.lower() in channels:
            return part

    if len(parts) >= 3 and parts[2] in ("main", "subagent"):
        return "local"

    return "-"


def format_tokens(tokens: int) -> str:
    """Format token count for display.

    Args:
        tokens: Token count.

    Returns:
        Formatted string (e.g., "45k", "120k", "1.2M").
    """
    if tokens >= 1_000_000:
        return f"{tokens / 1_000_000:.1f}M"
    elif tokens >= 1_000:
        return f"{tokens // 1_000}k"
    return str(tokens)


def get_token_color(tokens: int) -> str:
    """Get color based on absolute token count.

    Args:
        tokens: Total token count.

    Returns:
        Color name for Rich markup.
    """
    if tokens >= CRITICAL_TOKEN_THRESHOLD:
        return "red"
    elif tokens >= WARN_TOKEN_THRESHOLD:
        return "yellow"
    return "green"


def get_token_glyph(tokens: int) -> str:
    """Get status glyph based on token count.

    Args:
        tokens: Total token count.

    Returns:
        Phosphor-style glyph character.
    """
    if tokens >= CRITICAL_TOKEN_THRESHOLD:
        return GLYPH_CRITICAL
    elif tokens >= WARN_TOKEN_THRESHOLD:
        return GLYPH_WARN
    return GLYPH_BULLET


class SessionRowSelected(Message):
    """Message emitted when a session row is selected.

    Attributes:
        session_key: The key of the selected session.
    """

    def __init__(self, session_key: str) -> None:
        """Initialize the message.

        Args:
            session_key: The key of the selected session.
        """
        self.session_key = session_key
        super().__init__()


class SessionsPanel(Static):
    """Panel displaying active sessions with phosphor amber aesthetic.

    Shows sessions in a DataTable with:
    - Session key (truncated)
    - Kind (main/subagent/group)
    - Channel (parsed from key)
    - Model name
    - Token usage with color highlighting

    Token highlighting:
    - >50k tokens: yellow warning
    - >100k tokens: red critical
    """

    DEFAULT_CSS = """
    SessionsPanel {
        height: auto;
    }

    SessionsPanel DataTable {
        height: auto;
        max-height: 16;
    }
    """

    def compose(self) -> ComposeResult:
        """Compose the panel's child widgets."""
        table: DataTable[str] = DataTable(
            id="sessions-panel-table",
            zebra_stripes=True,
            cursor_type="row",
        )
        yield table

    def on_mount(self) -> None:
        """Initialize the table when mounted."""
        table = self.query_one("#sessions-panel-table", DataTable)
        table.add_columns("Key", "Kind", "Channel", "Model", "Tokens")
        self.refresh_data()

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle row selection - emit SessionRowSelected message."""
        table = self.query_one("#sessions-panel-table", DataTable)
        row_key = event.row_key
        if row_key is not None:
            try:
                row_data = table.get_row(row_key)
                if row_data:
                    session_key = str(row_data[0])
                    self.post_message(SessionRowSelected(session_key))
            except Exception:
                pass

    def refresh_data(self) -> None:
        """Refresh session data from the collector."""
        data = sessions.collect()
        table = self.query_one("#sessions-panel-table", DataTable)
        table.clear()

        session_list = data.get("sessions", [])

        if not session_list:
            table.add_row("-", "-", "-", "-", "[dim]No sessions[/]")
            return

        for session in session_list:
            key = session.get("key", "unknown")
            kind = session.get("kind", "unknown")
            model = session.get("model", "-")
            total_tokens = session.get("totalTokens", 0)

            # Truncate display key
            display_key = key[:18] + GLYPH_ELLIPSIS if len(key) > 18 else key

            # Parse channel from key
            channel = parse_channel_from_key(key)

            # Format and color tokens
            token_color = get_token_color(total_tokens)
            token_glyph = get_token_glyph(total_tokens)
            tokens_display = f"[{token_color}]{token_glyph} {format_tokens(total_tokens)}[/]"

            # Color kind based on type
            kind_lower = kind.lower() if kind else ""
            if kind_lower == "main":
                kind_display = f"[{MEDIUM_TURQUOISE}]{kind}[/]"
            elif kind_lower == "subagent":
                kind_display = f"[cyan]{kind}[/]"
            elif kind_lower == "group":
                kind_display = f"[{TITANIUM_YELLOW}]{kind}[/]"
            else:
                kind_display = f"[dim]{kind}[/]"

            # Truncate model name
            model_display = model[:12] + GLYPH_ELLIPSIS if len(model) > 12 else model

            # Highlight high-token session keys
            if total_tokens >= CRITICAL_TOKEN_THRESHOLD:
                display_key = f"[bold red]{display_key}[/]"
            elif total_tokens >= WARN_TOKEN_THRESHOLD:
                display_key = f"[bold {DARK_ORANGE}]{display_key}[/]"

            table.add_row(
                display_key,
                kind_display,
                channel,
                model_display,
                tokens_display,
            )


class SessionsPanelSummary(Static):
    """Compact sessions summary with token-based warnings.

    Shows active/total count and count of high-token sessions.
    """

    def compose(self) -> ComposeResult:
        """Compose the panel's child widgets."""
        yield Static("", id="sessions-panel-summary")

    def refresh_data(self) -> None:
        """Refresh the sessions summary display."""
        data = sessions.collect()
        content = self.query_one("#sessions-panel-summary", Static)

        total = data.get("total", 0)
        active = data.get("active", 0)

        if total == 0:
            content.update("[dim]No sessions[/]")
            return

        session_list = data.get("sessions", [])

        # Count high-token sessions
        warn_count = 0
        critical_count = 0
        for s in session_list:
            tokens = s.get("totalTokens", 0)
            if tokens >= CRITICAL_TOKEN_THRESHOLD:
                critical_count += 1
            elif tokens >= WARN_TOKEN_THRESHOLD:
                warn_count += 1

        # Build summary
        parts = [f"[{MEDIUM_TURQUOISE}]{GLYPH_BULLET}[/] {active}/{total}"]

        if critical_count > 0:
            parts.append(f"[red]{GLYPH_CRITICAL}{critical_count}[/]")
        if warn_count > 0:
            parts.append(f"[yellow]{GLYPH_WARN}{warn_count}[/]")

        content.update(" ".join(parts))
