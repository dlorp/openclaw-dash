"""
config.py — Shared configuration loading for openclaw-dash tools.

Loads configuration from ~/.config/openclaw-dash/tools.yaml (or XDG_CONFIG_HOME).
Provides common settings and helper functions for all tools.

Usage:
    from config import get_config, get_repos, get_org, get_repo_base

    # Get all config for a tool (merges global + tool-specific)
    cfg = get_config("pr-tracker")

    # Get common values
    repos = get_repos()           # List of repo names
    org = get_org()               # GitHub org/user
    base = get_repo_base()        # Path to cloned repos
    fmt = get_output_format()     # Default output format

Config file example (~/.config/openclaw-dash/tools.yaml):
    github_org: myusername
    repos:
      - repo1
      - repo2
    repo_base: ~/repos
    output_format: text

    # Tool-specific overrides
    pr-tracker:
      repos:
        - repo1  # Override repos list for this tool only

    repo-scanner:
      repos:
        - repo2
        - repo3
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

# Try to import yaml, fall back gracefully
try:
    import yaml

    HAS_YAML = True
except ImportError:
    HAS_YAML = False


# Default values
DEFAULTS: dict[str, Any] = {
    "github_org": "",
    "repos": ["synapse-engine", "r3LAY", "t3rra1n", "openclaw-dash"],
    "repo_base": str(Path.home() / "repos"),
    "output_format": "text",
}


def _get_config_path() -> Path:
    """Get the config file path, respecting XDG_CONFIG_HOME."""
    xdg_config = os.environ.get("XDG_CONFIG_HOME")
    if xdg_config:
        base = Path(xdg_config)
    else:
        base = Path.home() / ".config"
    return base / "openclaw-dash" / "tools.yaml"


def _load_config_file() -> dict[str, Any]:
    """Load the config file if it exists."""
    config_path = _get_config_path()

    if not config_path.exists():
        return {}

    if not HAS_YAML:
        # Can't parse YAML without the library
        return {}

    try:
        with open(config_path) as f:
            data = yaml.safe_load(f)
            return data if isinstance(data, dict) else {}
    except Exception:
        return {}


# Cache the loaded config
_config_cache: dict[str, Any] | None = None


def _get_raw_config() -> dict[str, Any]:
    """Get the raw config, loading from file if needed."""
    global _config_cache
    if _config_cache is None:
        _config_cache = _load_config_file()
    return _config_cache


def reload_config() -> None:
    """Force reload of config from file."""
    global _config_cache
    _config_cache = None


def get_config(tool_name: str | None = None) -> dict[str, Any]:
    """
    Get configuration, optionally merged with tool-specific overrides.

    Args:
        tool_name: Optional tool name (e.g., "pr-tracker") for tool-specific config

    Returns:
        Dict with configuration values. Tool-specific values override global ones.
    """
    raw = _get_raw_config()

    # Start with defaults
    config: dict[str, Any] = dict(DEFAULTS)

    # Merge global config (top-level keys that aren't tool names)
    tool_keys = {"pr-tracker", "pr-describe", "repo-scanner", "dep-shepherd"}
    for key, value in raw.items():
        if key not in tool_keys:
            config[key] = value

    # Merge tool-specific config if requested
    if tool_name and tool_name in raw:
        tool_config = raw[tool_name]
        if isinstance(tool_config, dict):
            for key, value in tool_config.items():
                config[key] = value

    # Environment variable overrides (highest priority)
    env_org = os.environ.get("GITHUB_ORG")
    if env_org:
        config["github_org"] = env_org

    return config


def get_repos(tool_name: str | None = None) -> list[str]:
    """
    Get the list of repos to work with.

    Args:
        tool_name: Optional tool name for tool-specific repo list

    Returns:
        List of repository names
    """
    config = get_config(tool_name)
    repos = config.get("repos", DEFAULTS["repos"])
    return repos if isinstance(repos, list) else DEFAULTS["repos"]


def get_org() -> str:
    """
    Get the GitHub org/username.

    Returns:
        GitHub org string, or empty string if not configured

    Raises:
        ValueError: If org is not configured (use require_org=True behavior)
    """
    config = get_config()
    return config.get("github_org", "")


def get_repo_base() -> Path:
    """
    Get the base path for cloned repos.

    Returns:
        Path to the repos directory
    """
    config = get_config()
    base = config.get("repo_base", DEFAULTS["repo_base"])
    # Expand ~ in path
    return Path(base).expanduser()


def get_output_format() -> str:
    """
    Get the default output format.

    Returns:
        Output format string (e.g., "text", "json", "markdown")
    """
    config = get_config()
    return config.get("output_format", DEFAULTS["output_format"])


def require_org() -> str:
    """
    Get the GitHub org, raising an error if not configured.

    Returns:
        GitHub org string

    Raises:
        SystemExit: If org is not configured
    """
    import sys

    org = get_org()
    if not org:
        print(
            "Error: GitHub org not configured.\n"
            "Set GITHUB_ORG environment variable or add to config:\n"
            f"  {_get_config_path()}\n\n"
            "Example config:\n"
            "  github_org: your-username\n"
            "  repos:\n"
            "    - repo1\n"
            "    - repo2",
            file=sys.stderr,
        )
        sys.exit(1)
    return org


def get_config_path() -> Path:
    """Get the config file path (for display/debugging)."""
    return _get_config_path()
