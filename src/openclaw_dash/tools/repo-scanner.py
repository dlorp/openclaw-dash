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
import importlib.util
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

# Use shared config module for common settings
from config import get_config as get_shared_config
from config import get_config_path, get_repo_base

# Tool configuration schema for discovery
CONFIG_SCHEMA = {
    "skip_docstrings": {
        "type": "bool",
        "default": False,
        "help": "Ignore TODOs found in docstrings (documentation notes)",
    },
    "output_format": {
        "type": "choice",
        "options": ["text", "json", "markdown"],
        "default": "text",
        "help": "Output format for scan results",
    },
    "include_test_counts": {
        "type": "bool",
        "default": True,
        "help": "Include test file counts in scan results",
    },
    "git_timeout": {
        "type": "int",
        "default": 30,
        "help": "Timeout in seconds for git operations",
    },
}

GIT_TIMEOUT = 30


# -----------------------------------------------------------------------------
# Smart task marker categorization (dynamically loaded from scanner module)
# -----------------------------------------------------------------------------
def _load_smart_todo_scanner():
    """Dynamically load smart-todo-scanner module (hyphenated filename)."""
    scanner_path = Path(__file__).parent / "smart-todo-scanner.py"
    if not scanner_path.exists():
        return None
    spec = importlib.util.spec_from_file_location("smart_todo_scanner", scanner_path)
    if spec is None or spec.loader is None:
        return None
    module = importlib.util.module_from_spec(spec)
    # Register module in sys.modules before exec (required for dataclasses)
    sys.modules["smart_todo_scanner"] = module
    try:
        spec.loader.exec_module(module)
        return module
    except Exception:
        # Clean up on failure
        sys.modules.pop("smart_todo_scanner", None)
        return None


# Try to load task marker scanner module for advanced categorization
_smart_scanner = _load_smart_todo_scanner()


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


