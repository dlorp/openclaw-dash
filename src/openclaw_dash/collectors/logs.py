"""Logs collector for OpenClaw gateway logs."""

from __future__ import annotations

import os
import re
from collections import deque
from datetime import datetime
from pathlib import Path
from typing import Any

from openclaw_dash.demo import is_demo_mode

# Log parsing regex
LOG_PATTERN = re.compile(r"^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z)\s+\[([^\]]+)\]\s+(.*)$")

# Default log locations to check
LOG_PATHS = [
    Path(os.path.expanduser("~/.openclaw/logs/gateway.log")),
    Path("/tmp/openclaw/openclaw-{date}.log"),
]


def find_log_file() -> Path | None:
    """Find the OpenClaw gateway log file."""
    today = datetime.now().strftime("%Y-%m-%d")

    for path_template in LOG_PATHS:
        path = Path(str(path_template).format(date=today))
        if path.exists():
            return path

    return None


def parse_log_line(line: str) -> dict[str, Any] | None:
    """Parse a single log line."""
    match = LOG_PATTERN.match(line.strip())
    if not match:
        return None

    timestamp, tag, message = match.groups()
    return {
        "timestamp": timestamp,
        "tag": tag,
        "message": message,
        "raw": line.strip(),
    }


def get_log_level(tag: str, message: str) -> str:
    """Infer log level from tag and message content."""
    message_lower = message.lower()
    tag_lower = tag.lower()

    if any(word in message_lower for word in ["error", "failed", "exception"]):
        return "error"
    elif any(word in message_lower for word in ["warn", "warning"]):
        return "warning"
    elif any(word in tag_lower for word in ["error", "err"]):
        return "error"
    elif "disconnect" in message_lower or "shutting down" in message_lower:
        return "warning"
    elif "started" in message_lower or "ready" in message_lower or "listening" in message_lower:
        return "info"
    else:
        return "debug"


def get_level_color(level: str) -> str:
    """Get Rich color for log level."""
    colors = {
        "error": "red",
        "warning": "yellow",
        "info": "green",
        "debug": "dim",
    }
    return colors.get(level, "white")


def get_level_icon(level: str) -> str:
    """Get icon for log level."""
    icons = {
        "error": "✗",
        "warning": "⚠",
        "info": "•",
        "debug": "·",
    }
    return icons.get(level, "•")


def tail_file(path: Path, n: int = 50) -> list[str]:
    """Read last n lines from a file efficiently."""
    try:
        with open(path, "rb") as f:
            # Seek to end
            f.seek(0, 2)
            file_size = f.tell()

            # Read in chunks from the end
            chunk_size = 8192
            lines: deque[str] = deque(maxlen=n)
            remaining = b""

            while file_size > 0 and len(lines) < n:
                read_size = min(chunk_size, file_size)
                file_size -= read_size
                f.seek(file_size)
                chunk = f.read(read_size) + remaining
                remaining = b""

                # Split by newlines
                chunk_lines = chunk.split(b"\n")

                # First chunk part might be incomplete
                if file_size > 0:
                    remaining = chunk_lines[0]
                    chunk_lines = chunk_lines[1:]

                # Add lines in reverse order
                for line in reversed(chunk_lines):
                    if line:
                        try:
                            lines.appendleft(line.decode("utf-8", errors="replace"))
                        except Exception:
                            pass
                    if len(lines) >= n:
                        break

            return list(lines)[-n:]
    except OSError:
        return []


def collect(
    n: int = 50,
    log_path: Path | None = None,
    filter_tags: list[str] | None = None,
    filter_level: str | None = None,
) -> dict[str, Any]:
    """Collect recent log entries.

    Args:
        n: Number of log lines to return
        log_path: Override log file path
        filter_tags: Only include logs with these tags
        filter_level: Minimum log level (error, warning, info, debug)

    Returns:
        Dictionary with log entries and metadata
    """
    # Return mock data in demo mode
    if is_demo_mode():
        now = datetime.now()
        mock_entries = [
            {
                "timestamp": (now.replace(second=0)).isoformat() + "Z",
                "tag": "gateway",
                "message": "Gateway started successfully",
                "level": "info",
            },
            {
                "timestamp": (now.replace(second=15)).isoformat() + "Z",
                "tag": "ws",
                "message": "WebSocket connection established",
                "level": "info",
            },
            {
                "timestamp": (now.replace(second=30)).isoformat() + "Z",
                "tag": "session",
                "message": "Session main:discord initialized",
                "level": "debug",
            },
            {
                "timestamp": (now.replace(second=45)).isoformat() + "Z",
                "tag": "tool",
                "message": "exec: command completed in 245ms",
                "level": "debug",
            },
        ]
        return {
            "entries": mock_entries[:n],
            "log_file": "/mock/logs/gateway.log",
            "total": len(mock_entries[:n]),
            "levels": {"error": 0, "warning": 0, "info": 2, "debug": 2},
            "collected_at": now.isoformat(),
        }

    path = log_path or find_log_file()

    if not path or not path.exists():
        return {
            "entries": [],
            "log_file": None,
            "total": 0,
            "error": "Log file not found",
            "collected_at": datetime.now().isoformat(),
        }

    # Read more lines to account for filtering
    raw_lines = tail_file(path, n * 3 if (filter_tags or filter_level) else n)

    entries = []
    level_priority = {"error": 0, "warning": 1, "info": 2, "debug": 3}
    min_priority = level_priority.get(filter_level or "debug", 3)

    for line in raw_lines:
        parsed = parse_log_line(line)
        if not parsed:
            continue

        tag = parsed["tag"]
        message = parsed["message"]
        level = get_log_level(tag, message)
        parsed["level"] = level

        # Apply filters
        if filter_tags and tag not in filter_tags:
            continue
        if level_priority.get(level, 3) > min_priority:
            continue

        entries.append(parsed)

    # Limit to requested count
    entries = entries[-n:]

    # Count by level
    level_counts = {"error": 0, "warning": 0, "info": 0, "debug": 0}
    for entry in entries:
        level = entry.get("level", "debug")
        level_counts[level] = level_counts.get(level, 0) + 1

    return {
        "entries": entries,
        "log_file": str(path),
        "total": len(entries),
        "levels": level_counts,
        "collected_at": datetime.now().isoformat(),
    }
