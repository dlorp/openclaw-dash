#!/usr/bin/env python3
"""
smart-todo-scanner.py — Intelligent TODO scanner that distinguishes
between documentation notes and actual incomplete work.

Categorizes TODOs:
- DOCSTRING: Inside docstrings (often just notes)
- COMMENT: Regular code comments (likely actual TODOs)
- INLINE: Inline with code (high priority)

Usage:
    python3 smart-todo-scanner.py [path]
    python3 smart-todo-scanner.py --help
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass
class TodoItem:
    file: str
    line: int
    category: str  # DOCSTRING, COMMENT, INLINE
    text: str


# Regex to match TODOs only in comments, not string literals
# Matches: # TODO, // TODO, /* TODO, * TODO (for multi-line comments)
TODO_COMMENT_PATTERN = re.compile(
    r"""
    (?:
        ^\s*[#].*                     # Line starting with # (Python comment)
        |
        ^\s*//.*                      # Line starting with // (JS/TS comment)
        |
        ^\s*/\*.*                     # Line starting with /* (block comment start)
        |
        ^\s*\*\s.*                    # Line starting with * (inside block comment)
        |
        [^"']\s*[#].*                 # # after code but not in string
        |
        [^"']\s*//.*                  # // after code but not in string
    )
    (TODO|FIXME|HACK)[:\s]*(.*)
    """,
    re.VERBOSE | re.IGNORECASE,
)


def is_in_docstring(lines: list[str], line_idx: int) -> bool:
    """Check if a line is inside a docstring.

    Properly handles multi-line docstrings by tracking open/close state.
    Also detects single-line docstrings (e.g., '''TODO: note''').
    """
    current_line = lines[line_idx]

    # Check if current line is a single-line docstring (opens and closes on same line)
    # Must have at least 2 sets of triple quotes
    double_count = current_line.count('"""')
    single_count = current_line.count("'''")
    if double_count >= 2 or single_count >= 2:
        # It's a single-line docstring - check if TODO is between the quotes
        for quote in ['"""', "'''"]:
            if current_line.count(quote) >= 2:
                first = current_line.find(quote)
                second = current_line.find(quote, first + 3)
                if first != -1 and second != -1:
                    # Check if there's a TODO between the quotes
                    between = current_line[first + 3 : second]
                    if re.search(r"(TODO|FIXME|HACK)", between, re.IGNORECASE):
                        return True

    # Check if we're inside a multi-line docstring (opened on a previous line)
    in_single_docstring = False
    in_double_docstring = False

    for i in range(line_idx):
        line = lines[i]

        # Track state transitions through triple quotes
        j = 0
        while j < len(line):
            # Check for triple double quotes
            if line[j : j + 3] == '"""':
                if not in_single_docstring:
                    in_double_docstring = not in_double_docstring
                j += 3
                continue
            # Check for triple single quotes
            if line[j : j + 3] == "'''":
                if not in_double_docstring:
                    in_single_docstring = not in_single_docstring
                j += 3
                continue
            j += 1

    return in_single_docstring or in_double_docstring


def is_in_string_literal(line: str, match_start: int) -> bool:
    """Check if a position in a line is inside a string literal."""
    in_single = False
    in_double = False
    i = 0

    while i < match_start:
        char = line[i]

        # Handle escape sequences
        if char == "\\" and i + 1 < len(line):
            i += 2
            continue

        if char == '"' and not in_single:
            in_double = not in_double
        elif char == "'" and not in_double:
            in_single = not in_single

        i += 1

    return in_single or in_double


def find_todo_in_comment(line: str) -> tuple[str, str] | None:
    """Find TODO/FIXME/HACK in a comment, not in string literals.

    Returns (keyword, text) tuple if found, None otherwise.
    """
    # Find all potential TODO/FIXME/HACK matches
    for match in re.finditer(r"(TODO|FIXME|HACK)[:\s]*(.*)", line, re.IGNORECASE):
        match_start = match.start()

        # Check if this match is in a string literal
        if is_in_string_literal(line, match_start):
            continue

        # Check if it's in a comment
        # For Python: check if there's a # before the match (not in a string)
        comment_start = -1
        for i, char in enumerate(line[:match_start]):
            if char == "#" and not is_in_string_literal(line, i):
                comment_start = i
                break

        # For JS/TS: check for // comment
        if comment_start == -1:
            for i in range(match_start):
                if line[i : i + 2] == "//" and not is_in_string_literal(line, i):
                    comment_start = i
                    break

        if comment_start != -1 and comment_start < match_start:
            return (match.group(1), match.group(2).strip())

    return None


def categorize_todo(lines: list[str], line_idx: int, line: str) -> str:
    """Categorize a TODO based on context."""
    stripped = line.strip()

    # Check if inside docstring
    if is_in_docstring(lines, line_idx):
        return "DOCSTRING"

    # Check if it's a pure comment line (starts with # or //)
    if stripped.startswith("#") or stripped.startswith("//"):
        return "COMMENT"

    # Check if it's inline with code
    if "#" in line or "//" in line:
        # Find comment position
        comment_pos = len(line)
        for i, char in enumerate(line):
            if char == "#" and not is_in_string_literal(line, i):
                comment_pos = i
                break
            if line[i : i + 2] == "//" and not is_in_string_literal(line, i):
                comment_pos = i
                break

        # Has code before the comment
        code_part = line[:comment_pos].strip()
        if code_part:
            return "INLINE"

    return "COMMENT"


def find_todo_in_docstring(line: str) -> tuple[str, str] | None:
    """Find TODO/FIXME/HACK in a docstring line.

    Returns (keyword, text) tuple if found, None otherwise.
    """
    match = re.search(r"(TODO|FIXME|HACK)[:\s]*(.*)", line, re.IGNORECASE)
    if match:
        return (match.group(1), match.group(2).strip())
    return None


def scan_file(filepath: Path) -> list[TodoItem]:
    """Scan a file for TODOs."""
    todos = []

    try:
        content = filepath.read_text()
        lines = content.split("\n")
    except Exception:
        return []

    for i, line in enumerate(lines):
        # Check if we're inside a docstring first
        if is_in_docstring(lines, i):
            # In docstrings, match TODO directly (no comment marker needed)
            todo_match = find_todo_in_docstring(line)
            if todo_match:
                keyword, text = todo_match
                todos.append(
                    TodoItem(
                        file=str(filepath),
                        line=i + 1,
                        category="DOCSTRING",
                        text=text[:80] if text else f"{keyword} (no description)",
                    )
                )
        else:
            # Outside docstrings, only look for TODOs in comments
            todo_match = find_todo_in_comment(line)
            if todo_match:
                keyword, text = todo_match
                category = categorize_todo(lines, i, line)

                todos.append(
                    TodoItem(
                        file=str(filepath),
                        line=i + 1,
                        category=category,
                        text=text[:80] if text else f"{keyword} (no description)",
                    )
                )

    return todos


def scan_directory(path: Path, extensions: list[str]) -> list[TodoItem]:
    """Scan a directory recursively."""
    todos = []

    for ext in extensions:
        for filepath in path.rglob(f"*{ext}"):
            # Skip common ignore patterns
            if any(p in str(filepath) for p in ["node_modules", "__pycache__", ".git", "venv"]):
                continue
            todos.extend(scan_file(filepath))

    return todos


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Intelligent TODO scanner that distinguishes between "
        "documentation notes and actual incomplete work.",
        epilog="Examples:\n"
        "  %(prog)s                    # Scan current directory\n"
        "  %(prog)s ./src              # Scan src directory\n"
        "  %(prog)s myfile.py          # Scan single file\n",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "path",
        nargs="?",
        default=".",
        help="Path to scan (file or directory). Defaults to current directory.",
    )
    parser.add_argument(
        "--extensions",
        "-e",
        nargs="+",
        default=[".py", ".ts", ".tsx", ".js", ".jsx"],
        help="File extensions to scan (default: .py .ts .tsx .js .jsx)",
    )

    args = parser.parse_args()
    path = Path(args.path)

    # Validate path exists
    if not path.exists():
        print(f"Error: Path '{path}' does not exist.", file=sys.stderr)
        return 1

    if path.is_file():
        todos = scan_file(path)
    else:
        todos = scan_directory(path, args.extensions)

    # Group by category
    by_category: dict[str, list[TodoItem]] = {
        "DOCSTRING": [],
        "COMMENT": [],
        "INLINE": [],
    }
    for todo in todos:
        by_category[todo.category].append(todo)

    # Print report
    print("## 📝 Smart TODO Scan")
    print(f"**Path:** {path}")
    print(f"**Total:** {len(todos)} TODOs found")
    print()

    print("### ⚠️ INLINE (code TODOs - high priority)")
    if by_category["INLINE"]:
        for t in by_category["INLINE"][:10]:
            print(f"  {t.file}:{t.line} — {t.text}")
    else:
        print("  *None*")
    print()

    print(f"### 💬 COMMENT ({len(by_category['COMMENT'])} items)")
    if by_category["COMMENT"]:
        for t in by_category["COMMENT"][:10]:
            print(f"  {t.file}:{t.line} — {t.text}")
        if len(by_category["COMMENT"]) > 10:
            print(f"  ... and {len(by_category['COMMENT']) - 10} more")
    else:
        print("  *None*")
    print()

    print(f"### 📚 DOCSTRING ({len(by_category['DOCSTRING'])} items - documentation notes)")
    if by_category["DOCSTRING"]:
        print(f"  {len(by_category['DOCSTRING'])} documentation notes (low priority)")
    else:
        print("  *None*")

    # Summary
    actionable = len(by_category["INLINE"]) + len(by_category["COMMENT"])
    docs = len(by_category["DOCSTRING"])
    print()
    print("---")
    print(f"**Actionable:** {actionable} | **Documentation notes:** {docs}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
