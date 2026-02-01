"""ASCII art styling utilities for terminal dashboards."""

from __future__ import annotations

# Box drawing characters
SINGLE_BOX = {
    "tl": "┌",
    "tr": "┐",
    "bl": "└",
    "br": "┘",
    "h": "─",
    "v": "│",
}

DOUBLE_BOX = {
    "tl": "╔",
    "tr": "╗",
    "bl": "╚",
    "br": "╝",
    "h": "═",
    "v": "║",
}

# Sparkline blocks (eighth blocks, bottom to top)
SPARK_BLOCKS = " ▁▂▃▄▅▆▇█"

# Progress bar blocks
PROGRESS_BLOCKS = " ░▒▓█"

# Status indicators
STATUS = {
    "ok": "●",
    "warn": "◐",
    "error": "○",
    "unknown": "◌",
    "up": "▲",
    "down": "▼",
    "right": "▶",
    "left": "◀",
}


def draw_box(
    content: list[str],
    *,
    double: bool = False,
    title: str | None = None,
    min_width: int = 0,
) -> list[str]:
    """Draw a box around content lines.

    Args:
        content: Lines of text to wrap in a box.
        double: Use double-line borders if True.
        title: Optional title for top border.
        min_width: Minimum box width (excluding borders).

    Returns:
        List of strings forming the box.
    """
    chars = DOUBLE_BOX if double else SINGLE_BOX
    width = max(len(line) for line in content) if content else 0
    width = max(width, min_width)
    if title:
        width = max(width, len(title) + 2)

    # Top border
    if title:
        padding = width - len(title) - 2
        top = f"{chars['tl']}{chars['h']} {title} {chars['h'] * padding}{chars['tr']}"
    else:
        top = f"{chars['tl']}{chars['h'] * (width + 2)}{chars['tr']}"

    # Content lines
    lines = [top]
    for line in content:
        padded = line.ljust(width)
        lines.append(f"{chars['v']} {padded} {chars['v']}")

    # Bottom border
    lines.append(f"{chars['bl']}{chars['h'] * (width + 2)}{chars['br']}")

    return lines


def sparkline(values: list[float], width: int | None = None) -> str:
    """Generate a sparkline from values.

    Args:
        values: Numeric values to visualize.
        width: Optional width (resamples if needed).

    Returns:
        String of block characters representing the data.
    """
    if not values:
        return ""

    # Resample if width specified and different
    if width and len(values) != width:
        resampled = []
        step = len(values) / width
        for i in range(width):
            idx = int(i * step)
            resampled.append(values[min(idx, len(values) - 1)])
        values = resampled

    min_val = min(values)
    max_val = max(values)
    val_range = max_val - min_val if max_val != min_val else 1

    result = []
    for v in values:
        normalized = (v - min_val) / val_range
        idx = int(normalized * (len(SPARK_BLOCKS) - 1))
        result.append(SPARK_BLOCKS[idx])

    return "".join(result)


def progress_bar(
    value: float,
    width: int = 20,
    *,
    show_percent: bool = True,
    filled: str = "█",
    empty: str = "░",
) -> str:
    """Generate a progress bar.

    Args:
        value: Progress value between 0 and 1.
        width: Bar width in characters.
        show_percent: Append percentage if True.
        filled: Character for filled portion.
        empty: Character for empty portion.

    Returns:
        Progress bar string.
    """
    value = max(0.0, min(1.0, value))
    filled_count = int(value * width)
    bar = filled * filled_count + empty * (width - filled_count)

    if show_percent:
        return f"{bar} {value * 100:5.1f}%"
    return bar


def status_icon(status: str) -> str:
    """Get a status indicator symbol.

    Args:
        status: Status key (ok, warn, error, unknown, up, down, right, left).

    Returns:
        Unicode symbol for the status.
    """
    return STATUS.get(status.lower(), STATUS["unknown"])
