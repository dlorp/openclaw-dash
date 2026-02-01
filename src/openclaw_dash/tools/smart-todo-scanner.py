#!/usr/bin/env python3
"""
smart-todo-scanner.py — Intelligent TODO scanner that distinguishes
between documentation notes and actual incomplete work.

Categorizes TODOs:
- DOCSTRING: Inside docstrings (often just notes)
- COMMENT: Regular code comments (likely actual TODOs)
- INLINE: Inline with code (high priority)

Usage:
    python3 smart-todo-scanner.py <path>
"""

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


def is_in_docstring(lines: list[str], line_idx: int) -> bool:
    """Check if a line is inside a docstring."""
    # Count triple quotes before this line
    triple_single = 0
    triple_double = 0

    for i in range(line_idx):
        line = lines[i]
        triple_single += line.count("'''")
        triple_double += line.count('"""')

    # If odd number of triple quotes, we're inside a docstring
    return (triple_single % 2 == 1) or (triple_double % 2 == 1)


def categorize_todo(lines: list[str], line_idx: int, line: str) -> str:
    """Categorize a TODO based on context."""
    stripped = line.strip()

    # Check if inside docstring
    if is_in_docstring(lines, line_idx):
        return "DOCSTRING"

    # Check if it's a comment line (starts with #)
    if stripped.startswith("#"):
        return "COMMENT"

    # Check if it's inline with code
    if "#" in line and "TODO" in line.split("#")[-1]:
        # Has code before the comment
        code_part = line.split("#")[0].strip()
        if code_part and not code_part.startswith("#"):
            return "INLINE"
        return "COMMENT"

    return "COMMENT"


def scan_file(filepath: Path) -> list[TodoItem]:
    """Scan a file for TODOs."""
    todos = []

    try:
        content = filepath.read_text()
        lines = content.split("\n")
    except Exception:
        return []

    for i, line in enumerate(lines):
        if "TODO" in line or "FIXME" in line or "HACK" in line:
            category = categorize_todo(lines, i, line)

            # Extract the TODO text
            match = re.search(r"(TODO|FIXME|HACK)[:\s]*(.+)", line)
            text = match.group(2).strip() if match else line.strip()

            todos.append(
                TodoItem(file=str(filepath), line=i + 1, category=category, text=text[:80])
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


def main():
    if len(sys.argv) < 2:
        print("Usage: smart-todo-scanner.py <path>")
        sys.exit(1)

    path = Path(sys.argv[1])

    if path.is_file():
        todos = scan_file(path)
    else:
        todos = scan_directory(path, [".py", ".ts", ".tsx", ".js", ".jsx"])

    # Group by category
    by_category = {"DOCSTRING": [], "COMMENT": [], "INLINE": []}
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


if __name__ == "__main__":
    main()
