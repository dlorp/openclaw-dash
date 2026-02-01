"""Sessions collector."""

import subprocess
import json
from typing import Any
from datetime import datetime


def collect() -> dict[str, Any]:
    """Collect session information."""
    try:
        result = subprocess.run(
            ["openclaw", "sessions", "list", "--json"],
            capture_output=True,
            text=True,
            timeout=15,
        )
        if result.returncode == 0:
            data = json.loads(result.stdout)
            sessions = []
            for s in data.get("sessions", []):
                sessions.append({
                    "key": s.get("key", s.get("sessionKey", "?")),
                    "kind": s.get("kind", "unknown"),
                    "active": s.get("active", False),
                    "context_pct": s.get("contextUsage", 0) * 100 if s.get("contextUsage") else 0,
                })
            return {
                "sessions": sessions,
                "total": len(sessions),
                "active": sum(1 for s in sessions if s.get("active")),
                "collected_at": datetime.now().isoformat(),
            }
    except (subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError):
        pass

    return {"sessions": [], "total": 0, "active": 0, "collected_at": datetime.now().isoformat()}
