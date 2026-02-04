"""Sessions table panel widget using DataTable for tabular display.

This module provides a DataTable-based widget for viewing active OpenClaw
sessions with clickable rows for taking actions on sessions.
"""

from __future__ import annotations

from textual.app import ComposeResult
from textual.message import Message
from textual.widgets import DataTable, Static

from openclaw_dash.collectors import sessions
from openclaw_dash.themes import DARK_ORANGE, MEDIUM_TURQUOISE

# High token threshold - sessions using more than this % of context are highlighted
HIGH_TOKEN_THRESHOLD = 70


def parse_channel_from_key(key: str) -> str:
    """Extract channel info from session key.

    Session keys follow patterns like:
    - agent:main:discord:channel:1234567890
    - agent:florp:subagent:abc123
    - agent:main:main

    Args:
        key: The session key string.

    Returns:
        Extracted channel name or "-" if not found.
    """
    if not key:
        return "-"

    parts = key.split(":")
    # Look for common channel identifiers
    channel_types = {"discord", "telegram", "slack", "whatsapp", "signal", "cli", "web"}

    for i, part in enumerate(parts):
        if part.lower() in channel_types:
            return part

    # Check if it looks like agent:name:channel:...
    if len(parts) >= 3 and parts[2].lower() in channel_types:
        return parts[2]

    # If kind is main/subagent without channel, mark as local
    if len(parts) >= 3 and parts[2] in ("main", "subagent"):
        return "local"

    return "-"


def classify_kind(kind: str) -> str:
    """Classify session kind into main/group/other.

    Args:
        kind: The session kind from the collector.

    Returns:
        Classified kind: "main", "group", or "other".
    """
    kind_lower = kind.lower() if kind else ""

    if kind_lower in ("main", "primary"):
        return "main"
    elif kind_lower in ("group", "shared", "channel"):
        return "group"
    elif kind_lower in ("subagent", "sub", "agent"):
        return "subagent"
    else:
        return kind or "other"


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
    else:
        return str(tokens)


def get_context_color(pct: float) -> str:
    """Get color for context usage percentage.

    Args:
        pct: Context usage percentage (0-100).

    Returns:
        Color name for Rich markup.
    """
    if pct >= 80:
        return "red"
    elif pct >= HIGH_TOKEN_THRESHOLD:
        return DARK_ORANGE  # Brand orange for warning
    elif pct >= 50:
        return "yellow"
    else:
        return "green"


