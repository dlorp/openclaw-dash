"""Tamagotchi-style sprite widget for displaying agent state.

A small animated character (lorp) that shows the agent's current state at a glance.
Retro, low-poly feel inspired by Game Boy era. Constraints as creativity.
"""

from __future__ import annotations

from enum import Enum

from textual.app import ComposeResult
from textual.reactive import reactive
from textual.widgets import Static


class SpriteState(Enum):
    """Agent states with associated display properties."""

    IDLE = "idle"
    THINKING = "thinking"
    WORKING = "working"
    SPAWNING = "spawning"
    DONE = "done"
    ALERT = "alert"


# =============================================================================
# ASCII Art Frames - Game Boy Era Style
# =============================================================================
# Each state has 2 frames for simple animation. Keep it small (5 lines max).
# Width: 7 chars for the sprite itself (fits in status bar corner)

SPRITE_FRAMES: dict[SpriteState, list[str]] = {
    SpriteState.IDLE: [
        # Frame 1: sleeping, eyes closed
        r"""
  .-.
 (- -)
 /| |\
  d b
 z z z
""".strip(),
        # Frame 2: sleeping, deeper z's
        r"""
  .-.
 (- -)
 /| |\
  d b
z z z
""".strip(),
    ],
    SpriteState.THINKING: [
        # Frame 1: thinking, looking up-left
        r"""
  .-.  ?
 (o.o)
 /| |\
  d b

""".strip(),
        # Frame 2: thinking, looking up-right
        r"""
  .-. ?
 (o.o)
 /| |\
  d b

""".strip(),
    ],
    SpriteState.WORKING: [
        # Frame 1: working, arms moving
        r"""
  .-.
 (o_o)
 \|~|/
  d b
 *   *
""".strip(),
        # Frame 2: working, arms other way
        r"""
  .-.
 (o_o)
 /|~|\
  d b
*   *
""".strip(),
    ],
    SpriteState.SPAWNING: [
        # Frame 1: spawning, magic happening
        r"""
  .-.  o
 (^_^) o
 /| |\ o
  d b
 ~~~
""".strip(),
        # Frame 2: spawning, sub-agent emerging
        r"""
  .-.   .
 (^_^)  :
 /| |\ ':'
  d b
~~~
""".strip(),
    ],
    SpriteState.DONE: [
        # Frame 1: done, celebrating
        r"""
  .-.
 (^o^)
 \| |/
  d b
  v
""".strip(),
        # Frame 2: done, arms up
        r"""
  .-.
 (^o^)
 \|v|/
  d b
 \v/
""".strip(),
    ],
    SpriteState.ALERT: [
        # Frame 1: alert, eyes wide
        r"""
  .-.  !
 (O_O)
 /| |\
  d b
 !!!
""".strip(),
        # Frame 2: alert, urgent
        r"""
  .-.  !
 (O O)
 /| |\
  d b
! ! !
""".strip(),
    ],
}

# State icons (emoji-style, for compact mode)
STATE_ICONS: dict[SpriteState, str] = {
    SpriteState.IDLE: "😴",
    SpriteState.THINKING: "🤔",
    SpriteState.WORKING: "⚡",
    SpriteState.SPAWNING: "👥",
    SpriteState.DONE: "✅",
    SpriteState.ALERT: "⚠️",
}

# State colors for Textual rich markup
STATE_COLORS: dict[SpriteState, str] = {
    SpriteState.IDLE: "dim",
    SpriteState.THINKING: "yellow",
    SpriteState.WORKING: "cyan",
    SpriteState.SPAWNING: "magenta",
    SpriteState.DONE: "green",
    SpriteState.ALERT: "red",
}

# Default status messages for each state
DEFAULT_STATUS_TEXT: dict[SpriteState, str] = {
    SpriteState.IDLE: "zzz...",
    SpriteState.THINKING: "hmm...",
    SpriteState.WORKING: "working...",
    SpriteState.SPAWNING: "spawning...",
    SpriteState.DONE: "done!",
    SpriteState.ALERT: "attention!",
}


def get_sprite_frame(state: SpriteState, frame: int = 0) -> str:
    """Get a specific animation frame for a state.

    Args:
        state: The sprite state
        frame: Frame index (0 or 1)

    Returns:
        ASCII art string for the frame
    """
    frames = SPRITE_FRAMES.get(state, SPRITE_FRAMES[SpriteState.IDLE])
    return frames[frame % len(frames)]


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
    """Tamagotchi-style animated sprite showing agent state.

    A small widget that displays an ASCII art character representing
    the current agent state. Supports animation between frames.

    Attributes:
        state: Current sprite state (reactive)
        status_text: Status message displayed below sprite (reactive)
        frame: Current animation frame (reactive)
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
    frame: reactive[int] = reactive(0)

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

    def watch_frame(self, new_frame: int) -> None:
        """React to frame changes (animation)."""
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
            sprite_art = get_sprite_frame(self.state, self.frame)
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

    def advance_frame(self) -> None:
        """Advance to the next animation frame."""
        self.frame = (self.frame + 1) % 2

    def animate(self) -> None:
        """Alias for advance_frame - triggers animation."""
        self.advance_frame()


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
