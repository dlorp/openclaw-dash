#!/usr/bin/env python3
"""
pr-tracker.py — Track PR status across configured repos.

Features:
- List all open PRs with age
- Detect merged PRs since last check
- Detect closed PRs without merge
- Save state for comparison
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from config import get_repos, require_org

STATE_FILE = Path(__file__).parent / ".pr_state.json"


def run(cmd: list[str]) -> tuple[int, str]:
    """Run a command and return (returncode, output)."""
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode, result.stdout.strip()


def get_prs(org: str, repo: str, state: str = "all") -> list[dict]:
    """Get PRs for a repo."""
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
            "number,title,state,createdAt,mergedAt,closedAt,author,headRefName,statusCheckRollup",
            "--limit",
            "20",
        ]
    )
    if returncode != 0:
        # gh CLI failed - likely invalid org/repo
        print(
            f"Warning: Failed to fetch PRs for {org}/{repo} (gh exit code {returncode})",
            file=sys.stderr,
        )
        return []
    try:
        return json.loads(output) if output else []
    except json.JSONDecodeError:
        return []


def validate_org(org: str) -> bool:
    """Check if the org/user exists on GitHub."""
    returncode, _ = run(["gh", "api", f"users/{org}", "--silent"])
    if returncode != 0:
        # Also try as an org
        returncode, _ = run(["gh", "api", f"orgs/{org}", "--silent"])
    return returncode == 0


def load_state() -> dict:
    """Load previous state with graceful handling of corrupted files."""
    if STATE_FILE.exists():
        try:
            data = json.loads(STATE_FILE.read_text())
            if not isinstance(data, dict):
                print("Warning: State file corrupted (not a dict), resetting", file=sys.stderr)
                return {"prs": {}, "last_check": None}
            # Handle null/None values - ensure prs is always a dict
            if data.get("prs") is None:
                data["prs"] = {}
            return data
        except json.JSONDecodeError as e:
            print(f"Warning: State file corrupted ({e}), resetting", file=sys.stderr)
            return {"prs": {}, "last_check": None}
        except OSError as e:
            print(f"Warning: Cannot read state file ({e}), resetting", file=sys.stderr)
            return {"prs": {}, "last_check": None}
    return {"prs": {}, "last_check": None}


def save_state(state: dict):
    """Save current state."""
    state["last_check"] = datetime.now().isoformat()
    STATE_FILE.write_text(json.dumps(state, indent=2))


def format_age(created_at: str | None) -> str:
    """Format PR age as human readable with date validation."""
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
    except (ValueError, AttributeError, TypeError) as e:
        # Invalid date format or missing timezone info
        print(f"Warning: Invalid date '{created_at}': {e}", file=sys.stderr)
        return "?"


def calculate_age_days(created_at: str | None) -> int | None:
    """Calculate PR age in days for structured output."""
    if not created_at or not isinstance(created_at, str):
        return None

    try:
        created = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        age = datetime.now(created.tzinfo) - created
        return age.days
    except (ValueError, AttributeError, TypeError):
        return None


def extract_ci_status(status_check_rollup) -> str:
    """Extract CI status from GitHub's statusCheckRollup."""
    if not status_check_rollup:
        return "unknown"

    # statusCheckRollup is a list of status checks
    if not isinstance(status_check_rollup, list) or len(status_check_rollup) == 0:
        return "unknown"

    # Look for overall status - if any check failed, consider it failed
    # If all are success/neutral, consider it success
    # If any are pending, consider it pending
    statuses = []
    for check in status_check_rollup:
        if isinstance(check, dict) and "state" in check:
            statuses.append(check["state"].lower())

    if not statuses:
        return "unknown"

    if "failure" in statuses or "error" in statuses:
        return "failure"
    elif "pending" in statuses:
        return "pending"
    elif all(s in ["success", "neutral"] for s in statuses):
        return "success"
    else:
        return "unknown"


def normalize_pr_data(pr: dict, repo: str) -> dict:
    """Normalize PR data for consistent structure."""
    return {
        "number": pr["number"],
        "repo": repo,
        "title": pr["title"],
        "status": pr["state"].lower(),  # open, merged, closed
        "ci_status": extract_ci_status(pr.get("statusCheckRollup")),
        "age": calculate_age_days(pr.get("createdAt")),
        "age_formatted": format_age(pr.get("createdAt")),
        "created_at": pr.get("createdAt"),
        "merged_at": pr.get("mergedAt"),
        "closed_at": pr.get("closedAt"),
        "author": pr.get("author", {}).get("login") if pr.get("author") else None,
        "head_ref": pr.get("headRefName"),
    }


def check_changes(old_state: dict, current_prs: dict) -> dict[str, list[Any]]:
    """Detect changes between states."""
    changes: dict[str, list[Any]] = {
        "merged": [],
        "closed": [],
        "new": [],
    }

    # Handle null/None - ensure old_prs is always a dict
    old_prs = old_state.get("prs") or {}

    for pr_key, pr in current_prs.items():
        if pr_key not in old_prs:
            if pr["state"] == "OPEN":
                changes["new"].append(pr)
        else:
            old_pr = old_prs[pr_key]
            if old_pr["state"] == "OPEN" and pr["state"] == "MERGED":
                changes["merged"].append(pr)
            elif old_pr["state"] == "OPEN" and pr["state"] == "CLOSED":
                changes["closed"].append(pr)

    return changes


