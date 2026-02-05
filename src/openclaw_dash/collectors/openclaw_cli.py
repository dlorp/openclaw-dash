"""Parser for `openclaw status` CLI output."""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class SessionInfo:
    """Parsed session from openclaw status."""

    key: str
    kind: str
    age: str
    model: str
    tokens_used: int
    tokens_max: int
    context_pct: float


@dataclass
class OpenClawStatus:
    """Parsed openclaw status output."""

    # Gateway info
    gateway_mode: str = "unknown"  # local, remote, etc.
    gateway_url: str = ""
    gateway_reachable: bool = False
    gateway_latency_ms: int | None = None

    # Service status
    gateway_service_status: str = "unknown"

    # Memory
    memory_enabled: bool = False
    memory_status: str = "unknown"  # unavailable, available, etc.

    # Heartbeat
    heartbeat_interval: str = ""

    # Agents/Sessions overview
    agent_count: int = 0
    session_count: int = 0
    default_model: str = ""
    default_context: int = 0

    # Channels
    channels: list[dict[str, Any]] = field(default_factory=list)

    # Sessions detail
    sessions: list[SessionInfo] = field(default_factory=list)

    # OS info
    os_info: str = ""

    # Update available
    update_available: bool = False

    # Raw output for debugging
    raw_output: str = ""


def parse_latency(text: str) -> int | None:
    """Extract latency in ms from text like 'reachable 20ms'."""
    match = re.search(r"reachable\s+(\d+)ms", text)
    return int(match.group(1)) if match else None


def parse_tokens(text: str) -> tuple[int, int, float]:
    """Parse token info like '95k/200k (48%)'."""
    match = re.search(r"([\d.]+)k/([\d.]+)k\s*\((\d+)%\)", text)
    if match:
        used = int(float(match.group(1)) * 1000)
        total = int(float(match.group(2)) * 1000)
        pct = float(match.group(3))
        return used, total, pct
    return 0, 200000, 0.0


def parse_session_count(text: str) -> int:
    """Parse session count from 'sessions 51' format."""
    match = re.search(r"sessions?\s+(\d+)", text, re.IGNORECASE)
    return int(match.group(1)) if match else 0


def parse_agent_count(text: str) -> int:
    """Parse agent count from '1 · no bootstraps' format."""
    match = re.match(r"(\d+)", text.strip())
    return int(match.group(1)) if match else 0


def parse_heartbeat(text: str) -> str:
    """Parse heartbeat interval like '30m (main)'."""
    match = re.match(r"([\d]+[smhd])", text.strip())
    return match.group(1) if match else text.strip()


