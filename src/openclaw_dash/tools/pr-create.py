#!/usr/bin/env python3
"""
pr-create.py — Create a PR with auto-generated title and description.

Uses pr-describe.py to generate PR content, then calls gh pr create.

Examples:
    pr-create.py                    # Create PR for current branch
    pr-create.py --base develop     # Target different base branch
    pr-create.py --draft            # Create as draft PR
    pr-create.py --dry-run          # Show what would be created
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def run(cmd: list[str], cwd: Path | None = None) -> tuple[int, str, str]:
    """Run a command and return (returncode, stdout, stderr)."""
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd, timeout=120)
        return result.returncode, result.stdout.strip(), result.stderr.strip()
    except subprocess.TimeoutExpired:
        return -1, "", "Command timed out"
    except Exception as e:
        return -1, "", str(e)


def get_current_branch(repo_path: Path) -> str:
    """Get the current git branch name."""
    code, stdout, _ = run(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=repo_path)
    return stdout if code == 0 else "HEAD"


def get_default_branch(repo_path: Path) -> str:
    """Get the default branch (main or master)."""
    code, _, _ = run(["git", "show-ref", "--verify", "refs/heads/main"], cwd=repo_path)
    if code == 0:
        return "main"

    code, _, _ = run(["git", "show-ref", "--verify", "refs/heads/master"], cwd=repo_path)
    if code == 0:
        return "master"

    return "main"


def check_gh_cli() -> bool:
    """Check if gh CLI is available and authenticated."""
    code, _, _ = run(["gh", "auth", "status"])
    return code == 0


def check_existing_pr(repo_path: Path, branch: str) -> str | None:
    """Check if PR already exists for this branch. Returns PR URL if exists."""
    code, stdout, _ = run(
        ["gh", "pr", "view", branch, "--json", "url", "-q", ".url"], cwd=repo_path
    )
    return stdout if code == 0 and stdout else None


def get_pr_description(repo_path: Path, base: str) -> tuple[str, str]:
    """
    Get PR title and body using pr-describe.py.

    Returns (title, body) tuple.
    """
    # Find pr-describe.py relative to this script
    script_dir = Path(__file__).parent
    pr_describe = script_dir / "pr-describe.py"

    if not pr_describe.exists():
        print(f"Error: pr-describe.py not found at {pr_describe}", file=sys.stderr)
        sys.exit(1)

    # Get title
    code, title, stderr = run(
        [sys.executable, str(pr_describe), "--base", base, "--title"],
        cwd=repo_path,
    )
    if code != 0:
        print(f"Error generating PR title: {stderr}", file=sys.stderr)
        sys.exit(1)

    # Get body (markdown format, concise style)
    code, body, stderr = run(
        [sys.executable, str(pr_describe), "--base", base, "--style", "concise"],
        cwd=repo_path,
    )
    if code != 0:
        print(f"Error generating PR body: {stderr}", file=sys.stderr)
        sys.exit(1)

    return title, body


def create_pr(
    repo_path: Path,
    title: str,
    body: str,
    base: str,
    draft: bool = False,
) -> tuple[bool, str]:
    """
    Create PR using gh CLI.

    Returns (success, url_or_error).
    """
    cmd = ["gh", "pr", "create", "--title", title, "--body", body, "--base", base]

    if draft:
        cmd.append("--draft")

    code, stdout, stderr = run(cmd, cwd=repo_path)

    if code == 0:
        return True, stdout
    else:
        return False, stderr


def main():
    parser = argparse.ArgumentParser(
        description=__doc__.split("\n\n")[0],
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                    Create PR for current branch
  %(prog)s --base develop     Target different base branch
  %(prog)s --draft            Create as draft PR
  %(prog)s --dry-run          Show what would be created
""",
    )
    parser.add_argument(
        "--base",
        metavar="BRANCH",
        help="base branch to target (default: main or master)",
    )
    parser.add_argument(
        "--draft",
        action="store_true",
        help="create PR as draft",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="show what would be created without creating",
    )

    args = parser.parse_args()

    repo_path = Path.cwd()

    # Check we're in a git repo
    code, _, _ = run(["git", "rev-parse", "--git-dir"], cwd=repo_path)
    if code != 0:
        print("Error: Not a git repository", file=sys.stderr)
        sys.exit(1)

    # Check gh CLI
    if not args.dry_run and not check_gh_cli():
        print("Error: gh CLI not authenticated. Run: gh auth login", file=sys.stderr)
        sys.exit(1)

    # Get branches
    base_branch = args.base if args.base else get_default_branch(repo_path)
    head_branch = get_current_branch(repo_path)

    if base_branch == head_branch:
        print(f"Error: Cannot create PR from {head_branch} to itself", file=sys.stderr)
        print("Hint: Checkout a feature branch first", file=sys.stderr)
        sys.exit(1)

    # Check for existing PR
    if not args.dry_run:
        existing_url = check_existing_pr(repo_path, head_branch)
        if existing_url:
            print(f"PR already exists: {existing_url}", file=sys.stderr)
            sys.exit(1)

    # Generate title and body
    print(f"Generating PR description for {head_branch} → {base_branch}...", file=sys.stderr)
    title, body = get_pr_description(repo_path, base_branch)

    # Dry run - show what would be created
    if args.dry_run:
        print("\n" + "=" * 60)
        print("DRY RUN - Would create PR with:")
        print("=" * 60)
        print(f"\nBranch: {head_branch} → {base_branch}")
        print(f"Draft: {args.draft}")
        print(f"\nTitle: {title}")
        print("\nBody:")
        print("-" * 60)
        print(body)
        print("-" * 60)
        return

    # Create PR
    print("Creating PR...", file=sys.stderr)
    success, result = create_pr(repo_path, title, body, base_branch, draft=args.draft)

    if success:
        print(result)  # Print the PR URL
    else:
        print(f"Error creating PR: {result}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
