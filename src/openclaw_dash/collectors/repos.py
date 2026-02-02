"""Repository health collector."""

from __future__ import annotations

import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

from openclaw_dash.demo import is_demo_mode, mock_repos

DEFAULT_REPOS = ["synapse-engine", "r3LAY", "t3rra1n", "openclaw-dash"]
REPO_BASE = Path.home() / "repos"


def collect(repos: list[str] | None = None) -> dict[str, Any]:
    """Collect repository health metrics."""
    # Return mock data in demo mode
    if is_demo_mode():
        mock_data = mock_repos()
        # Filter by requested repos if specified
        if repos is not None:
            mock_data = [r for r in mock_data if r.get("name") in repos]
        return {
            "repos": mock_data,
            "total": len(mock_data),
            "collected_at": datetime.now().isoformat(),
        }

    repos = repos or DEFAULT_REPOS
    results = []

    for repo_name in repos:
        repo_path = REPO_BASE / repo_name
        if not repo_path.exists():
            continue

        repo_data = {"name": repo_name, "path": str(repo_path)}

        # Open PRs
        try:
            result = subprocess.run(
                ["gh", "pr", "list", "--json", "number"],
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=15,
            )
            if result.returncode == 0:
                prs = json.loads(result.stdout)
                repo_data["open_prs"] = len(prs)
        except (subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError):
            repo_data["open_prs"] = 0

        # Last commit
        try:
            result = subprocess.run(
                ["git", "log", "-1", "--format=%ar"],
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                repo_data["last_commit"] = result.stdout.strip()
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

        # Health emoji
        prs = repo_data.get("open_prs", 0)
        if prs == 0:
            repo_data["health"] = "✨"
        elif prs <= 2:
            repo_data["health"] = "🟢"
        elif prs <= 5:
            repo_data["health"] = "🟡"
        else:
            repo_data["health"] = "🔴"

        results.append(repo_data)

    return {"repos": results, "total": len(results), "collected_at": datetime.now().isoformat()}
