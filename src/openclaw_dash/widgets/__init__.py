"""Custom widgets."""

from openclaw_dash.widgets.ascii_art import (
    DOUBLE,
    ROUNDED,
    SINGLE,
    STATUS_SYMBOLS,
    draw_box,
    format_with_trend,
    mini_bar,
    progress_bar,
    separator,
    sparkline,
    status_indicator,
    trend_indicator,
)
from openclaw_dash.widgets.help_panel import HelpScreen
from openclaw_dash.widgets.notifications import (
    NotificationLevel,
    notify,
    notify_error,
    notify_info,
    notify_panel_error,
    notify_refresh,
    notify_success,
    notify_theme_change,
    notify_warning,
)
from openclaw_dash.widgets.security import (
    DepsPanel,
    DepsSummaryPanel,
    SecurityPanel,
    SecuritySummaryPanel,
)

__all__ = [
    "SINGLE",
    "DOUBLE",
    "ROUNDED",
    "STATUS_SYMBOLS",
    "draw_box",
    "sparkline",
    "progress_bar",
    "status_indicator",
    "separator",
    "mini_bar",
    "trend_indicator",
    "format_with_trend",
    "HelpScreen",
    "SecurityPanel",
    "SecuritySummaryPanel",
    "DepsPanel",
    "DepsSummaryPanel",
    # Notifications
    "NotificationLevel",
    "notify",
    "notify_info",
    "notify_success",
    "notify_warning",
    "notify_error",
    "notify_refresh",
    "notify_theme_change",
    "notify_panel_error",
]
