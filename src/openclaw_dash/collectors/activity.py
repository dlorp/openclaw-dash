"""Activity and current task collector.

Reads from the activity log and workspace state to determine
what's currently being worked on.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from openclaw_dash.demo import is_demo_mode, mock_activity

WORKSPACE = Path.home() / ".openclaw" / "workspace"
ACTIVITY_LOG = WORKSPACE / "memory" / "activity.json"

# Default structure for activity data
_DEFAULT_ACTIVITY: dict[str, Any] = {"current_task": None, "recent": []}


def _read_activity_data() -> dict[str, Any]:
    """Read activity data from the log file.

    Returns:
        Activity data dictionary, or defaults if file doesn't exist or is invalid.
    """
    if not ACTIVITY_LOG.exists():
        return dict(_DEFAULT_ACTIVITY)

    try:
        return json.loads(ACTIVITY_LOG.read_text())
    except (OSError, json.JSONDecodeError):
        return dict(_DEFAULT_ACTIVITY)


def _write_activity_data(data: dict[str, Any]) -> None:
    """Write activity data to the log file.

    Creates parent directories if needed. Updates the 'updated_at' timestamp.

    Args:
        data: Activity data to write.
    """
    ACTIVITY_LOG.parent.mkdir(parents=True, exist_ok=True)
    data["updated_at"] = datetime.now().isoformat()
    ACTIVITY_LOG.write_text(json.dumps(data, indent=2))


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

    # Load activity data using shared helper
    data = _read_activity_data()
    result: dict[str, Any] = {
        "current_task": data.get("current_task"),
        "recent": data.get("recent", [])[-10:],
        "collected_at": datetime.now().isoformat(),
    }

    # Fallback: check today's memory file for recent activity
    today = datetime.now().strftime("%Y-%m-%d")
    memory_file = WORKSPACE / "memory" / f"{today}.md"
    recent_list: list[dict[str, Any]] = result.get("recent", [])
    if memory_file.exists() and not recent_list:
        try:
            content = memory_file.read_text()
            # Extract timestamped entries
            for line in content.split("\n"):
                if "AKST" in line and ("##" in line or "-" in line[:5]):
                    # Extract time and action
                    parts = line.split("AKST", 1)
                    if len(parts) == 2:
                        time_part = parts[0].strip().split()[-1] if parts[0].strip() else "?"
                        action_str = parts[1].strip().lstrip(")").strip()
                        if action_str:
                            recent_list.append(
                                {
                                    "time": time_part,
                                    "action": action_str[:50],
                                }
                            )
            result["recent"] = recent_list
        except OSError:
            pass

    return result


def set_current_task(task: str) -> None:
    """Set the current task for display in the dashboard."""
    data = _read_activity_data()

    # Add previous task to recent if exists
    recent_items: list[dict[str, Any]] = data.get("recent", [])
    if data.get("current_task"):
        recent_items.append(
            {
                "time": datetime.now().strftime("%H:%M"),
                "action": f"Completed: {data['current_task'][:40]}",
            }
        )
        data["recent"] = recent_items[-20:]  # Keep last 20

    data["current_task"] = task
    _write_activity_data(data)


def log_activity(action: str) -> None:
    """Log an activity event."""
    data = _read_activity_data()

    recent_items: list[dict[str, Any]] = data.get("recent", [])
    recent_items.append(
        {
            "time": datetime.now().strftime("%H:%M"),
            "action": action[:100],
        }
    )
    data["recent"] = recent_items[-20:]
    _write_activity_data(data)
