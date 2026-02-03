#!/usr/bin/env python3
"""
pr-describe.py — Generate structured PR descriptions from git diffs.

Analyzes git diff between branches, infers intent from commit messages,
categorizes changes, and flags breaking changes or new dependencies.

Examples:
    pr-describe.py                      # Current branch vs main
    pr-describe.py feature-xyz          # Compare feature-xyz vs main
    pr-describe.py --base develop       # Compare against develop
    pr-describe.py --format json        # Output as JSON
    pr-describe.py --clipboard          # Copy to clipboard
    pr-describe.py --title              # Just output suggested PR title
    pr-describe.py --include-comments   # Include existing PR discussion

Module usage:
    from pr_describe import generate_pr_description
    desc = generate_pr_description("/path/to/repo", "main", "feature-branch")
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from pathlib import Path

# Try to import yaml, fall back gracefully
try:
    import yaml

    HAS_YAML = True
except ImportError:
    HAS_YAML = False

# Config file location
CONFIG_DIR = Path.home() / ".config" / "openclaw-dash"
CONFIG_FILE = CONFIG_DIR / "pr-describe.yaml"

# Default configuration
DEFAULT_CONFIG = {
    "output_style": "verbose",  # verbose|concise|minimal
    "include_testing": True,
    "include_breaking_changes": True,
    "title_format": "{type}: {summary}",  # Template for PR titles
    "max_files_shown": 15,
    "max_commits_shown": 7,
}

# Conventional commit types
COMMIT_TYPES = {
    "feat": "feature",
    "fix": "fix",
    "docs": "docs",
    "style": "style",
    "refactor": "refactor",
    "test": "test",
    "chore": "chore",
    "ci": "ci",
    "perf": "perf",
    "build": "build",
    "revert": "revert",
}

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


@dataclass
class Config:
    """Configuration for pr-describe."""

    output_style: str = "verbose"
    include_testing: bool = True
    include_breaking_changes: bool = True
    title_format: str = "{type}: {summary}"
    max_files_shown: int = 15
    max_commits_shown: int = 7


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
    commit_type: str = ""  # feat, fix, etc.
    scope: str = ""  # Optional scope from conventional commits


@dataclass
class PRComment:
    author: str
    body: str
    created_at: str = ""


@dataclass
class PRDescription:
    summary: str
    changes: dict[str, list[str]]
    testing: list[str]
    notes: list[str]
    commits: list[CommitInfo | dict]
    stats: dict[str, int]
    title: str = ""
    comments: list[PRComment] = field(default_factory=list)


def load_config() -> Config:
    """Load configuration from file, creating defaults if needed."""
    config_dict = DEFAULT_CONFIG.copy()

    if CONFIG_FILE.exists() and HAS_YAML:
        try:
            with open(CONFIG_FILE) as f:
                user_config = yaml.safe_load(f) or {}
                config_dict.update(user_config)
        except Exception:
            pass  # Use defaults on error

    return Config(**config_dict)


def ensure_config_exists() -> None:
    """Create config file with defaults if it doesn't exist."""
    if not HAS_YAML:
        return

    if not CONFIG_FILE.exists():
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_FILE, "w") as f:
            yaml.dump(DEFAULT_CONFIG, f, default_flow_style=False, sort_keys=False)


def run(cmd: list[str], cwd: Path | None = None) -> tuple[int, str, str]:
    """Run a command and return (returncode, stdout, stderr)."""
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd, timeout=60)
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
    # Try main first
    code, _, _ = run(["git", "show-ref", "--verify", "refs/heads/main"], cwd=repo_path)
    if code == 0:
        return "main"

    # Fall back to master
    code, _, _ = run(["git", "show-ref", "--verify", "refs/heads/master"], cwd=repo_path)
    if code == 0:
        return "master"

    # Try to get from remote
    code, stdout, _ = run(["git", "remote", "show", "origin"], cwd=repo_path)
    if code == 0 and stdout:
        for line in stdout.split("\n"):
            if "HEAD branch" in line:
                return line.split(":")[-1].strip()

    return "main"


def parse_conventional_commit(subject: str) -> tuple[str, str, str]:
    """
    Parse a conventional commit message.

    Returns (type, scope, summary) where type and scope may be empty.
    """
    # Pattern: type(scope): summary or type: summary
    match = re.match(r"^(\w+)(?:\(([^)]+)\))?:\s*(.+)$", subject)
    if match:
        commit_type = match.group(1).lower()
        scope = match.group(2) or ""
        summary = match.group(3)
        if commit_type in COMMIT_TYPES:
            return commit_type, scope, summary
    return "", "", subject