def main():
    parser = argparse.ArgumentParser(
        description="Track PR status across configured repos.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  pr-tracker.py                        Show current PR status
  pr-tracker.py --check                Check for changes since last run
  pr-tracker.py --json                 Output as structured JSON
  pr-tracker.py --repo myrepo          Scan a specific repo
  pr-tracker.py --org myorg            Override GITHUB_ORG
  pr-tracker.py --status open          Show only open PRs
  pr-tracker.py --status merged --json Get merged PRs as JSON
""",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check for changes since last run",
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
        help="Repo to scan (can be repeated; defaults to built-in list)",
    )
    parser.add_argument(
        "--org",
        metavar="ORG",
        help="GitHub org/user (default: GITHUB_ORG env var)",
    )
    parser.add_argument(
        "--status",
        choices=["open", "merged", "closed"],
        help="Filter PRs by status",
    )
    args = parser.parse_args()

    # Resolve org (require_org exits with helpful message if not configured)
    org = args.org or require_org()

    # Validate org exists on GitHub
    if not validate_org(org):
        print(
            f"Warning: GitHub org/user '{org}' may not exist or is inaccessible. "
            "Results may be empty.",
            file=sys.stderr,
        )

    # Resolve repos (from args, or config file, or defaults)
    repos = args.repo if args.repo else get_repos("pr-tracker")

    # Load previous state
    old_state = load_state()

    # Gather current PRs
    all_prs = {}
    normalized_prs = {
        "open": [],
        "merged": [],
        "closed": [],
    }

    for repo in repos:
        # Filter repos if specified
        if args.repo and repo not in args.repo:
            continue

        prs = get_prs(org, repo, "all")
        for pr in prs:
            # Normalize PR data
            normalized_pr = normalize_pr_data(pr, repo)

            # Store for state tracking (keep original format for compatibility)
            pr["repo"] = repo
            pr_key = f"{repo}#{pr['number']}"
            all_prs[pr_key] = pr

            # Categorize normalized PRs
            status = normalized_pr["status"]
            if status in normalized_prs:
                normalized_prs[status].append(normalized_pr)

    # Apply status filter
    if args.status:
        filtered_prs = {args.status: normalized_prs.get(args.status, [])}
        # Keep other categories empty but present for consistency
        for status_key in ["open", "merged", "closed"]:
            if status_key not in filtered_prs:
                filtered_prs[status_key] = []
        normalized_prs = filtered_prs

    # Check for changes
    changes = check_changes(old_state, all_prs)

    # Normalize change data too
    normalized_changes = {}
    for change_type, prs in changes.items():
        normalized_changes[change_type] = [
            normalize_pr_data(pr, pr["repo"]) for pr in prs
        ]

    # Save new state
    save_state({"prs": all_prs})

    if args.output_json:
        output = {
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total_open": len(normalized_prs["open"]),
                "total_merged": len(normalized_prs["merged"]),
                "total_closed": len(normalized_prs["closed"]),
            },
            "open_prs": normalized_prs["open"],
            "merged_prs": normalized_prs["merged"],
            "closed_prs": normalized_prs["closed"],
            "new_prs": normalized_changes.get("new", []),
            "ci_status": {
                "success": len([pr for pr in normalized_prs["open"] if pr["ci_status"] == "success"]),
                "failure": len([pr for pr in normalized_prs["open"] if pr["ci_status"] == "failure"]),
                "pending": len([pr for pr in normalized_prs["open"] if pr["ci_status"] == "pending"]),
                "unknown": len([pr for pr in normalized_prs["open"] if pr["ci_status"] == "unknown"]),
            },
        }

        if args.check:
            output["changes"] = normalized_changes

        print(json.dumps(output, indent=2))
        return

    # Format output
    lines = ["## PR Status"]
    lines.append(f"**Updated:** {datetime.now().strftime('%Y-%m-%d %H:%M AKST')}")
    lines.append("")

    # Report changes if in check mode
    if args.check and old_state.get("last_check"):
        if normalized_changes.get("merged"):
            lines.append("### ✅ Merged Since Last Check")
            for pr in normalized_changes["merged"]:
                lines.append(f"- **{pr['repo']}#{pr['number']}**: {pr['title']}")
            lines.append("")

        if normalized_changes.get("closed"):
            lines.append("### ❌ Closed Without Merge")
            for pr in normalized_changes["closed"]:
                lines.append(f"- **{pr['repo']}#{pr['number']}**: {pr['title']}")
            lines.append("")

        if normalized_changes.get("new"):
            lines.append("### 🆕 New PRs")
            for pr in normalized_changes["new"]:
                lines.append(f"- **{pr['repo']}#{pr['number']}**: {pr['title']}")
            lines.append("")

    # Display PRs based on filter or show all sections
    if args.status:
        # Show only filtered status
        status_labels = {
            "open": "Open PRs",
            "merged": "Merged PRs",
            "closed": "Closed PRs"
        }
        lines.append(f"### {status_labels[args.status]}")
        prs_to_show = normalized_prs[args.status]
        if prs_to_show:
            for pr in sorted(prs_to_show, key=lambda x: x["created_at"] or ""):
                age = pr["age_formatted"]
                ci_icon = {"success": "✅", "failure": "❌", "pending": "🟡", "unknown": "❓"}[pr["ci_status"]]
                lines.append(f"- **{pr['repo']}#{pr['number']}** ({age}) {ci_icon}: {pr['title'][:50]}")
        else:
            lines.append(f"No {args.status} PRs.")
    else:
        # Show open PRs by default
        lines.append("### Open PRs")
        open_prs = normalized_prs["open"]
        if open_prs:
            for pr in sorted(open_prs, key=lambda x: x["created_at"] or ""):
                age = pr["age_formatted"]
                ci_icon = {"success": "✅", "failure": "❌", "pending": "🟡", "unknown": "❓"}[pr["ci_status"]]
                lines.append(f"- **{pr['repo']}#{pr['number']}** ({age}) {ci_icon}: {pr['title'][:50]}")
        else:
            lines.append("No open PRs.")

    print("\n".join(lines))


if __name__ == "__main__":
    main()
