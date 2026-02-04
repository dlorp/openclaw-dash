"""
tool_schemas.py — Discover and aggregate CONFIG_SCHEMA from tools.

Scans tool files for CONFIG_SCHEMA dictionaries and provides a unified
interface for retrieving tool configuration schemas.

Usage:
    from tool_schemas import discover_tool_schemas, get_tool_schema

    # Get all schemas
    schemas = discover_tool_schemas(Path("src/openclaw_dash/tools"))

    # Get specific tool schema
    schema = get_tool_schema("repo-scanner")
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Any


def _tool_name_from_path(path: Path) -> str:
    """Convert tool file path to tool name (strip .py, keep hyphens)."""
    return path.stem


def _extract_config_schema(file_path: Path) -> dict[str, Any] | None:
    """Extract CONFIG_SCHEMA dict from a Python file using AST parsing.

    Args:
        file_path: Path to the Python file

    Returns:
        The CONFIG_SCHEMA dict if found, None otherwise
    """
    try:
        source = file_path.read_text()
        tree = ast.parse(source)
    except (SyntaxError, OSError):
        return None

    for node in ast.walk(tree):
        # Look for top-level assignment: CONFIG_SCHEMA = {...}
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "CONFIG_SCHEMA":
                    # Try to safely evaluate the dict literal
                    try:
                        return ast.literal_eval(node.value)
                    except (ValueError, TypeError):
                        # Not a simple literal, skip
                        return None
    return None


def discover_tool_schemas(tools_dir: Path) -> dict[str, dict[str, Any]]:
    """Scan tools directory and extract CONFIG_SCHEMA from each tool.

    Args:
        tools_dir: Path to the tools directory

    Returns:
        Dict mapping tool names to their CONFIG_SCHEMA dicts.
        Tools without CONFIG_SCHEMA are omitted.

    Example:
        >>> schemas = discover_tool_schemas(Path("src/openclaw_dash/tools"))
        >>> schemas
        {
            "repo-scanner": {
                "skip_docstrings": {"type": "bool", "default": False, ...},
                ...
            },
            "pr-tracker": {...},
        }
    """
    if not tools_dir.is_dir():
        return {}

    schemas: dict[str, dict[str, Any]] = {}

    for tool_file in tools_dir.glob("*.py"):
        # Skip __init__.py and other special files
        if tool_file.name.startswith("_"):
            continue
        # Skip config.py (shared config, not a tool)
        if tool_file.name == "config.py":
            continue

        tool_name = _tool_name_from_path(tool_file)
        schema = _extract_config_schema(tool_file)

        if schema is not None:
            schemas[tool_name] = schema

    return schemas


def get_tool_schema(tool_name: str, tools_dir: Path | None = None) -> dict[str, Any] | None:
    """Get CONFIG_SCHEMA for a specific tool.

    Args:
        tool_name: Name of the tool (e.g., "repo-scanner")
        tools_dir: Optional path to tools directory. Defaults to
                   src/openclaw_dash/tools relative to this file.

    Returns:
        The CONFIG_SCHEMA dict if found, None otherwise
    """
    if tools_dir is None:
        # Default to tools/ relative to this module's parent
        tools_dir = Path(__file__).parent / "tools"

    tool_file = tools_dir / f"{tool_name}.py"
    if not tool_file.exists():
        return None

    return _extract_config_schema(tool_file)


def list_tools_with_schemas(tools_dir: Path | None = None) -> list[str]:
    """List all tools that have CONFIG_SCHEMA defined.

    Args:
        tools_dir: Optional path to tools directory.

    Returns:
        List of tool names with schemas
    """
    if tools_dir is None:
        tools_dir = Path(__file__).parent / "tools"

    schemas = discover_tool_schemas(tools_dir)
    return sorted(schemas.keys())


if __name__ == "__main__":
    import json
    import sys

    # Default tools directory
    default_dir = Path(__file__).parent / "tools"
    tools_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else default_dir

    print(f"Scanning: {tools_dir}")
    schemas = discover_tool_schemas(tools_dir)

    if not schemas:
        print("No tools with CONFIG_SCHEMA found.")
    else:
        print(f"\nFound {len(schemas)} tool(s) with schemas:\n")
        print(json.dumps(schemas, indent=2))
