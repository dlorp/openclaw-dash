"""Demo mode with mock data for testing and screenshots."""

from datetime import datetime, timedelta
from typing import Any

# Global demo mode flag
_DEMO_MODE = False


def is_demo_mode() -> bool:
    """Check if demo mode is enabled."""
    return _DEMO_MODE


def enable_demo_mode() -> None:
    """Enable demo mode with mock data."""
    global _DEMO_MODE
    _DEMO_MODE = True


def disable_demo_mode() -> None:
    """Disable demo mode."""
    global _DEMO_MODE
    _DEMO_MODE = False


def mock_gateway_status() -> dict[str, Any]:
    """Mock gateway status data."""
    return {
        "healthy": True,
        "uptime": "2h 15m",
        "pid": 12345,
        "version": "0.9.0",
        "context_pct": 45.2,
        "collected_at": datetime.now().isoformat(),
    }


def mock_sessions() -> list[dict[str, Any]]:
    """Mock active sessions data."""
    return [
        {
            "key": "agent:main:main",
            "kind": "main",
            "displayName": "main",
            "totalTokens": 45000,
            "contextTokens": 200000,
            "updatedAt": datetime.now().timestamp() * 1000,
        },
        {
            "key": "agent:main:subagent:blorp",
            "kind": "subagent",
            "label": "blorp",
            "displayName": "blorp",
            "totalTokens": 12000,
            "contextTokens": 200000,
            "updatedAt": (datetime.now() - timedelta(minutes=5)).timestamp() * 1000,
        },
        {
            "key": "agent:main:subagent:slorp",
            "kind": "subagent",
            "label": "slorp",
            "displayName": "slorp",
            "totalTokens": 8500,
            "contextTokens": 200000,
            "updatedAt": (datetime.now() - timedelta(minutes=10)).timestamp() * 1000,
        },
    ]


def mock_cron_jobs() -> list[dict[str, Any]]:
    """Mock cron jobs data."""
    return [
        {
            "id": "daily-summary",
            "name": "daily-summary",
            "schedule": {"kind": "cron", "expr": "0 4 * * *"},
            "enabled": True,
            "lastRun": (datetime.now() - timedelta(hours=8)).isoformat(),
        },
        {
            "id": "heartbeat",
            "name": "heartbeat",
            "schedule": {"kind": "every", "everyMs": 1800000},
            "enabled": True,
            "lastRun": (datetime.now() - timedelta(minutes=15)).isoformat(),
        },
        {
            "id": "pr-monitor",
            "name": "wlorp-pr-watch",
            "schedule": {"kind": "every", "everyMs": 10000},
            "enabled": True,
            "lastRun": datetime.now().isoformat(),
        },
    ]


def mock_activity() -> list[dict[str, Any]]:
    """Mock recent activity data."""
    now = datetime.now()
    return [
        {"time": now - timedelta(minutes=5), "action": "Pushed feature branch", "type": "git"},
        {"time": now - timedelta(minutes=15), "action": "Reviewed PR #42", "type": "pr"},
        {"time": now - timedelta(minutes=30), "action": "Fixed CI pipeline", "type": "ci"},
        {"time": now - timedelta(hours=1), "action": "Spawned blorp for cleanup", "type": "agent"},
        {"time": now - timedelta(hours=2), "action": "Merged PR #41", "type": "pr"},
    ]


def mock_repos() -> list[dict[str, Any]]:
    """Mock repository data."""
    return [
        {"name": "synapse-engine", "status": "healthy", "prs": 0, "ci": "passing"},
        {"name": "r3LAY", "status": "healthy", "prs": 1, "ci": "passing"},
        {"name": "t3rra1n", "status": "healthy", "prs": 2, "ci": "passing"},
        {"name": "openclaw-dash", "status": "healthy", "prs": 1, "ci": "passing"},
    ]


def mock_alerts() -> list[dict[str, Any]]:
    """Mock alerts data."""
    return [
        # Empty - no alerts in demo mode
    ]


def mock_channels() -> list[dict[str, Any]]:
    """Mock connected channels."""
    return [
        {"name": "discord", "status": "connected", "type": "discord"},
        {"name": "telegram", "status": "connected", "type": "telegram"},
    ]


def mock_cost_data() -> dict[str, Any]:
    """Mock cost tracking data."""
    return {
        "today": {"total": 0.42, "input": 0.15, "output": 0.27},
        "trend": {"values": [0.35, 0.41, 0.38, 0.45, 0.42]},
        "streak": 12,
    }


def mock_metrics() -> dict[str, Any]:
    """Mock metrics data."""
    return {
        "requests_today": 147,
        "errors_today": 3,
        "error_rate": 0.02,
        "avg_latency_ms": 245,
        "cache_hit_rate": 0.78,
    }


def mock_resources() -> dict[str, Any]:
    """Mock system resources."""
    return {
        "cpu_percent": 23.5,
        "memory_percent": 45.2,
        "disk_percent": 68.1,
        "network_sent_mb": 12.4,
        "network_recv_mb": 45.8,
    }
