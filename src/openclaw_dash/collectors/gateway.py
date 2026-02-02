"""Gateway status collector."""

from datetime import datetime
from typing import Any

from openclaw_dash.collectors.openclaw_cli import get_openclaw_status, status_to_gateway_data
from openclaw_dash.demo import is_demo_mode, mock_gateway_status


def collect() -> dict[str, Any]:
    """Collect gateway status."""
    # Return mock data in demo mode
    if is_demo_mode():
        return mock_gateway_status()

    # Try real CLI data first
    status = get_openclaw_status()
    if status is not None:
        return status_to_gateway_data(status)

    # Fallback - try HTTP health check
    try:
        import httpx

        resp = httpx.get("http://localhost:18789/health", timeout=5)
        if resp.status_code == 200:
            return {
                "healthy": True,
                "mode": "unknown",
                "url": "http://localhost:18789",
                "collected_at": datetime.now().isoformat(),
            }
    except Exception:
        pass

    return {
        "healthy": False,
        "error": "Cannot connect to gateway",
        "collected_at": datetime.now().isoformat(),
    }
