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
        "uptime": "2d 14h",
        "pid": 12345,
        "version": "0.9.0",
        "context_pct": 45.0,
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
        {"name": "synapse-engine", "status": "healthy", "prs": 2, "todos": 5, "ci": "passing"},
        {"name": "r3LAY", "status": "issues", "prs": 3, "todos": 12, "ci": "failing"},
        {"name": "t3rra1n", "status": "healthy", "prs": 1, "todos": 3, "ci": "passing"},
        {"name": "openclaw-dash", "status": "issues", "prs": 4, "todos": 8, "ci": "passing"},
        {"name": "openclaw-core", "status": "healthy", "prs": 0, "todos": 2, "ci": "passing"},
    ]


def mock_alerts() -> list[dict[str, Any]]:
    """Mock alerts data."""
    now = datetime.now()
    return [
        {
            "id": "ci-fail-1",
            "severity": "warning",
            "message": "CI pipeline failing on r3LAY main branch",
            "timestamp": (now - timedelta(minutes=25)).isoformat(),
            "source": "github",
        },
        {
            "id": "cost-spike-1",
            "severity": "info",
            "message": "Daily cost up 15% from yesterday",
            "timestamp": (now - timedelta(hours=2)).isoformat(),
            "source": "cost-monitor",
        },
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
        "today": {"total": 2.45, "input": 0.85, "output": 1.60},
        "alltime": {"total": 45.20, "input": 16.50, "output": 28.70},
        "trend": {"values": [1.85, 2.10, 2.35, 2.60, 2.45]},
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


def mock_agents() -> list[dict[str, Any]]:
    """Mock sub-agents data."""
    now = datetime.now()
    return [
        {
            "key": "agent:main:subagent:blorp",
            "label": "blorp",
            "status": "active",
            "started_at": (now - timedelta(minutes=15)).isoformat(),
            "running_time": "15m 23s",
            "task_summary": "PR review for feature branch",
            "context_pct": 22.5,
            "tokens_used": 45000,
        },
        {
            "key": "agent:main:subagent:slorp",
            "label": "slorp",
            "status": "active",
            "started_at": (now - timedelta(minutes=8)).isoformat(),
            "running_time": "8m 12s",
            "task_summary": "Code cleanup and tests",
            "context_pct": 12.0,
            "tokens_used": 24000,
        },
        {
            "key": "agent:main:subagent:research-1",
            "label": "research-1",
            "status": "idle",
            "started_at": (now - timedelta(hours=1)).isoformat(),
            "running_time": "1h 2m",
            "task_summary": "Documentation research",
            "context_pct": 45.0,
            "tokens_used": 90000,
        },
    ]
