"""Tamagotchi-style sprite widget for displaying agent state.

A small animated character (lorp) that shows the agent's current state at a glance.
Retro, low-poly feel inspired by Game Boy era. Constraints as creativity.

FINAL lorp sprite design:
- Dimensions: 5 display chars wide × 5 lines tall
- Antenna: ¡ (U+00A1 inverted exclamation)
"""

from __future__ import annotations

from enum import Enum

from textual.app import ComposeResult
from textual.reactive import reactive
from textual.widgets import Static


class SpriteState(Enum):
    """Agent states with associated display properties."""

    IDLE = "idle"
    SLEEP = "sleep"
    THINK = "think"
    WORK = "work"
    SPAWN = "spawn"
    DONE = "done"
    ALERT = "alert"


# =============================================================================
# ASCII Art - FINAL lorp design
# =============================================================================
# 5 display chars wide × 5 lines tall
# Antenna: ¡ (U+00A1 inverted exclamation)

SPRITES: dict[str, list[str]] = {
    "idle": [
        "  ¡  ",
        " .-. ",
        "(o.o)",
        "|   |",
        "`~~~'",
    ],
    "sleep": [
        "  ¡  ",
        " .-. ",
        "(-.-)",
        "|   |",
        "`~~~'",
    ],
    "think": [
        "  ¡  ",
        " .-. ",
        "(o.o)",
        "| ? |",
        "`~~~'",
    ],
    "work": [
        "  ¡  ",
        " .-. ",
        "(o.o)",
        "|~~~|",
        "`~~~'",
    ],
    "spawn": [
        "  ¡ o",
        " .-. ",
        "(o.o)",
        "|~~~|",
        "`~~~'",
    ],
    "done": [
        "  ¡  ",
        " .-. ",
        "(^.^)",
        "|   |",
        "`~~~'",
    ],
    "alert": [
        "  ¡ !",
        " .-. ",
        "(!.!)",
        "|   |",
        "`~~~'",
    ],
}

# State icons (emoji-style, for compact mode)
STATE_ICONS: dict[SpriteState, str] = {
    SpriteState.IDLE: "😊",
    SpriteState.SLEEP: "😴",
    SpriteState.THINK: "🤔",
    SpriteState.WORK: "⚡",
    SpriteState.SPAWN: "👥",
    SpriteState.DONE: "✅",
    SpriteState.ALERT: "⚠️",
}

# State colors for Textual rich markup
STATE_COLORS: dict[SpriteState, str] = {
    SpriteState.IDLE: "white",
    SpriteState.SLEEP: "dim",
    SpriteState.THINK: "yellow",
    SpriteState.WORK: "cyan",
    SpriteState.SPAWN: "magenta",
    SpriteState.DONE: "green",
    SpriteState.ALERT: "red",
}

# Default status messages for each state
DEFAULT_STATUS_TEXT: dict[SpriteState, str] = {
    SpriteState.IDLE: "ready",
    SpriteState.SLEEP: "zzz...",
    SpriteState.THINK: "hmm...",
    SpriteState.WORK: "working...",
    SpriteState.SPAWN: "spawning...",
    SpriteState.DONE: "done!",
    SpriteState.ALERT: "attention!",
}


def get_sprite(state: SpriteState | str) -> list[str]:
    """Get sprite lines for a state.

    Args:
        state: The sprite state (enum or string)

    Returns:
        List of sprite lines (5 lines)
    """
    if isinstance(state, SpriteState):
        key = state.value
    else:
        key = state.lower()
    return SPRITES.get(key, SPRITES["idle"])


def get_sprite_art(state: SpriteState | str) -> str:
    """Get sprite as a single string.

    Args:
        state: The sprite state (enum or string)

    Returns:
        ASCII art string for the sprite
    """
    return "\n".join(get_sprite(state))


def get_state_icon(state: SpriteState) -> str:
    """Get the emoji icon for a state.

    Args:
        state: The sprite state

    Returns:
        Emoji character for the state
    """
    return STATE_ICONS.get(state, "●")


def get_state_color(state: SpriteState) -> str:
    """Get the color for a state.

    Args:
        state: The sprite state

    Returns:
        Color name for Textual markup
    """
    return STATE_COLORS.get(state, "white")


def parse_state(state_str: str | SpriteState | None) -> SpriteState:
    """Parse a string or enum to SpriteState.

    Args:
        state_str: State as string or SpriteState enum

    Returns:
        SpriteState enum value
    """
    if state_str is None:
        return SpriteState.IDLE
    if isinstance(state_str, SpriteState):
        return state_str
    try:
        return SpriteState(state_str.lower())
    except ValueError:
        return SpriteState.IDLE


