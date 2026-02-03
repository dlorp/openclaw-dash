"""Data collectors for the dashboard."""

from openclaw_dash.collectors import (
    activity,
    agents,
    alerts,
    billing,
    channels,
    cron,
    gateway,
    logs,
    repos,
    resources,
    sessions,
)
from openclaw_dash.collectors.base import (
    CollectorResult,
    CollectorState,
    collect_with_fallback,
    format_error_for_display,
    get_collector_state,
    get_last_success,
    is_stale,
    parse_json_output,
    run_command,
    safe_get,
    validate_data_shape,
    with_retry,
)
from openclaw_dash.collectors.cache import (
    CollectorCache,
    cached_collector,
    get_cache,
    reset_cache,
)

__all__ = [
    # Collector modules
    "gateway",
    "sessions",
    "cron",
    "repos",
    "activity",
    "channels",
    "alerts",
    "billing",
    "logs",
    "resources",
    "agents",
    # Base utilities
    "CollectorResult",
    "CollectorState",
    "get_collector_state",
    "get_last_success",
    "is_stale",
    "run_command",
    "parse_json_output",
    "safe_get",
    "validate_data_shape",
    "with_retry",
    "collect_with_fallback",
    "format_error_for_display",
    # Cache utilities
    "CollectorCache",
    "cached_collector",
    "get_cache",
    "reset_cache",
]
