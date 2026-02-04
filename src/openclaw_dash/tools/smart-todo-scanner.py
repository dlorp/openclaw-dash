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
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

# Tool configuration schema for discovery
CONFIG_SCHEMA = {
    "show_docstrings": {
        "type": "bool",
        "default": True,
        "help": "Include TODOs found in docstrings (documentation notes)",
    },
    "output_format": {
        "type": "choice",
        "options": ["text", "json", "markdown"],
        "default": "text",
        "help": "Output format for TODO listings",
    },
    "min_priority": {
        "type": "choice",
        "options": ["LOW", "MEDIUM", "HIGH"],
        "default": "LOW",
        "help": "Minimum priority level to include in results",
    },
    "patterns": {
        "type": "list",
        "default": ["TODO", "FIXME", "HACK"],
        "help": "Patterns to search for (case-insensitive)",
    },
}


@dataclass
class TodoItem:
    file: str
    line: int
    category: str  # DOCSTRING, COMMENT, INLINE
    text: str
    priority: str  # HIGH, MEDIUM, LOW

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)


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


def compute_docstring_state(lines: list[str]) -> list[bool]:
    """Precompute docstring state for all lines in O(n) time.

    Returns a list where result[i] is True if line i is inside a docstring.
    This replaces the O(n²) approach of checking each line independently.
    """
    n = len(lines)
    in_docstring = [False] * n
    in_single_docstring = False
    in_double_docstring = False

    for i, line in enumerate(lines):
        # Track state at start of this line (before processing quotes on this line)
        was_in_docstring = in_single_docstring or in_double_docstring

        # Process all triple quotes on this line
        j = 0
        while j < len(line):
            if line[j : j + 3] == '"""':
                if not in_single_docstring:
                    in_double_docstring = not in_double_docstring
                j += 3
                continue
            if line[j : j + 3] == "'''":
                if not in_double_docstring:
                    in_single_docstring = not in_single_docstring
                j += 3
                continue
            j += 1

        # Line is in docstring if it started in one, or contains content inside quotes
        is_in_now = in_single_docstring or in_double_docstring
        in_docstring[i] = was_in_docstring or is_in_now

    return in_docstring


def is_single_line_docstring_with_todo(line: str) -> bool:
    """Check if line is a single-line docstring containing a TODO.

    Detects patterns like: '''TODO: note''' or \"\"\"FIXME: something\"\"\"
    """
    for quote in ['"""', "'''"]:
        if line.count(quote) >= 2:
            first = line.find(quote)
            second = line.find(quote, first + 3)
            if first != -1 and second != -1:
                between = line[first + 3 : second]
                if re.search(r"(TODO|FIXME|HACK)", between, re.IGNORECASE):
                    return True
    return False


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


def categorize_todo(line: str, is_in_docstring: bool) -> str:
    """Categorize a TODO based on context."""
    stripped = line.strip()

    # Check if inside docstring
    if is_in_docstring:
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


def get_priority(category: str) -> str:
    """Get priority level based on category."""
    priority_map = {"INLINE": "HIGH", "COMMENT": "MEDIUM", "DOCSTRING": "LOW"}
    return priority_map.get(category, "MEDIUM")


def find_todo_in_docstring(line: str) -> tuple[str, str] | None:
    """Find TODO/FIXME/HACK in a docstring line.

    Returns (keyword, text) tuple if found, None otherwise.
    """
    match = re.search(r"(TODO|FIXME|HACK)[:\s]*(.*)", line, re.IGNORECASE)
    if match:
        return (match.group(1), match.group(2).strip())
    return None


