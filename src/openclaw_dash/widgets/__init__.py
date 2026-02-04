"""Custom widgets."""

from openclaw_dash.widgets.activity import (
    ActivityPanel,
    ActivitySummaryPanel,
    ActivityType,
    get_activity_color,
    get_activity_icon,
    get_activity_type,
)
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
from openclaw_dash.widgets.cron import (
    CronPanel,
    CronSummaryPanel,
)
from openclaw_dash.widgets.help_panel import HelpScreen
from openclaw_dash.widgets.input_pane import CommandSent, InputPane
from openclaw_dash.widgets.logs import LogsPanel, LogsSummaryPanel
from openclaw_dash.widgets.metric_boxes import (
    MetricBox,
    MetricBoxesBar,
)
from openclaw_dash.widgets.model_manager import (
    ModelBackend,
    ModelInfo,
    ModelManagerData,
    ModelManagerPanel,
    ModelManagerSummaryPanel,
    ModelStatus,
    ModelTier,
    TierSummaryPanel,
    get_backend_icon,
    get_tier_color,
    get_tier_icon,
)
from openclaw_dash.widgets.model_manager import (
    get_status_color as get_model_status_color,
)
from openclaw_dash.widgets.model_manager import (
    get_status_icon as get_model_status_icon,
)
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
from openclaw_dash.widgets.sessions import (
    SessionsPanel,
    SessionsSummaryPanel,
    SessionStatus,
)
from openclaw_dash.widgets.sessions import (
    get_status_color as get_session_status_color,
)
from openclaw_dash.widgets.sessions import (
    get_status_icon as get_session_status_icon,
)
from openclaw_dash.widgets.states import (
    StateDisplay,
    WidgetState,
    check_and_render_state,
    format_collector_status_line,
    get_state_indicator,
    render_disconnected,
    render_empty,
    render_error,
    render_loading,
    render_stale,
    render_unavailable,
)
from openclaw_dash.widgets.tabbed_groups import (
    CodeTabGroup,
    RuntimeTabGroup,
    next_tab,
    prev_tab,
    switch_tab,
)
from openclaw_dash.widgets.tool_harness import (
    CompactToolHarnessPanel,
    Tool,
    ToolHarnessData,
    ToolHarnessPanel,
    ToolState,
)

__all__ = [
    # Activity
    "ActivityPanel",
    "ActivitySummaryPanel",
    "ActivityType",
    "get_activity_type",
    "get_activity_icon",
    "get_activity_color",
    # ASCII Art
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
    # Input pane
    "InputPane",
    "CommandSent",
    "LogsPanel",
    "LogsSummaryPanel",
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
    # Tabbed groups
    "RuntimeTabGroup",
    "CodeTabGroup",
    "switch_tab",
    "next_tab",
    "prev_tab",
    # Metric boxes
    "MetricBox",
    "MetricBoxesBar",
    # Tool harness
    "ToolHarnessPanel",
    "CompactToolHarnessPanel",
    "ToolHarnessData",
    "Tool",
    "ToolState",
    # Sessions
    "SessionsPanel",
    "SessionsSummaryPanel",
    "SessionStatus",
    "get_session_status_color",
    "get_session_status_icon",
    # Cron panel
    "CronPanel",
    "CronSummaryPanel",
    # Widget states
    "WidgetState",
    "StateDisplay",
    "render_loading",
    "render_error",
    "render_empty",
    "render_stale",
    "render_disconnected",
    "render_unavailable",
    "check_and_render_state",
    "get_state_indicator",
    "format_collector_status_line",
    # Model manager
    "ModelManagerPanel",
    "ModelManagerSummaryPanel",
    "TierSummaryPanel",
    "ModelInfo",
    "ModelManagerData",
    "ModelStatus",
    "ModelTier",
    "ModelBackend",
    "get_model_status_icon",
    "get_model_status_color",
    "get_tier_icon",
    "get_tier_color",
    "get_backend_icon",
]
