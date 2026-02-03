#!/usr/bin/env python3
"""
status.py — Combined status report for repos and PRs.

Combines pr-tracker and repo-scanner into a unified view.

Usage:
    python3 status.py              # Quick overview
    python3 status.py --ci         # Include CI status (slower)
    python3 status.py --skip-docstrings   # Smart TODO counting
    python3 status.py --json       # Output as JSON
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from config import get_repo_base, get_repos, require_org

GIT_TIMEOUT = 30


# ============================================================================
# PR Tracking (from pr-tracker.py)
# ============================================================================


def run(cmd: list[str], cwd: Path | None = None, timeout: int = GIT_TIMEOUT) -> tuple[int, str]:
    """Run a command and return (returncode, output)."""
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd, timeout=timeout)
        return result.returncode, result.stdout.strip()
    except subprocess.TimeoutExpired:
        return -1, f"Command timed out after {timeout}s"


def get_prs(org: str, repo: str, state: str = "open", fetch_ci: bool = False) -> list[dict]:
    """Get PRs for a repo."""
    fields = "number,title,state,createdAt,mergedAt,closedAt,author,headRefName"
    if fetch_ci:
        fields += ",statusCheckRollup"

    returncode, output = run(
        [
            "gh",
            "pr",
            "list",
            "-R",
            f"{org}/{repo}",
            "--state",
            state,
            "--json",
            fields,
            "--limit",
            "20",
        ]
    )
    if returncode != 0:
        return []
    try:
        return json.loads(output) if output else []
    except json.JSONDecodeError:
        return []


def extract_ci_status(status_check_rollup: list[dict] | None) -> str:
    """Extract CI status from GitHub's statusCheckRollup."""
    if not status_check_rollup:
        return "unknown"

    if not isinstance(status_check_rollup, list) or len(status_check_rollup) == 0:
        return "unknown"

    statuses = []
    for check in status_check_rollup:
        if not isinstance(check, dict):
            continue
        conclusion = check.get("conclusion")
        if conclusion:
            statuses.append(conclusion.upper())
        elif check.get("status") in ("IN_PROGRESS", "PENDING", "QUEUED", "REQUESTED", "WAITING"):
            statuses.append("PENDING")
        elif check.get("state"):
            statuses.append(check["state"].upper())

    if not statuses:
        return "unknown"

    failure_states = {
        "FAILURE",
        "ERROR",
        "CANCELLED",
        "TIMED_OUT",
        "ACTION_REQUIRED",
        "STARTUP_FAILURE",
    }
    pending_states = {"PENDING", "IN_PROGRESS", "QUEUED", "REQUESTED", "WAITING", "EXPECTED"}
    success_states = {"SUCCESS", "NEUTRAL", "SKIPPED", "STALE"}

    if any(s in failure_states for s in statuses):
        return "failure"
    elif any(s in pending_states for s in statuses):
        return "pending"
    elif all(s in success_states for s in statuses):
        return "success"
    else:
        return "unknown"


def get_ci_icon(ci_status: str) -> str:
    """Get emoji icon for CI status."""
    return {
        "success": "✅",
        "failure": "❌",
        "pending": "⏳",
        "unknown": "❓",
    }.get(ci_status, "❓")


def format_age(created_at: str | None) -> str:
    """Format PR age as human readable."""
    if not created_at or not isinstance(created_at, str):
        return "?"

    try:
        created = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        age = datetime.now(created.tzinfo) - created

        if age.days > 0:
            return f"{age.days}d"
        elif age.seconds >= 3600:
            return f"{age.seconds // 3600}h"
        else:
            return f"{age.seconds // 60}m"
    except (ValueError, AttributeError, TypeError):
        return "?"


# ============================================================================
# Smart TODO Scanning (from smart-todo-scanner.py)
# ============================================================================


@dataclass
class TodoItem:
    file: str
    line: int
    category: str  # DOCSTRING, COMMENT, INLINE
    text: str


def compute_docstring_state(lines: list[str]) -> list[bool]:
    """Precompute docstring state for all lines in O(n) time."""
    n = len(lines)
    in_docstring = [False] * n
    in_single_docstring = False
    in_double_docstring = False

    for i, line in enumerate(lines):
        was_in_docstring = in_single_docstring or in_double_docstring
        j = 0
        while j < len(line):
            if line[j : j + 3] == '"""':
                if not in_single_docstring:
                    in_double_docstring = not in_double_docstring
                j += 3
                continue
            if line[j : j + 3] == "'''":
                if not in_double_docstring:
                    in_single_docstring = not in_single_docstring
                j += 3
                continue
            j += 1
        is_in_now = in_single_docstring or in_double_docstring
        in_docstring[i] = was_in_docstring or is_in_now

    return in_docstring


