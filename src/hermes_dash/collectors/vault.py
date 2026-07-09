"""Knowledge Vault metrics collector.

Collects metrics from the HDLS knowledge vault:
- Total vault entries (markdown files)
- Domain count
- Research queue depth (pending items)
- Pipeline status from kanban.db
"""

from __future__ import annotations

import re
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

# Default vault path — works on lorpBot and M4
_VAULT_PATHS = [
    Path.home() / "repos" / "knowledge-vault",
    Path.home() / "r3LAY" / "repos" / "knowledge-vault",
]

# Kanban DB path
_KANBAN_DB = Path.home() / ".hermes" / "kanban.db"

# Directories to exclude from entry count
_SKIP_DIRS = {".git", "_meta", "_scripts", "_media", "node_modules"}


def _find_vault() -> Path | None:
    """Find the knowledge-vault directory."""
    for path in _VAULT_PATHS:
        if path.exists():
            return path
    return None


def _count_entries(vault: Path) -> int:
    """Count .md entries in vault, excluding meta/system dirs."""
    count = 0
    for item in vault.iterdir():
        if item.is_dir() and item.name not in _SKIP_DIRS:
            for md in item.rglob("*.md"):
                if ".git" not in md.parts:
                    count += 1
    return count


def _count_domains(vault: Path) -> int:
    """Count top-level domain directories."""
    return sum(
        1
        for item in vault.iterdir()
        if item.is_dir() and item.name not in _SKIP_DIRS and not item.name.startswith("_")
    )


def _count_research_queue(vault: Path) -> dict[str, int]:
    """Parse research-queue.md for pending vs resolved items."""
    queue_path = vault / "_meta" / "research-queue.md"
    if not queue_path.exists():
        return {"pending": 0, "resolved": 0, "total": 0}

    try:
        content = queue_path.read_text(errors="ignore")
    except OSError:
        return {"pending": 0, "resolved": 0, "total": 0}

    pending = len(re.findall(r"^- \[ \]", content, re.MULTILINE))
    resolved = len(re.findall(r"^- \[x\]", content, re.IGNORECASE | re.MULTILINE))

    return {"pending": pending, "resolved": resolved, "total": pending + resolved}


def _get_kanban_status() -> dict[str, Any]:
    """Read pipeline status from kanban.db."""
    if not _KANBAN_DB.exists():
        return {"error": "kanban.db not found"}

    try:
        conn = sqlite3.connect(str(_KANBAN_DB), timeout=3)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT status, COUNT(*) FROM tasks GROUP BY status"
        )
        rows = cursor.fetchall()
        conn.close()

        status_counts = {status: count for status, count in rows}
        return {
            "ready": status_counts.get("ready", 0),
            "running": status_counts.get("running", 0),
            "blocked": status_counts.get("blocked", 0),
            "done": status_counts.get("done", 0),
            "archived": status_counts.get("archived", 0),
            "total": sum(status_counts.values()),
        }
    except (sqlite3.Error, OSError):
        return {"error": "failed to read kanban.db"}


def collect() -> dict[str, Any]:
    """Collect vault metrics.

    Returns:
        Dictionary with vault entry count, domain count, research queue
        depth, and pipeline status.
    """
    vault = _find_vault()

    if vault is None:
        return {
            "available": False,
            "error": "Knowledge vault not found",
            "collected_at": datetime.now().isoformat(),
        }

    entries = _count_entries(vault)
    domains = _count_domains(vault)
    research = _count_research_queue(vault)
    pipeline = _get_kanban_status()

    return {
        "available": True,
        "entries": entries,
        "domains": domains,
        "research_queue": research,
        "pipeline": pipeline,
        "vault_path": str(vault),
        "collected_at": datetime.now().isoformat(),
    }
