#!/usr/bin/env python3
"""
pr-tracker.py — Track PR status across configured repos.

Features:
- List all open PRs with age
- Detect merged PRs since last check
- Detect closed PRs without merge
- Save state for comparison
"""

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

# Configuration - customize for your setup
DEFAULT_REPOS = ["synapse-engine", "r3LAY", "t3rra1n"]
STATE_FILE = Path(__file__).parent / ".pr_state.json"


def run(cmd: list[str]) -> tuple[int, str]:
    """Run a command and return (returncode, output)."""
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode, result.stdout.strip()


def get_prs(org: str, repo: str, state: str = "all") -> list[dict]:
    """Get PRs for a repo."""
    _, output = run(
        [
            "gh",
            "pr",
            "list",
            "-R",
            f"{org}/{repo}",
            "--state",
            state,
            "--json",
            "number,title,state,createdAt,mergedAt,closedAt,author",
            "--limit",
            "20",
        ]
    )
    try:
        return json.loads(output) if output else []
    except json.JSONDecodeError:
        return []


def load_state() -> dict:
    """Load previous state."""
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {"prs": {}, "last_check": None}


def save_state(state: dict):
    """Save current state."""
    state["last_check"] = datetime.now().isoformat()
    STATE_FILE.write_text(json.dumps(state, indent=2))


def format_age(created_at: str) -> str:
    """Format PR age as human readable."""
    created = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
    age = datetime.now(created.tzinfo) - created

    if age.days > 0:
        return f"{age.days}d"
    elif age.seconds >= 3600:
        return f"{age.seconds // 3600}h"
    else:
        return f"{age.seconds // 60}m"


def check_changes(old_state: dict, current_prs: dict) -> dict[str, list[Any]]:
    """Detect changes between states."""
    changes: dict[str, list[Any]] = {
        "merged": [],
        "closed": [],
        "new": [],
    }

    old_prs = old_state.get("prs", {})

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
  pr-tracker.py --check          Check for changes since last run
  pr-tracker.py --json           Output as JSON
  pr-tracker.py --repo myrepo    Scan a specific repo
  pr-tracker.py --org myorg      Override GITHUB_ORG
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
    args = parser.parse_args()

    # Resolve org
    org = args.org or os.environ.get("GITHUB_ORG", "")
    if not org:
        print("Error: GITHUB_ORG not set. Use --org or set GITHUB_ORG env var.", file=sys.stderr)
        sys.exit(1)

    # Resolve repos
    repos = args.repo if args.repo else DEFAULT_REPOS

    # Load previous state
    old_state = load_state()

    # Gather current PRs
    all_prs = {}
    open_prs = []

    for repo in repos:
        prs = get_prs(org, repo, "all")
        for pr in prs:
            pr["repo"] = repo
            pr_key = f"{repo}#{pr['number']}"
            all_prs[pr_key] = pr
            if pr["state"] == "OPEN":
                open_prs.append(pr)

    # Check for changes
    changes = check_changes(old_state, all_prs)

    # Save new state
    save_state({"prs": all_prs})

    if args.output_json:
        print(
            json.dumps(
                {
                    "open_prs": open_prs,
                    "changes": changes,
                    "timestamp": datetime.now().isoformat(),
                },
                indent=2,
            )
        )
        return

    # Format output
    lines = ["## PR Status"]
    lines.append(f"**Updated:** {datetime.now().strftime('%Y-%m-%d %H:%M AKST')}")
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
            lines.append(f"- **{pr['repo']}#{pr['number']}** ({age}): {pr['title'][:50]}")
    else:
        lines.append("No open PRs.")

    print("\n".join(lines))


if __name__ == "__main__":
    main()