def is_in_string_literal(line: str, match_start: int) -> bool:
    """Check if a position in a line is inside a string literal."""
    in_single = False
    in_double = False
    i = 0

    while i < match_start:
        char = line[i]
        if char == "\\" and i + 1 < len(line):
            i += 2
            continue
        if char == '"' and not in_single:
            in_double = not in_double
        elif char == "'" and not in_double:
            in_single = not in_single
        i += 1

    return in_single or in_double


def find_todo_in_comment(line: str) -> tuple[str, str] | None:
    """Find TODO/FIXME/HACK in a comment, not in string literals."""
    for match in re.finditer(r"(TODO|FIXME|HACK)[:\s]*(.*)", line, re.IGNORECASE):
        match_start = match.start()

        if is_in_string_literal(line, match_start):
            continue

        comment_start = -1
        for i, char in enumerate(line[:match_start]):
            if char == "#" and not is_in_string_literal(line, i):
                comment_start = i
                break

        if comment_start == -1:
            for i in range(match_start):
                if line[i : i + 2] == "//" and not is_in_string_literal(line, i):
                    comment_start = i
                    break

        if comment_start != -1 and comment_start < match_start:
            return (match.group(1), match.group(2).strip())

    return None


def find_todo_in_docstring(line: str) -> tuple[str, str] | None:
    """Find TODO/FIXME/HACK in a docstring line."""
    match = re.search(r"(TODO|FIXME|HACK)[:\s]*(.*)", line, re.IGNORECASE)
    if match:
        return (match.group(1), match.group(2).strip())
    return None


def is_single_line_docstring_with_todo(line: str) -> bool:
    """Check if line is a single-line docstring containing a TODO."""
    for quote in ['"""', "'''"]:
        if line.count(quote) >= 2:
            first = line.find(quote)
            second = line.find(quote, first + 3)
            if first != -1 and second != -1:
                between = line[first + 3 : second]
                if re.search(r"(TODO|FIXME|HACK)", between, re.IGNORECASE):
                    return True
    return False


def categorize_todo(line: str, is_in_docstring: bool) -> str:
    """Categorize a TODO based on context."""
    stripped = line.strip()

    if is_in_docstring:
        return "DOCSTRING"

    if stripped.startswith("#") or stripped.startswith("//"):
        return "COMMENT"

    if "#" in line or "//" in line:
        comment_pos = len(line)
        for i, char in enumerate(line):
            if char == "#" and not is_in_string_literal(line, i):
                comment_pos = i
                break
            if line[i : i + 2] == "//" and not is_in_string_literal(line, i):
                comment_pos = i
                break

        code_part = line[:comment_pos].strip()
        if code_part:
            return "INLINE"

    return "COMMENT"


def scan_file_for_todos(filepath: Path) -> list[TodoItem]:
    """Scan a file for TODOs with smart categorization."""
    todos = []

    try:
        content = filepath.read_text()
        lines = content.split("\n")
    except Exception:
        return []

    docstring_state = compute_docstring_state(lines)

    for i, line in enumerate(lines):
        line_in_docstring = docstring_state[i]

        if is_single_line_docstring_with_todo(line):
            line_in_docstring = True

        if line_in_docstring:
            todo_match = find_todo_in_docstring(line)
            if todo_match:
                keyword, text = todo_match
                todos.append(
                    TodoItem(
                        file=str(filepath),
                        line=i + 1,
                        category="DOCSTRING",
                        text=text[:80] if text else f"{keyword} (no description)",
                    )
                )
        else:
            todo_match = find_todo_in_comment(line)
            if todo_match:
                keyword, text = todo_match
                category = categorize_todo(line, line_in_docstring)
                todos.append(
                    TodoItem(
                        file=str(filepath),
                        line=i + 1,
                        category=category,
                        text=text[:80] if text else f"{keyword} (no description)",
                    )
                )

    return todos


