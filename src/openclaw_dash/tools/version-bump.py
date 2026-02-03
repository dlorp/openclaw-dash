#!/usr/bin/env python3
"""Simple semver version bumping based on conventional commits."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

# Common monorepo subdirectory patterns
MONOREPO_PATTERNS = [
    "backend",
    "frontend",
    "packages",
    "apps",
    "libs",
    "server",
    "client",
    "api",
    "web",
]


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


def find_version_file(search_path: Path) -> tuple[str, Path, str] | None:
    """Find version file in a directory. Returns (version, path, type) or None."""
    # Try pyproject.toml first
    pyproject = search_path / "pyproject.toml"
    if pyproject.exists():
        content = pyproject.read_text()
        match = re.search(r'^version\s*=\s*["\']([^"\']+)["\']', content, re.MULTILINE)
        if match:
            return match.group(1), pyproject, "pyproject"

    # Try package.json
    package_json = search_path / "package.json"
    if package_json.exists():
        data = json.loads(package_json.read_text())
        if "version" in data:
            return data["version"], package_json, "package.json"

    # Try VERSION file
    version_file = search_path / "VERSION"
    if version_file.exists():
        return version_file.read_text().strip(), version_file, "VERSION"

    return None


def discover_all_version_files(repo_root: Path) -> list[tuple[str, Path, str]]:
    """Discover all version files in repo root and common monorepo subdirs."""
    found = []

    # Check repo root
    result = find_version_file(repo_root)
    if result:
        found.append(result)

    # Check monorepo subdirectories
    for pattern in MONOREPO_PATTERNS:
        subdir = repo_root / pattern
        if subdir.is_dir():
            result = find_version_file(subdir)
            if result:
                found.append(result)

    return found


def get_current_version(
    repo_root: Path, specified_path: str | None = None
) -> tuple[str, Path, str]:
    """Find and return current version, file path, and file type."""
    # If path specified, look there first
    if specified_path:
        search_path = (repo_root / specified_path).resolve()
        if not search_path.is_relative_to(repo_root.resolve()):
            print("Error: Path must be within repository", file=sys.stderr)
            sys.exit(1)
        if not search_path.is_dir():
            print(f"Error: Specified path does not exist: {specified_path}", file=sys.stderr)
            sys.exit(1)
        result = find_version_file(search_path)
        if result:
            return result
        print(f"Error: No version file found in {specified_path}")
        sys.exit(1)

    # Check repo root first
    result = find_version_file(repo_root)
    if result:
        return result

    # Auto-detect monorepo patterns
    for pattern in MONOREPO_PATTERNS:
        subdir = repo_root / pattern
        if subdir.is_dir():
            result = find_version_file(subdir)
            if result:
                print(f"Auto-detected monorepo: found version in {pattern}/")
                return result

    print("Error: No version file found (pyproject.toml, package.json, VERSION)")
    print("Tip: Use --path to specify subdirectory or --sync to update all")
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
    parser.add_argument(
        "--path",
        metavar="PATH",
        help="Subdirectory containing version file (e.g., backend, frontend)",
    )
    parser.add_argument(
        "--sync",
        action="store_true",
        help="Find and update all version files to the same version",
    )
    args = parser.parse_args()

    # Find repo root
    repo_root = find_repo_root()

    # Handle --sync mode: update all version files
    if args.sync:
        all_files = discover_all_version_files(repo_root)
        if not all_files:
            print("Error: No version files found in repo")
            sys.exit(1)

        print(f"Found {len(all_files)} version file(s):")
        for version, path, _ in all_files:
            print(f"  {path.relative_to(repo_root)}: {version}")

        # Use first file's version as the base
        current_version, _, _ = all_files[0]
        major, minor, patch = parse_version(current_version)

        # Determine bump type
        if args.major:
            bump_type = "major"
        elif args.minor:
            bump_type = "minor"
        elif args.patch:
            bump_type = "patch"
        else:
            last_tag = get_last_tag()
            if last_tag:
                print(f"Last tag: {last_tag}")
            commits = get_commits_since(last_tag)
            bump_type = detect_bump_type(commits) if commits else "patch"

        new_version = bump_version(major, minor, patch, bump_type)
        print(f"\nBump type: {bump_type}")
        print(f"New version: {new_version}")

        if args.dry_run:
            print("\n[dry-run] Would update:")
            for _, path, _ in all_files:
                print(f"  {path.relative_to(repo_root)}")
            return

        # Update all files
        print("\nUpdating files:")
        for old_ver, path, file_type in all_files:
            update_version_file(path, file_type, old_ver, new_version)
            print(f"  ✓ {path.relative_to(repo_root)}")

        if args.tag:
            create_git_tag(new_version)

        print(f"\n✓ All {len(all_files)} version file(s) synced to {new_version}")
        return

    # Normal mode: single file
    current_version, version_file, file_type = get_current_version(repo_root, args.path)
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
