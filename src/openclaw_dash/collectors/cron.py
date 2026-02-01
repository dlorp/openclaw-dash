"""Cron jobs collector."""

import json
import subprocess
from datetime import datetime
from typing import Any


def collect() -> dict[str, Any]:
    """Collect cron job information."""
    try:
        result = subprocess.run(
            ["openclaw", "cron", "list", "--json"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            data = json.loads(result.stdout)
            jobs = []
            for j in data.get("jobs", []):
                jobs.append(
                    {
                        "id": j.get("id", j.get("jobId", "?")),
                        "name": j.get("name", j.get("id", "unnamed")),
                        "enabled": j.get("enabled", True),
                        "schedule": j.get("schedule", {}),
                        "last_run": j.get("lastRun"),
                        "next_run": j.get("nextRun"),
                    }
                )
            return {
                "jobs": jobs,
                "total": len(jobs),
                "enabled": sum(1 for j in jobs if j.get("enabled")),
                "collected_at": datetime.now().isoformat(),
            }
    except (subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError):
        pass

    return {"jobs": [], "total": 0, "enabled": 0, "collected_at": datetime.now().isoformat()}
