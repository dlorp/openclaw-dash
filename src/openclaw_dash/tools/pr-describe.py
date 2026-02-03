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
from collections import Counter, defaultdict
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

# Action verbs for extracting meaningful title summaries
# Priority order: more specific first
ACTION_VERBS = {
    "remove", "add", "prevent", "filter", "generate", "extract",
    "validate", "handle", "parse", "format", "replace", "skip", "ignore",
    "enable", "disable", "support", "implement", "fix", "improve",
    "refactor", "simplify", "optimize", "cache", "update", "create",
}

# Technical terms that should preserve their original case when lowercasing
# These are programming language keywords, type names, and special values
TECHNICAL_TERMS = {
    # Python/JavaScript literals
    "None", "True", "False", "NoneType",
    # General programming
    "NULL", "NaN", "undefined", "nil",
    # Type names (when used as type references)
    "String", "Integer", "Boolean", "Float", "Double",
    # Common class/type patterns
    "TypeError", "ValueError", "KeyError", "AttributeError",
    "RuntimeError", "IndexError", "IOError", "OSError",
}

# Pairs of contradictory action verbs (doing both = refactoring, not two separate actions)
# Format: frozenset({verb1, verb2}) - order doesn't matter
CONTRADICTORY_VERB_PAIRS = {
    frozenset({"add", "remove"}),
    frozenset({"enable", "disable"}),
    frozenset({"create", "delete"}),
    frozenset({"show", "hide"}),
}