def parse_status_output(output: str) -> OpenClawStatus:
    """Parse the full openclaw status output."""
    status = OpenClawStatus(raw_output=output)

    lines = output.split("\n")

    # Track current section - None means no section yet
    current_section: str | None = None

    for i, line in enumerate(lines):
        stripped = line.strip()

        # Section headers - must be on their own line (not in a table row)
        if "│" not in line:
            if stripped == "Overview" or "Overview" in stripped and not stripped.startswith("│"):
                current_section = "overview"
                continue
            # Channels section header - standalone line
            elif stripped == "Channels":
                current_section = "channels"
                continue
            # Sessions section header - must be the exact word or "Sessions" with trailing content
            elif stripped.startswith("Sessions") and not stripped.startswith("Sessions "):
                current_section = "sessions"
                continue

        # Skip table borders
        if stripped.startswith("├") or stripped.startswith("└") or stripped.startswith("┌"):
            continue

        # Parse table rows
        if "│" in line and current_section:
            parts = [p.strip() for p in line.split("│") if p.strip()]
            if len(parts) < 2:
                continue

            if current_section == "overview":
                key = parts[0].lower()
                value = parts[1] if len(parts) > 1 else ""

                if key == "gateway":
                    status.gateway_mode = value.split("·")[0].strip() if "·" in value else "unknown"
                    status.gateway_reachable = "reachable" in value.lower()
                    status.gateway_latency_ms = parse_latency(value)
                    url_match = re.search(r"(wss?://[^\s]+)", value)
                    if url_match:
                        status.gateway_url = url_match.group(1).split()[0].rstrip(")")

                elif key == "gateway service":
                    status.gateway_service_status = value

                elif key == "memory":
                    status.memory_enabled = "enabled" in value.lower()
                    if "unavailable" in value.lower():
                        status.memory_status = "unavailable"
                    elif "available" in value.lower():
                        status.memory_status = "available"
                    else:
                        status.memory_status = "unknown"

                elif key == "heartbeat":
                    status.heartbeat_interval = parse_heartbeat(value)

                elif key == "agents":
                    status.agent_count = parse_agent_count(value)
                    status.session_count = parse_session_count(value)

                elif key == "sessions":
                    active_match = re.search(r"(\d+)\s+active", value)
                    if active_match:
                        status.session_count = int(active_match.group(1))
                    model_match = re.search(r"default\s+([^\s]+)\s+\((\d+)k\s+ctx\)", value)
                    if model_match:
                        status.default_model = model_match.group(1)
                        status.default_context = int(model_match.group(2)) * 1000

                elif key == "os":
                    status.os_info = value

            elif current_section == "channels":
                # Skip header row
                if parts[0].lower() in ("channel", "item"):
                    continue
                if len(parts) >= 4:
                    status.channels.append(
                        {
                            "name": parts[0],
                            "enabled": parts[1].upper() == "ON",
                            "state": parts[2],
                            "detail": parts[3] if len(parts) > 3 else "",
                        }
                    )

            elif current_section == "sessions":
                # Skip header row
                if parts[0].lower() in ("key", "item"):
                    continue
                if len(parts) >= 5:
                    tokens_used, tokens_max, context_pct = parse_tokens(parts[4])
                    status.sessions.append(
                        SessionInfo(
                            key=parts[0],
                            kind=parts[1],
                            age=parts[2],
                            model=parts[3],
                            tokens_used=tokens_used,
                            tokens_max=tokens_max,
                            context_pct=context_pct,
                        )
                    )

    status.update_available = "update available" in output.lower()
    return status


import time as _time

# Cached status to avoid repeated slow CLI calls
_cached_status: OpenClawStatus | None = None
_cached_at: float = 0.0
_CACHE_TTL: float = 10.0  # Cache for 10 seconds


def get_openclaw_status(timeout: int = 5) -> OpenClawStatus | None:
    """Run openclaw status and parse the output.

    Results are cached for 10 seconds to avoid repeated slow CLI calls.
    """
    global _cached_status, _cached_at

    # Return cached if fresh
    now = _time.monotonic()
    if _cached_status is not None and (now - _cached_at) < _CACHE_TTL:
        return _cached_status

    try:
        result = subprocess.run(
            ["openclaw", "status"],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        status = None
        if result.stdout:
            status = parse_status_output(result.stdout)
        elif result.stderr:
            status = parse_status_output(result.stderr)

        # Cache the result (even if None, to avoid retrying immediately)
        _cached_status = status
        _cached_at = now
        return status

    except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
        # Cache the failure too
        _cached_status = None
        _cached_at = now
        return None


def status_to_gateway_data(status: OpenClawStatus) -> dict[str, Any]:
    """Convert parsed status to gateway collector format."""
    return {
        "healthy": status.gateway_reachable,
        "mode": status.gateway_mode,
        "url": status.gateway_url,
        "latency_ms": status.gateway_latency_ms,
        "service_status": status.gateway_service_status,
        "memory_enabled": status.memory_enabled,
        "memory_status": status.memory_status,
        "heartbeat_interval": status.heartbeat_interval,
        "session_count": status.session_count,
        "default_model": status.default_model,
        "os_info": status.os_info,
        "update_available": status.update_available,
        "collected_at": datetime.now().isoformat(),
    }


def status_to_sessions_data(status: OpenClawStatus) -> dict[str, Any]:
    """Convert parsed status to sessions collector format."""
    sessions = []
    for s in status.sessions:
        sessions.append(
            {
                "key": s.key,
                "kind": s.kind,
                "age": s.age,
                "model": s.model,
                "totalTokens": s.tokens_used,
                "contextTokens": s.tokens_max,
                "context_pct": s.context_pct,
            }
        )

    return {
        "sessions": sessions,
        "total": len(sessions),
        "active": len(sessions),
        "default_model": status.default_model,
        "default_context": status.default_context,
        "collected_at": datetime.now().isoformat(),
    }
