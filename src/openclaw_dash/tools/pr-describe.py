#!/usr/bin/env python3
"""
pr-describe.py — Generate structured PR descriptions from git diffs.

Features:
- Analyze git diff between branches
- Infer intent from commit messages
- Categorize changed files (added, modified, removed)
- Suggest testing scenarios
- Flag breaking changes, new dependencies, config changes

Usage:
    python3 pr-describe.py [branch]              # Current branch vs main
    python3 pr-describe.py --base develop        # Compare against develop
    python3 pr-describe.py --json                # Output as JSON
    python3 pr-describe.py --clipboard           # Copy to clipboard

Module usage:
    from pr_describe import generate_pr_description
    desc = generate_pr_description("/path/to/repo", "main", "feature-branch")
"""

import json
import re
import subprocess
import sys
from collections import defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path

# File categorization patterns
FILE_CATEGORIES = {
    "tests": [r"test_", r"_test\.", r"\.test\.", r"tests/", r"__tests__/", r"spec/"],
    "docs": [r"\.md$", r"docs/", r"README", r"CHANGELOG", r"\.rst$"],
    "config": [
        r"\.json$",
        r"\.ya?ml$",
        r"\.toml$",
        r"\.ini$",
        r"\.env",
        r"Makefile",
        r"Dockerfile",
    ],
    "deps": [
        r"requirements",
        r"package\.json$",
        r"package-lock\.json$",
        r"pyproject\.toml$",
        r"poetry\.lock$",
        r"Cargo\.toml$",
    ],
    "ci": [r"\.github/", r"\.gitlab-ci", r"\.circleci/", r"Jenkinsfile", r"\.travis"],
}

# Breaking change indicators
BREAKING_PATTERNS = [
    r"BREAKING",
    r"breaking change",
    r"incompatible",
    r"removed?\s+(api|endpoint|function|method|class)",
    r"renamed?\s+(api|endpoint|function|method|class)",
    r"changed?\s+signature",
    r"deprecated",
]

# Dependency patterns
DEP_FILES = [
    "requirements.txt",
    "requirements-dev.txt",
    "pyproject.toml",
    "package.json",
    "Cargo.toml",
]


@dataclass
class FileChange:
    path: str
    status: str  # A=added, M=modified, D=deleted, R=renamed
    additions: int = 0
    deletions: int = 0
    category: str = "source"


@dataclass
class CommitInfo:
    hash: str
    subject: str
    body: str = ""


@dataclass
class PRDescription:
    summary: str
    changes: dict[str, list[str]]
    testing: list[str]
    notes: list[str]
    commits: list[CommitInfo]
    stats: dict[str, int]


def run(cmd: str, cwd: Path | None = None) -> tuple[int, str, str]:
    """Run a shell command and return (returncode, stdout, stderr)."""
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, cwd=cwd, timeout=60
        )
        return result.returncode, result.stdout.strip(), result.stderr.strip()
    except subprocess.TimeoutExpired:
        return -1, "", "Command timed out"
    except Exception as e:
        return -1, "", str(e)


def get_current_branch(repo_path: Path) -> str:
    """Get the current git branch name."""
    code, stdout, _ = run("git rev-parse --abbrev-ref HEAD", cwd=repo_path)
    return stdout if code == 0 else "HEAD"


def get_default_branch(repo_path: Path) -> str:
    """Get the default branch (main or master)."""
    # Try main first
    code, _, _ = run("git show-ref --verify refs/heads/main", cwd=repo_path)
    if code == 0:
        return "main"

    # Fall back to master
    code, _, _ = run("git show-ref --verify refs/heads/master", cwd=repo_path)
    if code == 0:
        return "master"

    # Try to get from remote
    code, stdout, _ = run(
        "git remote show origin 2>/dev/null | grep 'HEAD branch' | cut -d: -f2", cwd=repo_path
    )
    if code == 0 and stdout.strip():
        return stdout.strip()

    return "main"