def count_todos_smart(repo_path: Path) -> dict[str, Any]:
    """Count TODOs with smart categorization (separating docstrings)."""
    by_category: dict[str, int] = {"DOCSTRING": 0, "COMMENT": 0, "INLINE": 0}

    # Get tracked files from git
    try:
        ls_result = subprocess.run(
            ["git", "ls-files"],
            capture_output=True,
            text=True,
            cwd=repo_path,
            timeout=GIT_TIMEOUT,
        )
    except subprocess.TimeoutExpired:
        return {"actionable": 0, "docstrings": 0, "total": 0}

    tracked_files = ls_result.stdout.strip().split("\n") if ls_result.stdout.strip() else []
    extensions = {".py", ".ts", ".tsx", ".js", ".jsx"}
    source_files = [f for f in tracked_files if Path(f).suffix in extensions]

    for f in source_files:
        filepath = repo_path / f
        if filepath.exists():
            todos = scan_file_for_todos(filepath)
            for todo in todos:
                by_category[todo.category] += 1

    actionable = by_category["COMMENT"] + by_category["INLINE"]
    docstrings = by_category["DOCSTRING"]

    return {
        "actionable": actionable,
        "docstrings": docstrings,
        "total": actionable + docstrings,
        "by_category": by_category,
    }


def count_todos_simple(repo_path: Path) -> int:
    """Simple TODO count (grep-based, fast)."""
    try:
        ls_result = subprocess.run(
            ["git", "ls-files"],
            capture_output=True,
            text=True,
            cwd=repo_path,
            timeout=GIT_TIMEOUT,
        )
    except subprocess.TimeoutExpired:
        return 0

    tracked_files = ls_result.stdout.strip().split("\n") if ls_result.stdout.strip() else []
    extensions = {".py", ".ts", ".tsx", ".js", ".jsx"}
    source_files = [f for f in tracked_files if Path(f).suffix in extensions]

    if not source_files:
        return 0

    try:
        grep_result = subprocess.run(
            ["grep", "-c", r"TODO\|FIXME\|HACK\|XXX", "--", *source_files],
            capture_output=True,
            text=True,
            cwd=repo_path,
            timeout=GIT_TIMEOUT,
        )
    except subprocess.TimeoutExpired:
        return 0

    total = 0
    for line in grep_result.stdout.strip().split("\n"):
        if ":" in line:
            try:
                total += int(line.split(":")[-1])
            except ValueError:
                pass
    return total


# ============================================================================
# Combined Status Report
# ============================================================================


def scan_repo(
    repo: str, repo_base: Path, github_org: str, fetch_ci: bool, skip_docstrings: bool
) -> dict[str, Any]:
    """Scan a single repo for combined status."""
    repo_path = repo_base / repo

    if not repo_path.exists():
        return {"name": repo, "error": f"Repo not found: {repo_path}"}

    # Fetch PRs
    prs = get_prs(github_org, repo, "open", fetch_ci=fetch_ci)
    for pr in prs:
        pr["repo"] = repo
        if fetch_ci:
            pr["ci_status"] = extract_ci_status(pr.get("statusCheckRollup"))

    # Count TODOs
    if skip_docstrings:
        todo_data = count_todos_smart(repo_path)
    else:
        todo_count = count_todos_simple(repo_path)
        todo_data = {"actionable": todo_count, "docstrings": 0, "total": todo_count}

    return {
        "name": repo,
        "prs": prs,
        "todos": todo_data,
    }


