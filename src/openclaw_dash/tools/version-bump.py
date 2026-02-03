#!/usr/bin/env python3
"""Simple semver version bumping based on conventional commits."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path


def run(cmd: list[str], check: bool = True) -> str:
    """Run a command and return stdout."""
    result = subprocess.run(cmd, capture_output=True, text=True, check=check)
    return result.stdout.strip()


def find_repo_root() -> Path:
    """Find git repository root."""
    try:
        root = run(["git", "rev-parse", "--show-toplevel"])
        return Path(root)
    except subprocess.CalledProcessError:
        print("Error: Not in a git repository", file=sys.stderr)
        sys.exit(1)


def get_current_version(repo_root: Path) -> tuple[str, Path, str]:
    """Find and return current version, file path, and file type."""
    # Try pyproject.toml first
    pyproject = repo_root / "pyproject.toml"
    if pyproject.exists():
        content = pyproject.read_text()
        match = re.search(r'^version\s*=\s*["\']([^"\']+)["\']', content, re.MULTILINE)
        if match:
            return match.group(1), pyproject, "pyproject"

    # Try package.json
    package_json = repo_root / "package.json"
    if package_json.exists():
        data = json.loads(package_json.read_text())
        if "version" in data:
            return data["version"], package_json, "package.json"

    # Try VERSION file
    version_file = repo_root / "VERSION"
    if version_file.exists():
        return version_file.read_text().strip(), version_file, "VERSION"

    print("Error: No version file found (pyproject.toml, package.json, VERSION)")
    sys.exit(1)


def parse_version(version: str) -> tuple[int, int, int]:
    """Parse semver string into tuple."""
    match = re.match(r"(\d+)\.(\d+)\.(\d+)", version)
    if not match:
        print(f"Error: Invalid version format: {version}", file=sys.stderr)
        sys.exit(1)
    return int(match.group(1)), int(match.group(2)), int(match.group(3))


def bump_version(major: int, minor: int, patch: int, bump_type: str) -> str:
    """Apply bump and return new version string."""
    if bump_type == "major":
        return f"{major + 1}.0.0"
    elif bump_type == "minor":
        return f"{major}.{minor + 1}.0"
    else:  # patch
        return f"{major}.{minor}.{patch + 1}"


def get_last_tag() -> str | None:
    """Get the most recent version tag."""
    try:
        # Get tags that look like versions, sorted by version
        tags = run(["git", "tag", "-l", "v*", "--sort=-v:refname"], check=False)
        if tags:
            return tags.split("\n")[0]
        # Also try without v prefix
        tags = run(["git", "tag", "-l", "[0-9]*", "--sort=-v:refname"], check=False)
        if tags:
            return tags.split("\n")[0]
    except subprocess.CalledProcessError:
        pass
    return None


def get_commits_since(tag: str | None) -> list[str]:
    """Get commit messages since the given tag (or all if no tag)."""
    try:
        if tag:
            output = run(["git", "log", f"{tag}..HEAD", "--pretty=format:%s"])
        else:
            output = run(["git", "log", "--pretty=format:%s"])
        return [line for line in output.split("\n") if line]
    except subprocess.CalledProcessError:
        return []


def detect_bump_type(commits: list[str]) -> str:
    """Analyze commits to determine bump type."""
    bump = "patch"  # default

    for msg in commits:
        msg_lower = msg.lower()
        # Check for breaking changes (major)
        if "breaking change" in msg_lower or re.match(r"^\w+!:", msg):
            return "major"
        # Check for features (minor)
        if msg_lower.startswith("feat:") or msg_lower.startswith("feat("):
            bump = "minor"

    return bump


def update_version_file(
    file_path: Path, file_type: str, old_version: str, new_version: str
) -> None:
    """Update version in the appropriate file."""
    content = file_path.read_text()

    if file_type == "pyproject":
        # Replace version in pyproject.toml
        new_content = re.sub(
            r'^(version\s*=\s*["\'])' + re.escape(old_version) + r'(["\'])',
            rf"\g<1>{new_version}\g<2>",
            content,
            flags=re.MULTILINE,
        )
    elif file_type == "package.json":
        # Parse and update JSON
        data = json.loads(content)
        data["version"] = new_version
        new_content = json.dumps(data, indent=2) + "\n"
    else:  # VERSION file
        new_content = new_version + "\n"

    file_path.write_text(new_content)


def create_git_tag(version: str) -> None:
    """Create a git tag for the version."""
    tag = f"v{version}"
    run(["git", "tag", "-a", tag, "-m", f"Release {tag}"])
    print(f"Created tag: {tag}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Bump semantic version based on conventional commits"
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--major", action="store_true", help="Force major version bump")
    group.add_argument("--minor", action="store_true", help="Force minor version bump")
    group.add_argument("--patch", action="store_true", help="Force patch version bump")
    parser.add_argument(
        "--dry-run", action="store_true", help="Show what would happen without changes"
    )
    parser.add_argument("--tag", action="store_true", help="Create git tag after bumping")
    args = parser.parse_args()

    # Find repo and version
    repo_root = find_repo_root()
    current_version, version_file, file_type = get_current_version(repo_root)
    major, minor, patch = parse_version(current_version)

    print(f"Current version: {current_version}")
    print(f"Version file: {version_file.relative_to(repo_root)}")

    # Determine bump type
    if args.major:
        bump_type = "major"
    elif args.minor:
        bump_type = "minor"
    elif args.patch:
        bump_type = "patch"
    else:
        # Auto-detect from commits
        last_tag = get_last_tag()
        if last_tag:
            print(f"Last tag: {last_tag}")
        else:
            print("No previous tags found")

        commits = get_commits_since(last_tag)
        if not commits:
            print("No commits since last tag")
            sys.exit(0)

        print(f"Commits since tag: {len(commits)}")
        bump_type = detect_bump_type(commits)

    new_version = bump_version(major, minor, patch, bump_type)
    print(f"Bump type: {bump_type}")
    print(f"New version: {new_version}")

    if args.dry_run:
        print("\n[dry-run] No changes made")
        return

    # Update version file
    update_version_file(version_file, file_type, current_version, new_version)
    print(f"\nUpdated {version_file.name}")

    # Create tag if requested
    if args.tag:
        create_git_tag(new_version)

    print(f"\n✓ Version bumped to {new_version}")


if __name__ == "__main__":
    main()