def get_commits(repo_path: Path, base: str, head: str) -> list[CommitInfo]:
    """Get commits between base and head branches."""
    # Format: hash|||subject|||body
    code, stdout, _ = run(
        f'git log {base}..{head} --format="%H|||%s|||%b---COMMIT---"', cwd=repo_path
    )

    if code != 0 or not stdout:
        return []

    commits = []
    for entry in stdout.split("---COMMIT---"):
        entry = entry.strip()
        if not entry:
            continue
        parts = entry.split("|||", 2)
        if len(parts) >= 2:
            commits.append(
                CommitInfo(
                    hash=parts[0][:8],
                    subject=parts[1].strip(),
                    body=parts[2].strip() if len(parts) > 2 else "",
                )
            )

    return commits


def get_changed_files(repo_path: Path, base: str, head: str) -> list[FileChange]:
    """Get list of changed files with status."""
    # Get file statuses
    code, stdout, _ = run(f"git diff {base}...{head} --name-status", cwd=repo_path)

    if code != 0:
        return []

    files = []
    for line in stdout.split("\n"):
        if not line.strip():
            continue
        parts = line.split("\t")
        if len(parts) >= 2:
            status = parts[0][0]  # First char: A, M, D, R, etc.
            filepath = parts[-1]  # Last part is the path (handles renames)

            files.append(
                FileChange(path=filepath, status=status, category=categorize_file(filepath))
            )

    # Get numstat for additions/deletions
    code, stdout, _ = run(f"git diff {base}...{head} --numstat", cwd=repo_path)

    if code == 0 and stdout:
        numstat = {}
        for line in stdout.split("\n"):
            parts = line.split("\t")
            if len(parts) == 3:
                adds = int(parts[0]) if parts[0] != "-" else 0
                dels = int(parts[1]) if parts[1] != "-" else 0
                numstat[parts[2]] = (adds, dels)

        for f in files:
            if f.path in numstat:
                f.additions, f.deletions = numstat[f.path]

    return files


def categorize_file(filepath: str) -> str:
    """Categorize a file based on its path and name."""
    filepath_lower = filepath.lower()

    for category, patterns in FILE_CATEGORIES.items():
        for pattern in patterns:
            if re.search(pattern, filepath_lower):
                return category

    return "source"


def detect_breaking_changes(commits: list[CommitInfo], diff_text: str) -> list[str]:
    """Detect potential breaking changes from commits and diff."""
    breaking = []

    # Check commit messages
    for commit in commits:
        full_msg = f"{commit.subject} {commit.body}".lower()
        for pattern in BREAKING_PATTERNS:
            if re.search(pattern, full_msg, re.IGNORECASE):
                breaking.append(f"Commit {commit.hash}: {commit.subject}")
                break

    # Check diff for API changes (function/class removals)
    removed_defs = re.findall(r"^-\s*(def|class|function|export)\s+(\w+)", diff_text, re.MULTILINE)
    for kind, name in removed_defs:
        breaking.append(f"Removed {kind} `{name}`")

    return list(set(breaking))[:5]  # Dedupe and limit


def detect_new_dependencies(
    repo_path: Path, base: str, head: str, files: list[FileChange]
) -> list[str]:
    """Detect new dependencies added."""
    new_deps = []

    dep_changes = [f for f in files if f.category == "deps"]

    for dep_file in dep_changes:
        code, stdout, _ = run(f'git diff {base}...{head} -- "{dep_file.path}"', cwd=repo_path)

        if code != 0:
            continue

        # Python requirements
        if "requirements" in dep_file.path:
            for match in re.finditer(r"^\+([a-zA-Z0-9_-]+)", stdout, re.MULTILINE):
                pkg = match.group(1)
                if not pkg.startswith("#") and pkg not in ["#", "-r", "-e"]:
                    new_deps.append(f"pip: {pkg}")

        # package.json
        if "package.json" in dep_file.path:
            # Look for added lines in dependencies sections
            for match in re.finditer(r'^\+\s*"([^"]+)":\s*"([^"]+)"', stdout, re.MULTILINE):
                new_deps.append(f"npm: {match.group(1)}@{match.group(2)}")

        # pyproject.toml
        if "pyproject.toml" in dep_file.path:
            for match in re.finditer(r'^\+\s*"?([a-zA-Z0-9_-]+)', stdout, re.MULTILINE):
                pkg = match.group(1)
                if pkg and not pkg.startswith("["):
                    new_deps.append(f"pip: {pkg}")

    return list(set(new_deps))[:10]


