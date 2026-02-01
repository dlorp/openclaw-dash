"""GitHub metrics - contribution streaks, PR cycle times, TODO trends."""

import json
import subprocess
from dataclasses import dataclass
from datetime import datetime, timedelta, date
from pathlib import Path
from typing import Any


DEFAULT_METRICS_DIR = Path.home() / ".openclaw" / "workspace" / "metrics"
REPOS_SNAPSHOT_DIR = Path.home() / ".openclaw" / "workspace" / "repos"


@dataclass
class PRMetrics:
    """Metrics for a pull request."""
    number: int
    title: str
    state: str
    created_at: str
    merged_at: str | None
    cycle_hours: float | None
    repo: str


class GitHubMetrics:
    """Collect GitHub-related metrics."""

    def __init__(self, metrics_dir: Path | None = None, repos: list[str] | None = None):
        self.metrics_dir = metrics_dir or DEFAULT_METRICS_DIR
        self.metrics_dir.mkdir(parents=True, exist_ok=True)
        self.github_file = self.metrics_dir / "github.json"
        self.repos = repos or []

    def _load_history(self) -> dict[str, Any]:
        """Load GitHub metrics history from disk."""
        if self.github_file.exists():
            try:
                return json.loads(self.github_file.read_text())
            except (json.JSONDecodeError, IOError):
                pass
        return {"streaks": {}, "pr_cycles": [], "todo_trends": {}}

    def _save_history(self, data: dict[str, Any]) -> None:
        """Save GitHub metrics history to disk."""
        self.github_file.write_text(json.dumps(data, indent=2, default=str))

    def _run_gh_command(self, args: list[str]) -> dict[str, Any] | list | None:
        """Run a GitHub CLI command and parse JSON output."""
        try:
            result = subprocess.run(
                ["gh"] + args + ["--json"],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode == 0 and result.stdout.strip():
                return json.loads(result.stdout)
        except (subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError):
            pass
        return None

    def get_contribution_streak(self, username: str | None = None) -> dict[str, Any]:
        """Calculate current contribution streak.
        
        Uses `gh api` to fetch contribution data.
        """
        # Get authenticated user if not provided
        if not username:
            user_result = subprocess.run(
                ["gh", "api", "user", "--jq", ".login"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if user_result.returncode == 0:
                username = user_result.stdout.strip()
            else:
                return {"streak_days": 0, "error": "Could not determine username"}
        
        # Fetch recent events to detect activity
        try:
            result = subprocess.run(
                ["gh", "api", f"users/{username}/events", "--jq", ".[].created_at"],
                capture_output=True,
                text=True,
                timeout=15,
            )
            if result.returncode != 0:
                return {"streak_days": 0, "error": "Could not fetch events"}
            
            # Parse dates
            dates_with_activity: set[str] = set()
            for line in result.stdout.strip().split('\n'):
                if line:
                    try:
                        dt = datetime.fromisoformat(line.replace('Z', '+00:00'))
                        dates_with_activity.add(dt.date().isoformat())
                    except ValueError:
                        continue
            
            # Count consecutive days from today
            streak = 0
            check_date = date.today()
            while check_date.isoformat() in dates_with_activity:
                streak += 1
                check_date -= timedelta(days=1)
            
            # Also check yesterday if today hasn't had activity yet
            if streak == 0:
                yesterday = date.today() - timedelta(days=1)
                if yesterday.isoformat() in dates_with_activity:
                    streak = 1
                    check_date = yesterday - timedelta(days=1)
                    while check_date.isoformat() in dates_with_activity:
                        streak += 1
                        check_date -= timedelta(days=1)
            
            return {
                "username": username,
                "streak_days": streak,
                "last_activity": max(dates_with_activity) if dates_with_activity else None,
            }
            
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return {"streak_days": 0, "error": "gh command failed"}

    def get_pr_cycle_times(self, repo: str | None = None, limit: int = 20) -> list[PRMetrics]:
        """Get PR cycle times (opened → merged)."""
        prs: list[PRMetrics] = []
        
        repos_to_check = [repo] if repo else self.repos
        if not repos_to_check:
            # Try to get repos from current directory
            repos_to_check = ["."]
        
        for r in repos_to_check:
            try:
                cmd = ["gh", "pr", "list", "--repo", r, "--state", "merged", 
                       "--limit", str(limit), "--json", "number,title,state,createdAt,mergedAt"]
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                if result.returncode == 0 and result.stdout.strip():
                    data = json.loads(result.stdout)
                    for pr in data:
                        created = datetime.fromisoformat(pr["createdAt"].replace('Z', '+00:00'))
                        merged = datetime.fromisoformat(pr["mergedAt"].replace('Z', '+00:00')) if pr.get("mergedAt") else None
                        
                        cycle_hours = None
                        if merged:
                            cycle_hours = round((merged - created).total_seconds() / 3600, 2)
                        
                        prs.append(PRMetrics(
                            number=pr["number"],
                            title=pr["title"],
                            state=pr["state"],
                            created_at=pr["createdAt"],
                            merged_at=pr.get("mergedAt"),
                            cycle_hours=cycle_hours,
                            repo=r,
                        ))
            except (subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError):
                continue
        
        return prs

    def get_todo_trends(self) -> dict[str, Any]:
        """Get TODO trends from repo-scanner snapshots."""
        trends: dict[str, list[dict[str, Any]]] = {}
        
        if not REPOS_SNAPSHOT_DIR.exists():
            return {"repos": {}, "error": "No snapshot directory found"}
        
        # Look for repo scan results
        for repo_dir in REPOS_SNAPSHOT_DIR.iterdir():
            if not repo_dir.is_dir():
                continue
            
            repo_name = repo_dir.name
            todo_files = list(repo_dir.glob("*todo*.json")) + list(repo_dir.glob("*scan*.json"))
            
            if not todo_files:
                continue
            
            repo_trends = []
            for todo_file in sorted(todo_files, key=lambda p: p.stat().st_mtime)[-30:]:
                try:
                    data = json.loads(todo_file.read_text())
                    # Handle different formats
                    todo_count = 0
                    if isinstance(data, dict):
                        todo_count = data.get("todo_count", data.get("todos", 0))
                        if "items" in data:
                            todo_count = len(data["items"])
                    elif isinstance(data, list):
                        todo_count = len(data)
                    
                    mtime = datetime.fromtimestamp(todo_file.stat().st_mtime)
                    repo_trends.append({
                        "date": mtime.date().isoformat(),
                        "count": todo_count,
                    })
                except (json.JSONDecodeError, IOError):
                    continue
            
            if repo_trends:
                trends[repo_name] = repo_trends
        
        return {"repos": trends}

    def collect(self) -> dict[str, Any]:
        """Collect all GitHub metrics."""
        history = self._load_history()
        
        # Get contribution streak
        streak = self.get_contribution_streak()
        
        # Get PR cycle times
        prs = self.get_pr_cycle_times()
        cycle_times = [pr.cycle_hours for pr in prs if pr.cycle_hours is not None]
        avg_cycle = round(sum(cycle_times) / len(cycle_times), 2) if cycle_times else 0
        
        # Get TODO trends
        todo_trends = self.get_todo_trends()
        
        # Update history
        today = date.today().isoformat()
        history["streaks"][today] = streak
        history["todo_trends"] = todo_trends
        
        self._save_history(history)
        
        return {
            "streak": streak,
            "pr_metrics": {
                "recent_prs": len(prs),
                "avg_cycle_hours": avg_cycle,
                "fastest_merge_hours": min(cycle_times) if cycle_times else None,
                "slowest_merge_hours": max(cycle_times) if cycle_times else None,
            },
            "todo_trends": todo_trends,
            "collected_at": datetime.now().isoformat(),
        }

    def get_streak_history(self, days: int = 30) -> list[dict[str, Any]]:
        """Get streak history over time."""
        history = self._load_history()
        dates = sorted(history.get("streaks", {}).keys(), reverse=True)[:days]
        return [
            {"date": d, **history["streaks"][d]}
            for d in dates
        ]
