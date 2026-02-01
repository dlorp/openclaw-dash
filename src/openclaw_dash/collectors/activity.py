"""Activity and current task collector.

Reads from lorp's activity log and workspace state to determine
what's currently being worked on.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from openclaw_dash.demo import is_demo_mode, mock_activity

WORKSPACE = Path.home() / ".openclaw" / "workspace"
ACTIVITY_LOG = WORKSPACE / "memory" / "activity.json"


def collect() -> dict[str, Any]:
    """Collect current task and recent activity."""
    # Return mock data in demo mode
    if is_demo_mode():
        activity = mock_activity()
        return {
            "current_task": "Building new feature for project-x",
            "recent": [
                {"time": a["time"].isoformat(), "action": a["action"], "type": a["type"]}
                for a in activity
            ],
            "collected_at": datetime.now().isoformat(),
        }

    result = {
        "current_task": None,
        "recent": [],
        "collected_at": datetime.now().isoformat(),
    }

    # Try to read activity log if it exists
    if ACTIVITY_LOG.exists():
        try:
            data = json.loads(ACTIVITY_LOG.read_text())
            result["current_task"] = data.get("current_task")
            result["recent"] = data.get("recent", [])[-10:]
        except (OSError, json.JSONDecodeError):
            pass

    # Fallback: check today's memory file for recent activity
    today = datetime.now().strftime("%Y-%m-%d")
    memory_file = WORKSPACE / "memory" / f"{today}.md"
    if memory_file.exists() and not result["recent"]:
        try:
            content = memory_file.read_text()
            # Extract timestamped entries
            for line in content.split("\n"):
                if "AKST" in line and ("##" in line or "-" in line[:5]):
                    # Extract time and action
                    parts = line.split("AKST", 1)
                    if len(parts) == 2:
                        time_part = parts[0].strip().split()[-1] if parts[0].strip() else "?"
                        action = parts[1].strip().lstrip(")").strip()
                        if action:
                            result["recent"].append(
                                {
                                    "time": time_part,
                                    "action": action[:50],
                                }
                            )
        except OSError:
            pass

    return result


def set_current_task(task: str) -> None:
    """Set the current task (called by lorp during work)."""
    ACTIVITY_LOG.parent.mkdir(parents=True, exist_ok=True)

    data = {"current_task": None, "recent": []}
    if ACTIVITY_LOG.exists():
        try:
            data = json.loads(ACTIVITY_LOG.read_text())
        except (OSError, json.JSONDecodeError):
            pass

    # Add previous task to recent if exists
    if data.get("current_task"):
        data["recent"].append(
            {
                "time": datetime.now().strftime("%H:%M"),
                "action": f"Completed: {data['current_task'][:40]}",
            }
        )
        data["recent"] = data["recent"][-20:]  # Keep last 20

    data["current_task"] = task
    data["updated_at"] = datetime.now().isoformat()

    ACTIVITY_LOG.write_text(json.dumps(data, indent=2))


def log_activity(action: str) -> None:
    """Log an activity event."""
    ACTIVITY_LOG.parent.mkdir(parents=True, exist_ok=True)

    data = {"current_task": None, "recent": []}
    if ACTIVITY_LOG.exists():
        try:
            data = json.loads(ACTIVITY_LOG.read_text())
        except (OSError, json.JSONDecodeError):
            pass

    data["recent"].append(
        {
            "time": datetime.now().strftime("%H:%M"),
            "action": action[:100],
        }
    )
    data["recent"] = data["recent"][-20:]
    data["updated_at"] = datetime.now().isoformat()

    ACTIVITY_LOG.write_text(json.dumps(data, indent=2))
