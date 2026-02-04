#!/usr/bin/env python3
"""
pr-create.py — Create a PR with auto-generated title and description.

Uses pr-describe.py to generate PR content, then calls gh pr create.

Examples:
    pr-create.py                              # Create PR for current branch
    pr-create.py --base develop               # Target different base branch
    pr-create.py --draft                      # Create as draft PR
    pr-create.py --dry-run                    # Show what would be created
    pr-create.py --sync --branch fix/my-feat  # Sync main, create branch, then work
    pr-create.py --sync --branch fix/foo --base develop  # Sync from develop
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


def branch_exists(repo_path: Path, branch: str) -> bool:
    """Check if a local branch already exists."""
    code, _, _ = run(["git", "show-ref", "--verify", f"refs/heads/{branch}"], cwd=repo_path)
    return code == 0


def has_uncommitted_changes(repo_path: Path) -> bool:
    """Check if there are uncommitted changes (staged or unstaged)."""
    code, stdout, _ = run(["git", "status", "--porcelain"], cwd=repo_path)
    return code == 0 and bool(stdout.strip())


def sync_branch(repo_path: Path, base_branch: str, new_branch: str) -> bool:
    """
    Sync with base branch and create a new feature branch.

    Steps:
    1. Stash any uncommitted changes
    2. Checkout base branch
    3. Pull latest from origin
    4. Create and checkout new branch
    5. Pop stash if there was one

    Returns True on success, exits on failure.
    """
    had_stash = False

    # Step 1: Stash uncommitted changes if any
    if has_uncommitted_changes(repo_path):
        print("Stashing uncommitted changes...", file=sys.stderr)
        code, _, stderr = run(["git", "stash", "push", "-m", "pr-create-sync"], cwd=repo_path)
        if code != 0:
            print(f"Error: Failed to stash changes: {stderr}", file=sys.stderr)
            sys.exit(1)
        had_stash = True

    # Step 2: Checkout base branch
    print(f"Checking out {base_branch}...", file=sys.stderr)
    code, _, stderr = run(["git", "checkout", base_branch], cwd=repo_path)
    if code != 0:
        print(f"Error: Failed to checkout {base_branch}: {stderr}", file=sys.stderr)
        if had_stash:
            print(
                "Note: Your changes are still stashed. Run 'git stash pop' to recover.",
                file=sys.stderr,
            )
        sys.exit(1)

    # Step 3: Pull latest from origin
    print(f"Pulling latest from origin/{base_branch}...", file=sys.stderr)
    code, _, stderr = run(["git", "pull", "origin", base_branch], cwd=repo_path)
    if code != 0:
        print(f"Error: Failed to pull from origin: {stderr}", file=sys.stderr)
        print("Hint: Check your network connection or remote configuration.", file=sys.stderr)
        if had_stash:
            print(
                "Note: Your changes are still stashed. Run 'git stash pop' to recover.",
                file=sys.stderr,
            )
        sys.exit(1)

    # Step 4: Create and checkout new branch
    print(f"Creating branch {new_branch}...", file=sys.stderr)
    code, _, stderr = run(["git", "checkout", "-b", new_branch], cwd=repo_path)
    if code != 0:
        print(f"Error: Failed to create branch {new_branch}: {stderr}", file=sys.stderr)
        if had_stash:
            print(
                "Note: Your changes are still stashed. Run 'git stash pop' to recover.",
                file=sys.stderr,
            )
        sys.exit(1)

    # Step 5: Pop stash if we had one
    if had_stash:
        print("Restoring stashed changes...", file=sys.stderr)
        code, _, stderr = run(["git", "stash", "pop"], cwd=repo_path)
        if code != 0:
            print(f"Warning: Failed to pop stash: {stderr}", file=sys.stderr)
            print("Your changes are still in stash. Run 'git stash pop' manually.", file=sys.stderr)
            # Don't exit - branch was created successfully

    print(f"✓ Ready to work on {new_branch}", file=sys.stderr)
    return True


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
  %(prog)s                              Create PR for current branch
  %(prog)s --base develop               Target different base branch
  %(prog)s --draft                      Create as draft PR
  %(prog)s --dry-run                    Show what would be created
  %(prog)s --sync --branch fix/my-feat  Sync main, create branch, then work
  %(prog)s --sync --branch fix/foo --base develop  Sync from develop
""",
    )
    parser.add_argument(
        "--base",
        metavar="BRANCH",
        help="base branch to target (default: main or master)",
    )
    parser.add_argument(
        "--branch",
        metavar="NAME",
        help="new branch name (required with --sync)",
    )
    parser.add_argument(
        "--sync",
        action="store_true",
        help="sync base branch and create new feature branch before working",
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

    # Validate --sync requires --branch
    if args.sync and not args.branch:
        print("Error: --sync requires --branch NAME", file=sys.stderr)
        print("Usage: pr-create.py --sync --branch <branch-name>", file=sys.stderr)
        sys.exit(1)

    repo_path = Path.cwd()

    # Check we're in a git repo
    code, _, _ = run(["git", "rev-parse", "--git-dir"], cwd=repo_path)
    if code != 0:
        print("Error: Not a git repository", file=sys.stderr)
        sys.exit(1)

    # Handle --sync mode: sync base branch and create new feature branch
    if args.sync:
        base_branch = args.base if args.base else get_default_branch(repo_path)

        # Check if branch already exists
        if branch_exists(repo_path, args.branch):
            print(f"Error: Branch '{args.branch}' already exists", file=sys.stderr)
            print(
                "Hint: Use a different branch name or delete the existing branch", file=sys.stderr
            )
            sys.exit(1)

        sync_branch(repo_path, base_branch, args.branch)
        # After sync, exit - user now works on the branch
        return

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
