"""ASCII art utilities for TUI dashboard styling.

Provides box drawing, sparklines, progress bars, and status indicators
using Unicode box-drawing characters and symbols.
"""

from __future__ import annotations

from typing import Literal

# =============================================================================
# dlorp Brand Colors (for reference in widgets)
# =============================================================================
# Use these constants for consistent color styling across widgets.
# For Textual themes, see themes.py - these are for Rich markup in widgets.

BRAND_COLORS = {
    "granite_gray": "#636764",      # Borders, muted elements
    "dark_orange": "#FB8B24",       # Warnings, important actions
    "titanium_yellow": "#F4E409",   # Highlights, focus states
    "medium_turquoise": "#50D8D7",  # Success, online status
    "royal_blue": "#3B60E4",        # Primary, links
}


# Box drawing characters
SINGLE = {
    "tl": "┌",
    "tr": "┐",
    "bl": "└",
    "br": "┘",
    "h": "─",
    "v": "│",
    "lj": "├",
    "rj": "┤",
    "tj": "┬",
    "bj": "┴",
    "x": "┼",
}

DOUBLE = {
    "tl": "╔",
    "tr": "╗",
    "bl": "╚",
    "br": "╝",
    "h": "═",
    "v": "║",
    "lj": "╠",
    "rj": "╣",
    "tj": "╦",
    "bj": "╩",
    "x": "╬",
}

ROUNDED = {
    "tl": "╭",
    "tr": "╮",
    "bl": "╰",
    "br": "╯",
    "h": "─",
    "v": "│",
    "lj": "├",
    "rj": "┤",
    "tj": "┬",
    "bj": "┴",
    "x": "┼",
}

# Sparkline characters (8 levels)
SPARK_CHARS = "▁▂▃▄▅▆▇█"

# Progress bar characters
PROGRESS_FULL = "█"
PROGRESS_EMPTY = "░"
PROGRESS_PARTIAL = "▓▒░"  # For smooth gradients

# Block characters for bar charts
BLOCKS_H = " ▏▎▍▌▋▊▉█"  # Horizontal eighth blocks
BLOCKS_V = " ▁▂▃▄▅▆▇█"  # Vertical eighth blocks

# Status indicator symbols
STATUS_SYMBOLS = {
    "ok": "✓",
    "error": "✗",
    "warning": "⚠",
    "info": "ℹ",
    "pending": "◌",
    "running": "●",
    "stopped": "○",
    "arrow_right": "→",
    "arrow_left": "←",
    "arrow_up": "↑",
    "arrow_down": "↓",
    "bullet": "•",
    "diamond": "◆",
    "star": "★",
    "star_empty": "☆",
    "heart": "♥",
    "lightning": "⚡",
    "fire": "🔥",
    "snowflake": "❄",
    "check": "✔",
    "cross": "✘",
    "circle_full": "●",
    "circle_empty": "○",
    "square_full": "■",
    "square_empty": "□",
    "triangle_right": "▶",
    "triangle_left": "◀",
    "triangle_up": "▲",
    "triangle_down": "▼",
}

# Separators
SEPARATORS = {
    "thin": "─",
    "thick": "━",
    "double": "═",
    "dotted": "┄",
    "dashed": "┈",
}

BorderStyle = Literal["single", "double", "rounded"]


def get_border_chars(style: BorderStyle = "single") -> dict[str, str]:
    """Get border characters for the specified style."""
    return {"single": SINGLE, "double": DOUBLE, "rounded": ROUNDED}[style]


def draw_box(
    content: str | list[str],
    width: int | None = None,
    style: BorderStyle = "single",
    title: str | None = None,
    padding: int = 1,
) -> str:
    """Draw a box around content.

    Args:
        content: String or list of lines to wrap in a box
        width: Fixed width (auto-calculated if None)
        style: Border style (single, double, rounded)
        title: Optional title for top border
        padding: Horizontal padding inside box

    Returns:
        Multi-line string with box-drawn content
    """
    chars = get_border_chars(style)

    if isinstance(content, str):
        lines = content.split("\n")
    else:
        lines = list(content)

    # Calculate width
    if width is None:
        max_line = max((len(line) for line in lines), default=0)
        # Total width = borders (2) + padding on each side (padding * 2) + content
        width = max_line + (padding * 2) + 2

    inner_width = width - 2  # Account for side borders

    # Build box
    result = []

    # Top border with optional title
    if title:
        title_part = f" {title} "
        remaining = inner_width - len(title_part)
        left_pad = remaining // 2
        right_pad = remaining - left_pad
        top = (
            chars["tl"] + chars["h"] * left_pad + title_part + chars["h"] * right_pad + chars["tr"]
        )
    else:
        top = chars["tl"] + chars["h"] * inner_width + chars["tr"]
    result.append(top)

    # Content lines
    content_width = inner_width - (padding * 2)
    for line in lines:
        padded = line.ljust(content_width)[:content_width]
        result.append(f"{chars['v']}{' ' * padding}{padded}{' ' * padding}{chars['v']}")

    # Bottom border
    bottom = chars["bl"] + chars["h"] * inner_width + chars["br"]
    result.append(bottom)

    return "\n".join(result)


