"""Repository health collector."""

from __future__ import annotations

import json
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from openclaw_dash.collectors.base import (
    CollectorResult,
    CollectorState,
    update_collector_state,
)
from openclaw_dash.demo import is_demo_mode, mock_repos

COLLECTOR_NAME = "repos"
DEFAULT_REPOS = ["synapse-engine", "r3LAY", "t3rra1n", "openclaw-dash"]
REPO_BASE = Path.home() / "repos"


def _get_open_prs(repo_path: Path) -> tuple[int, str | None]:
    """Get open PR count for a repository.

    Returns:
        Tuple of (pr_count, error_message_or_none).
    """
    try:
        result = subprocess.run(
            ["gh", "pr", "list", "--json", "number"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=15,
        )
        if result.returncode == 0:
            try:
                prs_list = json.loads(result.stdout)
                return len(prs_list), None
            except json.JSONDecodeError:
                return 0, "Invalid JSON from gh"
        else:
            # gh CLI not authenticated or other error
            if "not logged in" in (result.stderr or "").lower():
                return 0, "GitHub CLI not authenticated"
            return 0, None  # Treat as 0 PRs

    except subprocess.TimeoutExpired:
        return 0, "gh command timed out"

    except FileNotFoundError:
        return 0, "GitHub CLI not installed"

    except OSError:
        return 0, None


def _get_last_commit(repo_path: Path) -> tuple[str | None, str | None]:
    """Get last commit time for a repository.

    Returns:
        Tuple of (last_commit_str, error_message_or_none).
    """
    try:
        result = subprocess.run(
            ["git", "log", "-1", "--format=%ar"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip(), None
        else:
            return None, "git log failed"

    except subprocess.TimeoutExpired:
        return None, "git command timed out"

    except FileNotFoundError:
        return None, "git not installed"

    except OSError:
        return None, None


def _health_emoji(prs_count: int) -> str:
    """Get health emoji based on PR count."""
    if prs_count == 0:
        return "✨"
    elif prs_count <= 2:
        return "🟢"
    elif prs_count <= 5:
        return "🟡"
    else:
        return "🔴"


def collect(repos: list[str] | None = None) -> dict[str, Any]:
    """Collect repository health metrics with error tracking.

    Args:
        repos: List of repository names to check. Uses defaults if None.

    Returns:
        Dictionary containing repository health data and any errors encountered.
    """
    start_time = time.time()

    # Return mock data in demo mode
    if is_demo_mode():
        mock_data = mock_repos()
        # Filter by requested repos if specified
        if repos is not None:
            mock_data = [r for r in mock_data if r.get("name") in repos]
        data = {
            "repos": mock_data,
            "total": len(mock_data),
            "collected_at": datetime.now().isoformat(),
        }
        result = CollectorResult(data=data)
        update_collector_state(COLLECTOR_NAME, result)
        return data

    repos = repos or DEFAULT_REPOS
    results = []
    errors: list[dict[str, str]] = []
    missing_repos: list[str] = []

    for repo_name in repos:
        repo_path = REPO_BASE / repo_name

        if not repo_path.exists():
            missing_repos.append(repo_name)
            continue

        repo_data: dict[str, Any] = {
            "name": repo_name,
            "path": str(repo_path),
        }

        # Open PRs
        open_prs, pr_error = _get_open_prs(repo_path)
        repo_data["open_prs"] = open_prs
        if pr_error:
            repo_data["_pr_error"] = pr_error
            errors.append({"repo": repo_name, "error": pr_error, "field": "open_prs"})

        # Last commit
        last_commit, commit_error = _get_last_commit(repo_path)
        if last_commit:
            repo_data["last_commit"] = last_commit
        else:
            repo_data["last_commit"] = "unknown"
            if commit_error:
                repo_data["_commit_error"] = commit_error
                errors.append({"repo": repo_name, "error": commit_error, "field": "last_commit"})

        # Health emoji
        repo_data["health"] = _health_emoji(open_prs)

        results.append(repo_data)

    duration_ms = (time.time() - start_time) * 1000

    data = {
        "repos": results,
        "total": len(results),
        "collected_at": datetime.now().isoformat(),
    }

    # Include error summary if any
    if errors:
        data["_errors"] = errors
        data["_error_count"] = len(errors)

    if missing_repos:
        data["_missing_repos"] = missing_repos

    # Determine overall state
    if not results and missing_repos:
        state = CollectorState.UNAVAILABLE
        error_msg = f"No repositories found at {REPO_BASE}"
    elif errors:
        state = CollectorState.OK  # Partial success
        error_msg = None
    else:
        state = CollectorState.OK
        error_msg = None

    result = CollectorResult(
        data=data,
        state=state,
        error=error_msg,
        duration_ms=duration_ms,
    )
    update_collector_state(COLLECTOR_NAME, result)
    return data
