"""Sub-agents collector for the dashboard.

Collects information about active sub-agents spawned by OpenClaw,
including their status, running time, and task summaries.
"""

from __future__ import annotations

import json
import subprocess
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from openclaw_dash.demo import is_demo_mode, mock_sessions

# Simple cache for sessions to avoid repeated slow CLI calls
_sessions_cache: dict[str, Any] = {"data": [], "error": None, "timestamp": 0}
_CACHE_TTL_SECONDS = 10  # Cache sessions for 10 seconds


class AgentStatus(Enum):
    """Status of a sub-agent."""

    ACTIVE = "active"
    IDLE = "idle"
    COMPLETED = "completed"
    ERROR = "error"


@dataclass
class Agent:
    """Represents a sub-agent."""

    key: str
    label: str
    status: AgentStatus
    started_at: datetime
    task_summary: str = ""
    context_pct: float = 0.0
    tokens_used: int = 0
    last_activity: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def running_time(self) -> str:
        """Get human-readable running time."""
        delta = datetime.now() - self.started_at
        total_seconds = int(delta.total_seconds())

        if total_seconds < 60:
            return f"{total_seconds}s"
        elif total_seconds < 3600:
            minutes = total_seconds // 60
            seconds = total_seconds % 60
            return f"{minutes}m {seconds}s"
        else:
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            return f"{hours}h {minutes}m"

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for display."""
        return {
            "key": self.key,
            "label": self.label,
            "status": self.status.value,
            "started_at": self.started_at.isoformat(),
            "running_time": self.running_time,
            "task_summary": self.task_summary,
            "context_pct": self.context_pct,
            "tokens_used": self.tokens_used,
            "last_activity": self.last_activity.isoformat() if self.last_activity else None,
            "metadata": self.metadata,
        }


def _parse_timestamp(value: Any) -> datetime:
    """Parse timestamp from various formats."""
    if isinstance(value, (int, float)):
        # Unix timestamp in milliseconds
        return datetime.fromtimestamp(value / 1000)
    elif isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return datetime.now()
    return datetime.now()


def _extract_task_summary(session: dict[str, Any]) -> str:
    """Extract task summary from session data."""
    # Try to get task from various possible fields
    task = session.get("task", "")
    if task:
        return task[:80]  # Truncate long tasks

    # Try label-based heuristics
    label = session.get("label", "")
    if label:
        # Common patterns
        if "-" in label:
            return label.replace("-", " ").title()
        return label.title()

    return "Background task"


def _determine_status(session: dict[str, Any]) -> AgentStatus:
    """Determine agent status from session data."""
    if session.get("error"):
        return AgentStatus.ERROR

    if session.get("completed"):
        return AgentStatus.COMPLETED

    # Check activity time
    updated_at = session.get("updatedAt")
    if updated_at:
        last_update = _parse_timestamp(updated_at)
        idle_threshold = 300  # 5 minutes
        if (datetime.now() - last_update).total_seconds() > idle_threshold:
            return AgentStatus.IDLE

    return AgentStatus.ACTIVE


def collect() -> dict[str, Any]:
    """Collect information about active sub-agents.

    Returns:
        Dictionary containing:
        - agents: List of agent dictionaries
        - total: Total number of sub-agents
        - active: Number of active sub-agents
        - collected_at: Timestamp of collection
        - error: Error message if collection failed (optional)
    """
    # Return mock data in demo mode
    if is_demo_mode():
        sessions = mock_sessions()
        fetch_error = None
    else:
        sessions, fetch_error = _fetch_sessions()

    agents: list[Agent] = []

    for session in sessions:
        kind = session.get("kind", "")

        # Only include sub-agents (not main sessions)
        if kind != "subagent":
            continue

        key = session.get("key", session.get("sessionKey", "?"))
        label = session.get("label", session.get("displayName", "unnamed"))

        # Calculate context usage percentage
        total_tokens = session.get("totalTokens", 0)
        context_tokens = session.get("contextTokens", 1)  # Avoid division by zero
        context_pct = (total_tokens / context_tokens * 100) if context_tokens else 0

        # Parse timestamps
        created_at = session.get("createdAt", session.get("updatedAt"))
        started_at = _parse_timestamp(created_at) if created_at else datetime.now()

        updated_at = session.get("updatedAt")
        last_activity = _parse_timestamp(updated_at) if updated_at else None

        agent = Agent(
            key=key,
            label=label,
            status=_determine_status(session),
            started_at=started_at,
            task_summary=_extract_task_summary(session),
            context_pct=context_pct,
            tokens_used=total_tokens,
            last_activity=last_activity,
            metadata={
                "channel": session.get("channel"),
                "model": session.get("model"),
            },
        )
        agents.append(agent)

    # Sort by status (active first) then by start time (newest first)
    status_order = {
        AgentStatus.ACTIVE: 0,
        AgentStatus.IDLE: 1,
        AgentStatus.ERROR: 2,
        AgentStatus.COMPLETED: 3,
    }
    agents.sort(key=lambda a: (status_order[a.status], -a.started_at.timestamp()))

    active_count = sum(1 for a in agents if a.status == AgentStatus.ACTIVE)

    result = {
        "agents": [a.to_dict() for a in agents],
        "total": len(agents),
        "active": active_count,
        "collected_at": datetime.now().isoformat(),
    }

    # Include error information if fetch failed but we have no agents
    if fetch_error and not agents:
        result["error"] = fetch_error
        result["_error_type"] = "fetch_failed"

    return result


def _fetch_sessions() -> tuple[list[dict[str, Any]], str | None]:
    """Fetch sessions from OpenClaw CLI with error tracking and caching.

    Returns:
        Tuple of (sessions_list, error_message_or_none).
    """
    global _sessions_cache

    # Return cached data if still fresh
    now = time.time()
    if now - _sessions_cache["timestamp"] < _CACHE_TTL_SECONDS:
        return _sessions_cache["data"], _sessions_cache["error"]

    try:
        result = subprocess.run(
            ["openclaw", "sessions", "list", "--json"],
            capture_output=True,
            text=True,
            timeout=3,  # Reduced from 15s - fail fast
        )
        if result.returncode == 0:
            try:
                data = json.loads(result.stdout)
                sessions = data.get("sessions", [])
                _sessions_cache = {"data": sessions, "error": None, "timestamp": now}
                return sessions, None
            except json.JSONDecodeError as e:
                err = f"Invalid JSON response: {e}"
                _sessions_cache = {"data": [], "error": err, "timestamp": now}
                return [], err
        else:
            error = result.stderr.strip() if result.stderr else f"Exit code {result.returncode}"
            _sessions_cache = {"data": [], "error": error, "timestamp": now}
            return [], error

    except subprocess.TimeoutExpired:
        err = "Command timed out"
        # Use stale cache if available on timeout
        if _sessions_cache["data"]:
            return _sessions_cache["data"], None
        _sessions_cache = {"data": [], "error": err, "timestamp": now}
        return [], err

    except FileNotFoundError:
        err = "OpenClaw CLI not found"
        _sessions_cache = {"data": [], "error": err, "timestamp": now}
        return [], err

    except OSError as e:
        err = f"OS error: {e}"
        _sessions_cache = {"data": [], "error": err, "timestamp": now}
        return [], err


def get_status_icon(status: str) -> str:
    """Get icon for agent status."""
    icons = {
        "active": "●",
        "idle": "◐",
        "completed": "✓",
        "error": "✗",
    }
    return icons.get(status.lower(), "?")


def get_status_color(status: str) -> str:
    """Get color for agent status."""
    colors = {
        "active": "green",
        "idle": "yellow",
        "completed": "dim",
        "error": "red",
    }
    return colors.get(status.lower(), "white")