def sparkline(
    values: list[float | int],
    width: int | None = None,
    min_val: float | None = None,
    max_val: float | None = None,
) -> str:
    """Generate a sparkline from values.

    Args:
        values: List of numeric values
        width: Max width (uses len(values) if None)
        min_val: Minimum value for scaling (auto if None)
        max_val: Maximum value for scaling (auto if None)

    Returns:
        String of sparkline characters
    """
    if not values:
        return ""

    # Limit to width
    if width and len(values) > width:
        values = values[-width:]

    # Calculate range
    if min_val is None:
        min_val = min(values)
    if max_val is None:
        max_val = max(values)

    # Avoid division by zero
    val_range = max_val - min_val
    if val_range == 0:
        return SPARK_CHARS[4] * len(values)  # Middle level

    # Map values to sparkline characters
    result = []
    for v in values:
        normalized = (v - min_val) / val_range
        index = int(normalized * (len(SPARK_CHARS) - 1))
        index = max(0, min(len(SPARK_CHARS) - 1, index))
        result.append(SPARK_CHARS[index])

    return "".join(result)


def progress_bar(
    value: float,
    width: int = 20,
    show_percent: bool = True,
    style: Literal["block", "smooth", "ascii"] = "block",
) -> str:
    """Generate a progress bar.

    Args:
        value: Progress value between 0.0 and 1.0
        width: Width of the bar (excluding percentage)
        show_percent: Whether to append percentage
        style: Visual style (block, smooth, ascii)

    Returns:
        Progress bar string
    """
    value = max(0.0, min(1.0, value))

    if style == "ascii":
        filled = int(value * width)
        bar = "=" * filled + "-" * (width - filled)
        bar = f"[{bar}]"
    elif style == "smooth":
        filled_full = int(value * width)
        remainder = (value * width) - filled_full
        partial_idx = int(remainder * len(BLOCKS_H))

        bar = PROGRESS_FULL * filled_full
        if partial_idx > 0 and filled_full < width:
            bar += BLOCKS_H[partial_idx]
            filled_full += 1
        bar += PROGRESS_EMPTY * (width - filled_full)
    else:  # block
        filled = int(value * width)
        bar = PROGRESS_FULL * filled + PROGRESS_EMPTY * (width - filled)

    if show_percent:
        bar += f" {value * 100:5.1f}%"

    return bar


def status_indicator(
    status: str,
    label: str | None = None,
    color: bool = True,
) -> str:
    """Generate a status indicator with optional label.

    Args:
        status: Status key (ok, error, warning, running, stopped, etc.)
        label: Optional text label
        color: Whether to include Textual color markup

    Returns:
        Status indicator string
    """
    symbol = STATUS_SYMBOLS.get(status, STATUS_SYMBOLS["bullet"])

    # Color mapping for Textual rich markup
    colors = {
        "ok": "green",
        "error": "red",
        "warning": "yellow",
        "info": "blue",
        "running": "green",
        "stopped": "dim",
        "pending": "yellow",
    }

    if color and status in colors:
        result = f"[{colors[status]}]{symbol}[/]"
    else:
        result = symbol

    if label:
        result += f" {label}"

    return result


def separator(
    width: int = 40,
    style: Literal["thin", "thick", "double", "dotted", "dashed"] = "thin",
    label: str | None = None,
) -> str:
    """Generate a horizontal separator line.

    Args:
        width: Width of separator
        style: Line style
        label: Optional centered label

    Returns:
        Separator string
    """
    char = SEPARATORS[style]

    if label:
        label_part = f" {label} "
        remaining = width - len(label_part)
        left = remaining // 2
        right = remaining - left
        return char * left + label_part + char * right

    return char * width


def mini_bar(
    value: float,
    width: int = 8,
) -> str:
    """Generate a minimal inline bar using eighth blocks.

    Args:
        value: Value between 0.0 and 1.0
        width: Width in characters

    Returns:
        Horizontal bar string
    """
    value = max(0.0, min(1.0, value))
    total_eighths = int(value * width * 8)

    full_blocks = total_eighths // 8
    partial_eighths = total_eighths % 8

    result = PROGRESS_FULL * full_blocks
    if partial_eighths > 0 and full_blocks < width:
        result += BLOCKS_H[partial_eighths]
        full_blocks += 1

    # Pad with spaces to maintain width
    result += " " * (width - len(result))

    return result


def trend_indicator(
    current: float,
    previous: float,
    threshold: float = 0.05,
) -> str:
    """Generate a trend indicator arrow.

    Args:
        current: Current value
        previous: Previous value
        threshold: Percentage change threshold for showing trend

    Returns:
        Colored trend indicator
    """
    if previous == 0:
        return STATUS_SYMBOLS["bullet"]

    change = (current - previous) / abs(previous)

    if change > threshold:
        return f"[green]{STATUS_SYMBOLS['arrow_up']}[/]"
    elif change < -threshold:
        return f"[red]{STATUS_SYMBOLS['arrow_down']}[/]"
    else:
        return f"[dim]{STATUS_SYMBOLS['bullet']}[/]"


def format_with_trend(
    label: str,
    value: str,
    trend_values: list[float | int] | None = None,
    sparkline_width: int = 10,
) -> str:
    """Format a metric with optional sparkline trend.

    Args:
        label: Metric label
        value: Formatted value string
        trend_values: Optional list of historical values for sparkline
        sparkline_width: Width of sparkline

    Returns:
        Formatted string with optional sparkline
    """
    base = f"[bold]{label}:[/] {value}"

    if trend_values and len(trend_values) > 1:
        spark = sparkline(trend_values, width=sparkline_width)
        trend = trend_indicator(trend_values[-1], trend_values[-2])
        base += f" {spark} {trend}"

    return base