def format_report(results: list[dict], fetch_ci: bool, skip_docstrings: bool) -> str:
    """Format the combined status report."""
    lines = ["## Status Report"]
    lines.append(f"**Updated:** {datetime.now().strftime('%Y-%m-%d %H:%M AKST')}")
    lines.append("")

    # Collect all PRs
    all_prs = []
    for r in results:
        if "error" not in r:
            all_prs.extend(r["prs"])

    # Open PRs section
    lines.append(f"### Open PRs ({len(all_prs)} total)")
    if all_prs:
        # Sort by created date (newest first)
        sorted_prs = sorted(all_prs, key=lambda x: x.get("createdAt", ""), reverse=True)
        for pr in sorted_prs[:10]:
            ci_icon = get_ci_icon(pr.get("ci_status", "unknown")) if fetch_ci else ""
            title = pr["title"][:50] + "..." if len(pr["title"]) > 50 else pr["title"]
            prefix = f"{ci_icon} " if ci_icon else ""
            lines.append(f"- {prefix}**{pr['repo']}#{pr['number']}**: {title}")
        if len(sorted_prs) > 10:
            lines.append(f"- *...and {len(sorted_prs) - 10} more*")
    else:
        lines.append("*No open PRs*")
    lines.append("")

    # Repo Health section
    lines.append("### Repo Health")
    repos_needing_attention = []
    for r in results:
        if "error" in r:
            lines.append(f"- ❌ **{r['name']}**: {r['error']}")
            continue

        name = r["name"]
        todos = r["todos"]
        pr_count = len(r["prs"])

        # Determine status based on TODOs and PRs
        actionable = todos["actionable"]
        if actionable > 20 or pr_count > 5:
            status = "🔴"
            repos_needing_attention.append(name)
        elif actionable > 10 or pr_count > 3:
            status = "🟡"
        else:
            status = "✅"

        if skip_docstrings and todos["docstrings"] > 0:
            todo_str = f"{actionable} actionable TODOs ({todos['docstrings']} docstrings)"
        else:
            todo_str = f"{todos['total']} TODOs"

        lines.append(
            f"- {status} **{name}**: {todo_str}, {pr_count} PR{'s' if pr_count != 1 else ''}"
        )
    lines.append("")

    # Summary section
    lines.append("### Summary")
    total_prs = len(all_prs)

    # CI summary if fetched
    if fetch_ci and all_prs:
        passing = sum(1 for p in all_prs if p.get("ci_status") == "success")
        failing = sum(1 for p in all_prs if p.get("ci_status") == "failure")
        pending = sum(1 for p in all_prs if p.get("ci_status") == "pending")

        ci_parts = []
        if passing:
            ci_parts.append(f"{passing} passing")
        if failing:
            ci_parts.append(f"{failing} failing")
        if pending:
            ci_parts.append(f"{pending} pending")

        ci_summary = f" ({', '.join(ci_parts)})" if ci_parts else ""
        lines.append(f"- {total_prs} open PRs{ci_summary}")
    else:
        lines.append(f"- {total_prs} open PRs")

    if repos_needing_attention:
        lines.append(
            f"- {len(repos_needing_attention)} repo{'s' if len(repos_needing_attention) != 1 else ''} need attention: {', '.join(repos_needing_attention)}"
        )
    else:
        lines.append("- All repos healthy ✅")

    return "\n".join(lines)


def format_json(results: list[dict], fetch_ci: bool) -> str:
    """Format results as JSON."""
    all_prs = []
    for r in results:
        if "error" not in r:
            all_prs.extend(r["prs"])

    output = {
        "timestamp": datetime.now().isoformat(),
        "open_prs": all_prs,
        "repos": results,
        "summary": {
            "total_prs": len(all_prs),
            "repos_count": len(results),
        },
    }

    if fetch_ci:
        output["ci_summary"] = {
            "success": sum(1 for p in all_prs if p.get("ci_status") == "success"),
            "failure": sum(1 for p in all_prs if p.get("ci_status") == "failure"),
            "pending": sum(1 for p in all_prs if p.get("ci_status") == "pending"),
            "unknown": sum(1 for p in all_prs if p.get("ci_status") == "unknown"),
        }

    return json.dumps(output, indent=2)


def progress(msg: str, current: int, total: int) -> None:
    """Print progress message to stderr."""
    print(f"[{current}/{total}] {msg}...", file=sys.stderr)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Combined status report for repos and PRs.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  status.py                       Quick overview
  status.py --ci                  Include CI status (slower)
  status.py --skip-docstrings     Smart TODO counting (exclude docstrings)
  status.py --json                Output as JSON
  status.py --repo myrepo         Scan specific repo(s)
""",
    )
    parser.add_argument(
        "--ci",
        action="store_true",
        help="Fetch and show CI status (slower, requires API calls)",
    )
    parser.add_argument(
        "--skip-docstrings",
        action="store_true",
        help="Use smart TODO counting (separate docstrings from actionable TODOs)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="output_json",
        help="Output as JSON",
    )
    parser.add_argument(
        "--repo",
        action="append",
        metavar="REPO",
        help="Repo to scan (can be repeated; defaults to configured list)",
    )
    parser.add_argument(
        "--org",
        metavar="ORG",
        help="GitHub org/user (default: GITHUB_ORG env var)",
    )

    args = parser.parse_args()

    # Resolve config
    org = args.org or require_org()
    repos = args.repo if args.repo else get_repos("status")
    repo_base = get_repo_base()

    if not repo_base.exists():
        print(f"Error: Repo base directory not found: {repo_base}", file=sys.stderr)
        return 1

    # Scan repos
    results = []
    total = len(repos)
    for i, repo in enumerate(repos, 1):
        progress(f"Scanning {repo}", i, total)
        results.append(scan_repo(repo, repo_base, org, args.ci, args.skip_docstrings))

    # Output
    if args.output_json:
        print(format_json(results, args.ci))
    else:
        print(format_report(results, args.ci, args.skip_docstrings))

    return 0


if __name__ == "__main__":
    sys.exit(main())