def get_commits(repo_path: Path, base: str, head: str) -> list[CommitInfo]:
    """Get commits between base and head branches."""
    # Format: hash|||subject|||body
    code, stdout, _ = run(
        ["git", "log", f"{base}..{head}", "--format=%H|||%s|||%b---COMMIT---"], cwd=repo_path
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
            subject = parts[1].strip()
            commit_type, scope, _ = parse_conventional_commit(subject)
            commits.append(
                CommitInfo(
                    hash=parts[0][:8],
                    subject=subject,
                    body=parts[2].strip() if len(parts) > 2 else "",
                    commit_type=commit_type,
                    scope=scope,
                )
            )

    return commits


def get_changed_files(repo_path: Path, base: str, head: str) -> list[FileChange]:
    """Get list of changed files with status."""
    # Get file statuses
    code, stdout, _ = run(["git", "diff", f"{base}...{head}", "--name-status"], cwd=repo_path)

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
    code, stdout, _ = run(["git", "diff", f"{base}...{head}", "--numstat"], cwd=repo_path)

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
        code, stdout, _ = run(
            ["git", "diff", f"{base}...{head}", "--", dep_file.path], cwd=repo_path
        )

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


def _extract_key_words(text: str) -> list[str]:
    """Extract meaningful words from text, filtering stop words."""
    stop_words = {
        "the",
        "a",
        "an",
        "to",
        "for",
        "in",
        "on",
        "at",
        "by",
        "with",
        "and",
        "or",
        "of",
        "from",
        "is",
        "be",
        "was",
        "were",
        "been",
        "this",
        "that",
        "it",
        "its",
        "as",
        "if",
        "when",
        "also",
        "into",
        "some",
        "all",
        "more",
        "new",
        "change",
        "changes",
        "update",
        "updates",
    }
    words = re.findall(r"\b[a-zA-Z][a-zA-Z0-9_-]*\b", text.lower())
    return [w for w in words if w not in stop_words and len(w) > 2]


def _build_multi_commit_summary(summaries: list[str], scopes: set[str]) -> str:
    """
    Build a meaningful summary from multiple commit summaries.

    Strategy:
    1. If there's a single summary, use it
    2. If all commits share a scope, describe improvements to that scope
    3. Find common words across summaries for a theme
    4. Fall back to listing first few key changes
    """
    if not summaries:
        return "various updates"

    # Clean up summaries
    clean_summaries = [s.strip() for s in summaries if s.strip()]
    if not clean_summaries:
        return "various updates"

    if len(clean_summaries) == 1:
        return clean_summaries[0][:60]

    # If all commits share a single scope, that's a strong signal
    if len(scopes) == 1:
        scope = list(scopes)[0]
        # Try to find common action words
        words_per_summary = [set(_extract_key_words(s)) for s in clean_summaries]
        if words_per_summary:
            common = set.intersection(*words_per_summary)
            if common:
                key_word = sorted(common, key=len, reverse=True)[0]
                return f"{key_word} {scope}"
        return f"{scope} improvements"

    # Find words common to all summaries
    words_per_summary = [set(_extract_key_words(s)) for s in clean_summaries]
    if len(words_per_summary) > 1:
        common = set.intersection(*words_per_summary)
        if common:
            # Use the longest common word as the theme
            key_words = sorted(common, key=len, reverse=True)[:2]
            return " and ".join(key_words) + " updates"

    # Find words that appear in multiple (but not all) summaries
    word_counts: dict[str, int] = defaultdict(int)
    for word_set in words_per_summary:
        for word in word_set:
            word_counts[word] += 1

    # Words appearing in at least half the summaries
    threshold = max(2, len(clean_summaries) // 2)
    frequent = [w for w, c in word_counts.items() if c >= threshold]
    if frequent:
        key_words = sorted(frequent, key=lambda w: word_counts[w], reverse=True)[:2]
        return " and ".join(key_words) + " updates"

    # Last resort: list first two changes briefly
    short_summaries = []
    total_len = 0
    for s in clean_summaries:
        # Take first few words of each summary
        words = s.split()[:4]
        short_text = " ".join(words)
        if len(short_text) > 25:
            short_text = short_text[:22] + "..."
        if total_len + len(short_text) > 50:
            break
        short_summaries.append(short_text)
        total_len += len(short_text) + 2  # account for ", "

    if short_summaries:
        return ", ".join(short_summaries)

    # Absolute last resort: use first summary truncated
    return clean_summaries[0][:60]


def generate_pr_title(commits: list[CommitInfo], config: Config) -> str:
    """
    Generate a PR title from commits using conventional commit format.

    Strategy:
    - Single commit: use its subject directly
    - Multiple commits: extract meaningful description from commit messages
    - Never just count commits - always describe WHAT changed
    """
    if not commits:
        return "Untitled PR"

    # Count commit types
    type_counts: dict[str, int] = defaultdict(int)
    typed_commits = []
    for commit in commits:
        if commit.commit_type:
            type_counts[commit.commit_type] += 1
            typed_commits.append(commit)

    # Single commit - use it directly
    if len(commits) == 1:
        commit = commits[0]
        if commit.commit_type:
            _, _, summary = parse_conventional_commit(commit.subject)
            return config.title_format.format(
                type=commit.commit_type,
                scope=commit.scope or "",
                summary=summary.capitalize() if summary else "update",
            )
        return commit.subject

    # Multiple commits - find dominant type and build meaningful summary
    if type_counts:
        dominant_type = max(type_counts, key=lambda k: type_counts[k])

        # Collect scopes and summaries for the dominant type
        scopes = set()
        summaries = []
        for c in typed_commits:
            if c.commit_type == dominant_type:
                if c.scope:
                    scopes.add(c.scope)
                _, _, summary = parse_conventional_commit(c.subject)
                if summary:
                    summaries.append(summary.strip())

        # Build a descriptive summary (never just count commits)
        summary_text = _build_multi_commit_summary(summaries, scopes)
        scope_text = list(scopes)[0] if len(scopes) == 1 else ""

        return config.title_format.format(
            type=dominant_type,
            scope=scope_text,
            summary=summary_text,
        )

    # No conventional commits - use first commit subject
    return commits[0].subject


def generate_summary(commits: list[CommitInfo], files: list[FileChange], config: Config) -> str:
    """Generate a summary based on commits and file changes."""
    if not commits:
        return "No commits found in this branch."

    # Use the main commit messages to form summary
    if len(commits) == 1:
        summary = commits[0].subject
        if commits[0].body and config.output_style == "verbose":
            summary += f"\n\n{commits[0].body}"
        return summary

    # Multiple commits - list changes directly without intro fluff
    lines = []
    max_commits = config.max_commits_shown if config.output_style == "verbose" else 3

    for commit in commits[:max_commits]:
        # Clean up conventional commit prefixes
        subject = commit.subject
        subject = re.sub(
            r"^(feat|fix|docs|style|refactor|test|chore|ci|perf|build)(\([^)]+\))?:\s*", "", subject
        )
        lines.append(f"- {subject}")

    if len(commits) > max_commits:
        lines.append(f"- ... and {len(commits) - max_commits} more commits")

    return "\n".join(lines)


def generate_testing_suggestions(files: list[FileChange], commits: list[CommitInfo]) -> list[str]:
    """Generate actionable testing suggestions based on changed code paths."""
    suggestions = []

    # Group files by type
    by_category = defaultdict(list)
    for f in files:
        by_category[f.category].append(f)

    source_files = by_category.get("source", [])
    test_files = by_category.get("tests", [])

    # Test file changes - specific and actionable
    if test_files:
        test_paths = [f.path for f in test_files[:3]]
        suggestions.append(f"Run updated tests: `pytest {' '.join(test_paths)}`")

    # Source code changes - identify specific modules
    if source_files:
        modules = set()
        for f in source_files:
            parts = Path(f.path).parts
            if len(parts) > 1:
                modules.add(parts[0])
        if modules:
            module_list = list(modules)[:3]
            suggestions.append(f"Run tests for changed modules: `pytest {' '.join(module_list)}/`")

    # API/endpoint changes - actionable
    api_files = [
        f
        for f in source_files
        if any(x in f.path.lower() for x in ["api", "route", "endpoint", "view", "controller"])
    ]
    if api_files:
        endpoints = [Path(f.path).stem for f in api_files[:3]]
        suggestions.append(f"Verify API behavior for: {', '.join(endpoints)}")

    # Database/migration files - specific action
    db_files = [f for f in files if any(x in f.path.lower() for x in ["migration", "schema"])]
    if db_files:
        suggestions.append("Run migrations on fresh DB: `alembic upgrade head`")

    # Config changes - specific action
    config_files = by_category.get("config", [])
    if config_files:
        config_names = [Path(f.path).name for f in config_files[:3]]
        suggestions.append(f"Validate config: {', '.join(config_names)}")

    # Only return actionable suggestions, skip generic fallbacks
    return suggestions[:5]


def get_diff_text(repo_path: Path, base: str, head: str) -> str:
    """Get the full diff text."""
    code, stdout, _ = run(["git", "diff", f"{base}...{head}"], cwd=repo_path)
    return stdout if code == 0 else ""


def get_pr_comments(repo_path: Path, head_branch: str) -> list[PRComment]:
    """
    Get existing PR comments using gh CLI.

    Returns empty list if no PR exists or gh is not available.
    """
    # Check if gh is available
    code, _, _ = run(["which", "gh"])
    if code != 0:
        return []

    # Try to get PR number for this branch
    code, stdout, _ = run(
        ["gh", "pr", "view", head_branch, "--json", "comments"],
        cwd=repo_path,
    )

    if code != 0 or not stdout:
        return []

    try:
        data = json.loads(stdout)
        comments = []
        for c in data.get("comments", []):
            comments.append(
                PRComment(
                    author=c.get("author", {}).get("login", "unknown"),
                    body=c.get("body", ""),
                    created_at=c.get("createdAt", ""),
                )
            )
        return comments
    except (json.JSONDecodeError, KeyError):
        return []


def get_code_snippets(repo_path: Path, base: str, head: str, files: list[FileChange]) -> dict[str, str]:
    """Extract key code snippets from git diff for each changed file."""
    snippets = {}

    # Focus on the most important files (source files, docs, config - exclude tests)
    important_files = [f for f in files if f.category in ("source", "docs", "config") and f.status in ("A", "M")]

    for file_change in important_files[:5]:  # Limit to top 5 files to keep output manageable
        code, stdout, _ = run(
            ["git", "diff", f"{base}...{head}", "--", file_change.path], cwd=repo_path
        )

        if code != 0 or not stdout:
            continue

        # Extract key changes (added/modified lines)
        lines = stdout.split("\n")
        added_lines = []

        for i, line in enumerate(lines):
            if line.startswith("+") and not line.startswith("+++"):
                # Get some context around added lines
                start = max(0, i - 2)
                end = min(len(lines), i + 3)

                context_block = []
                for j in range(start, end):
                    if not lines[j].startswith("@@") and not lines[j].startswith("+++") and not lines[j].startswith("---"):
                        # Clean up diff markers for display
                        clean_line = lines[j][1:] if lines[j].startswith(("+", "-", " ")) else lines[j]
                        if lines[j].startswith("+"):
                            context_block.append(clean_line)
                        elif lines[j].startswith(" "):
                            context_block.append(clean_line)

                if context_block:
                    added_lines.extend(context_block)

        # Take first meaningful chunk (around 5-10 lines)
        if added_lines:
            # Remove duplicates while preserving order
            unique_lines = []
            seen = set()
            for line in added_lines:
                if line not in seen and line.strip():
                    unique_lines.append(line)
                    seen.add(line)

            if unique_lines:
                snippets[file_change.path] = "\n".join(unique_lines[:10])

    return snippets


def extract_structured_section(commits: list[CommitInfo], section: str) -> str | None:
    """Extract explicit What:, Why:, or How: sections from commit bodies.

    Args:
        commits: List of commit info objects
        section: Section name to extract ("What", "Why", or "How")

    Returns:
        The extracted section text, or None if not found
    """
    pattern = re.compile(rf"^{section}:\s*(.+)$", re.MULTILINE | re.IGNORECASE)

    for commit in commits:
        if not commit.body:
            continue

        match = pattern.search(commit.body)
        if match:
            return match.group(1).strip()

    return None


def generate_what_section(commits: list[CommitInfo]) -> str:
    """Generate the What section - one sentence summary from commit message.

    First looks for explicit "What:" sections in commit bodies, then falls back to inference.
    """
    if not commits:
        return "No changes found"

    # First, try to extract explicit "What:" section
    explicit_what = extract_structured_section(commits, "What")
    if explicit_what:
        return explicit_what

    # Fallback to existing inference logic
    # For single commit, extract the summary part
    if len(commits) == 1:
        commit = commits[0]
        _, _, summary = parse_conventional_commit(commit.subject)
        return summary.capitalize() if summary else commit.subject

    # For multiple commits, combine the actual summaries
    summaries = []
    for commit in commits:
        _, _, summary = parse_conventional_commit(commit.subject)
        if summary:
            summaries.append(summary)
        else:
            # If not conventional commit, use the whole subject
            summaries.append(commit.subject)

    if len(summaries) == 1:
        return summaries[0].capitalize()
    elif len(summaries) == 2:
        return f"{summaries[0]} and {summaries[1]}"
    else:
        # For more than 2, join with commas and "and"
        return f"{', '.join(summaries[:-1])}, and {summaries[-1]}"


def generate_why_section(commits: list[CommitInfo], files: list[FileChange]) -> str:
    """Generate the Why section - infer motivation from commit types and changes.

    First looks for explicit "Why:" sections in commit bodies, then falls back to inference.
    """
    if not commits:
        return "No context available"

    # First, try to extract explicit "Why:" section
    explicit_why = extract_structured_section(commits, "Why")
    if explicit_why:
        return explicit_why

    # Fallback to existing inference logic
    # Look for "Resolves" or problem statements in commit bodies
    specific_reasons = []
    for commit in commits:
        if commit.body:
            lines = commit.body.split('\n')
            for line in lines:
                line = line.strip()
                # Look for "Resolves X" statements
                if line.startswith("Resolves "):
                    reason = line[9:].strip()  # Remove "Resolves "
                    specific_reasons.append(reason)
                # Look for problem statements containing "when", "crashed", "hanging", etc.
                elif any(keyword in line.lower() for keyword in ["crashed", "hanging", "failed", "broken", "error when"]):
                    specific_reasons.append(line)
                # Look for lines ending with "." that describe a problem
                elif any(keyword in line.lower() for keyword in ["missing", "not installed", "large directories", "infinite loop"]):
                    if line.endswith('.'):
                        specific_reasons.append(line)

    if specific_reasons:
        if len(specific_reasons) == 1:
            return specific_reasons[0]
        else:
            # Combine multiple specific reasons with better formatting
            return " and ".join(specific_reasons).replace(". and ", " and ")

    # Look for issue references: "Resolves", "Fixes", "Closes" in subject
    for commit in commits:
        issue_match = re.search(
            r"(?:resolves?|fixes?|closes?)\s+#?(\d+|[A-Z]+-\d+)",
            commit.subject,
            re.IGNORECASE
        )
        if issue_match:
            specific_reasons.append(f"Addresses issue #{issue_match.group(1)}")

        # Also check body for issue refs and "because/since/due to" phrases
        if commit.body:
            for line in commit.body.split('\n'):
                line = line.strip()
                issue_match = re.search(
                    r"(?:resolves?|fixes?|closes?)\s+#?(\d+|[A-Z]+-\d+)",
                    line,
                    re.IGNORECASE
                )
                if issue_match:
                    specific_reasons.append(f"Addresses issue #{issue_match.group(1)}")
                    continue

                reason_match = re.search(
                    r"(?:because|since|due to)\s+(.+)",
                    line,
                    re.IGNORECASE
                )
                if reason_match:
                    reason = reason_match.group(1).strip().rstrip('.')
                    if len(reason) > 10:
                        specific_reasons.append(reason.capitalize())

    # Dedupe while preserving order
    seen = set()
    unique_reasons = []
    for r in specific_reasons:
        r_lower = r.lower()
        if r_lower not in seen:
            seen.add(r_lower)
            unique_reasons.append(r)

    if unique_reasons:
        return " ".join(unique_reasons[:3]) if len(unique_reasons) > 1 else unique_reasons[0]

    # Infer from commit types
    type_counts = defaultdict(int)
    for commit in commits:
        if commit.commit_type:
            type_counts[commit.commit_type] += 1

    if type_counts:
        dominant_type = max(type_counts, key=lambda k: type_counts[k])
        type_reasons = {
            "fix": "The previous behavior had bugs or issues that needed correction.",
            "feat": "This capability was missing or requested.",
            "refactor": "The code needed restructuring for better maintainability.",
            "perf": "Performance improvements were needed.",
            "docs": "Documentation was missing, outdated, or unclear.",
            "test": "Test coverage was insufficient or tests needed updates.",
            "chore": "Maintenance tasks were needed.",
            "ci": "CI/CD pipeline needed updates or fixes.",
            "style": "Code style or formatting needed cleanup.",
        }
        if dominant_type in type_reasons:
            return type_reasons[dominant_type]

    # Fallback based on file categories
    categories = defaultdict(int)
    for f in files:
        categories[f.category] += 1

    if categories:
        dominant_cat = max(categories, key=lambda k: categories[k])
        cat_desc = {
            "source": "The codebase needed updates to improve functionality.",
            "tests": "Test coverage needed improvements.",
            "docs": "Documentation needed updates.",
            "config": "Configuration needed adjustments.",
            "ci": "CI/CD pipeline needed updates.",
            "deps": "Dependencies needed updates.",
        }
        return cat_desc.get(dominant_cat, "Changes were needed to improve the codebase.")

    # Ultimate fallback when no context is available
    return "Changes were needed to improve the codebase."


def generate_how_section(commits: list[CommitInfo], files: list[FileChange]) -> str:
    """Generate the How section - brief explanation of approach.

    First looks for explicit "How:" sections in commit bodies, then falls back to inference.
    """
    if not commits:
        return "No implementation details available"

    # First, try to extract explicit "How:" section
    explicit_how = extract_structured_section(commits, "How")
    if explicit_how:
        return explicit_how

    # Fallback to existing inference logic
    # Extract specific implementation details from commit bodies
    implementation_details = []

    for commit in commits:
        if commit.body:
            lines = commit.body.split('\n')
            for line in lines:
                line = line.strip()
                # Look for lines starting with "- " (bullet points describing implementation)
                if line.startswith("- "):
                    implementation = line[2:].strip()  # Remove "- "
                    # Filter for implementation details (not problem descriptions)
                    if any(keyword in implementation.lower() for keyword in [
                        "add", "use", "wrap", "check", "implement", "improve", "fix", "handle",
                        "prevent", "skip", "filter"
                    ]):
                        implementation_details.append(implementation)

    if implementation_details:
        # Group related implementation details
        if len(implementation_details) <= 3:
            return ". ".join(implementation_details) + "."
        else:
            # For many details, take the most important ones and summarize
            key_details = implementation_details[:2]  # Take first 2 most important
            result = ". ".join(key_details)
            result += f". Plus {len(implementation_details) - 2} additional improvements"
            return result + "."

    # Describe based on files changed - be specific about modules
    if files:
        modules = defaultdict(list)
        for f in files:
            parts = Path(f.path).parts
            if len(parts) > 1:
                mod = parts[0] if parts[0] not in ("src", "lib", "app") else (parts[1] if len(parts) > 1 else parts[0])
                modules[mod].append(f)
            else:
                modules["root"].append(f)

        descriptions = []
        status_verbs = {"A": "Added", "M": "Modified", "D": "Removed", "R": "Renamed"}

        for module, module_files in list(modules.items())[:3]:
            status_counts = defaultdict(int)
            for f in module_files:
                status_counts[f.status] += 1
            dominant_status = max(status_counts, key=lambda k: status_counts[k])
            verb = status_verbs.get(dominant_status, "Updated")

            file_types = set(Path(f.path).suffix for f in module_files)
            if ".py" in file_types:
                descriptions.append(f"{verb} `{module}` module")
            elif ".md" in file_types or ".rst" in file_types:
                descriptions.append(f"{verb} `{module}` documentation")
            elif any(f.category == "config" for f in module_files):
                descriptions.append(f"{verb} `{module}` configuration")
            elif any(f.category == "tests" for f in module_files):
                descriptions.append(f"{verb} `{module}` tests")
            else:
                descriptions.append(f"{verb} `{module}` files")

        if descriptions:
            return ". ".join(descriptions) + "."

    # Describe based on commit summaries
    actions = []
    for commit in commits:
        _, _, summary = parse_conventional_commit(commit.subject)
        if summary:
            s_lower = summary.lower()
            if s_lower.startswith("add "):
                actions.append("Added " + summary[4:])
            elif s_lower.startswith("fix "):
                actions.append("Fixed " + summary[4:])
            elif s_lower.startswith("update "):
                actions.append("Updated " + summary[7:])
            elif s_lower.startswith("remove "):
                actions.append("Removed " + summary[7:])
            elif s_lower.startswith("refactor "):
                actions.append("Refactored " + summary[9:])
            elif s_lower.startswith("improve "):
                actions.append("Improved " + summary[8:])
            else:
                actions.append(summary[0].upper() + summary[1:] if summary else summary)

    if actions:
        seen = set()
        unique_actions = []
        for a in actions:
            a_lower = a.lower()
            if a_lower not in seen:
                seen.add(a_lower)
                unique_actions.append(a)

        return ". ".join(unique_actions[:3]) + "."

    # Ultimate fallback - describe file changes numerically
    added = sum(1 for f in files if f.status == "A")
    modified = sum(1 for f in files if f.status == "M")
    removed = sum(1 for f in files if f.status == "D")

    parts = []
    if added:
        parts.append(f"added {added} file{'s' if added > 1 else ''}")
    if modified:
        parts.append(f"modified {modified} file{'s' if modified > 1 else ''}")
    if removed:
        parts.append(f"removed {removed} file{'s' if removed > 1 else ''}")

    if parts:
        return "Changes " + ", ".join(parts) + "."

    return f"Updated {len(files)} file{'s' if len(files) != 1 else ''}."


def generate_pr_description(
    repo_path: str | Path,
    base_branch: str,
    head_branch: str,
    config: Config | None = None,
    include_comments: bool = False,
) -> PRDescription:
    """
    Generate a PR description for the given branches.

    This is the main module API for use by other tools (e.g., dep-shepherd).

    Args:
        repo_path: Path to the git repository
        base_branch: The target branch (e.g., "main")
        head_branch: The source branch (e.g., "feature-xyz")
        config: Optional configuration (uses defaults if not provided)
        include_comments: Whether to fetch existing PR comments

    Returns:
        PRDescription dataclass with all analysis results
    """
    repo_path = Path(repo_path)
    if config is None:
        config = load_config()

    # Gather data
    commits = get_commits(repo_path, base_branch, head_branch)
    files = get_changed_files(repo_path, base_branch, head_branch)
    diff_text = get_diff_text(repo_path, base_branch, head_branch)

    # Analyze
    title = generate_pr_title(commits, config)
    summary = generate_summary(commits, files, config)
    testing = generate_testing_suggestions(files, commits) if config.include_testing else []

    breaking = (
        detect_breaking_changes(commits, diff_text) if config.include_breaking_changes else []
    )
    new_deps = detect_new_dependencies(repo_path, base_branch, head_branch, files)
    config_changes = detect_config_changes(files)

    # Get PR comments if requested
    comments = get_pr_comments(repo_path, head_branch) if include_comments else []

    # Get code snippets for the new template format
    code_snippets = get_code_snippets(repo_path, base_branch, head_branch, files)

    # Group files by status (keep for backward compatibility)
    changes = {
        "added": [f.path for f in files if f.status == "A"],
        "modified": [f.path for f in files if f.status == "M"],
        "removed": [f.path for f in files if f.status == "D"],
        "renamed": [f.path for f in files if f.status == "R"],
        "code_snippets": code_snippets,  # Add code snippets to changes
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
    if config_changes and config.output_style != "minimal":
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

    return PRDescription(
        title=title,
        summary=summary,
        changes=changes,
        testing=testing,
        notes=notes,
        commits=[asdict(c) for c in commits],
        stats=stats,
        comments=[asdict(c) for c in comments],
    )


def format_markdown(desc: PRDescription, config: Config) -> str:
    """Format PRDescription as markdown using What/Why/How/Changes/Testing template."""
    lines = []

    # Extract data for the new template
    commits = [CommitInfo(**c) if isinstance(c, dict) else c for c in desc.commits]
    files = []

    # Reconstruct file list from changes dict for generating sections
    for status, file_list in desc.changes.items():
        if status != "code_snippets":
            for file_path in file_list:
                files.append(FileChange(path=file_path, status=status[0].upper()))

    # What section
    what_text = generate_what_section(commits)
    lines.append("## What")
    lines.append("")
    lines.append(what_text)
    lines.append("")

    # Why section
    why_text = generate_why_section(commits, files)
    lines.append("## Why")
    lines.append("")
    lines.append(why_text)
    lines.append("")

    # How section
    how_text = generate_how_section(commits, files)
    lines.append("## How")
    lines.append("")
    lines.append(how_text)
    lines.append("")

    # Changes section with actual code snippets
    lines.append("## Changes")
    lines.append("")

    # Show code snippets first (the key requirement)
    code_snippets = desc.changes.get("code_snippets", {})
    if code_snippets:
        for file_path, snippet in code_snippets.items():
            lines.append(f"**{file_path}**")

            # Detect file type for appropriate code block formatting
            if file_path.endswith(('.py', '.pyx')):
                lines.append("```python")
            elif file_path.endswith('.md'):
                lines.append("```markdown")
            elif file_path.endswith(('.js', '.jsx')):
                lines.append("```javascript")
            elif file_path.endswith(('.ts', '.tsx')):
                lines.append("```typescript")
            elif file_path.endswith(('.yml', '.yaml')):
                lines.append("```yaml")
            elif file_path.endswith('.json'):
                lines.append("```json")
            elif file_path.endswith('.toml'):
                lines.append("```toml")
            elif file_path.endswith('.sh'):
                lines.append("```bash")
            else:
                lines.append("```")

            lines.append(snippet)
            lines.append("```")
            lines.append("")

    # Also show file lists if in verbose mode
    if config.output_style == "verbose":
        max_files = config.max_files_shown

        if desc.changes.get("added"):
            lines.append("**Additional files added:**")
            for f in desc.changes["added"][:max_files]:
                if f not in code_snippets:  # Don't duplicate files already shown with snippets
                    lines.append(f"- `{f}`")
            lines.append("")

        if desc.changes.get("modified"):
            modified_not_shown = [f for f in desc.changes["modified"] if f not in code_snippets]
            if modified_not_shown:
                lines.append("**Additional files modified:**")
                for f in modified_not_shown[:max_files]:
                    lines.append(f"- `{f}`")
                lines.append("")

        if desc.changes.get("removed"):
            lines.append("**Files removed:**")
            for f in desc.changes["removed"][:10]:
                lines.append(f"- `{f}`")
            lines.append("")

    # Testing section (if enabled)
    if desc.testing and config.include_testing:
        lines.append("## Testing")
        lines.append("")
        for t in desc.testing:
            lines.append(f"{t}")
        lines.append("")

    # Add notes section if there are breaking changes or important info
    if desc.notes and config.output_style != "minimal":
        lines.append("## Notes")
        lines.append("")
        for note in desc.notes:
            lines.append(note)
        lines.append("")

    return "\n".join(lines)


def format_plain(desc: PRDescription, config: Config) -> str:
    """Format PRDescription as plain text (no markdown)."""
    lines = []

    # Summary
    lines.append("SUMMARY")
    lines.append("-" * 40)
    lines.append(desc.summary)
    lines.append("")

    # Changes (skip in minimal mode)
    if config.output_style != "minimal":
        lines.append("CHANGES")
        lines.append("-" * 40)

        if desc.changes.get("added"):
            lines.append("Added:")
            for f in desc.changes["added"][: config.max_files_shown]:
                lines.append(f"  + {f}")

        if desc.changes.get("modified"):
            lines.append("Modified:")
            for f in desc.changes["modified"][: config.max_files_shown]:
                lines.append(f"  ~ {f}")

        if desc.changes.get("removed"):
            lines.append("Removed:")
            for f in desc.changes["removed"][:10]:
                lines.append(f"  - {f}")

        lines.append("")

    # Testing
    if desc.testing and config.include_testing:
        lines.append("TESTING")
        lines.append("-" * 40)
        for t in desc.testing:
            # Remove markdown backticks
            t_plain = t.replace("`", "")
            lines.append(f"  [ ] {t_plain}")
        lines.append("")

    # Notes
    if desc.notes:
        lines.append("NOTES")
        lines.append("-" * 40)
        for note in desc.notes:
            # Remove markdown formatting
            note_plain = re.sub(r"\*\*|\`", "", note)
            lines.append(note_plain)
        lines.append("")

    # Stats
    if config.output_style != "minimal":
        lines.append("-" * 40)
        lines.append(
            f"{desc.stats['commits']} commits, {desc.stats['files_changed']} files changed "
            f"(+{desc.stats['additions']}/-{desc.stats['deletions']})"
        )

    return "\n".join(lines)


def format_json(desc: PRDescription) -> str:
    """Format PRDescription as JSON."""
    return json.dumps(asdict(desc), indent=2)


def format_squash(desc: PRDescription, config: Config) -> str:
    """Format PRDescription as a compact squash commit message.

    Designed for large PRs - short, scannable, no fluff.
    """
    lines = []

    # Summary - max 2 sentences
    summary_text = desc.summary.replace("\n", " ").strip()
    # Take first sentence or first 150 chars
    if ". " in summary_text:
        summary_text = summary_text.split(". ")[0] + "."
    if len(summary_text) > 150:
        summary_text = summary_text[:147] + "..."
    lines.append(summary_text)
    lines.append("")

    # Key changes as brief bullets (max 5)
    all_files = (
        desc.changes.get("added", []) +
        desc.changes.get("modified", []) +
        desc.changes.get("removed", [])
    )
    if all_files:
        lines.append("Changes:")
        for f in all_files[:5]:
            lines.append(f"- {Path(f).name}")
        if len(all_files) > 5:
            lines.append(f"- +{len(all_files) - 5} more files")
        lines.append("")

    # Stats
    stats = desc.stats
    lines.append(
        f"{stats['files_changed']} files, "
        f"+{stats['additions']}/-{stats['deletions']}"
    )

    # Breaking changes (critical - always show)
    breaking = [n for n in desc.notes if "Breaking" in n or "⚠️" in n]
    if breaking:
        lines.append("")
        lines.append("⚠️ BREAKING: " + breaking[0].replace("⚠️ ", "").replace("**Breaking Changes:**", "").strip())

    return "\n".join(lines)


def copy_to_clipboard(text: str) -> bool:
    """Copy text to clipboard. Returns True on success."""
    # Try pbcopy (macOS)
    code, _, _ = run(["which", "pbcopy"])
    if code == 0:
        proc = subprocess.Popen(["pbcopy"], stdin=subprocess.PIPE)
        proc.communicate(text.encode())
        return proc.returncode == 0

    # Try xclip (Linux)
    code, _, _ = run(["which", "xclip"])
    if code == 0:
        proc = subprocess.Popen(["xclip", "-selection", "clipboard"], stdin=subprocess.PIPE)
        proc.communicate(text.encode())
        return proc.returncode == 0

    # Try xsel (Linux)
    code, _, _ = run(["which", "xsel"])
    if code == 0:
        proc = subprocess.Popen(["xsel", "--clipboard", "--input"], stdin=subprocess.PIPE)
        proc.communicate(text.encode())
        return proc.returncode == 0

    return False


def main():
    parser = argparse.ArgumentParser(
        description=__doc__.split("\n\n")[0],  # First paragraph of docstring
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                      Compare current branch vs main
  %(prog)s feature-xyz          Compare feature-xyz vs main
  %(prog)s --base develop       Compare current branch vs develop
  %(prog)s --format json        Output JSON
  %(prog)s --title              Just output suggested PR title
  %(prog)s --include-comments   Include PR discussion context
  %(prog)s --style minimal      Minimal output

Config file: ~/.config/openclaw-dash/pr-describe.yaml
""",
    )
    parser.add_argument(
        "branch",
        nargs="?",
        help="branch to describe (default: current branch)",
    )
    parser.add_argument(
        "--base",
        metavar="BRANCH",
        help="base branch to compare against (default: main or master)",
    )
    parser.add_argument(
        "--format",
        choices=["markdown", "plain", "json"],
        default="markdown",
        help="output format (default: markdown)",
    )
    parser.add_argument(
        "--style",
        choices=["verbose", "concise", "minimal"],
        help="output style (overrides config)",
    )
    parser.add_argument(
        "--title",
        action="store_true",
        help="output just the suggested PR title",
    )
    parser.add_argument(
        "--include-comments",
        action="store_true",
        help="include existing PR discussion (requires gh CLI)",
    )
    parser.add_argument(
        "--clipboard",
        action="store_true",
        help="copy output to clipboard",
    )
    parser.add_argument(
        "--squash",
        action="store_true",
        help="compact format optimized for squash commit messages",
    )
    parser.add_argument(
        "--no-testing",
        action="store_true",
        help="omit testing suggestions",
    )
    parser.add_argument(
        "--no-breaking",
        action="store_true",
        help="omit breaking change detection",
    )
    parser.add_argument(
        "--init-config",
        action="store_true",
        help="create default config file and exit",
    )
    # Keep --json for backward compatibility
    parser.add_argument(
        "--json",
        action="store_true",
        help=argparse.SUPPRESS,  # Hidden, use --format json instead
    )

    args = parser.parse_args()

    # Handle --init-config
    if args.init_config:
        if not HAS_YAML:
            print("Error: PyYAML not installed. Run: pip install pyyaml", file=sys.stderr)
            sys.exit(1)
        ensure_config_exists()
        print(f"Config file created: {CONFIG_FILE}")
        sys.exit(0)

    # Load config
    config = load_config()

    # Apply CLI overrides
    if args.style:
        config.output_style = args.style
    if args.no_testing:
        config.include_testing = False
    if args.no_breaking:
        config.include_breaking_changes = False

    # Handle --json backward compatibility
    output_format = args.format
    if args.json:
        output_format = "json"

    # Default to current directory
    repo_path = Path.cwd()

    # Check if we're in a git repo
    code, _, _ = run(["git", "rev-parse", "--git-dir"], cwd=repo_path)
    if code != 0:
        print("Error: Not a git repository", file=sys.stderr)
        sys.exit(1)

    # Determine branches
    base_branch = args.base if args.base else get_default_branch(repo_path)
    head_branch = args.branch if args.branch else get_current_branch(repo_path)

    # Check if branches are the same
    if base_branch == head_branch:
        print(f"Error: base and head are the same branch ({base_branch})", file=sys.stderr)
        print("Hint: checkout a feature branch or specify --base <branch>", file=sys.stderr)
        sys.exit(1)

    # Check if there are commits
    code, stdout, _ = run(
        ["git", "rev-list", f"{base_branch}..{head_branch}", "--count"], cwd=repo_path
    )
    if code != 0 or stdout == "0":
        print(f"Error: No commits between {base_branch} and {head_branch}", file=sys.stderr)
        sys.exit(1)

    # Generate description
    desc = generate_pr_description(
        repo_path, base_branch, head_branch, config, include_comments=args.include_comments
    )

    # Handle --title flag
    if args.title:
        print(desc.title)
        return

    print(f"Analyzing {head_branch} vs {base_branch}...", file=sys.stderr)

    # Format output
    if args.squash:
        output = format_squash(desc, config)
    elif output_format == "json":
        output = format_json(desc)
    elif output_format == "plain":
        output = format_plain(desc, config)
    else:
        output = format_markdown(desc, config)

    # Copy to clipboard if requested
    if args.clipboard:
        if copy_to_clipboard(output):
            print("✅ Copied to clipboard!", file=sys.stderr)
        else:
            print("⚠️  Could not copy to clipboard (pbcopy/xclip not found)", file=sys.stderr)

    print(output)


if __name__ == "__main__":
    main()
