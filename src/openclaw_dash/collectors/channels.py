"""Channels collector - Discord, Telegram, Signal status."""

import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

from openclaw_dash.demo import is_demo_mode, mock_channels

# PyYAML is optional - only needed for reading config files directly
try:
    import yaml

    HAS_YAML = True
except ImportError:
    HAS_YAML = False


def _parse_yaml_config(config_path: Path) -> dict[str, Any] | None:
    """Parse YAML config file if PyYAML is available.

    Args:
        config_path: Path to the YAML config file.

    Returns:
        Parsed config dict or None if parsing fails.
    """
    if not HAS_YAML:
        return None

    try:
        return yaml.safe_load(config_path.read_text())  # type: ignore[union-attr]
    except (OSError, yaml.YAMLError):  # type: ignore[attr-defined]
        return None


def collect() -> dict[str, Any]:
    """Collect channel connection status."""
    # Return mock data in demo mode
    if is_demo_mode():
        channels = mock_channels()
        connected = sum(1 for c in channels if c.get("status") == "connected")
        return {
            "channels": channels,
            "connected": connected,
            "total": len(channels),
            "collected_at": datetime.now().isoformat(),
        }

    result: dict[str, Any] = {
        "channels": [],
        "connected": 0,
        "total": 0,
        "collected_at": datetime.now().isoformat(),
    }

    # Try to read OpenClaw config for channel info
    config_path = Path.home() / ".openclaw" / "config.yaml"
    if not config_path.exists():
        config_path = Path.home() / ".openclaw" / "config.yml"

    if config_path.exists():
        config = _parse_yaml_config(config_path)
        if config is not None:
            channels_config = config.get("channels", {})

            for channel_type in ["discord", "telegram", "signal", "slack", "whatsapp"]:
                channel_conf = channels_config.get(channel_type, {})
                if channel_conf:
                    enabled = channel_conf.get("enabled", True)
                    # Check if channel appears configured
                    has_token = bool(
                        channel_conf.get("token")
                        or channel_conf.get("botToken")
                        or channel_conf.get("apiKey")
                    )

                    status = "disabled"
                    if enabled and has_token:
                        status = "configured"
                        # Try to verify connection
                        if _check_channel_health(channel_type):
                            status = "connected"

                    result["channels"].append(
                        {
                            "type": channel_type,
                            "status": status,
                            "enabled": enabled,
                        }
                    )
                    result["total"] += 1
                    if status == "connected":
                        result["connected"] += 1

    # Fallback: try openclaw CLI if available
    if not result["channels"]:
        try:
            proc = subprocess.run(
                ["openclaw", "status", "--json"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if proc.returncode == 0:
                data = json.loads(proc.stdout)
                for ch in data.get("channels", []):
                    result["channels"].append(
                        {
                            "type": ch.get("type", "unknown"),
                            "status": ch.get("status", "unknown"),
                            "enabled": ch.get("enabled", False),
                        }
                    )
                    result["total"] += 1
                    if ch.get("status") == "connected":
                        result["connected"] += 1
        except (subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError):
            pass

    return result


def _check_channel_health(channel_type: str) -> bool:
    """Check if a channel is actually connected."""
    # For now, we assume configured = connected
    # In the future, we could ping each service
    return True


def get_channel_icon(channel_type: str) -> str:
    """Get emoji icon for channel type."""
    icons = {
        "discord": "",
        "telegram": "",
        "signal": "",
        "slack": "",
        "whatsapp": "",
        "imessage": "",
    }
    return icons.get(channel_type, "")


def get_status_icon(status: str) -> str:
    """Get status indicator."""
    icons = {
        "connected": "✓",
        "configured": "○",
        "disabled": "—",
        "error": "✗",
    }
    return icons.get(status, "?")