class SessionSelected(Message):
    """Message emitted when a session row is clicked/selected.

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


class SessionsTablePanel(Static):
    """Panel displaying active sessions in a DataTable with phosphor amber aesthetic.

    Shows sessions with:
    - Session key (truncated for display)
    - Kind (main/group/subagent/other)
    - Channel (parsed from key)
    - Model name
    - Token usage with visual indicator
    - Context percentage with color coding

    Clickable rows emit SessionSelected messages for future actions.
    """

    DEFAULT_CSS = """
    SessionsTablePanel {
        height: auto;
    }

    SessionsTablePanel DataTable {
        height: auto;
        max-height: 20;
    }

    SessionsTablePanel .high-tokens {
        background: $warning 20%;
    }
    """

    def compose(self) -> ComposeResult:
        """Compose the panel's child widgets.

        Yields:
            A DataTable widget for displaying sessions.
        """
        table: DataTable[str] = DataTable(
            id="sessions-table",
            zebra_stripes=True,
            cursor_type="row",
        )
        yield table

    def on_mount(self) -> None:
        """Initialize the table when mounted."""
        table = self.query_one("#sessions-table", DataTable)
        table.add_columns("Key", "Kind", "Channel", "Model", "Tokens", "Context")
        self.refresh_data()

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle row selection - emit SessionSelected message.

        Args:
            event: The row selection event.
        """
        table = self.query_one("#sessions-table", DataTable)
        row_key = event.row_key
        if row_key is not None:
            # Get the session key from the first cell of the selected row
            try:
                row_data = table.get_row(row_key)
                if row_data:
                    # First column is the key
                    session_key = str(row_data[0])
                    self.post_message(SessionSelected(session_key))
            except Exception:
                pass

    def refresh_data(self) -> None:
        """Refresh session data from the collector.

        Fetches active session data and updates the DataTable with
        status indicators and context usage visualizations.
        """
        data = sessions.collect()
        table = self.query_one("#sessions-table", DataTable)
        table.clear()

        session_list = data.get("sessions", [])

        if not session_list:
            # Add a placeholder row when empty
            table.add_row("-", "-", "-", "-", "-", "[dim]No sessions[/]")
            return

        for session in session_list:
            key = session.get("key", "unknown")
            raw_kind = session.get("kind", "unknown")
            model = session.get("model", "-")
            total_tokens = session.get("totalTokens", 0)
            context_pct = session.get("context_pct", 0.0)

            # Process fields
            display_key = key[:20] + "…" if len(key) > 20 else key
            kind = classify_kind(raw_kind)
            channel = parse_channel_from_key(key)
            tokens_str = format_tokens(total_tokens)

            # Color code context percentage
            ctx_color = get_context_color(context_pct)
            context_str = f"[{ctx_color}]{context_pct:.0f}%[/]"

            # Add visual bar for context
            bar_width = 6
            filled = int((context_pct / 100) * bar_width)
            bar = f"[{ctx_color}]{'█' * filled}[/][dim]{'░' * (bar_width - filled)}[/]"
            context_display = f"{context_str} {bar}"

            # Color kind based on type
            if kind == "main":
                kind_display = f"[{MEDIUM_TURQUOISE}]{kind}[/]"
            elif kind == "subagent":
                kind_display = f"[cyan]{kind}[/]"
            elif kind == "group":
                kind_display = f"[yellow]{kind}[/]"
            else:
                kind_display = f"[dim]{kind}[/]"

            # Highlight high-token sessions
            if context_pct >= HIGH_TOKEN_THRESHOLD:
                display_key = f"[bold {DARK_ORANGE}]{display_key}[/]"
                tokens_str = f"[bold {DARK_ORANGE}]{tokens_str}[/]"

            table.add_row(
                display_key,
                kind_display,
                channel,
                model[:15] if len(model) > 15 else model,
                tokens_str,
                context_display,
            )


class SessionsTableSummary(Static):
    """Compact sessions summary showing counts and average context usage.

    Suitable for metric boxes or dashboard headers.
    """

    def compose(self) -> ComposeResult:
        """Compose the panel's child widgets.

        Yields:
            A Static widget for displaying the summary.
        """
        yield Static("", id="sessions-table-summary")

    def refresh_data(self) -> None:
        """Refresh the sessions summary display.

        Collects session data and renders a compact summary with
        active counts and average context usage indicator.
        """
        data = sessions.collect()
        content = self.query_one("#sessions-table-summary", Static)

        total = data.get("total", 0)
        active = data.get("active", 0)

        if total == 0:
            content.update("[dim]No sessions[/]")
            return

        # Calculate average context usage
        session_list = data.get("sessions", [])
        if session_list:
            avg_ctx = sum(s.get("context_pct", 0) for s in session_list) / len(session_list)
            high_ctx_count = sum(
                1 for s in session_list if s.get("context_pct", 0) >= HIGH_TOKEN_THRESHOLD
            )
        else:
            avg_ctx = 0
            high_ctx_count = 0

        # Color based on context usage
        ctx_color = get_context_color(avg_ctx)

        # Build summary
        parts = [f"[{MEDIUM_TURQUOISE}]●[/] {active}/{total}"]
        parts.append(f"[{ctx_color}]{avg_ctx:.0f}%[/]")

        if high_ctx_count > 0:
            parts.append(f"[{DARK_ORANGE}]⚠{high_ctx_count}[/]")

        content.update(" ".join(parts))
