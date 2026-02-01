"""Help panel showing keyboard shortcuts."""

from __future__ import annotations

from typing import TYPE_CHECKING

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Center, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Static

if TYPE_CHECKING:
    from textual.app import App

# Static shortcuts that aren't in app bindings (navigation hints, etc.)
STATIC_SHORTCUTS: list[tuple[str, list[tuple[str, str]]]] = [
    (
        "Navigation",
        [
            ("↑/↓", "Scroll focused panel"),
            ("Tab", "Move focus to next panel"),
            ("Shift+Tab", "Move focus to previous panel"),
        ],
    ),
]

# Human-readable key name mappings
KEY_DISPLAY_MAP: dict[str, str] = {
    "question_mark": "?",
    "escape": "Esc",
    "ctrl+p": "Ctrl+P",
    "ctrl+c": "Ctrl+C",
    "ctrl+q": "Ctrl+Q",
    "up": "↑",
    "down": "↓",
    "left": "←",
    "right": "→",
    "space": "Space",
    "enter": "Enter",
    "tab": "Tab",
}


def _format_key(key: str) -> str:
    """Format a key binding for display."""
    key_lower = key.lower()
    if key_lower in KEY_DISPLAY_MAP:
        return KEY_DISPLAY_MAP[key_lower]
    # Handle modifier combinations
    if "+" in key:
        parts = key.split("+")
        formatted = [KEY_DISPLAY_MAP.get(p.lower(), p.capitalize()) for p in parts]
        return "+".join(formatted)
    return key.upper() if len(key) == 1 else key.capitalize()


def _categorize_binding(action: str) -> str:
    """Categorize a binding by its action name."""
    action_lower = action.lower()

    # Panel focus actions
    if "focus" in action_lower or action_lower in (
        "gateway",
        "security",
        "metrics",
        "alerts",
        "cron",
        "repos",
    ):
        return "Panel Focus"

    # Theme/display actions
    if "theme" in action_lower or "cycle" in action_lower:
        return "Display"

    # Help actions
    if "help" in action_lower:
        return "Help"

    # Default to general
    return "General"


def extract_bindings_from_app(app: App) -> list[tuple[str, list[tuple[str, str]]]]:
    """Extract and categorize bindings from the app.

    Args:
        app: The Textual app instance to extract bindings from.

    Returns:
        List of (category_name, [(key, description), ...]) tuples.
    """
    categories: dict[str, list[tuple[str, str]]] = {}
    seen_actions: set[str] = set()  # Avoid duplicate entries

    # Get bindings from the app
    for binding in app.BINDINGS:
        if isinstance(binding, tuple):
            # Handle tuple format: (key, action, description) or (key, action)
            if len(binding) >= 3:
                key, action, description = binding[0], binding[1], binding[2]
            elif len(binding) == 2:
                key, action = binding[0], binding[1]
                description = action.replace("_", " ").title()
            else:
                continue
        elif isinstance(binding, Binding):
            key = binding.key
            action = binding.action
            description = binding.description or action.replace("_", " ").title()
        else:
            continue

        # Skip if we've already seen this action (avoid duplicates like h/?)
        if action in seen_actions:
            continue
        seen_actions.add(action)

        # Format the key for display
        display_key = _format_key(key)

        # Find other keys bound to same action
        other_keys = []
        for other_binding in app.BINDINGS:
            if isinstance(other_binding, tuple) and len(other_binding) >= 2:
                other_key, other_action = other_binding[0], other_binding[1]
            elif isinstance(other_binding, Binding):
                other_key, other_action = other_binding.key, other_binding.action
            else:
                continue

            if other_action == action and other_key != key:
                other_keys.append(_format_key(other_key))

        # Combine keys if multiple bound to same action
        if other_keys:
            display_key = f"{display_key} / {' / '.join(other_keys)}"

        # Categorize and add
        category = _categorize_binding(action)
        if category not in categories:
            categories[category] = []
        categories[category].append((display_key, description))

    # Convert to sorted list of tuples
    # Order: General first, then alphabetical, with Help last
    category_order = {"General": 0, "Display": 1, "Panel Focus": 2, "Help": 99}
    result = [
        (name, shortcuts)
        for name, shortcuts in sorted(
            categories.items(), key=lambda x: (category_order.get(x[0], 50), x[0])
        )
    ]

    return result


class HelpScreen(ModalScreen[None]):
    """Modal screen showing keyboard shortcuts."""

    BINDINGS = [
        Binding("escape", "dismiss", "Close", priority=True),
        Binding("h", "dismiss", "Close"),
        Binding("question_mark", "dismiss", "Close"),
    ]

    CSS = """
    HelpScreen {
        align: center middle;
    }

    #help-container {
        width: 56;
        height: auto;
        max-height: 85%;
        background: $surface;
        border: thick $primary;
        padding: 1 2;
    }

    #help-scroll {
        height: auto;
        max-height: 100%;
    }

    #help-title {
        text-align: center;
        text-style: bold;
        color: $primary;
        padding-bottom: 1;
    }

    .section-title {
        text-style: bold;
        color: $secondary;
        padding-top: 1;
    }

    .shortcut-row {
        padding-left: 2;
    }

    .key {
        color: $warning;
        text-style: bold;
    }

    #help-footer {
        text-align: center;
        color: $text-muted;
        padding-top: 1;
    }
    """

    def __init__(self, shortcuts: list[tuple[str, list[tuple[str, str]]]] | None = None) -> None:
        """Initialize help screen.

        Args:
            shortcuts: Optional list of shortcut categories. If None, will try to
                      extract from app bindings on compose.
        """
        super().__init__()
        self._shortcuts = shortcuts

    def compose(self) -> ComposeResult:
        # Try to get shortcuts from app if not provided
        shortcuts = self._shortcuts
        if shortcuts is None and self.app is not None:
            shortcuts = extract_bindings_from_app(self.app)

        # Fall back to empty if still None
        if shortcuts is None:
            shortcuts = []

        # Add static shortcuts (navigation hints)
        all_shortcuts = shortcuts + STATIC_SHORTCUTS

        with Center():
            with Vertical(id="help-container"):
                yield Static("⌨️  Keyboard Shortcuts", id="help-title")

                with VerticalScroll(id="help-scroll"):
                    for section_name, section_shortcuts in all_shortcuts:
                        yield Static(f"[bold]{section_name}[/]", classes="section-title")
                        for key, desc in section_shortcuts:
                            yield Static(
                                f"  [bold yellow]{key:14}[/] {desc}", classes="shortcut-row"
                            )

                yield Static(
                    "Press [bold]?[/], [bold]H[/], or [bold]Esc[/] to close", id="help-footer"
                )


# Legacy: Keep SHORTCUTS constant for backwards compatibility with tests
SHORTCUTS: list[tuple[str, list[tuple[str, str]]]] = [
    (
        "General",
        [
            ("Ctrl+P", "Open command palette"),
            ("Q", "Quit application"),
            ("R", "Refresh all panels"),
            ("T", "Cycle theme"),
            ("H / ?", "Toggle this help panel"),
        ],
    ),
    (
        "Panel Focus",
        [
            ("G", "Focus Gateway panel"),
            ("S", "Focus Security panel"),
            ("M", "Focus Metrics panel"),
            ("A", "Focus Alerts panel"),
            ("C", "Focus Cron panel"),
            ("P", "Focus Repositories panel"),
        ],
    ),
    (
        "Navigation",
        [
            ("↑/↓", "Scroll focused panel"),
            ("Tab", "Move focus to next panel"),
            ("Shift+Tab", "Move focus to previous panel"),
        ],
    ),
]
