#!/usr/bin/env python3
"""
repo-scanner.py — Scan repos for health metrics.

Tracks:
- TODO/FIXME counts by file
- Test counts
- Open PRs
- Last commit activity

Usage:
    python3 repo-scanner.py [--format FORMAT] [--save] [--repo-base PATH] [--org ORG]

Configuration:
    Config file: ~/.config/openclaw-dash/tools.yaml
    Or set GITHUB_ORG environment variable (required for PR checks).
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

# Use shared config module for common settings
from config import get_config as get_shared_config
from config import get_config_path, get_repo_base

GIT_TIMEOUT = 30


def load_config() -> dict[str, Any]:
    # Get shared config with tool-specific overrides
    shared = get_shared_config("repo-scanner")

    return {
        "repos": shared.get("repos", []),
        "repo_base": str(get_repo_base()),
        "github_org": shared.get("github_org", ""),
        "output_style": shared.get("output_format", "text"),
    }


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
    files_with_todos: list[str] = []

    for ext in ["py", "ts", "tsx", "js", "jsx"]:
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
    count = sum(1 for line in output.split("\n") if line.strip() and "node_modules" not in line)
    return count


def get_open_prs(repo: str, github_org: str) -> list:
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
    _, output = run(["git", "log", "-1", "--format=%h %s (%cr)"], cwd=repo_path)
    return output or "Unknown"


def scan_repo(repo: str, repo_base: Path, github_org: str) -> dict:
    """Scan a single repo for health metrics."""
    repo_path = repo_base / repo

    if not repo_path.exists():
        return {"name": repo, "error": f"Repo not found: {repo_path}"}

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


def format_todo_counts(todos: dict, style: str = "verbose") -> str:
    total = todos["total"]
    counts = todos["counts"]

    if style == "concise":
        return str(total)

    parts = []
    for key in ["TODO", "FIXME", "HACK", "XXX"]:
        if counts.get(key, 0) > 0:
            parts.append(f"{counts[key]} {key}")

    if parts:
        return f"{total} TODOs ({', '.join(parts)})"
    return f"{total} TODOs"


def format_markdown(results: list[dict], style: str = "verbose") -> str:
    lines = ["## Repo Status", ""]
    lines.append(f"**Scanned:** {datetime.now().strftime('%Y-%m-%d %H:%M')}")
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

        if todos["total"] == 0:
            status = "✨"
        elif todos["total"] < 10:
            status = "🟢"
        elif todos["total"] < 50:
            status = "🟡"
        else:
            status = "🔴"

        lines.append(f"### {status} {name}")
        lines.append(f"- **TODOs:** {format_todo_counts(todos, style)}")
        lines.append(f"- **Test files:** {r['test_files']}")
        lines.append(f"- **Open PRs:** {len(prs)}")

        if style == "verbose" and prs:
            for pr in prs[:3]:
                lines.append(f"  - #{pr['number']}: {pr['title'][:50]}")

        lines.append(f"- **Last commit:** {r['last_commit']}")
        lines.append("")

    lines.append("---")
    lines.append(f"**Totals:** {total_todos} TODOs, {total_prs} open PRs")

    return "\n".join(lines)


def format_plain(results: list[dict], style: str = "verbose") -> str:
    lines = ["REPO STATUS", "=" * 40]
    lines.append(f"Scanned: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append("")

    total_todos = 0
    total_prs = 0

    for r in results:
        if "error" in r:
            lines.append(f"[ERROR] {r.get('name', 'Unknown')}: {r['error']}")
            lines.append("")
            continue

        name = r["name"]
        todos = r["todos"]
        prs = r["open_prs"]

        total_todos += todos["total"]
        total_prs += len(prs)

        if todos["total"] == 0:
            status = "OK"
        elif todos["total"] < 10:
            status = "GOOD"
        elif todos["total"] < 50:
            status = "WARN"
        else:
            status = "ALERT"

        lines.append(f"[{status}] {name}")
        lines.append(f"  TODOs: {format_todo_counts(todos, style)}")
        lines.append(f"  Tests: {r['test_files']} files")
        lines.append(f"  PRs:   {len(prs)} open")

        if style == "verbose" and prs:
            for pr in prs[:3]:
                lines.append(f"         #{pr['number']}: {pr['title'][:50]}")

        lines.append(f"  Last:  {r['last_commit']}")
        lines.append("")

    lines.append("-" * 40)
    lines.append(f"TOTALS: {total_todos} TODOs, {total_prs} open PRs")

    return "\n".join(lines)


def format_json(results: list[dict], _style: str = "verbose") -> str:
    return json.dumps(results, indent=2)


def save_snapshot(results: list[dict], path: Path) -> Path:
    """Save results as JSON snapshot for trending."""
    snapshots_dir = path.parent / "snapshots"
    snapshots_dir.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    snapshot_file = snapshots_dir / f"health_{timestamp}.json"

    with open(snapshot_file, "w") as f:
        json.dump(results, f, indent=2)

    snapshots = sorted(snapshots_dir.glob("health_*.json"))
    for old in snapshots[:-30]:
        old.unlink()

    return snapshot_file


def progress(msg: str, current: int, total: int) -> None:
    print(f"[{current}/{total}] {msg}...", file=sys.stderr)


def main():
    config = load_config()

    parser = argparse.ArgumentParser(
        description="Scan repos for health metrics (TODOs, tests, PRs, commits).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
Examples:
  %(prog)s                        # Scan repos, print markdown report
  %(prog)s --format json          # Output as JSON
  %(prog)s --format plain         # Output as plain text
  %(prog)s --repo-base ~/code     # Use custom repo directory
  %(prog)s --org myorg            # Override GitHub org
  %(prog)s --save                 # Save snapshot for trending

Configuration:
  Config file: {get_config_path()}
  Example config (tools.yaml):
    github_org: myorg
    repos:
      - repo1
      - repo2
    repo_base: ~/repos
    output_format: text  # or json

Environment:
  GITHUB_ORG    GitHub username/org (can be set in config or via --org)
""",
    )
    parser.add_argument(
        "--format",
        choices=["markdown", "plain", "json"],
        default="markdown",
        metavar="FORMAT",
        help="Output format: markdown (default), plain, json",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON (deprecated, use --format json)",
    )
    parser.add_argument("--save", action="store_true", help="Save snapshot for trending")
    parser.add_argument(
        "--repo-base",
        type=Path,
        default=None,
        metavar="PATH",
        help=f"Base directory for repos (default: {config['repo_base']})",
    )
    parser.add_argument(
        "--org",
        metavar="ORG",
        help="GitHub org/user (default: GITHUB_ORG env var or config)",
    )
    parser.add_argument(
        "--style",
        choices=["verbose", "concise"],
        default=None,
        metavar="STYLE",
        help="Output style: verbose (default) shows PR details and full TODO breakdown; concise shows only totals",
    )
    args = parser.parse_args()

    # Resolve configuration with CLI overrides
    repo_base = args.repo_base or Path(config["repo_base"]).expanduser()
    github_org = args.org or config["github_org"]
    repos = config["repos"]
    output_style = args.style or config["output_style"]

    # Handle deprecated --json flag
    output_format = args.format
    if args.json:
        print("Warning: --json is deprecated, use --format json", file=sys.stderr)
        output_format = "json"

    if not github_org:
        print(
            "Error: GitHub org not configured.\n"
            f"Set via --org, GITHUB_ORG env var, or config file:\n"
            f"  {get_config_path()}",
            file=sys.stderr,
        )
        sys.exit(1)

    if not repo_base.exists():
        print(f"Error: Repo base directory not found: {repo_base}", file=sys.stderr)
        sys.exit(1)

    results = []
    total = len(repos)
    for i, repo in enumerate(repos, 1):
        progress(f"Scanning {repo}", i, total)
        results.append(scan_repo(repo, repo_base, github_org))

    if args.save:
        snapshot = save_snapshot(results, Path(__file__))
        print(f"Saved snapshot: {snapshot}", file=sys.stderr)

    # Format output
    formatters = {
        "markdown": format_markdown,
        "plain": format_plain,
        "json": format_json,
    }
    print(formatters[output_format](results, output_style))


if __name__ == "__main__":
    main()
