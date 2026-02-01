"""Gateway status collector."""

import json
import subprocess
from datetime import datetime
from typing import Any


def collect() -> dict[str, Any]:
    """Collect gateway status."""
    try:
        result = subprocess.run(
            ["openclaw", "gateway", "status", "--json"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            data = json.loads(result.stdout)
            return {
                "healthy": data.get("running", False),
                "uptime": data.get("uptime", "unknown"),
                "pid": data.get("pid"),
                "version": data.get("version"),
                "context_pct": data.get("contextUsage", 0) * 100 if data.get("contextUsage") else 0,
                "collected_at": datetime.now().isoformat(),
            }
    except (subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError):
        pass

    # Fallback
    try:
        import httpx

        resp = httpx.get("http://localhost:3000/health", timeout=5)
        if resp.status_code == 200:
            return {
                "healthy": True,
                "uptime": "unknown",
                "collected_at": datetime.now().isoformat(),
            }
    except Exception:
        pass

    return {"healthy": False, "error": "Cannot connect", "collected_at": datetime.now().isoformat()}