# Incidental nouns - generic terms that don't describe domain/feature
# These are WHERE/HOW things happen, not WHAT the change is about
INCIDENTAL_NOUNS = {
    # Location/container nouns
    "directories",
    "directory",
    "files",
    "file",
    "folder",
    "folders",
    "path",
    "paths",
    "code",
    "codebase",
    "project",
    "projects",
    "repo",
    "repository",
    # Generic data terms
    "data",
    "items",
    "item",
    "things",
    "thing",
    "stuff",
    "content",
    "contents",
    "elements",
    "element",
    "entries",
    "entry",
    # Generic change terms (often in commit msgs)
    "changes",
    "updates",
    "modifications",
    "adjustments",
    # Generic problem terms (but not error/errors - those are meaningful)
    "issues",
    "issue",
    "problems",
    "problem",
    "bugs",
    "bug",
    # Generic technical terms
    "cases",
    "case",
    "options",
    "option",
    "values",
    "value",
    "types",
    "type",
    "results",
    "result",
    "objects",
    "object",
    "instances",
    "instance",
    "requests",
    "request",
    "responses",
    "response",
    # Process/action nouns
    "operations",
    "operation",
    "processes",
    "process",
    "actions",
    "action",
    "steps",
    "step",
    "tasks",
    "task",
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
    """Extract meaningful words from text, filtering stop words and adverbs."""
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
    # Filter stop words, short words, and adverbs (ending in -ly)
    return [
        w
        for w in words
        if w not in stop_words and len(w) > 2 and not (w.endswith("ly") and len(w) > 4)
    ]


def _extract_bigrams(text: str) -> list[str]:
    """Extract meaningful two-word phrases from text."""
    stop_words = {"the", "a", "an", "to", "for", "in", "on", "at", "by", "with", "and", "or", "of"}
    words = re.findall(r"\b[a-zA-Z][a-zA-Z0-9_-]*\b", text.lower())
    bigrams = []
    for i in range(len(words) - 1):
        w1, w2 = words[i], words[i + 1]
        # Skip if either word is a stop word or too short
        if w1 not in stop_words and w2 not in stop_words and len(w1) > 2 and len(w2) > 2:
            bigrams.append(f"{w1} {w2}")
    return bigrams


def _extract_action_phrase(text: str) -> tuple[str, str] | None:
    """
    Extract action verb and its direct object from a summary.

    Returns (verb, object) tuple or None if no action pattern found.
    E.g., "remove bullet points from summary" -> ("remove", "bullet points")

    Preserves case for technical terms (None, True, False, etc.) by extracting
    from the original text at the matched position rather than from lowercased text.

    Prioritizes verbs at the START of text to avoid matching mid-text noun phrases
    like "format extraction" where "format" is used as a noun, not a verb.
    """
    text_lower = text.lower()

    def _extract_match(verb: str, match: re.Match) -> tuple[str, str] | None:
        """Extract and clean the object from a regex match."""
        obj_start = match.start(1)
        obj_end = match.end(1)
        obj = text[obj_start:obj_end].strip()
        # Clean up trailing punctuation and common suffixes
        obj = re.sub(r"[.,;:!?]+$", "", obj)
        # Remove trailing adverbs (words ending in -ly)
        obj = re.sub(r"\s+\w+ly$", "", obj)
        if obj and len(obj) < 40:  # Sanity check
            return (verb, obj)
        return None

    # FIRST PASS: Look for verbs at the START of text (most reliable)
    # This catches "add feature X", "remove bullet points", etc.
    for verb in ACTION_VERBS:
        pattern = rf"^{verb}\s+(.+?)(?:\s+(?:from|in|for|to|on|when|if)\s+|$)"
        match = re.search(pattern, text_lower)
        if match:
            result = _extract_match(verb, match)
            if result:
                return result

    # SECOND PASS: Look for verbs mid-text (for "scope: verb object" patterns)
    # Only if no start-of-text verb found, to avoid matching noun phrases
    # like "format extraction" where "format" is a noun
    for verb in ACTION_VERBS:
        pattern = rf"\b{verb}\s+(.+?)(?:\s+(?:from|in|for|to|on|when|if)\s+|$)"
        match = re.search(pattern, text_lower)
        if match:
            # Skip if the verb is followed by a noun-like word ending in -tion, -ment, -ing
            # These are typically noun phrases like "format extraction", not verb phrases
            obj_start = match.start(1)
            obj_text = text_lower[obj_start:].split()[0] if text_lower[obj_start:].split() else ""
            if obj_text.endswith(("tion", "ment", "ing", "ness", "ity")):
                continue
            result = _extract_match(verb, match)
            if result:
                return result

    return None


def _normalize_object(obj: str) -> str:
    """
    Normalize an object string for comparison (singularize, lowercase, strip articles).

    E.g., "bullet points" and "bullet point" should match.
    """
    obj = obj.lower().strip()
    # Remove leading articles
    obj = re.sub(r"^(the|a|an)\s+", "", obj)
    # Simple singularization: remove trailing 's' for comparison
    # (handles "points" -> "point", "bullets" -> "bullet")
    if obj.endswith("s") and len(obj) > 3:
        obj_singular = obj[:-1]
        # Return both forms for comparison flexibility
        return obj_singular
    return obj


def _detect_contradictory_actions(
    action_phrases: list[tuple[str, str]],
) -> tuple[str, str] | None:
    """
    Detect if action phrases contain contradictory verb pairs on the same object.

    Returns (verb1, common_object) if contradiction found, None otherwise.
    E.g., [("add", "bullet points"), ("remove", "bullet points")] -> ("add", "bullet points")
    """
    if len(action_phrases) < 2:
        return None

    # Build mapping: normalized_object -> list of (verb, original_object)
    obj_to_verbs: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for verb, obj in action_phrases:
        norm_obj = _normalize_object(obj)
        obj_to_verbs[norm_obj].append((verb, obj))

    # Check each object for contradictory verb pairs
    for norm_obj, verb_obj_pairs in obj_to_verbs.items():
        if len(verb_obj_pairs) < 2:
            continue
        verbs = {v for v, _ in verb_obj_pairs}
        for pair in CONTRADICTORY_VERB_PAIRS:
            if pair <= verbs:  # Both verbs in pair are present
                # Return the first verb and object (for the refactor message)
                return (list(pair)[0], verb_obj_pairs[0][1])

    return None


def _build_multi_commit_summary(summaries: list[str], scopes: set[str]) -> str:
    """
    Build a meaningful summary from multiple commit summaries.

    Returns ONLY the summary text - scope formatting is handled by generate_pr_title()
    using conventional commit format: type(scope): summary

    Strategy:
    1. If there's a single summary, use it (truncated if needed)
    2. Extract action phrases (verb + object) and combine max 2
    3. Look for common phrases (bigrams) across summaries
    4. Find common action verbs + domain words
    5. If >2 actions or title too long, summarize generically
    6. Keep titles concise (~50 chars target for summary portion)

    Grammar rules:
    - All actions use verb form: "add", "remove", "extract" (not "extraction")
    - Max 2 actions combined with "and"
    - If >2 actions, summarize: "improve X generation"
    - No scope suffix - caller handles conventional commit format
    """
    MAX_SUMMARY_LENGTH = 50  # Target length for summary portion

    if not summaries:
        return "various updates"

    # Clean up summaries
    clean_summaries = [s.strip() for s in summaries if s.strip()]
    if not clean_summaries:
        return "various updates"

    if len(clean_summaries) == 1:
        summary = clean_summaries[0]
        # Truncate if too long
        if len(summary) > MAX_SUMMARY_LENGTH:
            words = summary.split()
            truncated = []
            length = 0
            for w in words:
                if length + len(w) + 1 > MAX_SUMMARY_LENGTH:
                    break
                truncated.append(w)
                length += len(w) + 1
            summary = " ".join(truncated)
        return summary

    # Strategy 1: Extract action phrases from summaries
    # This gives us specific "verb + object" descriptions instead of vague "improvements"
    action_phrases = []
    for s in clean_summaries:
        phrase = _extract_action_phrase(s)
        if phrase:
            action_phrases.append(phrase)

    if action_phrases:
        # Check for contradictory actions FIRST (add X + remove X = refactoring)
        contradiction = _detect_contradictory_actions(action_phrases)
        if contradiction:
            _, obj = contradiction
            # Use "refactor X handling" or "update X" for contradictory actions
            return f"refactor {obj} handling"

        # Group by verb
        verbs_to_objects: dict[str, list[str]] = defaultdict(list)
        for verb, obj in action_phrases:
            verbs_to_objects[verb].append(obj)

        # If all actions share the same verb, combine objects (max 2)
        if len(verbs_to_objects) == 1:
            verb = list(verbs_to_objects.keys())[0]
            objects = verbs_to_objects[verb]
            unique_objs = list(dict.fromkeys(objects))

            if len(unique_objs) == 1:
                result = f"{verb} {unique_objs[0]}"
            elif len(unique_objs) == 2:
                result = f"{verb} {unique_objs[0]} and {unique_objs[1]}"
            else:
                # >2 objects with same verb - summarize
                result = f"{verb} {unique_objs[0]} and more"

            # Length check - truncate if too long
            if len(result) <= MAX_SUMMARY_LENGTH:
                return result
            return f"{verb} {unique_objs[0]}"

        # Multiple verbs - combine max 2
        sorted_verbs = sorted(
            verbs_to_objects.keys(),
            key=lambda v: len(verbs_to_objects[v]),
            reverse=True,
        )

        if len(sorted_verbs) >= 2:
            v1, v2 = sorted_verbs[0], sorted_verbs[1]
            o1, o2 = verbs_to_objects[v1][0], verbs_to_objects[v2][0]
            combined = f"{v1} {o1} and {v2} {o2}"

            if len(combined) <= MAX_SUMMARY_LENGTH:
                return combined

            # Too long - just use main action
            result = f"{v1} {o1}"
            if len(result) <= MAX_SUMMARY_LENGTH:
                return result

        # Just use the most common action
        main_verb = sorted_verbs[0]
        main_obj = verbs_to_objects[main_verb][0]
        return f"{main_verb} {main_obj}"

    # Strategy 2: Look for bigrams appearing in MAJORITY (>50%) of summaries
    # (e.g., "structured output" in 2/3 commits should still match)
    bigrams_per_summary = [set(_extract_bigrams(s)) for s in clean_summaries]
    if len(bigrams_per_summary) > 1:
        # Count how many summaries contain each bigram
        all_bigrams = [bg for bgs in bigrams_per_summary for bg in bgs]
        bigram_counts = Counter(all_bigrams)
        threshold = len(clean_summaries) / 2
        common_bigrams = [bg for bg, count in bigram_counts.items() if count > threshold]
        if common_bigrams:
            # Use the longest common bigram (most descriptive)
            phrase = sorted(common_bigrams, key=len, reverse=True)[0]
            # Check if phrase contains an action verb - if so, use it directly
            phrase_words = phrase.split()
            if phrase_words and phrase_words[0] in ACTION_VERBS:
                return phrase
            return f"improve {phrase}"

    # Strategy 3: If all commits share a single scope, describe improvements
    # (Note: scope will be added by caller in conventional commit format)
    if len(scopes) == 1:
        words_per_summary = [set(_extract_key_words(s)) for s in clean_summaries]
        if words_per_summary:
            common = set.intersection(*words_per_summary)
            if common:
                # Find verbs/actions using ACTION_VERBS constant
                actions = [w for w in common if w in ACTION_VERBS]
                nouns = [w for w in common if w not in ACTION_VERBS]
                if actions and nouns:
                    return f"{actions[0]} {nouns[0]}"
                if actions:
                    return f"{actions[0]} handling"
                if nouns:
                    return f"improve {nouns[0]}"
        # Fall back to generic improvement (scope added by caller)
        return "improve handling"

    # Strategy 4: Find common theme words and build natural phrase
    words_per_summary = [set(_extract_key_words(s)) for s in clean_summaries]
    if len(words_per_summary) > 1:
        common = set.intersection(*words_per_summary)
        if common:
            # Use ACTION_VERBS constant for consistency
            actions = [w for w in common if w in ACTION_VERBS]
            # Filter out incidental nouns
            nouns = sorted(
                [w for w in common if w not in ACTION_VERBS and w not in INCIDENTAL_NOUNS],
                key=len,
                reverse=True,
            )

            if actions and nouns:
                # "add scanner support", "improve error handling"
                return f"{actions[0]} {nouns[0]}"
            if len(nouns) >= 2:
                # "improve scanner and parser" instead of vague "improvements"
                return f"improve {nouns[0]} and {nouns[1]}"
            if nouns:
                return f"improve {nouns[0]} handling"

    # Strategy 5: Find words in at least half the summaries
    word_counts: dict[str, int] = defaultdict(int)
    for word_set in words_per_summary:
        for word in word_set:
            word_counts[word] += 1

    threshold = max(2, len(clean_summaries) // 2)
    frequent = [w for w, c in word_counts.items() if c >= threshold]
    if frequent:
        # Use ACTION_VERBS constant
        actions = [w for w in frequent if w in ACTION_VERBS]
        # Filter out incidental nouns
        nouns = sorted(
            [w for w in frequent if w not in ACTION_VERBS and w not in INCIDENTAL_NOUNS],
            key=lambda w: word_counts[w],
            reverse=True,
        )

        if actions and nouns:
            return f"{actions[0]} {nouns[0]}"
        if len(nouns) >= 2:
            return f"improve {nouns[0]} and {nouns[1]}"
        if nouns:
            return f"improve {nouns[0]} handling"
        if actions:
            # Common action found but no specific nouns
            return f"{actions[0]} various components"

    # Strategy 6: Extract key nouns from each summary and list domains
    # Filter out common verbs/adjectives to find actual domain nouns
    common_verbs = {
        "add",
        "fix",
        "improve",
        "handle",
        "support",
        "implement",
        "enable",
        "prevent",
        "remove",
        "update",
        "create",
        "delete",
        "move",
        "rename",
        "refactor",
        "clean",
        "resolve",
        "use",
        "make",
        "get",
        "set",
        "check",
        "validate",
        "missing",
        "broken",
        "invalid",
        "empty",
        "null",
        "undefined",
        "large",
        "small",
        "new",
        "old",
        "gracefully",
        "hanging",
        "slow",
        "fast",
    }

    domains = []
    for s in clean_summaries[:3]:
        words = _extract_key_words(s)
        # Filter to likely nouns (not common verbs/adjectives or incidental nouns)
        nouns = [w for w in words if w not in common_verbs and w not in INCIDENTAL_NOUNS]
        if nouns:
            # Prefer simple words over hyphenated compound identifiers
            # Split hyphenated words and consider their parts too
            simple_nouns = []
            for w in nouns:
                if "-" in w:
                    # Extract meaningful parts from hyphenated words (e.g., "smart-todo-scanner" -> "scanner")
                    parts = [
                        p
                        for p in w.split("-")
                        if len(p) > 3 and p not in common_verbs and p not in INCIDENTAL_NOUNS
                    ]
                    simple_nouns.extend(parts)
                else:
                    simple_nouns.append(w)
            if simple_nouns:
                # Take the longest simple noun as the likely domain
                domain = sorted(simple_nouns, key=len, reverse=True)[0]
                if domain not in domains:
                    domains.append(domain)

    if len(domains) >= 2:
        return f"improve {domains[0]} and {domains[1]}"
    if domains:
        return f"improve {domains[0]} handling"

    # Absolute last resort: use first summary with adverbs stripped
    # Use _extract_key_words to get words without adverbs
    fallback_words = _extract_key_words(clean_summaries[0])
    if fallback_words:
        # Try to form "verb noun" if first word is a verb
        if fallback_words[0] in ACTION_VERBS:
            return " ".join(fallback_words[:3])  # Verb + up to 2 more words
        return f"improve {' '.join(fallback_words[:2])}"
    return clean_summaries[0]


def extract_branch_type(branch_name: str) -> str:
    """
    Extract conventional commit type from branch name prefix.

    Examples:
        feat/add-login -> feat
        fix/null-pointer -> fix
        chore/update-deps -> chore
        feature/xyz -> feat (normalize "feature" to "feat")
    """
    if not branch_name:
        return ""

    # Match common branch prefixes: type/description or type-description
    match = re.match(
        r"^(feat|fix|docs|style|refactor|test|chore|ci|perf|build|feature)[/-]",
        branch_name.lower(),
    )
    if match:
        branch_type = match.group(1)
        # Normalize "feature" to "feat"
        if branch_type == "feature":
            return "feat"
        return branch_type
    return ""


def generate_pr_title(commits: list[CommitInfo], config: Config, branch_name: str = "") -> str:
    """
    Generate a PR title from commits using conventional commit format.

    Strategy:
    - Single commit: use its subject directly
    - Multiple commits: extract meaningful description from commit messages
    - Never just count commits - always describe WHAT changed
    - Branch name prefix (feat/, fix/) is used as tiebreaker or override
    - First commit is weighted more heavily (it's usually the main change)
    - "test:" type is deprioritized unless ALL commits are tests
    """
    if not commits:
        return "Untitled PR"

    # Extract type from branch name for tiebreaking/override
    branch_type = extract_branch_type(branch_name)

    # Count commit types with weighting: first commit counts double
    type_counts: dict[str, int] = defaultdict(int)
    typed_commits = []
    for i, commit in enumerate(commits):
        if commit.commit_type:
            # First commit gets weight of 2, others get 1
            weight = 2 if i == 0 else 1
            type_counts[commit.commit_type] += weight
            typed_commits.append(commit)

    # Single commit - use it directly
    if len(commits) == 1:
        commit = commits[0]
        if commit.commit_type:
            _, _, summary = parse_conventional_commit(commit.subject)
            # Use conventional commit format with scope when present
            if commit.scope:
                title_format = "{type}({scope}): {summary}"
            else:
                title_format = config.title_format
            return title_format.format(
                type=commit.commit_type,
                scope=commit.scope or "",
                summary=summary.capitalize() if summary else "update",
            )
        return commit.subject

    # Multiple commits - find dominant type with smart selection
    if type_counts:
        # Check if ALL commits are tests - only then use "test" type
        all_tests = all(c.commit_type == "test" for c in typed_commits) if typed_commits else False

        # Deprioritize "test" type unless all commits are tests
        if not all_tests and "test" in type_counts and len(type_counts) > 1:
            # Remove test from consideration for dominant type
            type_counts_filtered = {k: v for k, v in type_counts.items() if k != "test"}
        else:
            type_counts_filtered = type_counts

        # Find dominant type from filtered counts
        if type_counts_filtered:
            # Get max count
            max_count = max(type_counts_filtered.values())
            # Find all types with max count (potential ties)
            top_types = [t for t, c in type_counts_filtered.items() if c == max_count]

            if len(top_types) == 1:
                dominant_type = top_types[0]
            elif branch_type and branch_type in top_types:
                # Use branch type as tiebreaker
                dominant_type = branch_type
            elif branch_type and branch_type in COMMIT_TYPES:
                # Branch type overrides when there's a tie and branch has valid type
                dominant_type = branch_type
            else:
                # Default to first in sorted order for consistency
                dominant_type = sorted(top_types)[0]
        else:
            # Fall back to test if that's all we have
            dominant_type = "test"

        # If branch type strongly suggests a different type and counts are close,
        # prefer branch type
        if branch_type and branch_type != dominant_type and branch_type in type_counts:
            branch_count = type_counts[branch_type]
            dominant_count = type_counts_filtered.get(dominant_type, 0)
            # If branch type has at least 50% of dominant count, prefer branch type
            if branch_count >= dominant_count * 0.5:
                dominant_type = branch_type

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

        # If no commits match dominant type (e.g., branch override), use first commit
        if not summaries and commits:
            _, _, summary = parse_conventional_commit(commits[0].subject)
            if summary:
                summaries.append(summary.strip())

        # Build a descriptive summary (never just count commits)
        summary_text = _build_multi_commit_summary(summaries, scopes)
        scope_text = list(scopes)[0] if len(scopes) == 1 else ""

        # Use conventional commit format with scope when present
        if scope_text:
            title_format = "{type}({scope}): {summary}"
        else:
            title_format = config.title_format

        return title_format.format(
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
    title = generate_pr_title(commits, config, branch_name=head_branch)
    summary = generate_summary(commits, files, config)
    testing = generate_testing_suggestions(files, commits) if config.include_testing else []

    breaking = (
        detect_breaking_changes(commits, diff_text) if config.include_breaking_changes else []
    )
    new_deps = detect_new_dependencies(repo_path, base_branch, head_branch, files)
    config_changes = detect_config_changes(files)

    # Get PR comments if requested
    comments = get_pr_comments(repo_path, head_branch) if include_comments else []

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
    """Format PRDescription as markdown."""
    lines = []

    # Summary
    lines.append("## What")
    lines.append("")
    lines.append(desc.summary)
    lines.append("")

    # Changes (skip in minimal mode)
    if config.output_style != "minimal":
        lines.append("## Changes")
        lines.append("")

        max_files = config.max_files_shown if config.output_style == "verbose" else 10

        if desc.changes.get("added"):
            lines.append("**Additional files added:**")
            for f in desc.changes["added"][:max_files]:
                lines.append(f"- `{f}`")
            if len(desc.changes["added"]) > max_files:
                lines.append(f"- ... and {len(desc.changes['added']) - max_files} more")
            lines.append("")

        if desc.changes.get("modified"):
            lines.append("**Additional files modified:**")
            for f in desc.changes["modified"][:max_files]:
                lines.append(f"- `{f}`")
            if len(desc.changes["modified"]) > max_files:
                lines.append(f"- ... and {len(desc.changes['modified']) - max_files} more")
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

    # Testing (if enabled)
    if desc.testing and config.include_testing:
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

    # Comments (if any)
    if desc.comments and config.output_style == "verbose":
        lines.append("## PR Discussion Context")
        lines.append("")
        for comment in desc.comments[:5]:
            if isinstance(comment, dict):
                lines.append(f"**@{comment['author']}:** {comment['body'][:200]}")
            else:
                lines.append(f"**@{comment.author}:** {comment.body[:200]}")
            lines.append("")

    # Stats footer (skip in minimal mode)
    if config.output_style != "minimal":
        lines.append("---")
        lines.append(
            f"*{desc.stats['commits']} commits, {desc.stats['files_changed']} files changed "
            f"(+{desc.stats['additions']}/-{desc.stats['deletions']})*"
        )

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
        desc.changes.get("added", [])
        + desc.changes.get("modified", [])
        + desc.changes.get("removed", [])
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
    lines.append(f"{stats['files_changed']} files, +{stats['additions']}/-{stats['deletions']}")

    # Breaking changes (critical - always show)
    breaking = [n for n in desc.notes if "Breaking" in n or "⚠️" in n]
    if breaking:
        lines.append("")
        lines.append(
            "⚠️ BREAKING: "
            + breaking[0].replace("⚠️ ", "").replace("**Breaking Changes:**", "").strip()
        )

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