def detect_config_changes(files: list[FileChange]) -> list[str]:
    """Detect config file changes."""
    config_files = [f for f in files if f.category in ("config", "ci")]

    changes = []
    for f in config_files[:10]:
        action = {"A": "Added", "M": "Modified", "D": "Removed"}.get(f.status, "Changed")
        changes.append(f"{action} `{f.path}`")

    return changes


def generate_summary(commits: list[CommitInfo], files: list[FileChange]) -> str:
    """Generate a summary based on commits and file changes."""
    if not commits:
        return "No commits found in this branch."

    # Use the main commit messages to form summary
    if len(commits) == 1:
        summary = commits[0].subject
        if commits[0].body:
            summary += f"\n\n{commits[0].body}"
        return summary

    # Multiple commits - create a bulleted summary
    lines = []

    # Try to find the overall theme
    all_subjects = " ".join(c.subject for c in commits).lower()

    if "fix" in all_subjects:
        lines.append("This PR includes bug fixes and improvements:")
    elif "feat" in all_subjects or "add" in all_subjects:
        lines.append("This PR adds new features and functionality:")
    elif "refactor" in all_subjects:
        lines.append("This PR refactors existing code:")
    elif "docs" in all_subjects:
        lines.append("This PR updates documentation:")
    else:
        lines.append("This PR includes the following changes:")

    lines.append("")

    for commit in commits[:7]:  # Limit to 7 commits
        # Clean up conventional commit prefixes
        subject = commit.subject
        subject = re.sub(
            r"^(feat|fix|docs|style|refactor|test|chore|ci|perf|build)(\([^)]+\))?:\s*", "", subject
        )
        lines.append(f"- {subject}")

    if len(commits) > 7:
        lines.append(f"- ... and {len(commits) - 7} more commits")

    return "\n".join(lines)


def generate_testing_suggestions(files: list[FileChange], commits: list[CommitInfo]) -> list[str]:
    """Generate testing suggestions based on changed code paths."""
    suggestions = []

    # Group files by type
    by_category = defaultdict(list)
    for f in files:
        by_category[f.category].append(f)

    # Source code changes
    source_files = by_category.get("source", [])
    if source_files:
        # Identify modules/components changed
        modules = set()
        for f in source_files:
            parts = Path(f.path).parts
            if len(parts) > 1:
                modules.add(parts[0])
            else:
                modules.add(Path(f.path).stem)

        if modules:
            suggestions.append(f"Run unit tests for: {', '.join(list(modules)[:5])}")

    # API/endpoint changes
    api_files = [
        f
        for f in source_files
        if any(x in f.path.lower() for x in ["api", "route", "endpoint", "view", "controller"])
    ]
    if api_files:
        suggestions.append("Test API endpoints for request/response changes")

    # Test file changes
    test_files = by_category.get("tests", [])
    if test_files:
        suggestions.append("Review and run updated tests")
    elif source_files:
        suggestions.append("Consider adding tests for new functionality")

    # Config changes
    config_files = by_category.get("config", [])
    if config_files:
        suggestions.append("Verify configuration changes in development environment")

    # Database/migration files
    db_files = [
        f
        for f in files
        if any(x in f.path.lower() for x in ["migration", "schema", "model", "database"])
    ]
    if db_files:
        suggestions.append("Test database migrations on staging data")

    # Frontend changes
    frontend_files = [
        f for f in source_files if any(x in f.path for x in [".tsx", ".jsx", ".vue", ".svelte"])
    ]
    if frontend_files:
        suggestions.append("Visual regression testing for UI changes")

    # Performance-related
    perf_commits = [
        c for c in commits if "perf" in c.subject.lower() or "optim" in c.subject.lower()
    ]
    if perf_commits:
        suggestions.append("Benchmark performance changes")

    return suggestions[:6] if suggestions else ["Run full test suite"]


def get_diff_text(repo_path: Path, base: str, head: str) -> str:
    """Get the full diff text."""
    code, stdout, _ = run(f"git diff {base}...{head}", cwd=repo_path)
    return stdout if code == 0 else ""


