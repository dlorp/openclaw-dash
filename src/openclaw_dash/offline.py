"""Gateway-independent features and error handling.

The OpenClaw gateway runs LOCALLY on the user's machine. After initial setup
(pip install, git clone), everything should work without network access.

This module identifies which features require the gateway to be running
vs which work independently. If the gateway is unavailable, it's likely
because it hasn't been started — not because of network issues.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

# Global flag to skip gateway checks (for testing/development)
_skip_gateway: bool = False

# Features that work without the gateway running
# (These are local operations that don't need gateway connectivity)
GATEWAY_INDEPENDENT_FEATURES = {
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
        "description": "PR tracking (local tool)",
    },
}

# For backwards compatibility
OFFLINE_FEATURES = GATEWAY_INDEPENDENT_FEATURES

# Features that require the gateway to be running
GATEWAY_REQUIRED_FEATURES = {
    "sessions": "Active sessions and agents",
    "activity": "Real-time activity monitoring",
    "gateway_status": "Gateway health and context",
    "cron": "Scheduled tasks",
    "billing": "Cost and usage data",
    "logs": "Live log streaming",
}

# For backwards compatibility
GATEWAY_FEATURES = GATEWAY_REQUIRED_FEATURES


@dataclass
class GatewayErrorHint:
    """A hint about what to do when gateway is unavailable."""

    feature_name: str
    error_message: str
    independent_commands: list[str]
    primary_suggestion: str | None = None

    def format_message(self, include_commands: bool = True) -> str:
        """Format the hint as a user-friendly message.

        Args:
            include_commands: Whether to include command suggestions.

        Returns:
            Formatted error message with suggestions.
        """
        lines = [self.error_message]

        if include_commands and self.independent_commands:
            lines.append("")
            lines.append("These commands don't require the gateway:")
            for cmd in self.independent_commands[:3]:  # Show top 3
                lines.append(f"  • {cmd}")

        return "\n".join(lines)

    def format_short(self) -> str:
        """Format a short version for compact displays."""
        if self.primary_suggestion:
            return f"{self.error_message} Try: {self.primary_suggestion}"
        return self.error_message


# Backwards compatibility alias
OfflineHint = GatewayErrorHint


def is_offline_mode() -> bool:
    """Check if gateway checks should be skipped.

    Note: This is primarily for testing/development. The gateway runs
    locally, so "offline mode" is not really a thing in normal use.

    Returns:
        True if gateway checks should be skipped.
    """
    return _skip_gateway or os.environ.get("OPENCLAW_DASH_SKIP_GATEWAY", "").lower() in (
        "1",
        "true",
        "yes",
    )


def enable_offline_mode() -> None:
    """Enable skipping gateway checks (for testing)."""
    global _skip_gateway
    _skip_gateway = True


def disable_offline_mode() -> None:
    """Disable skipping gateway checks."""
    global _skip_gateway
    _skip_gateway = False


def get_offline_hint(feature: str, error: str | None = None) -> GatewayErrorHint:
    """Get a hint for when a gateway-dependent feature fails.

    The gateway runs locally, so failures are typically either:
    - Gateway not started yet (run `openclaw gateway start`)
    - A bug (unexpected timeout or hang)

    Args:
        feature: Name of the feature that failed.
        error: Optional error message from the failure.

    Returns:
        GatewayErrorHint with suggestions.
    """
    # Check if this is a timeout (likely a bug since gateway is local)
    is_timeout = error and ("timeout" in error.lower() or "timed out" in error.lower())

    if is_timeout:
        return GatewayErrorHint(
            feature_name=feature,
            error_message="Command timed out unexpectedly — this may be a bug",
            independent_commands=[
                "Run `openclaw gateway status` to check gateway health",
                "Run `openclaw gateway restart` if the gateway is stuck",
                "Report at: https://github.com/dlorp/openclaw-dash/issues",
            ],
            primary_suggestion="openclaw gateway status",
        )

    # Build the error message for non-timeout errors
    if error:
        error_msg = f"Gateway error: {error}"
    else:
        error_msg = "Gateway not responding"

    commands = [
        "Run `openclaw gateway start` to start the gateway",
        f"`{GATEWAY_INDEPENDENT_FEATURES['security']['command']}` - "
        f"{GATEWAY_INDEPENDENT_FEATURES['security']['description']}",
    ]

    return GatewayErrorHint(
        feature_name=feature,
        error_message=error_msg,
        independent_commands=commands,
        primary_suggestion="openclaw gateway start",
    )


def format_gateway_error(
    error: str | None = None,
    context: str | None = None,
    verbose: bool = False,
) -> str:
    """Format a gateway error message.

    The gateway runs locally, so errors are typically either:
    - Gateway not started yet (run `openclaw gateway start`)
    - A bug (unexpected timeout or hang)

    Args:
        error: The error message from the connection attempt.
        context: Additional context about what was being attempted.
        verbose: Whether to include additional troubleshooting info.

    Returns:
        Formatted error message with suggestions.
    """
    lines = []

    # Check if this looks like a timeout (potential bug since gateway is local)
    is_timeout = error and ("timeout" in error.lower() or "timed out" in error.lower())

    if is_timeout:
        lines.append("⊘ Command timed out unexpectedly")
        if context:
            lines.append(f"  ({context})")
        lines.append("")
        lines.append("The gateway runs locally — this may be a bug.")
        lines.append("Please report: https://github.com/dlorp/openclaw-dash/issues")
    else:
        if error:
            lines.append(f"⊘ Gateway error: {error}")
        else:
            lines.append("⊘ Gateway not responding")

        if context:
            lines.append(f"  ({context})")

        lines.append("")
        lines.append("Try: `openclaw gateway start`")

        if verbose:
            lines.append("")
            lines.append("If this persists, please report the issue:")
            lines.append("  https://github.com/dlorp/openclaw-dash/issues")

    return "\n".join(lines)


def format_gateway_error_short(error: str | None = None) -> str:
    """Format a short gateway error for compact displays.

    Args:
        error: Optional error message to check for timeout indication.

    Returns:
        Short error message.
    """
    # Check if this is a timeout (potential bug since gateway is local)
    if error and ("timeout" in error.lower() or "timed out" in error.lower()):
        return "Command timed out unexpectedly — this may be a bug"
    return "Gateway not responding. Try: `openclaw gateway start`"


def should_skip_feature(feature: str) -> bool:
    """Check if a feature should be skipped when gateway is unavailable.

    Args:
        feature: Name of the feature to check.

    Returns:
        True if the feature requires gateway and checks are being skipped.
    """
    if not is_offline_mode():
        return False

    return feature in GATEWAY_REQUIRED_FEATURES


def get_available_offline_commands() -> list[dict[str, str]]:
    """Get list of commands that don't require the gateway.

    Returns:
        List of dicts with 'command' and 'description' keys.
    """
    return [
        {"command": info["command"], "description": info["description"]}
        for info in GATEWAY_INDEPENDENT_FEATURES.values()
    ]


def check_gateway_available() -> tuple[bool, str | None]:
    """Quick check if gateway is running.

    The gateway runs locally, so this checks the local service status.

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
        return False, "Gateway not running. Start with: openclaw gateway start"
    except subprocess.TimeoutExpired:
        return False, "Gateway check timed out (this may be a bug)"
    except FileNotFoundError:
        return False, "OpenClaw CLI not found. Install with: pip install openclaw"
    except Exception as e:
        return False, f"Unexpected error: {e}"
