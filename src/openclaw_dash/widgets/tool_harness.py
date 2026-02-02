"""Tool Harness panel widget for visualizing agent-tool connections.

Provides an ASCII art visualization of the agent runtime and its
connected tools, with color-coded states showing tool status.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from textual.app import ComposeResult
from textual.widgets import Static

from openclaw_dash.widgets.ascii_art import (
    SEPARATORS,
    STATUS_SYMBOLS,
    separator,
    status_indicator,
)


class ToolState(Enum):
    """Possible states for a tool in the harness."""

    ACTIVE = "active"
    PROCESSING = "processing"
    FAILED = "failed"
    IDLE = "idle"
    DISABLED = "disabled"


# Color mapping for tool states
STATE_COLORS = {
    ToolState.ACTIVE: "green",
    ToolState.PROCESSING: "cyan",
    ToolState.FAILED: "red",
    ToolState.IDLE: "dim",
    ToolState.DISABLED: "dim italic",
}

# Symbol mapping for tool states
STATE_SYMBOLS = {
    ToolState.ACTIVE: STATUS_SYMBOLS["circle_full"],
    ToolState.PROCESSING: STATUS_SYMBOLS["lightning"],
    ToolState.FAILED: STATUS_SYMBOLS["cross"],
    ToolState.IDLE: STATUS_SYMBOLS["circle_empty"],
    ToolState.DISABLED: STATUS_SYMBOLS["square_empty"],
}


@dataclass
class Tool:
    """Represents a tool connected to the agent runtime."""

    name: str
    state: ToolState = ToolState.IDLE
    last_call_ms: float | None = None
    call_count: int = 0
    error_count: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def success_rate(self) -> float:
        """Calculate success rate as a percentage."""
        if self.call_count == 0:
            return 100.0
        return ((self.call_count - self.error_count) / self.call_count) * 100


@dataclass
class ToolHarnessData:
    """Data for the tool harness visualization."""

    agent_name: str = "Agent Runtime"
    tools: list[Tool] = field(default_factory=list)
    total_calls: int = 0
    uptime_seconds: float = 0.0

    @classmethod
    def from_mock(cls) -> ToolHarnessData:
        """Create mock data for demonstration."""
        return cls(
            agent_name="Agent Runtime",
            tools=[
                Tool(
                    name="exec",
                    state=ToolState.ACTIVE,
                    last_call_ms=45.2,
                    call_count=127,
                    error_count=3,
                ),
                Tool(
                    name="read",
                    state=ToolState.IDLE,
                    last_call_ms=12.8,
                    call_count=89,
                    error_count=0,
                ),
                Tool(
                    name="write",
                    state=ToolState.PROCESSING,
                    last_call_ms=156.3,
                    call_count=34,
                    error_count=1,
                ),
                Tool(
                    name="browser",
                    state=ToolState.FAILED,
                    last_call_ms=2340.5,
                    call_count=12,
                    error_count=5,
                ),
                Tool(
                    name="web_search",
                    state=ToolState.IDLE,
                    last_call_ms=890.2,
                    call_count=23,
                    error_count=0,
                ),
                Tool(
                    name="message",
                    state=ToolState.ACTIVE,
                    last_call_ms=78.1,
                    call_count=156,
                    error_count=2,
                ),
            ],
            total_calls=441,
            uptime_seconds=3600.0,
        )


def render_tool_state(tool: Tool, position: str = "right") -> str:
    """Render a tool with its state indicator.

    Args:
        tool: The tool to render.
        position: "left" or "right" for connector direction.

    Returns:
        Formatted tool string with state coloring.
    """
    color = STATE_COLORS[tool.state]
    symbol = STATE_SYMBOLS[tool.state]

    # Connector lines
    h_line = SEPARATORS["dashed"]

    if position == "left":
        connector = f"{h_line}{h_line}{h_line}┤"
        return f"[{color}]{symbol} {tool.name:<12}[/]{connector}"
    else:
        connector = f"├{h_line}{h_line}{h_line}"
        return f"{connector}[{color}]{tool.name:<12} {symbol}[/]"


def render_harness_ascii(data: ToolHarnessData, width: int = 60) -> list[str]:
    """Render the tool harness as ASCII art.

    Creates a visualization with the agent runtime at center,
    connected to tools via dashed lines.

    Args:
        data: Tool harness data to visualize.
        width: Width of the output.

    Returns:
        List of lines forming the ASCII art visualization.
    """
    lines = []
    h_dash = SEPARATORS["dashed"]

    # Header
    lines.append(f"[bold]{STATUS_SYMBOLS['diamond']} Tool Harness[/]")
    lines.append(separator(width, style="dashed"))
    lines.append("")

    # Split tools into left and right columns
    tools = data.tools
    mid = (len(tools) + 1) // 2
    left_tools = tools[:mid]
    right_tools = tools[mid:]

    # Calculate column widths
    left_col_width = 22
    center_width = 16
    right_col_width = 22

    # Render the box around agent runtime
    center_box_top = f"┌{'─' * (center_width - 2)}┐"
    center_box_mid = f"│{data.agent_name:^{center_width - 2}}│"
    center_box_bot = f"└{'─' * (center_width - 2)}┘"

    # Pad left column
    max_rows = max(len(left_tools), len(right_tools), 3)  # At least 3 for the box

    # Pre-render left and right tool lines
    left_lines = []
    for tool in left_tools:
        symbol = STATE_SYMBOLS[tool.state]
        color = STATE_COLORS[tool.state]
        left_lines.append(f"[{color}]{symbol} {tool.name:<10}[/] {h_dash}{h_dash}┤")

    right_lines = []
    for tool in right_tools:
        symbol = STATE_SYMBOLS[tool.state]
        color = STATE_COLORS[tool.state]
        right_lines.append(f"├{h_dash}{h_dash} [{color}]{tool.name:<10} {symbol}[/]")

    # Pad to max_rows
    while len(left_lines) < max_rows:
        left_lines.append(" " * left_col_width)
    while len(right_lines) < max_rows:
        right_lines.append(" " * right_col_width)

    # Determine which row gets the center box
    box_start_row = (max_rows - 3) // 2
    if box_start_row < 0:
        box_start_row = 0

    # Build the visualization
    for i in range(max_rows):
        left_part = left_lines[i] if i < len(left_lines) else " " * left_col_width
        right_part = right_lines[i] if i < len(right_lines) else " " * right_col_width

        # Add center box rows
        if i == box_start_row:
            center_part = center_box_top
        elif i == box_start_row + 1:
            center_part = center_box_mid
        elif i == box_start_row + 2:
            center_part = center_box_bot
        else:
            # Just vertical line connectors when outside box
            center_part = " " * center_width

        # Pad each part to consistent width
        left_padded = f"{left_part:<{left_col_width}}"
        center_padded = f"{center_part:^{center_width}}"
        right_padded = f"{right_part:<{right_col_width}}"

        lines.append(f"{left_padded}{center_padded}{right_padded}")

    lines.append("")
    lines.append(separator(width, style="dashed"))

    return lines


def render_tool_stats(data: ToolHarnessData, width: int = 60) -> list[str]:
    """Render tool statistics summary.

    Args:
        data: Tool harness data.
        width: Width of the output.

    Returns:
        List of lines with statistics.
    """
    lines = []

    # Legend
    lines.append("[bold]Legend:[/]")
    legend_items = [
        f"  [{STATE_COLORS[ToolState.ACTIVE]}]{STATE_SYMBOLS[ToolState.ACTIVE]} Active[/]",
        f"  [{STATE_COLORS[ToolState.PROCESSING]}]{STATE_SYMBOLS[ToolState.PROCESSING]} Processing[/]",
        f"  [{STATE_COLORS[ToolState.FAILED]}]{STATE_SYMBOLS[ToolState.FAILED]} Failed[/]",
        f"  [{STATE_COLORS[ToolState.IDLE]}]{STATE_SYMBOLS[ToolState.IDLE]} Idle[/]",
    ]
    lines.append("  ".join(legend_items))
    lines.append("")

    # Stats summary
    active_count = sum(1 for t in data.tools if t.state == ToolState.ACTIVE)
    failed_count = sum(1 for t in data.tools if t.state == ToolState.FAILED)
    processing_count = sum(1 for t in data.tools if t.state == ToolState.PROCESSING)

    lines.append(f"[bold]Summary:[/] {len(data.tools)} tools connected")
    lines.append(
        f"  {status_indicator('running', f'{active_count} active')}  "
        f"{status_indicator('warning', f'{processing_count} processing')}  "
        f"{status_indicator('error', f'{failed_count} failed')}"
    )
    lines.append(f"  Total calls: {data.total_calls:,}")

    # Per-tool details for non-idle tools
    active_tools = [t for t in data.tools if t.state != ToolState.IDLE]
    if active_tools:
        lines.append("")
        lines.append(separator(width, style="thin", label="Active Tools"))
        for tool in active_tools:
            color = STATE_COLORS[tool.state]
            symbol = STATE_SYMBOLS[tool.state]
            latency_str = f"{tool.last_call_ms:.0f}ms" if tool.last_call_ms else "—"
            success = tool.success_rate
            success_color = "green" if success >= 95 else "yellow" if success >= 80 else "red"

            lines.append(
                f"  [{color}]{symbol}[/] [bold]{tool.name}[/]: "
                f"{tool.call_count} calls, [{success_color}]{success:.0f}%[/] ok, "
                f"last: {latency_str}"
            )

    return lines


def render_harness_compact(data: ToolHarnessData) -> str:
    """Render a compact single-line harness summary.

    Args:
        data: Tool harness data.

    Returns:
        Single line summary string.
    """
    active = sum(1 for t in data.tools if t.state == ToolState.ACTIVE)
    processing = sum(1 for t in data.tools if t.state == ToolState.PROCESSING)
    failed = sum(1 for t in data.tools if t.state == ToolState.FAILED)

    parts = [f"[bold]Tools:[/] {len(data.tools)}"]

    if active:
        parts.append(f"[green]{active} active[/]")
    if processing:
        parts.append(f"[cyan]{processing} processing[/]")
    if failed:
        parts.append(f"[red]{failed} failed[/]")

    parts.append(f"{data.total_calls:,} calls")

    return " │ ".join(parts)


class ToolHarnessPanel(Static):
    """Tool harness visualization panel."""

    DEFAULT_CSS = """
    ToolHarnessPanel {
        border: dashed $primary;
        padding: 1;
    }
    """

    def __init__(
        self,
        data: ToolHarnessData | None = None,
        show_stats: bool = True,
        compact: bool = False,
        **kwargs: Any,
    ) -> None:
        """Initialize the tool harness panel.

        Args:
            data: Tool harness data (uses mock if None).
            show_stats: Whether to show detailed stats.
            compact: Use compact single-line mode.
            **kwargs: Additional arguments for Static.
        """
        super().__init__(**kwargs)
        self._data = data or ToolHarnessData.from_mock()
        self._show_stats = show_stats
        self._compact = compact

    def compose(self) -> ComposeResult:
        yield Static("Loading...", id="harness-content")

    def on_mount(self) -> None:
        """Initial render on mount."""
        self.refresh_data()

    def refresh_data(self, data: ToolHarnessData | None = None) -> None:
        """Refresh the panel with new data.

        Args:
            data: New data to display (keeps current if None).
        """
        if data is not None:
            self._data = data

        try:
            content = self.query_one("#harness-content", Static)
        except Exception:
            # Not yet mounted
            return

        if self._compact:
            content.update(render_harness_compact(self._data))
        else:
            lines = render_harness_ascii(self._data)
            if self._show_stats:
                lines.extend(render_tool_stats(self._data))
            content.update("\n".join(lines))

    def update_tool_state(self, tool_name: str, state: ToolState) -> None:
        """Update the state of a specific tool.

        Args:
            tool_name: Name of the tool to update.
            state: New state for the tool.
        """
        for tool in self._data.tools:
            if tool.name == tool_name:
                tool.state = state
                self.refresh_data()
                return

    @property
    def data(self) -> ToolHarnessData:
        """Get the current harness data."""
        return self._data


class CompactToolHarnessPanel(Static):
    """Compact single-line tool harness summary."""

    def __init__(self, data: ToolHarnessData | None = None, **kwargs: Any) -> None:
        """Initialize compact panel.

        Args:
            data: Tool harness data (uses mock if None).
            **kwargs: Additional arguments for Static.
        """
        super().__init__(**kwargs)
        self._data = data or ToolHarnessData.from_mock()

    def compose(self) -> ComposeResult:
        yield Static("Loading...", id="harness-compact")

    def on_mount(self) -> None:
        """Initial render on mount."""
        self.refresh_data()

    def refresh_data(self, data: ToolHarnessData | None = None) -> None:
        """Refresh the panel with new data."""
        if data is not None:
            self._data = data

        content = self.query_one("#harness-compact", Static)
        content.update(render_harness_compact(self._data))