def scan_file(filepath: Path) -> list[TodoItem]:
    """Scan a file for TODOs.

    Uses O(n) precomputation for docstring detection instead of O(n²).
    """
    todos = []

    try:
        content = filepath.read_text()
        lines = content.split("\n")
    except Exception:
        return []

    # Precompute docstring state for all lines in O(n)
    docstring_state = compute_docstring_state(lines)

    for i, line in enumerate(lines):
        line_in_docstring = docstring_state[i]

        # Also check for single-line docstrings with TODOs
        if is_single_line_docstring_with_todo(line):
            line_in_docstring = True

        if line_in_docstring:
            # In docstrings, match TODO directly (no comment marker needed)
            todo_match = find_todo_in_docstring(line)
            if todo_match:
                keyword, text = todo_match
                category = "DOCSTRING"
                todos.append(
                    TodoItem(
                        file=str(filepath),
                        line=i + 1,
                        category=category,
                        text=text[:80] if text else f"{keyword} (no description)",
                        priority=get_priority(category),
                    )
                )
        else:
            # Outside docstrings, only look for TODOs in comments
            todo_match = find_todo_in_comment(line)
            if todo_match:
                keyword, text = todo_match
                category = categorize_todo(line, line_in_docstring)

                todos.append(
                    TodoItem(
                        file=str(filepath),
                        line=i + 1,
                        category=category,
                        text=text[:80] if text else f"{keyword} (no description)",
                        priority=get_priority(category),
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
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output in JSON format for machine processing",
    )
    parser.add_argument(
        "--skip-docstrings",
        action="store_true",
        help="Filter out TODOs inside docstrings (shows only actionable TODOs)",
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

    # Calculate totals BEFORE filtering (for summary breakdown)
    total_count = len(todos)
    docstring_count = sum(1 for t in todos if t.category == "DOCSTRING")
    actionable_count = total_count - docstring_count

    # Apply --skip-docstrings filter if requested
    if args.skip_docstrings:
        todos = [todo for todo in todos if todo.category != "DOCSTRING"]

    # Group by category
    by_category: dict[str, list[TodoItem]] = {
        "DOCSTRING": [],
        "COMMENT": [],
        "INLINE": [],
    }
    for todo in todos:
        by_category[todo.category].append(todo)

    if args.json:
        # JSON output
        output = {
            "scan_info": {
                "path": str(path),
                "extensions": args.extensions,
                "skip_docstrings": args.skip_docstrings,
            },
            "todos": [todo.to_dict() for todo in todos],
            "summary": {
                "total": total_count,
                "actionable": actionable_count,
                "in_docstrings": docstring_count,
                "by_category": {
                    "INLINE": len(by_category["INLINE"]),
                    "COMMENT": len(by_category["COMMENT"]),
                    "DOCSTRING": len(by_category["DOCSTRING"]),
                },
                "by_priority": {
                    "HIGH": len([t for t in todos if t.priority == "HIGH"]),
                    "MEDIUM": len([t for t in todos if t.priority == "MEDIUM"]),
                    "LOW": len([t for t in todos if t.priority == "LOW"]),
                },
            },
        }
        print(json.dumps(output, indent=2))
    else:
        # Human-readable prose output
        filter_note = " (actionable only)" if args.skip_docstrings else ""
        print(f"## 📝 Smart TODO Scan{filter_note}")
        print(f"**Path:** {path}")
        # Show breakdown format: "116 TODOs (21 actionable, 95 in docstrings)"
        print(
            f"**Total:** {total_count} TODOs "
            f"({actionable_count} actionable, {docstring_count} in docstrings)"
        )
        print()

        print("### ⚠️ INLINE (code TODOs - high priority)")
        if by_category["INLINE"]:
            for t in by_category["INLINE"][:10]:
                print(f"  {t.file}:{t.line} — {t.text}")
            if len(by_category["INLINE"]) > 10:
                print(f"  ... and {len(by_category['INLINE']) - 10} more")
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

        if not args.skip_docstrings:
            print(f"### 📚 DOCSTRING ({len(by_category['DOCSTRING'])} items - documentation notes)")
            if by_category["DOCSTRING"]:
                print(f"  {len(by_category['DOCSTRING'])} documentation notes (low priority)")
            else:
                print("  *None*")
            print()

        # Summary line
        print("---")
        if args.skip_docstrings:
            print(
                f"**Showing:** {len(todos)} actionable TODOs "
                f"(filtered {docstring_count} docstrings)"
            )
        else:
            print(
                f"**Actionable:** {actionable_count} | **Documentation notes:** {docstring_count}"
            )

    return 0


if __name__ == "__main__":
    sys.exit(main())