def generate_pr_description(repo_path: str | Path, base_branch: str, head_branch: str) -> str:
    """
    Generate a PR description for the given branches.

    This is the main module API for use by other tools (e.g., dep-shepherd).

    Args:
        repo_path: Path to the git repository
        base_branch: The target branch (e.g., "main")
        head_branch: The source branch (e.g., "feature-xyz")

    Returns:
        Formatted markdown PR description
    """
    repo_path = Path(repo_path)

    # Gather data
    commits = get_commits(repo_path, base_branch, head_branch)
    files = get_changed_files(repo_path, base_branch, head_branch)
    diff_text = get_diff_text(repo_path, base_branch, head_branch)

    # Analyze
    summary = generate_summary(commits, files)
    testing = generate_testing_suggestions(files, commits)

    breaking = detect_breaking_changes(commits, diff_text)
    new_deps = detect_new_dependencies(repo_path, base_branch, head_branch, files)
    config_changes = detect_config_changes(files)

    # Group files by status
    changes = {
        "added": [f.path for f in files if f.status == "A"],
        "modified": [f.path for f in files if f.status == "M"],
        "removed": [f.path for f in files if f.status == "D"],
        "renamed": [f.path for f in files if f.status == "R"],
    }

    # Build notes
    notes = []
    if breaking:
        notes.append("⚠️ **Breaking Changes:**")
        for b in breaking:
            notes.append(f"  - {b}")
    if new_deps:
        notes.append("📦 **New Dependencies:**")
        for d in new_deps:
            notes.append(f"  - {d}")
    if config_changes:
        notes.append("⚙️ **Configuration Changes:**")
        for c in config_changes:
            notes.append(f"  - {c}")

    # Stats
    stats = {
        "files_changed": len(files),
        "additions": sum(f.additions for f in files),
        "deletions": sum(f.deletions for f in files),
        "commits": len(commits),
    }

    # Format markdown
    return format_markdown(
        PRDescription(
            summary=summary,
            changes=changes,
            testing=testing,
            notes=notes,
            commits=[asdict(c) for c in commits],
            stats=stats,
        )
    )


def format_markdown(desc: PRDescription) -> str:
    """Format PRDescription as markdown."""
    lines = []

    # Summary
    lines.append("## Summary")
    lines.append("")
    lines.append(desc.summary)
    lines.append("")

    # Changes
    lines.append("## Changes")
    lines.append("")

    if desc.changes.get("added"):
        lines.append("**Added:**")
        for f in desc.changes["added"][:15]:
            lines.append(f"- `{f}`")
        if len(desc.changes["added"]) > 15:
            lines.append(f"- ... and {len(desc.changes['added']) - 15} more")
        lines.append("")

    if desc.changes.get("modified"):
        lines.append("**Modified:**")
        for f in desc.changes["modified"][:15]:
            lines.append(f"- `{f}`")
        if len(desc.changes["modified"]) > 15:
            lines.append(f"- ... and {len(desc.changes['modified']) - 15} more")
        lines.append("")

    if desc.changes.get("removed"):
        lines.append("**Removed:**")
        for f in desc.changes["removed"][:10]:
            lines.append(f"- `{f}`")
        if len(desc.changes["removed"]) > 10:
            lines.append(f"- ... and {len(desc.changes['removed']) - 10} more")
        lines.append("")

    if desc.changes.get("renamed"):
        lines.append("**Renamed:**")
        for f in desc.changes["renamed"][:10]:
            lines.append(f"- `{f}`")
        lines.append("")

    # Testing
    lines.append("## Testing")
    lines.append("")
    for t in desc.testing:
        lines.append(f"- [ ] {t}")
    lines.append("")

    # Notes (if any)
    if desc.notes:
        lines.append("## Notes")
        lines.append("")
        for note in desc.notes:
            lines.append(note)
        lines.append("")

    # Stats footer
    lines.append("---")
    lines.append(
        f"*{desc.stats['commits']} commits, {desc.stats['files_changed']} files changed (+{desc.stats['additions']}/-{desc.stats['deletions']})*"
    )

    return "\n".join(lines)


def format_json(desc: PRDescription) -> str:
    """Format PRDescription as JSON."""
    return json.dumps(asdict(desc), indent=2)