def count_todos(repo_path: Path, *, skip_docstrings: bool = False) -> dict:
    """Count TODOs and FIXMEs in tracked files only (via git ls-files).

    Args:
        repo_path: Path to the repository
        skip_docstrings: If True, use smart categorization to separate
            actionable TODOs from docstring TODOs
    """
    todos = {"TODO": 0, "FIXME": 0, "HACK": 0, "XXX": 0}
    files_with_todos: list[str] = []
    docstring_count = 0
    actionable_count = 0

    # Get list of tracked files from git
    try:
        ls_result = subprocess.run(
            ["git", "ls-files"],
            capture_output=True,
            text=True,
            cwd=repo_path,
            timeout=GIT_TIMEOUT,
        )
    except subprocess.TimeoutExpired:
        return {
            "counts": todos,
            "total": 0,
            "files_affected": 0,
            "actionable": 0,
            "in_docstrings": 0,
        }

    tracked_files = ls_result.stdout.strip().split("\n") if ls_result.stdout.strip() else []

    # Filter to source files we care about
    extensions = {".py", ".ts", ".tsx", ".js", ".jsx"}
    source_files = [f for f in tracked_files if Path(f).suffix in extensions]

    if not source_files:
        return {
            "counts": todos,
            "total": 0,
            "files_affected": 0,
            "actionable": 0,
            "in_docstrings": 0,
        }

    # If smart categorization is available and requested, use it
    if skip_docstrings and _smart_scanner is not None:
        for rel_path in source_files:
            filepath = repo_path / rel_path
            if not filepath.exists():
                continue
            items = _smart_scanner.scan_file(filepath)
            for item in items:
                # Count by keyword based on the task marker match
                text_upper = (item.text or "").upper()
                matched = False
                for kw in ["FIXME", "HACK", "XXX", "TODO"]:
                    if kw in text_upper:
                        todos[kw] += 1
                        matched = True
                        break
                if not matched:
                    todos["TODO"] += 1

                if item.category == "DOCSTRING":
                    docstring_count += 1
                else:
                    actionable_count += 1

                if rel_path not in files_with_todos:
                    files_with_todos.append(rel_path)

        total = sum(todos.values())
        return {
            "counts": todos,
            "total": total,
            "files_affected": len(files_with_todos),
            "actionable": actionable_count,
            "in_docstrings": docstring_count,
        }

    # Fallback: Use grep on just the tracked source files
    try:
        grep_result = subprocess.run(
            ["grep", "-Hn", r"TODO\|FIXME\|HACK\|XXX", "--", *source_files],
            capture_output=True,
            text=True,
            cwd=repo_path,
            timeout=GIT_TIMEOUT,
        )
    except subprocess.TimeoutExpired:
        return {
            "counts": todos,
            "total": 0,
            "files_affected": 0,
            "actionable": 0,
            "in_docstrings": 0,
        }

    output = grep_result.stdout.strip()
    if output:
        for line in output.split("\n"):
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

    total = sum(todos.values())
    return {
        "counts": todos,
        "total": total,
        "files_affected": len(files_with_todos),
        "actionable": total,  # Without smart scan, all are "actionable"
        "in_docstrings": 0,
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


def scan_repo(
    repo: str, repo_base: Path, github_org: str, *, skip_docstrings: bool = False
) -> dict:
    """Scan a single repo for health metrics."""
    repo_path = repo_base / repo

    if not repo_path.exists():
        return {"name": repo, "error": f"Repo not found: {repo_path}"}

    run(["git", "fetch", "--quiet"], cwd=repo_path)

    return {
        "name": repo,
        "path": str(repo_path),
        "todos": count_todos(repo_path, skip_docstrings=skip_docstrings),
        "test_files": count_tests(repo_path),
        "open_prs": get_open_prs(repo, github_org),
        "last_commit": get_last_commit(repo_path),
        "scanned_at": datetime.now().isoformat(),
    }


def format_todo_counts(todos: dict, style: str = "verbose", *, show_breakdown: bool = False) -> str:
    total = todos["total"]
    counts = todos["counts"]
    actionable = todos.get("actionable", total)
    in_docstrings = todos.get("in_docstrings", 0)

    if style == "concise":
        if show_breakdown and in_docstrings > 0:
            return f"{actionable} actionable"
        return str(total)

    # Show actionable breakdown when we have docstring data
    if show_breakdown and in_docstrings > 0:
        return f"{actionable} actionable ({in_docstrings} in docstrings)"

    parts = []
    for key in ["TODO", "FIXME", "HACK", "XXX"]:
        if counts.get(key, 0) > 0:
            parts.append(f"{counts[key]} {key}")

    if parts:
        return f"{total} TODOs ({', '.join(parts)})"
    return f"{total} TODOs"


def format_markdown(
    results: list[dict], style: str = "verbose", *, show_breakdown: bool = False
) -> str:
    lines = ["## Repo Status", ""]
    lines.append(f"**Scanned:** {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append("")

    total_todos = 0
    total_actionable = 0
    total_docstrings = 0
    total_prs = 0

    for r in results:
        if "error" in r:
            lines.append(f"### ✗ {r.get('name', 'Unknown')}")
            lines.append(f"Error: {r['error']}")
            lines.append("")
            continue

        name = r["name"]
        todos = r["todos"]
        prs = r["open_prs"]

        total_todos += todos["total"]
        total_actionable += todos.get("actionable", todos["total"])
        total_docstrings += todos.get("in_docstrings", 0)
        total_prs += len(prs)

        # Status based on open PR count
        pr_count = len(prs)
        if pr_count == 0:
            status = "✓"
        elif pr_count <= 3:
            status = "🟡"
        else:
            status = "🔴"

        lines.append(f"### {status} {name}")
        lines.append(
            f"- **TODOs:** {format_todo_counts(todos, style, show_breakdown=show_breakdown)}"
        )
        lines.append(f"- **Test files:** {r['test_files']}")
        lines.append(f"- **Open PRs:** {len(prs)}")

        if style == "verbose" and prs:
            for pr in prs[:3]:
                lines.append(f"  - #{pr['number']}: {pr['title'][:50]}")

        lines.append(f"- **Last commit:** {r['last_commit']}")
        lines.append("")

    lines.append("---")
    if show_breakdown and total_docstrings > 0:
        lines.append(
            f"**Totals:** {total_actionable} actionable TODOs "
            f"({total_docstrings} in docstrings), {total_prs} open PRs"
        )
    else:
        lines.append(f"**Totals:** {total_todos} TODOs, {total_prs} open PRs")

    return "\n".join(lines)


def format_plain(
    results: list[dict], style: str = "verbose", *, show_breakdown: bool = False
) -> str:
    lines = ["REPO STATUS", "=" * 40]
    lines.append(f"Scanned: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append("")

    total_todos = 0
    total_actionable = 0
    total_docstrings = 0
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
        total_actionable += todos.get("actionable", todos["total"])
        total_docstrings += todos.get("in_docstrings", 0)
        total_prs += len(prs)

        # Status based on open PR count
        pr_count = len(prs)
        if pr_count == 0:
            status = "OK"
        elif pr_count <= 3:
            status = "WARN"
        else:
            status = "ALERT"

        lines.append(f"[{status}] {name}")
        lines.append(f"  TODOs: {format_todo_counts(todos, style, show_breakdown=show_breakdown)}")
        lines.append(f"  Tests: {r['test_files']} files")
        lines.append(f"  PRs:   {len(prs)} open")

        if style == "verbose" and prs:
            for pr in prs[:3]:
                lines.append(f"         #{pr['number']}: {pr['title'][:50]}")

        lines.append(f"  Last:  {r['last_commit']}")
        lines.append("")

    lines.append("-" * 40)
    if show_breakdown and total_docstrings > 0:
        lines.append(
            f"TOTALS: {total_actionable} actionable TODOs "
            f"({total_docstrings} in docstrings), {total_prs} open PRs"
        )
    else:
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
  %(prog)s --all-todos            # Include TODOs in docstrings

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
        help="Output style: verbose (default) shows PR details and full TODO breakdown; "
        "concise shows only totals",
    )

    # Task marker filtering options (mutually exclusive)
    todo_group = parser.add_mutually_exclusive_group()
    todo_group.add_argument(
        "--skip-docstrings",
        action="store_true",
        default=True,
        help="Filter out TODOs in docstrings, show only actionable (default)",
    )
    todo_group.add_argument(
        "--all-todos",
        action="store_true",
        help="Count all TODOs including those in docstrings",
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

    # Determine task marker filtering mode
    skip_docstrings = not args.all_todos  # Default is to skip docstrings

    results = []
    total = len(repos)
    for i, repo in enumerate(repos, 1):
        progress(f"Scanning {repo}", i, total)
        results.append(scan_repo(repo, repo_base, github_org, skip_docstrings=skip_docstrings))

    if args.save:
        snapshot = save_snapshot(results, Path(__file__))
        print(f"Saved snapshot: {snapshot}", file=sys.stderr)

    # Format output
    if output_format == "json":
        print(format_json(results, output_style))
    elif output_format == "plain":
        print(format_plain(results, output_style, show_breakdown=skip_docstrings))
    else:
        print(format_markdown(results, output_style, show_breakdown=skip_docstrings))


if __name__ == "__main__":
    main()