class SpriteWidget(Static):
    """Tamagotchi-style sprite showing agent state.

    A small widget that displays an ASCII art character representing
    the current agent state.

    Attributes:
        state: Current sprite state (reactive)
        status_text: Status message displayed below sprite (reactive)
    """

    DEFAULT_CSS = """
    SpriteWidget {
        width: auto;
        height: auto;
        padding: 0 1;
    }
    """

    state: reactive[SpriteState] = reactive(SpriteState.IDLE)
    status_text: reactive[str] = reactive("")

    def __init__(
        self,
        state: SpriteState | str = SpriteState.IDLE,
        status_text: str | None = None,
        compact: bool = False,
        **kwargs,
    ) -> None:
        """Initialize the sprite widget.

        Args:
            state: Initial sprite state
            status_text: Optional status text (uses default if None)
            compact: Use compact emoji-only mode
            **kwargs: Additional arguments for Static
        """
        super().__init__(**kwargs)
        self._compact = compact
        self.state = parse_state(state)
        self.status_text = status_text or DEFAULT_STATUS_TEXT.get(self.state, "")

    def compose(self) -> ComposeResult:
        """Compose the widget content."""
        yield Static("", id="sprite-display")

    def on_mount(self) -> None:
        """Handle widget mount - render initial state."""
        self._render()

    def watch_state(self, new_state: SpriteState) -> None:
        """React to state changes."""
        # Update status text to default if not custom
        if not self.status_text or self.status_text in DEFAULT_STATUS_TEXT.values():
            self.status_text = DEFAULT_STATUS_TEXT.get(new_state, "")
        self._render()

    def watch_status_text(self, new_text: str) -> None:
        """React to status text changes."""
        self._render()

    def _render(self) -> None:
        """Render the sprite display."""
        try:
            display = self.query_one("#sprite-display", Static)
        except Exception:
            return

        color = get_state_color(self.state)

        if self._compact:
            # Compact mode: just icon + status
            icon = get_state_icon(self.state)
            display.update(f"[{color}]{icon}[/] {self.status_text}")
        else:
            # Full ASCII art mode
            sprite_art = get_sprite_art(self.state)
            # Add color to the sprite
            colored_sprite = f"[{color}]{sprite_art}[/]"
            # Status text below
            status_line = f"[dim]{self.status_text}[/]" if self.status_text else ""
            display.update(f"{colored_sprite}\n{status_line}")

    def set_state(self, state: SpriteState | str, status_text: str | None = None) -> None:
        """Update the sprite state and optionally the status text.

        Args:
            state: New sprite state
            status_text: Optional custom status text
        """
        self.state = parse_state(state)
        if status_text is not None:
            self.status_text = status_text


class CompactSpriteWidget(SpriteWidget):
    """Compact version of sprite widget using emoji icons.

    Suitable for status bars and tight spaces.
    """

    DEFAULT_CSS = """
    CompactSpriteWidget {
        width: auto;
        height: 1;
        padding: 0;
    }
    """

    def __init__(
        self,
        state: SpriteState | str = SpriteState.IDLE,
        status_text: str | None = None,
        **kwargs,
    ) -> None:
        """Initialize compact sprite widget.

        Args:
            state: Initial sprite state
            status_text: Optional status text
            **kwargs: Additional arguments for Static
        """
        super().__init__(state=state, status_text=status_text, compact=True, **kwargs)


# =============================================================================
# Utility Functions
# =============================================================================


def create_sprite(
    state: SpriteState | str = SpriteState.IDLE,
    status_text: str | None = None,
    compact: bool = False,
) -> SpriteWidget | CompactSpriteWidget:
    """Factory function to create a sprite widget.

    Args:
        state: Initial sprite state
        status_text: Optional status text
        compact: Use compact mode

    Returns:
        SpriteWidget or CompactSpriteWidget instance
    """
    if compact:
        return CompactSpriteWidget(state=state, status_text=status_text)
    return SpriteWidget(state=state, status_text=status_text)


def format_sprite_status(state: SpriteState | str, status_text: str = "") -> str:
    """Format a sprite status line for use in other widgets.

    Args:
        state: Sprite state
        status_text: Status message

    Returns:
        Formatted string with icon, color, and status
    """
    parsed_state = parse_state(state)
    icon = get_state_icon(parsed_state)
    color = get_state_color(parsed_state)
    text = status_text or DEFAULT_STATUS_TEXT.get(parsed_state, "")
    return f"[{color}]{icon}[/] {text}"
