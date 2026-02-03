#!/usr/bin/env python3
"""
repo-scanner.py — Scan repos for health metrics.

Tracks:
- TODO/FIXME counts by file
- Test counts
- Open PRs
- Last commit activity

Usage:
    python3 repo-scanner.py [--json] [--save] [--repo-base PATH]

Configuration:
    Set GITHUB_ORG environment variable (required for PR checks).
    Set REPOS list to match your setup.
"""

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# Configuration - customize for your setup
REPOS = ["synapse-engine", "r3LAY", "t3rra1n"]  # Your repos
DEFAULT_REPO_BASE = Path.home() / "repos"  # Default local path to cloned repos
GIT_TIMEOUT = 30  # Timeout in seconds for git operations


def run(cmd: list[str], cwd: Path | None = None, timeout: int = GIT_TIMEOUT) -> tuple[int, str]:
    """Run a command and return (returncode, output)."""
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd, timeout=timeout)
        return result.returncode, result.stdout.strip()
    except subprocess.TimeoutExpired:
        return -1, f"Command timed out after {timeout}s"


def count_todos(repo_path: Path) -> dict:
    """Count TODOs and FIXMEs in a repo."""
    todos = {"TODO": 0, "FIXME": 0, "HACK": 0, "XXX": 0}
    files_with_todos = []

    for ext in ["py", "ts", "tsx", "js", "jsx"]:
        # Use grep without shell - pipe filtering done in Python
        try:
            grep_result = subprocess.run(
                [
                    "grep",
                    "-rn",
                    r"TODO\|FIXME\|HACK\|XXX",
                    f"--include=*.{ext}",
                    ".",
                ],
                capture_output=True,
                text=True,
                cwd=repo_path,
                timeout=GIT_TIMEOUT,
            )
        except subprocess.TimeoutExpired:
            continue
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
    try:
        find_result = subprocess.run(
            [
                "find",
                ".",
                "-name",
                "test_*.py",
                "-o",
                "-name",
                "*.test.ts",
                "-o",
                "-name",
                "*.test.tsx",
            ],
            capture_output=True,
            text=True,
            cwd=repo_path,
            timeout=GIT_TIMEOUT,
        )
    except subprocess.TimeoutExpired:
        return 0
    output = find_result.stdout.strip()
    if not output:
        return 0
    # Filter out node_modules and count
    count = sum(1 for line in output.split("\n") if line.strip() and "node_modules" not in line)
    return count


def get_open_prs(repo: str, github_org: str) -> list:
    """Get open PRs for a repo."""
    if not github_org:
        return []
    _, output = run(
        [
            "gh",
            "pr",
            "list",
            "-R",
            f"{github_org}/{repo}",
            "--state",
            "open",
            "--json",
            "number,title",
            "--limit",
            "10",
        ]
    )
    try:
        return json.loads(output) if output else []
    except json.JSONDecodeError:
        return []


def get_last_commit(repo_path: Path) -> str:
    """Get last commit info."""
    _, output = run(["git", "log", "-1", "--format=%h %s (%cr)"], cwd=repo_path)
    return output or "Unknown"


def scan_repo(repo: str, repo_base: Path, github_org: str) -> dict:
    """Scan a single repo for health metrics."""
    repo_path = repo_base / repo

    if not repo_path.exists():
        return {"name": repo, "error": f"Repo not found: {repo_path}"}

    # Pull latest
    run(["git", "fetch", "--quiet"], cwd=repo_path)

    return {
        "name": repo,
        "path": str(repo_path),
        "todos": count_todos(repo_path),
        "test_files": count_tests(repo_path),
        "open_prs": get_open_prs(repo, github_org),
        "last_commit": get_last_commit(repo_path),
        "scanned_at": datetime.now().isoformat(),
    }


def format_todo_counts(todos: dict) -> str:
    """Format TODO counts as '5 TODOs (3 TODO, 2 FIXME)'."""
    total = todos["total"]
    counts = todos["counts"]

    # Build breakdown of non-zero counts
    parts = []
    for key in ["TODO", "FIXME", "HACK", "XXX"]:
        if counts.get(key, 0) > 0:
            parts.append(f"{counts[key]} {key}")

    if parts:
        return f"{total} TODOs ({', '.join(parts)})"
    return f"{total} TODOs"


def format_report(results: list[dict]) -> str:
    """Format results as a readable report."""
    lines = ["## Repo Status", ""]
    lines.append(f"**Scanned:** {datetime.now().strftime('%Y-%m-%d %H:%M AKST')}")
    lines.append("")

    total_todos = 0
    total_prs = 0

    for r in results:
        if "error" in r:
            lines.append(f"### ❌ {r.get('name', 'Unknown')}")
            lines.append(f"Error: {r['error']}")
            lines.append("")
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
        lines.append(f"- **TODOs:** {format_todo_counts(todos)}")
        lines.append(f"- **Test files:** {r['test_files']}")
        lines.append(f"- **Open PRs:** {len(prs)}")
        if prs:
            for pr in prs[:3]:
                lines.append(f"  - #{pr['number']}: {pr['title'][:50]}")
        lines.append(f"- **Last commit:** {r['last_commit']}")
        lines.append("")

    lines.append("---")
    lines.append(f"**Totals:** {total_todos} TODOs, {total_prs} open PRs")

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


def progress(msg: str, current: int, total: int) -> None:
    """Print progress indicator."""
    print(f"[{current}/{total}] {msg}...", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(
        description="Scan repos for health metrics (TODOs, tests, PRs, commits).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                        # Scan repos, print report
  %(prog)s --json                 # Output as JSON
  %(prog)s --repo-base ~/code     # Use custom repo directory
  %(prog)s --save                 # Save snapshot for trending

Environment:
  GITHUB_ORG    GitHub username/org (required for PR checks)
""",
    )
    parser.add_argument(
        "--json", action="store_true", help="Output results as JSON instead of report"
    )
    parser.add_argument("--save", action="store_true", help="Save snapshot for trending")
    parser.add_argument(
        "--repo-base",
        type=Path,
        default=DEFAULT_REPO_BASE,
        metavar="PATH",
        help=f"Base directory for repos (default: {DEFAULT_REPO_BASE})",
    )
    args = parser.parse_args()

    github_org = os.environ.get("GITHUB_ORG", "")
    if not github_org:
        print(
            "Error: GITHUB_ORG environment variable is not set.\n"
            "Set it to your GitHub username/org for PR checks:\n"
            "  export GITHUB_ORG=your-username",
            file=sys.stderr,
        )
        sys.exit(1)

    if not args.repo_base.exists():
        print(f"Error: Repo base directory not found: {args.repo_base}", file=sys.stderr)
        sys.exit(1)

    results = []
    total = len(REPOS)
    for i, repo in enumerate(REPOS, 1):
        progress(f"Scanning {repo}", i, total)
        results.append(scan_repo(repo, args.repo_base, github_org))

    if args.save:
        snapshot = save_snapshot(results, Path(__file__))
        print(f"Saved snapshot: {snapshot}", file=sys.stderr)

    if args.json:
        print(json.dumps(results, indent=2))
    else:
        print(format_report(results))


if __name__ == "__main__":
    main()
