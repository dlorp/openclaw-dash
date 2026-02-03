"""Offline mode utilities and error messaging.

This module provides utilities for detecting offline mode and generating
helpful error messages that guide users to features that work without
a gateway connection.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

# Global offline mode flag (set via --offline CLI flag)
_offline_mode: bool = False

# Features that work without gateway connection
OFFLINE_FEATURES = {
    "security": {
        "command": "openclaw-dash security",
        "description": "Security audit (scans config files, dependencies)",
    },
    "auto_backup": {
        "command": "openclaw-dash auto backup",
        "description": "Verify backup status",
    },
    "auto_cleanup": {
        "command": "openclaw-dash auto cleanup",
        "description": "Clean up stale git branches",
    },
    "auto_deps": {
        "command": "openclaw-dash auto deps",
        "description": "Check/update dependencies",
    },
    "metrics_github": {
        "command": "openclaw-dash metrics --github",
        "description": "GitHub metrics (uses local git)",
    },
    "export": {
        "command": "openclaw-dash export",
        "description": "Export dashboard data",
    },
    "pr_tracker": {
        "command": "python3 tools/pr-tracker.py --org YOUR_ORG",
        "description": "PR tracking without gateway",
    },
}

# Features that require gateway
GATEWAY_FEATURES = {
    "sessions": "Active sessions and agents",
    "activity": "Real-time activity monitoring",
    "gateway_status": "Gateway health and context",
    "cron": "Scheduled tasks",
    "billing": "Cost and usage data",
    "logs": "Live log streaming",
}


@dataclass
class OfflineHint:
    """A hint about what works offline when a feature fails."""

    feature_name: str
    error_message: str
    offline_alternatives: list[str]
    primary_alternative: str | None = None

    def format_message(self, include_alternatives: bool = True) -> str:
        """Format the hint as a user-friendly message.

        Args:
            include_alternatives: Whether to include alternative commands.

        Returns:
            Formatted error message with offline hints.
        """
        lines = [self.error_message]

        if include_alternatives and self.offline_alternatives:
            lines.append("")
            lines.append("Offline alternatives:")
            for alt in self.offline_alternatives[:3]:  # Show top 3
                lines.append(f"  • {alt}")

        return "\n".join(lines)

    def format_short(self) -> str:
        """Format a short version for compact displays."""
        if self.primary_alternative:
            return f"{self.error_message} Try: {self.primary_alternative}"
        return self.error_message


def is_offline_mode() -> bool:
    """Check if offline mode is enabled.

    Returns:
        True if offline mode is explicitly enabled via flag or environment.
    """
    return _offline_mode or os.environ.get("OPENCLAW_DASH_OFFLINE", "").lower() in (
        "1",
        "true",
        "yes",
    )


def enable_offline_mode() -> None:
    """Enable offline mode globally."""
    global _offline_mode
    _offline_mode = True


def disable_offline_mode() -> None:
    """Disable offline mode globally."""
    global _offline_mode
    _offline_mode = False


def get_offline_hint(feature: str, error: str | None = None) -> OfflineHint:
    """Get an offline hint for a failed feature.

    Args:
        feature: Name of the feature that failed.
        error: Optional error message from the failure.

    Returns:
        OfflineHint with alternatives.
    """
    # Build the error message
    if error:
        error_msg = f"Gateway not available: {error}"
    else:
        error_msg = "Gateway not available"

    # Get relevant alternatives based on the failed feature
    alternatives = []

    # Always suggest these core offline features
    alternatives.append(
        f"`{OFFLINE_FEATURES['security']['command']}` - "
        f"{OFFLINE_FEATURES['security']['description']}"
    )
    alternatives.append(
        f"`{OFFLINE_FEATURES['auto_backup']['command']}` - "
        f"{OFFLINE_FEATURES['auto_backup']['description']}"
    )

    # Add feature-specific suggestions
    if feature in ("sessions", "activity", "gateway"):
        alternatives.append(
            f"`{OFFLINE_FEATURES['metrics_github']['command']}` - "
            f"{OFFLINE_FEATURES['metrics_github']['description']}"
        )

    if feature == "repos":
        alternatives.append(
            f"`{OFFLINE_FEATURES['auto_cleanup']['command']}` - "
            f"{OFFLINE_FEATURES['auto_cleanup']['description']}"
        )

    return OfflineHint(
        feature_name=feature,
        error_message=error_msg,
        offline_alternatives=alternatives,
        primary_alternative=OFFLINE_FEATURES["security"]["command"],
    )


def format_gateway_error(
    error: str | None = None,
    context: str | None = None,
    verbose: bool = False,
) -> str:
    """Format a gateway connection error with offline hints.

    Args:
        error: The error message from the connection attempt.
        context: Additional context about what was being attempted.
        verbose: Whether to include full command examples.

    Returns:
        Formatted error message with offline alternatives.
    """
    lines = []

    # Main error
    if error:
        lines.append(f"⊘ Gateway not available: {error}")
    else:
        lines.append("⊘ Gateway not available")

    if context:
        lines.append(f"  ({context})")

    lines.append("")
    lines.append("These features work offline:")
    lines.append("  • `openclaw-dash security`     - Security audit")
    lines.append("  • `openclaw-dash auto backup`  - Backup verification")
    lines.append("  • `openclaw-dash metrics --github` - GitHub stats")

    if verbose:
        lines.append("")
        lines.append("For PR tracking without gateway:")
        lines.append("  python3 tools/pr-tracker.py --org YOUR_ORG")

    return "\n".join(lines)


def format_gateway_error_short() -> str:
    """Format a short gateway error for compact displays.

    Returns:
        Short error message.
    """
    return "Gateway offline. Try: `openclaw-dash security`, `openclaw-dash auto backup`"


def should_skip_feature(feature: str) -> bool:
    """Check if a feature should be skipped in offline mode.

    Args:
        feature: Name of the feature to check.

    Returns:
        True if the feature requires gateway and we're in offline mode.
    """
    if not is_offline_mode():
        return False

    return feature in GATEWAY_FEATURES


def get_available_offline_commands() -> list[dict[str, str]]:
    """Get list of commands available in offline mode.

    Returns:
        List of dicts with 'command' and 'description' keys.
    """
    return [
        {"command": info["command"], "description": info["description"]}
        for info in OFFLINE_FEATURES.values()
    ]


def check_gateway_available() -> tuple[bool, str | None]:
    """Quick check if gateway is likely available.

    Does a fast check without full connection attempt.

    Returns:
        Tuple of (is_available, error_message).
    """
    import subprocess

    try:
        result = subprocess.run(
            ["openclaw", "gateway", "status"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0 and "running" in result.stdout.lower():
            return True, None
        return False, "Gateway not running"
    except subprocess.TimeoutExpired:
        return False, "Gateway check timed out"
    except FileNotFoundError:
        return False, "OpenClaw CLI not found"
    except Exception as e:
        return False, str(e)
