"""Alerts collector for the dashboard.

Collects and prioritizes alerts from multiple sources:
- CI/CD failures from GitHub
- Security vulnerabilities from security module
- High context usage warnings from gateway
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from enum import IntEnum
from pathlib import Path
from typing import Any

from openclaw_dash.demo import is_demo_mode


class Severity(IntEnum):
    """Alert severity levels (lower = more severe)."""

    CRITICAL = 1
    HIGH = 2
    MEDIUM = 3
    LOW = 4
    INFO = 5


@dataclass
class Alert:
    """A single alert."""

    severity: Severity
    title: str
    source: str
    description: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    url: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "severity": self.severity.name.lower(),
            "title": self.title,
            "source": self.source,
            "description": self.description,
            "timestamp": self.timestamp.isoformat(),
            "url": self.url,
            "metadata": self.metadata,
        }


# Default repos - can be overridden in config file at ~/.config/openclaw-dash/config.json
# Format: {"repos": ["owner/repo", ...]}
DEFAULT_REPOS: list[str] = []


def _load_repos_from_config() -> list[str]:
    """Load repos from config file if it exists."""
    config_path = Path.home() / ".config" / "openclaw-dash" / "config.json"
    if config_path.exists():
        try:
            config = json.loads(config_path.read_text())
            return config.get("repos", [])
        except (OSError, json.JSONDecodeError):
            pass
    return DEFAULT_REPOS


# Context usage thresholds
CONTEXT_WARNING_PCT = 75
CONTEXT_CRITICAL_PCT = 90


def collect_ci_failures(repos: list[str] | None = None) -> list[Alert]:
    """Collect recent CI/CD failures from GitHub Actions."""
    alerts: list[Alert] = []
    repos_to_check = repos or _load_repos_from_config()

    for repo in repos_to_check:
        try:
            # Get recent failed workflow runs
            result = subprocess.run(
                [
                    "gh",
                    "run",
                    "list",
                    "--repo",
                    repo,
                    "--status",
                    "failure",
                    "--limit",
                    "5",
                    "--json",
                    "databaseId,name,conclusion,createdAt,headBranch,url",
                ],
                capture_output=True,
                text=True,
                timeout=15,
            )

            if result.returncode != 0:
                continue

            runs = json.loads(result.stdout) if result.stdout.strip() else []

            for run in runs:
                # Only alert on failures from last 24h
                created = datetime.fromisoformat(run["createdAt"].replace("Z", "+00:00"))
                age_hours = (datetime.now(created.tzinfo) - created).total_seconds() / 3600

                if age_hours > 24:
                    continue

                # Determine severity based on branch
                branch = run.get("headBranch", "")
                if branch in ("main", "master"):
                    severity = Severity.CRITICAL
                elif branch.startswith("release"):
                    severity = Severity.HIGH
                else:
                    severity = Severity.MEDIUM

                repo_name = repo.split("/")[-1] if "/" in repo else repo

                alerts.append(
                    Alert(
                        severity=severity,
                        title=f"CI failed: {run.get('name', 'workflow')}",
                        source=f"github/{repo_name}",
                        description=f"Branch: {branch}",
                        timestamp=created.replace(tzinfo=None),
                        url=run.get("url"),
                        metadata={"run_id": run.get("databaseId"), "repo": repo},
                    )
                )

        except (subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError):
            continue

    return alerts


def collect_security_vulnerabilities() -> list[Alert]:
    """Collect security vulnerabilities from the security audit module."""
    alerts: list[Alert] = []

    try:
        from openclaw_dash.security import run_audit

        result = run_audit(deep=False)

        severity_map = {
            "critical": Severity.CRITICAL,
            "high": Severity.HIGH,
            "medium": Severity.MEDIUM,
            "low": Severity.LOW,
            "info": Severity.INFO,
        }

        for finding in result.findings:
            alerts.append(
                Alert(
                    severity=severity_map.get(finding.severity, Severity.MEDIUM),
                    title=finding.title,
                    source=f"security/{finding.category}",
                    description=finding.description,
                    metadata={
                        "path": finding.path,
                        "line": finding.line,
                        "recommendation": finding.recommendation,
                        "auto_fixable": finding.auto_fixable,
                    },
                )
            )

    except ImportError:
        pass
    except Exception:
        pass

    return alerts


def collect_context_warnings() -> list[Alert]:
    """Collect high context usage warnings from gateway."""
    alerts: list[Alert] = []

    try:
        result = subprocess.run(
            ["openclaw", "gateway", "status", "--json"],
            capture_output=True,
            text=True,
            timeout=10,
        )

        if result.returncode == 0:
            data = json.loads(result.stdout)
            context_usage = data.get("contextUsage", 0)
            context_pct = context_usage * 100 if context_usage <= 1 else context_usage

            if context_pct >= CONTEXT_CRITICAL_PCT:
                alerts.append(
                    Alert(
                        severity=Severity.CRITICAL,
                        title=f"Context usage critical: {context_pct:.0f}%",
                        source="gateway/context",
                        description="Session context nearly exhausted. Consider starting fresh.",
                        metadata={"context_pct": context_pct},
                    )
                )
            elif context_pct >= CONTEXT_WARNING_PCT:
                alerts.append(
                    Alert(
                        severity=Severity.HIGH,
                        title=f"Context usage high: {context_pct:.0f}%",
                        source="gateway/context",
                        description="Session context running low.",
                        metadata={"context_pct": context_pct},
                    )
                )

            # Also check for sessions with high context
            sessions = data.get("sessions", [])
            for session in sessions:
                session_ctx = session.get("contextUsage", 0)
                session_pct = session_ctx * 100 if session_ctx <= 1 else session_ctx
                if session_pct >= CONTEXT_WARNING_PCT:
                    session_key = session.get("key", "unknown")[:20]
                    alerts.append(
                        Alert(
                            severity=Severity.MEDIUM,
                            title=f"Session '{session_key}' at {session_pct:.0f}%",
                            source="gateway/session",
                            description="Individual session context running low.",
                            metadata={
                                "session_key": session.get("key"),
                                "context_pct": session_pct,
                            },
                        )
                    )

    except (subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError):
        pass
    except Exception:
        pass

    return alerts


def collect(
    repos: list[str] | None = None,
    include_ci: bool = True,
    include_security: bool = True,
    include_context: bool = True,
) -> dict[str, Any]:
    """Collect all alerts and return prioritized list.

    Args:
        repos: List of GitHub repos to check for CI failures
        include_ci: Whether to check for CI failures
        include_security: Whether to run security audit
        include_context: Whether to check context usage

    Returns:
        Dictionary with alerts list and metadata
    """
    # Return mock data in demo mode
    if is_demo_mode():
        return {
            "alerts": [
                {
                    "severity": "medium",
                    "title": "Context usage high",
                    "source": "gateway",
                    "description": "Main session at 75% context",
                },
                {
                    "severity": "low",
                    "title": "Outdated dependency",
                    "source": "security",
                    "description": "requests 2.28.0 -> 2.31.0",
                },
            ],
            "summary": {"critical": 0, "high": 0, "medium": 1, "low": 1, "info": 0},
            "total": 2,
            "collected_at": datetime.now().isoformat(),
        }

    all_alerts: list[Alert] = []

    if include_ci:
        all_alerts.extend(collect_ci_failures(repos))

    if include_security:
        all_alerts.extend(collect_security_vulnerabilities())

    if include_context:
        all_alerts.extend(collect_context_warnings())

    # Sort by severity (critical first), then by timestamp (newest first)
    all_alerts.sort(key=lambda a: (a.severity, -a.timestamp.timestamp()))

    # Group by severity for summary
    summary = {
        "critical": sum(1 for a in all_alerts if a.severity == Severity.CRITICAL),
        "high": sum(1 for a in all_alerts if a.severity == Severity.HIGH),
        "medium": sum(1 for a in all_alerts if a.severity == Severity.MEDIUM),
        "low": sum(1 for a in all_alerts if a.severity == Severity.LOW),
        "info": sum(1 for a in all_alerts if a.severity == Severity.INFO),
    }

    return {
        "alerts": [a.to_dict() for a in all_alerts],
        "total": len(all_alerts),
        "summary": summary,
        "collected_at": datetime.now().isoformat(),
    }


def get_severity_color(severity: str) -> str:
    """Get color code for a severity level (for TUI rendering)."""
    colors = {
        "critical": "red",
        "high": "red",
        "medium": "yellow",
        "low": "blue",
        "info": "dim",
    }
    return colors.get(severity.lower(), "white")


def get_severity_icon(severity: str) -> str:
    """Get icon for a severity level."""
    icons = {
        "critical": "🔴",
        "high": "🟠",
        "medium": "🟡",
        "low": "🔵",
        "info": "",
    }
    return icons.get(severity.lower(), "•")
