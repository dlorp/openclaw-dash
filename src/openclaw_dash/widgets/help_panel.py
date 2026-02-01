"""Help panel showing keyboard shortcuts."""

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Center, Vertical
from textual.screen import ModalScreen
from textual.widgets import Static

SHORTCUTS = [
    (
        "General",
        [
            ("Ctrl+P", "Open command palette"),
            ("q", "Quit application"),
            ("r", "Refresh all panels"),
            ("t", "Cycle theme"),
            ("h / ?", "Toggle this help panel"),
        ],
    ),
    (
        "Navigation",
        [
            ("Tab", "Focus next panel"),
            ("Shift+Tab", "Focus previous panel"),
            ("g", "Focus Gateway panel"),
            ("s", "Focus Security panel"),
            ("m", "Focus Metrics panel"),
            ("a", "Focus Alerts panel"),
            ("c", "Focus Cron panel"),
            ("p", "Focus Repositories panel"),
            ("l", "Focus Logs panel"),
        ],
    ),
    (
        "Scrolling",
        [
            ("↑/↓", "Scroll focused panel"),
        ],
    ),
]


class HelpScreen(ModalScreen):
    """Modal screen showing keyboard shortcuts."""

    BINDINGS = [
        Binding("escape", "dismiss", "Close"),
        Binding("h", "dismiss", "Close"),
        Binding("question_mark", "dismiss", "Close"),
    ]

    CSS = """
    HelpScreen {
        align: center middle;
    }

    #help-container {
        width: 50;
        height: auto;
        max-height: 80%;
        background: $surface;
        border: thick $primary;
        padding: 1 2;
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

    def compose(self) -> ComposeResult:
        with Center():
            with Vertical(id="help-container"):
                yield Static("⌨️  Keyboard Shortcuts", id="help-title")

                for section_name, shortcuts in SHORTCUTS:
                    yield Static(f"[bold]{section_name}[/]", classes="section-title")
                    for key, desc in shortcuts:
                        yield Static(f"  [bold yellow]{key:12}[/] {desc}", classes="shortcut-row")

                yield Static("Press [bold]h[/] or [bold]Esc[/] to close", id="help-footer")
