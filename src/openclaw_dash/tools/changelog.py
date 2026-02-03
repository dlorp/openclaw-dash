#!/usr/bin/env python3
"""Generate CHANGELOG.md from git history and merged PRs.

Usage:
    changelog.py                        # generate changelog for unreleased
    changelog.py --since v1.0.0         # since specific tag
    changelog.py --output CHANGELOG.md  # write to file
    changelog.py --format markdown      # or --format json
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

# Conventional commit types -> Keep a Changelog sections
TYPE_MAP = {
    "feat": "Added",
    "fix": "Fixed",
    "refactor": "Changed",
    "perf": "Changed",
    "docs": "Documentation",
    "style": "Changed",
    "test": "Changed",
    "build": "Changed",
    "ci": "Changed",
    "chore": "Changed",
    "revert": "Removed",
    "breaking": "Breaking Changes",
}

# Section order for Keep a Changelog
SECTION_ORDER = [
    "Breaking Changes",
    "Added",
    "Changed",
    "Deprecated",
    "Removed",
    "Fixed",
    "Security",
    "Documentation",
]


def run_git(args: list[str]) -> str:
    """Run a git command and return stdout."""
    result = subprocess.run(
        ["git", *args],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return ""
    return result.stdout.strip()


def get_commits_since(since: str | None = None) -> list[dict]:
    """Get commits since a tag or all commits if no tag specified."""
    # Format: hash|subject|body|author|date
    fmt = "%H|%s|%b|%an|%ai"

    if since:
        # Get commits since the tag
        log_range = f"{since}..HEAD"
    else:
        # Try to find the latest tag
        latest_tag = run_git(["describe", "--tags", "--abbrev=0"])
        if latest_tag:
            log_range = f"{latest_tag}..HEAD"
        else:
            # No tags, get all commits
            log_range = "HEAD"

    output = run_git(["log", log_range, f"--format={fmt}", "--no-merges"])
    if not output:
        return []

    commits = []
    for line in output.split("\n"):
        if not line.strip():
            continue

        parts = line.split("|", 4)
        if len(parts) >= 4:
            commits.append(
                {
                    "hash": parts[0][:8],
                    "subject": parts[1],
                    "body": parts[2] if len(parts) > 2 else "",
                    "author": parts[3] if len(parts) > 3 else "",
                    "date": parts[4] if len(parts) > 4 else "",
                }
            )

    return commits


def parse_commit(commit: dict) -> dict:
    """Parse a commit message into type, scope, description, and PR number."""
    subject = commit["subject"]

    # Try to extract PR number from subject (e.g., "feat: add feature (#123)")
    pr_match = re.search(r"\(#(\d+)\)$", subject)
    pr_number = pr_match.group(1) if pr_match else None
    if pr_match:
        subject = subject[: pr_match.start()].strip()

    # Parse conventional commit format: type(scope): description
    conv_match = re.match(r"^(\w+)(?:\(([^)]+)\))?!?:\s*(.+)$", subject)

    if conv_match:
        commit_type = conv_match.group(1).lower()
        scope = conv_match.group(2)
        description = conv_match.group(3)

        # Check for breaking change indicator
        if "!" in commit["subject"].split(":")[0]:
            section = "Breaking Changes"
        else:
            section = TYPE_MAP.get(commit_type, "Changed")
    else:
        # Non-conventional commit
        commit_type = "other"
        scope = None
        description = subject
        section = "Changed"

    return {
        "hash": commit["hash"],
        "type": commit_type,
        "scope": scope,
        "description": description,
        "pr_number": pr_number,
        "author": commit["author"],
        "date": commit["date"],
        "section": section,
    }


def group_by_section(commits: list[dict]) -> dict[str, list[dict]]:
    """Group parsed commits by their changelog section."""
    grouped = defaultdict(list)
    for commit in commits:
        parsed = parse_commit(commit)
        grouped[parsed["section"]].append(parsed)
    return dict(grouped)


def format_markdown(grouped: dict[str, list[dict]], version: str = "Unreleased") -> str:
    """Format grouped commits as Keep a Changelog markdown."""
    lines = []
    date_str = datetime.now().strftime("%Y-%m-%d")

    lines.append(f"## [{version}] - {date_str}")
    lines.append("")

    for section in SECTION_ORDER:
        if section not in grouped:
            continue

        commits = grouped[section]
        lines.append(f"### {section}")
        lines.append("")

        for commit in commits:
            desc = commit["description"]
            pr = f" (#{commit['pr_number']})" if commit["pr_number"] else ""
            scope = f"**{commit['scope']}:** " if commit["scope"] else ""
            lines.append(f"- {scope}{desc}{pr}")

        lines.append("")

    return "\n".join(lines)


def format_json(grouped: dict[str, list[dict]], version: str = "Unreleased") -> str:
    """Format grouped commits as JSON."""
    data = {
        "version": version,
        "date": datetime.now().strftime("%Y-%m-%d"),
        "sections": grouped,
    }
    return json.dumps(data, indent=2)


def read_existing_changelog(path: Path) -> str:
    """Read existing changelog content."""
    if path.exists():
        return path.read_text()
    return ""


def merge_changelog(existing: str, new_section: str) -> str:
    """Merge new changelog section with existing content."""
    if not existing:
        # Create new changelog
        header = """# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

"""
        return header + new_section

    # Find where to insert (after header, before first version)
    lines = existing.split("\n")
    insert_idx = 0

    for i, line in enumerate(lines):
        if line.startswith("## ["):
            insert_idx = i
            break
    else:
        # No existing versions, append at end
        return existing.rstrip() + "\n\n" + new_section

    # Insert new section before first version
    return "\n".join(lines[:insert_idx]) + new_section + "\n".join(lines[insert_idx:])


def main():
    parser = argparse.ArgumentParser(description="Generate CHANGELOG.md from git history")
    parser.add_argument(
        "--since",
        help="Generate changelog since this tag (default: latest tag)",
    )
    parser.add_argument(
        "--output",
        "-o",
        help="Write output to file (supports incremental updates)",
    )
    parser.add_argument(
        "--format",
        "-f",
        choices=["markdown", "json"],
        default="markdown",
        help="Output format (default: markdown)",
    )
    parser.add_argument(
        "--version",
        "-v",
        default="Unreleased",
        help="Version label for this changelog (default: Unreleased)",
    )

    args = parser.parse_args()

    # Get and parse commits
    commits = get_commits_since(args.since)

    if not commits:
        print("No commits found.", file=sys.stderr)
        sys.exit(0)

    # Group by section
    grouped = group_by_section(commits)

    # Format output
    if args.format == "json":
        output = format_json(grouped, args.version)
    else:
        output = format_markdown(grouped, args.version)

    # Write or print
    if args.output:
        output_path = Path(args.output)
        if args.format == "markdown" and output_path.exists():
            existing = read_existing_changelog(output_path)
            output = merge_changelog(existing, output)
        output_path.write_text(output)
        print(f"Wrote changelog to {output_path}", file=sys.stderr)
    else:
        print(output)


if __name__ == "__main__":
    main()
