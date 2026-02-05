"""Notification/toast utilities for user feedback.

Uses Textual's built-in notify() system with consistent styling.
"""

from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from textual.app import App


class NotificationLevel(Enum):
    """Notification severity levels."""

    INFO = "information"
    WARNING = "warning"
    ERROR = "error"


# Alias for backwards compatibility
SUCCESS = NotificationLevel.INFO


# Default timeouts in seconds (by level name for clarity)
TIMEOUTS = {
    NotificationLevel.INFO: 1.5,
    NotificationLevel.WARNING: 3.0,
    NotificationLevel.ERROR: 5.0,
}

# Icons for notifications
ICONS = {
    NotificationLevel.INFO: "✓",
    NotificationLevel.WARNING: "",
    NotificationLevel.ERROR: "✗",
}


def notify(
    app: "App",
    message: str,
    level: NotificationLevel = NotificationLevel.INFO,
    timeout: float | None = None,
) -> None:
    """Show a notification toast.

    Args:
        app: The Textual app instance
        message: Message to display
        level: Severity level (affects styling and timeout)
        timeout: Custom timeout in seconds (uses level default if None)
    """
    icon = ICONS.get(level, "")
    display_message = f"{icon} {message}" if icon else message
    display_timeout = timeout if timeout is not None else TIMEOUTS.get(level, 2.0)

    app.notify(
        display_message,
        timeout=display_timeout,
        severity=level.value,
    )


def notify_info(app: "App", message: str, timeout: float | None = None) -> None:
    """Show an info notification."""
    notify(app, message, NotificationLevel.INFO, timeout)


def notify_success(app: "App", message: str, timeout: float | None = None) -> None:
    """Show a success notification (uses INFO level with shorter timeout)."""
    notify(app, message, NotificationLevel.INFO, timeout or 1.5)


def notify_warning(app: "App", message: str, timeout: float | None = None) -> None:
    """Show a warning notification."""
    notify(app, message, NotificationLevel.WARNING, timeout)


def notify_error(app: "App", message: str, timeout: float | None = None) -> None:
    """Show an error notification."""
    notify(app, message, NotificationLevel.ERROR, timeout)


def notify_refresh(app: "App", panel_count: int = 0) -> None:
    """Show a refresh notification."""
    if panel_count > 0:
        notify_success(app, f"Refreshed {panel_count} panels", timeout=1.0)
    else:
        notify_success(app, "Refreshed", timeout=1.0)


def notify_theme_change(app: "App", theme_name: str) -> None:
    """Show a theme change notification."""
    notify_info(app, f"Theme: {theme_name}", timeout=1.5)


def notify_panel_error(app: "App", panel_name: str, error: str) -> None:
    """Show a panel refresh error notification."""
    notify_error(app, f"{panel_name}: {error}", timeout=4.0)