def copy_to_clipboard(text: str) -> bool:
    """Copy text to clipboard. Returns True on success."""
    # Try pbcopy (macOS)
    code, _, _ = run("which pbcopy")
    if code == 0:
        proc = subprocess.Popen(["pbcopy"], stdin=subprocess.PIPE)
        proc.communicate(text.encode())
        return proc.returncode == 0

    # Try xclip (Linux)
    code, _, _ = run("which xclip")
    if code == 0:
        proc = subprocess.Popen(["xclip", "-selection", "clipboard"], stdin=subprocess.PIPE)
        proc.communicate(text.encode())
        return proc.returncode == 0

    # Try xsel (Linux)
    code, _, _ = run("which xsel")
    if code == 0:
        proc = subprocess.Popen(["xsel", "--clipboard", "--input"], stdin=subprocess.PIPE)
        proc.communicate(text.encode())
        return proc.returncode == 0

    return False


def main():
    # Parse arguments
    output_json = "--json" in sys.argv
    to_clipboard = "--clipboard" in sys.argv

    # Get base branch
    base_branch = None
    if "--base" in sys.argv:
        idx = sys.argv.index("--base")
        if idx + 1 < len(sys.argv):
            base_branch = sys.argv[idx + 1]

    # Get head branch (positional arg, not a flag)
    head_branch = None
    for arg in sys.argv[1:]:
        if not arg.startswith("-") and arg != base_branch:
            head_branch = arg
            break

    # Default to current directory
    repo_path = Path.cwd()

    # Check if we're in a git repo
    code, _, _ = run("git rev-parse --git-dir", cwd=repo_path)
    if code != 0:
        print("Error: Not a git repository", file=sys.stderr)
        sys.exit(1)

    # Determine branches
    if not base_branch:
        base_branch = get_default_branch(repo_path)

    if not head_branch:
        head_branch = get_current_branch(repo_path)

    # Check if branches are the same
    if base_branch == head_branch:
        print(f"Error: base and head are the same branch ({base_branch})", file=sys.stderr)
        print("Hint: checkout a feature branch or specify --base <branch>", file=sys.stderr)
        sys.exit(1)

    # Check if there are commits
    code, stdout, _ = run(f"git rev-list {base_branch}..{head_branch} --count", cwd=repo_path)
    if code != 0 or stdout == "0":
        print(f"Error: No commits between {base_branch} and {head_branch}", file=sys.stderr)
        sys.exit(1)

    print(f"Analyzing {head_branch} vs {base_branch}...", file=sys.stderr)

    # Generate description
    output = generate_pr_description(repo_path, base_branch, head_branch)

    # Handle JSON output
    if output_json:
        commits = get_commits(repo_path, base_branch, head_branch)
        files = get_changed_files(repo_path, base_branch, head_branch)
        diff_text = get_diff_text(repo_path, base_branch, head_branch)

        summary = generate_summary(commits, files)
        testing = generate_testing_suggestions(files, commits)
        breaking = detect_breaking_changes(commits, diff_text)
        new_deps = detect_new_dependencies(repo_path, base_branch, head_branch, files)
        config_changes = detect_config_changes(files)

        changes = {
            "added": [f.path for f in files if f.status == "A"],
            "modified": [f.path for f in files if f.status == "M"],
            "removed": [f.path for f in files if f.status == "D"],
            "renamed": [f.path for f in files if f.status == "R"],
        }

        notes = []
        if breaking:
            notes.extend([f"Breaking: {b}" for b in breaking])
        if new_deps:
            notes.extend([f"New dep: {d}" for d in new_deps])
        if config_changes:
            notes.extend([f"Config: {c}" for c in config_changes])

        stats = {
            "files_changed": len(files),
            "additions": sum(f.additions for f in files),
            "deletions": sum(f.deletions for f in files),
            "commits": len(commits),
        }

        desc = PRDescription(
            summary=summary,
            changes=changes,
            testing=testing,
            notes=notes,
            commits=[asdict(c) for c in commits],
            stats=stats,
        )
        output = format_json(desc)

    # Copy to clipboard if requested
    if to_clipboard:
        if copy_to_clipboard(output):
            print("✅ Copied to clipboard!", file=sys.stderr)
        else:
            print("⚠️  Could not copy to clipboard (pbcopy/xclip not found)", file=sys.stderr)

    print(output)


if __name__ == "__main__":
    main()
