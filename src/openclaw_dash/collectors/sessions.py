"""Sessions collector."""

from datetime import datetime
from typing import Any

from openclaw_dash.collectors.openclaw_cli import get_openclaw_status, status_to_sessions_data
from openclaw_dash.demo import is_demo_mode, mock_sessions


def collect() -> dict[str, Any]:
    """Collect session information."""
    # Return mock data in demo mode
    if is_demo_mode():
        sessions = mock_sessions()
        return {
            "sessions": sessions,
            "total": len(sessions),
            "active": len(sessions),  # All mock sessions are considered active
            "collected_at": datetime.now().isoformat(),
        }

    # Try real CLI data
    status = get_openclaw_status()
    if status is not None:
        return status_to_sessions_data(status)

    # Fallback - empty state
    return {
        "sessions": [],
        "total": 0,
        "active": 0,
        "collected_at": datetime.now().isoformat(),
    }
