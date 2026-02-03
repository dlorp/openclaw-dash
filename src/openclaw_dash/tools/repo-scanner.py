#!/usr/bin/env python3
"""
repo-scanner.py — Scan repos for health metrics.

Tracks:
- TODO/FIXME counts by file
- Test counts
- Open PRs
- Last commit activity

Usage:
    python3 repo-scanner.py [--json] [--update-discord]

Configuration:
    Set GITHUB_ORG environment variable or edit GITHUB_ORG below.
    Set REPOS list and REPO_BASE path to match your setup.
"""

import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

# Configuration - customize for your setup
GITHUB_ORG = os.environ.get("GITHUB_ORG", "")  # Set your GitHub username/org
REPOS = ["synapse-engine", "r3LAY", "t3rra1n"]  # Your repos
REPO_BASE = Path.home() / "repos"  # Local path to cloned repos


def run(cmd: list[str], cwd: Optional[Path] = None) -> tuple[int, str]:
    """Run a command and return (returncode, output)."""
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd)
    return result.returncode, result.stdout.strip()


def count_todos(repo_path: Path) -> dict:
    """Count TODOs and FIXMEs in a repo."""
    todos = {"TODO": 0, "FIXME": 0, "HACK": 0, "XXX": 0}
    files_with_todos = []

    for ext in ["py", "ts", "tsx", "js", "jsx"]:
        # Use grep without shell - pipe filtering done in Python
        grep_result = subprocess.run(
            ["grep", "-rn", r"TODO\|FIXME\|HACK\|XXX", f"--include=*.{ext}", "."],
            capture_output=True,
            text=True,
            cwd=repo_path,
        )
        output = grep_result.stdout.strip()
        if output:
            for line in output.split("\n"):
                # Filter out unwanted directories in Python
                if "node_modules" in line or "__pycache__" in line or ".git" in line:
                    continue
                if "TODO" in line:
                    todos["TODO"] += 1
                if "FIXME" in line:
                    todos["FIXME"] += 1
                if "HACK" in line:
                    todos["HACK"] += 1
                if "XXX" in line:
                    todos["XXX"] += 1
                # Extract filename
                if ":" in line:
                    fname = line.split(":")[0]
                    if fname not in files_with_todos:
                        files_with_todos.append(fname)

    return {
        "counts": todos,
        "total": sum(todos.values()),
        "files_affected": len(files_with_todos),
    }


def count_tests(repo_path: Path) -> int:
    """Count test files/functions."""
    # Use find without shell, filter in Python
    find_result = subprocess.run(
        ["find", ".", "-name", "test_*.py", "-o", "-name", "*.test.ts", "-o", "-name", "*.test.tsx"],
        capture_output=True,
        text=True,
        cwd=repo_path,
    )
    output = find_result.stdout.strip()
    if not output:
        return 0
    # Filter out node_modules and count
    count = sum(1 for line in output.split("\n") if line.strip() and "node_modules" not in line)
    return count


def get_open_prs(repo: str) -> list:
    """Get open PRs for a repo."""
    if not GITHUB_ORG:
        return []
    _, output = run([
        "gh", "pr", "list",
        "-R", f"{GITHUB_ORG}/{repo}",
        "--state", "open",
        "--json", "number,title",
        "--limit", "10"
    ])
    try:
        return json.loads(output) if output else []
    except json.JSONDecodeError:
        return []


def get_last_commit(repo_path: Path) -> str:
    """Get last commit info."""
    _, output = run(["git", "log", "-1", "--format=%h %s (%cr)"], cwd=repo_path)
    return output or "Unknown"


def scan_repo(repo: str) -> dict:
    """Scan a single repo for health metrics."""
    repo_path = REPO_BASE / repo

    if not repo_path.exists():
        return {"error": f"Repo not found: {repo_path}"}

    # Pull latest
    run(["git", "fetch", "--quiet"], cwd=repo_path)

    return {
        "name": repo,
        "path": str(repo_path),
        "todos": count_todos(repo_path),
        "test_files": count_tests(repo_path),
        "open_prs": get_open_prs(repo),
        "last_commit": get_last_commit(repo_path),
        "scanned_at": datetime.now().isoformat(),
    }


def format_report(results: list[dict]) -> str:
    """Format results as a readable report."""
    lines = ["## 🔍 Repo Health Scan", ""]
    lines.append(f"**Scanned:** {datetime.now().strftime('%Y-%m-%d %H:%M AKST')}")
    lines.append("")

    total_todos = 0
    total_prs = 0

    for r in results:
        if "error" in r:
            lines.append(f"### ❌ {r.get('name', 'Unknown')}")
            lines.append(f"Error: {r['error']}")
            continue

        name = r["name"]
        todos = r["todos"]
        prs = r["open_prs"]

        total_todos += todos["total"]
        total_prs += len(prs)

        # Status emoji
        if todos["total"] == 0:
            status = "✨"
        elif todos["total"] < 10:
            status = "🟢"
        elif todos["total"] < 50:
            status = "🟡"
        else:
            status = "🔴"

        lines.append(f"### {status} {name}")
        lines.append(f"- **TODOs:** {todos['total']} ({todos['counts']})")
        lines.append(f"- **Test files:** {r['test_files']}")
        lines.append(f"- **Open PRs:** {len(prs)}")
        if prs:
            for pr in prs[:3]:
                lines.append(f"  - #{pr['number']}: {pr['title'][:50]}")
        lines.append(f"- **Last commit:** {r['last_commit']}")
        lines.append("")

    lines.append("---")
    lines.append(f"**Totals:** {total_todos} TODOs | {total_prs} open PRs")

    return "\n".join(lines)


def save_snapshot(results: list[dict], path: Path):
    """Save results as JSON snapshot for trending."""
    snapshots_dir = path.parent / "snapshots"
    snapshots_dir.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    snapshot_file = snapshots_dir / f"health_{timestamp}.json"

    with open(snapshot_file, "w") as f:
        json.dump(results, f, indent=2)

    # Keep only last 30 snapshots
    snapshots = sorted(snapshots_dir.glob("health_*.json"))
    for old in snapshots[:-30]:
        old.unlink()

    return snapshot_file


def main():
    output_json = "--json" in sys.argv
    save_snapshot_flag = "--save" in sys.argv

    results = []
    for repo in REPOS:
        print(f"Scanning {repo}...", file=sys.stderr)
        results.append(scan_repo(repo))

    if save_snapshot_flag:
        snapshot = save_snapshot(results, Path(__file__))
        print(f"Saved snapshot: {snapshot}", file=sys.stderr)

    if output_json:
        print(json.dumps(results, indent=2))
    else:
        print(format_report(results))


if __name__ == "__main__":
    main()
