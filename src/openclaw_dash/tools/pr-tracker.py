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


def get_prs(org: str, repo: str, state: str = "all", fetch_ci: bool = False) -> list[dict]:
    """Get PRs for a repo.

    Args:
        org: GitHub org/user
        repo: Repository name
        state: PR state filter (all, open, closed, merged)
        fetch_ci: If True, include statusCheckRollup in the query
    """
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


def extract_ci_status(status_check_rollup: list[dict] | None) -> str:
    """Extract CI status from GitHub's statusCheckRollup.

    Args:
        status_check_rollup: List of check runs/status contexts from GitHub API

    Returns:
        One of: "success", "failure", "pending", "unknown"
    """
    if not status_check_rollup:
        return "unknown"

    if not isinstance(status_check_rollup, list) or len(status_check_rollup) == 0:
        return "unknown"

    # Parse each check - handles both CheckRun and StatusContext types
    # CheckRun has: conclusion (SUCCESS, FAILURE, etc.) and status (COMPLETED, IN_PROGRESS, etc.)
    # StatusContext has: state (SUCCESS, PENDING, FAILURE, ERROR)
    statuses = []
    for check in status_check_rollup:
        if not isinstance(check, dict):
            continue

        # Try conclusion field first (CheckRun items)
        conclusion = check.get("conclusion")
        if conclusion:
            statuses.append(conclusion.upper())
        # Check if it's in progress (conclusion is null but status indicates running)
        elif check.get("status") in (
            "IN_PROGRESS",
            "PENDING",
            "QUEUED",
            "REQUESTED",
            "WAITING",
        ):
            statuses.append("PENDING")
        # Try state field (StatusContext items)
        elif check.get("state"):
            statuses.append(check["state"].upper())

    if not statuses:
        return "unknown"

    # Determine overall status:
    # - Any FAILURE/ERROR/CANCELLED/TIMED_OUT/ACTION_REQUIRED = failure
    # - Any PENDING/IN_PROGRESS/QUEUED (and no failures) = pending
    # - All SUCCESS/NEUTRAL/SKIPPED = success
    failure_states = {
        "FAILURE",
        "ERROR",
        "CANCELLED",
        "TIMED_OUT",
        "ACTION_REQUIRED",
        "STARTUP_FAILURE",
    }
    pending_states = {
        "PENDING",
        "IN_PROGRESS",
        "QUEUED",
        "REQUESTED",
        "WAITING",
        "EXPECTED",
    }
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


def truncate_title(title: str, max_length: int = 50) -> str:
    """Truncate title at word boundary with ellipsis.

    Args:
        title: The title to truncate
        max_length: Maximum length before truncation

    Returns:
        Truncated title with ellipsis if needed, or full title if short enough
    """
    if len(title) <= max_length:
        return title

    # Find the last space before max_length
    truncated = title[:max_length]
    last_space = truncated.rfind(" ")

    if last_space > 0:
        # Cut at word boundary
        return title[:last_space] + "..."
    else:
        # No space found, fall back to hard cut
        return truncated + "..."


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
  pr-tracker.py                  Show current PR status
  pr-tracker.py --ci             Show with actual CI status
  pr-tracker.py --check          Check for changes since last run
  pr-tracker.py --json           Output as JSON
  pr-tracker.py --repo myrepo    Scan a specific repo
  pr-tracker.py --org myorg      Override GITHUB_ORG
""",
    )
    parser.add_argument(
        "--ci",
        action="store_true",
        help="Fetch and show actual CI status (slower, requires API calls)",
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
        "--full",
        action="store_true",
        help="Show full PR titles without truncation",
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
    open_prs = []

    for repo in repos:
        prs = get_prs(org, repo, "all", fetch_ci=args.ci)
        for pr in prs:
            pr["repo"] = repo
            pr_key = f"{repo}#{pr['number']}"
            # Extract CI status if --ci flag was passed
            if args.ci:
                pr["ci_status"] = extract_ci_status(pr.get("statusCheckRollup"))
            all_prs[pr_key] = pr
            if pr["state"] == "OPEN":
                open_prs.append(pr)

    # Check for changes
    changes = check_changes(old_state, all_prs)

    # Save new state
    save_state({"prs": all_prs})

    if args.output_json:
        output_data = {
            "open_prs": open_prs,
            "changes": changes,
            "timestamp": datetime.now().isoformat(),
        }
        # Add CI summary if --ci flag was passed
        if args.ci:
            output_data["ci_summary"] = {
                "success": len([p for p in open_prs if p.get("ci_status") == "success"]),
                "failure": len([p for p in open_prs if p.get("ci_status") == "failure"]),
                "pending": len([p for p in open_prs if p.get("ci_status") == "pending"]),
                "unknown": len([p for p in open_prs if p.get("ci_status") == "unknown"]),
            }
        print(json.dumps(output_data, indent=2))
        return

    # Format output
    lines = ["## PR Status"]
    lines.append(f"**Updated:** {datetime.now().astimezone().strftime('%Y-%m-%d %H:%M %Z')}")
    lines.append("")

    # Report changes if in check mode
    if args.check and old_state.get("last_check"):
        if changes["merged"]:
            lines.append("### ✅ Merged Since Last Check")
            for pr in changes["merged"]:
                lines.append(f"- **{pr['repo']}#{pr['number']}**: {pr['title']}")
            lines.append("")

        if changes["closed"]:
            lines.append("### ❌ Closed Without Merge")
            for pr in changes["closed"]:
                lines.append(f"- **{pr['repo']}#{pr['number']}**: {pr['title']}")
            lines.append("")

        if changes["new"]:
            lines.append("### New PRs")
            for pr in changes["new"]:
                lines.append(f"- **{pr['repo']}#{pr['number']}**: {pr['title']}")
            lines.append("")

    # Open PRs
    lines.append("### Open PRs")
    if open_prs:
        for pr in sorted(open_prs, key=lambda x: x["createdAt"]):
            age = format_age(pr["createdAt"])
            ci_icon = get_ci_icon(pr.get("ci_status", "unknown"))
            title = pr["title"] if args.full else truncate_title(pr["title"])
            lines.append(f"- **{pr['repo']}#{pr['number']}** ({age}) {ci_icon}: {title}")
    else:
        lines.append("No open PRs.")

    print("\n".join(lines))


if __name__ == "__main__":
    main()
