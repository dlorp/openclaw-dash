#!/usr/bin/env python3
"""
pr-tracker.py — Track PR status across configured repos.

Features:
- List all open PRs with age
- Detect merged PRs since last check
- Detect closed PRs without merge
- Save state for comparison

Usage:
    python3 pr-tracker.py           # Show current PR status
    python3 pr-tracker.py --check   # Check for changes since last run
    python3 pr-tracker.py --json    # Output as JSON

Configuration:
    Set GITHUB_ORG environment variable or edit GITHUB_ORG below.
    Set REPOS list to your repos.
"""

import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# Configuration - customize for your setup
GITHUB_ORG = os.environ.get("GITHUB_ORG", "")  # Set your GitHub username/org
REPOS = ["synapse-engine", "r3LAY", "t3rra1n"]  # Your repos
STATE_FILE = Path(__file__).parent / ".pr_state.json"


def run(cmd: str) -> tuple[int, str]:
    """Run a shell command and return (returncode, output)."""
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return result.returncode, result.stdout.strip()


def get_prs(repo: str, state: str = "all") -> list[dict]:
    """Get PRs for a repo."""
    if not GITHUB_ORG:
        print("Error: Set GITHUB_ORG environment variable or edit the script.", file=sys.stderr)
        return []
    _, output = run(
        f"gh pr list -R {GITHUB_ORG}/{repo} --state {state} --json number,title,state,createdAt,mergedAt,closedAt,author --limit 20"
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


def check_changes(old_state: dict, current_prs: dict) -> dict:
    """Detect changes between states."""
    changes = {
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
    output_json = "--json" in sys.argv
    check_mode = "--check" in sys.argv

    # Load previous state
    old_state = load_state()

    # Gather current PRs
    all_prs = {}
    open_prs = []

    for repo in REPOS:
        prs = get_prs(repo, "all")
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

    if output_json:
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
    lines = ["## 📬 PR Status"]
    lines.append(f"**Updated:** {datetime.now().strftime('%Y-%m-%d %H:%M AKST')}")
    lines.append("")

    # Report changes if in check mode
    if check_mode and old_state.get("last_check"):
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
            lines.append("### 🆕 New PRs")
            for pr in changes["new"]:
                lines.append(f"- **{pr['repo']}#{pr['number']}**: {pr['title']}")
            lines.append("")

    # Open PRs
    if open_prs:
        lines.append("### 🔓 Open PRs")
        for pr in sorted(open_prs, key=lambda x: x["createdAt"]):
            age = format_age(pr["createdAt"])
            lines.append(f"- **{pr['repo']}#{pr['number']}** ({age}): {pr['title'][:50]}")
    else:
        lines.append("### 🔓 Open PRs")
        lines.append("*None — all clear!*")

    print("\n".join(lines))


if __name__ == "__main__":
    main()
