"""Advanced settings management with schema validation and change callbacks.

Manages user configuration stored in ~/.config/openclaw-dash/config.toml with:
- Nested section support ([general], [tools.*], [appearance], [keybinds])
- Schema-based validation
- Type coercion (string "true" → bool True)
- Path expansion (~/ → home directory)
- Change callbacks for live updates
- Atomic file writes
"""

from __future__ import annotations

import os
import tempfile
from collections.abc import Callable
from copy import deepcopy
from pathlib import Path
from typing import Any

import tomli_w

try:
    import tomllib
except ImportError:
    import tomli as tomllib  # type: ignore[import-not-found,no-redef]

DEFAULT_CONFIG_DIR = Path.home() / ".config" / "openclaw-dash"
DEFAULT_CONFIG_PATH = DEFAULT_CONFIG_DIR / "config.toml"

# Built-in defaults for core sections
DEFAULT_SETTINGS: dict[str, Any] = {
    "general": {
        "refresh_interval": 30,
        "log_level": "info",
        "auto_save": True,
    },
    "appearance": {
        "theme": "dark",
        "font_size": 14,
        "show_notifications": True,
        "show_resources": True,
    },
    "keybinds": {
        "quit": "q",
        "refresh": "r",
        "help": "?",
    },
    "tools": {},
}

# Type coercion map: input_type -> {target_type: converter}
BOOL_TRUE_VALUES = {"true", "yes", "1", "on"}
BOOL_FALSE_VALUES = {"false", "no", "0", "off"}


def _coerce_value(value: Any, target_type: type) -> Any:
    """Coerce a value to the target type.

    Handles common conversions like:
    - "true"/"false" strings to bool
    - Numeric strings to int/float
    - Path expansion for strings containing ~/
    """
    if value is None:
        return None

    if isinstance(value, target_type):
        return value

    # String to bool
    if target_type is bool and isinstance(value, str):
        lower = value.lower()
        if lower in BOOL_TRUE_VALUES:
            return True
        if lower in BOOL_FALSE_VALUES:
            return False
        raise ValueError(f"Cannot coerce '{value}' to bool")

    # String to int/float
    if target_type is int and isinstance(value, str):
        return int(value)
    if target_type is float and isinstance(value, str):
        return float(value)

    # Bool to int (True->1, False->0)
    if target_type is int and isinstance(value, bool):
        return int(value)

    # Int to float
    if target_type is float and isinstance(value, int):
        return float(value)

    # List coercion - wrap single value
    if target_type is list and not isinstance(value, list):
        return [value]

    return value


def _expand_paths(value: Any) -> Any:
    """Recursively expand ~ in path strings."""
    if isinstance(value, str):
        if value.startswith("~/"):
            return os.path.expanduser(value)
        return value
    if isinstance(value, dict):
        return {k: _expand_paths(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_expand_paths(v) for v in value]
    return value


def _get_nested(data: dict[str, Any], keys: list[str], default: Any = None) -> Any:
    """Get a value from nested dicts using a list of keys."""
    current = data
    for key in keys:
        if not isinstance(current, dict):
            return default
        if key not in current:
            return default
        current = current[key]
    return current


def _set_nested(data: dict[str, Any], keys: list[str], value: Any) -> None:
    """Set a value in nested dicts, creating intermediate dicts as needed."""
    for key in keys[:-1]:
        if key not in data:
            data[key] = {}
        elif not isinstance(data[key], dict):
            data[key] = {}
        data = data[key]
    data[keys[-1]] = value


def _delete_nested(data: dict[str, Any], keys: list[str]) -> bool:
    """Delete a key from nested dicts. Returns True if deleted."""
    for key in keys[:-1]:
        if not isinstance(data, dict) or key not in data:
            return False
        data = data[key]
    if isinstance(data, dict) and keys[-1] in data:
        del data[keys[-1]]
        return True
    return False


ChangeCallback = Callable[[str, Any, Any], None]  # (key, old_value, new_value)


class SettingsManager:
    """Manages application settings with validation, type coercion, and change callbacks.

    Example:
        settings = SettingsManager()
        settings.get("appearance.theme")  # "dark"
        settings.set("tools.repo-scanner.skip_docstrings", True)
        settings.save()

    Supports dot-notation for nested keys: "tools.repo-scanner.max_files"
    """

    def __init__(self, config_path: Path | None = None) -> None:
        """Initialize settings manager.

        Args:
            config_path: Path to config file. Defaults to ~/.config/openclaw-dash/config.toml
        """
        self._path = config_path or DEFAULT_CONFIG_PATH
        self._data: dict[str, Any] = {}
        self._schemas: dict[str, dict[str, Any]] = {}
        self._callbacks: list[ChangeCallback] = []
        self._defaults: dict[str, Any] = deepcopy(DEFAULT_SETTINGS)

        self._load()

    def _load(self) -> None:
        """Load config from file, merging with defaults."""
        if self._path.exists():
            try:
                with open(self._path, "rb") as f:
                    file_data = tomllib.load(f)
                self._data = self._merge_defaults(file_data)
            except (tomllib.TOMLDecodeError, OSError) as e:
                import sys

                print(
                    f"Warning: Could not load config from {self._path}: {e}",
                    file=sys.stderr,
                )
                self._data = deepcopy(self._defaults)
        else:
            self._data = deepcopy(self._defaults)

    def _merge_defaults(self, data: dict[str, Any]) -> dict[str, Any]:
        """Deep merge data with defaults, preserving user values."""
        result = deepcopy(self._defaults)
        self._deep_merge(result, data)
        return result

    def _deep_merge(self, base: dict[str, Any], override: dict[str, Any]) -> None:
        """Recursively merge override into base."""
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._deep_merge(base[key], value)
            else:
                base[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        """Get a setting value by dot-notation key.

        Args:
            key: Dot-separated key path, e.g., "tools.repo-scanner.skip_docstrings"
            default: Value to return if key not found

        Returns:
            The setting value (with path expansion applied) or default
        """
        keys = key.split(".")
        value = _get_nested(self._data, keys, default)

        # Apply path expansion
        return _expand_paths(value)

    def get_raw(self, key: str, default: Any = None) -> Any:
        """Get raw value without path expansion."""
        keys = key.split(".")
        return _get_nested(self._data, keys, default)

    def set(self, key: str, value: Any) -> None:
        """Set a setting value, triggering callbacks.

        Args:
            key: Dot-separated key path
            value: Value to set (will be coerced based on schema if registered)
        """
        keys = key.split(".")
        old_value = _get_nested(self._data, keys)

        # Get expected type from schema if registered
        section = keys[0]
        if section in self._schemas:
            schema_key = ".".join(keys[1:]) if len(keys) > 1 else keys[0]
            expected_type = self._schemas[section].get(schema_key, {}).get("type")
            if expected_type:
                try:
                    value = _coerce_value(value, expected_type)
                except (ValueError, TypeError):
                    pass  # Keep original value if coercion fails

        _set_nested(self._data, keys, value)

        # Notify callbacks if value changed
        if old_value != value:
            for callback in self._callbacks:
                try:
                    callback(key, old_value, value)
                except Exception:
                    pass  # Don't let callback errors break settings

    def delete(self, key: str) -> bool:
        """Delete a setting. Returns True if the key existed."""
        keys = key.split(".")
        return _delete_nested(self._data, keys)

    def save(self) -> None:
        """Save settings to file atomically.

        Uses a temporary file + rename to ensure atomic writes.
        """
        self._path.parent.mkdir(parents=True, exist_ok=True)

        # Write to temp file first
        dir_path = self._path.parent
        try:
            with tempfile.NamedTemporaryFile(
                mode="wb",
                dir=dir_path,
                prefix=".config_",
                suffix=".tmp",
                delete=False,
            ) as tmp_file:
                tomli_w.dump(self._data, tmp_file)
                tmp_path = Path(tmp_file.name)

            # Atomic rename
            tmp_path.replace(self._path)
        except OSError:
            # Clean up temp file on failure
            if "tmp_path" in locals():
                try:
                    tmp_path.unlink()
                except OSError:
                    pass
            raise

    def reload(self) -> None:
        """Reload settings from file."""
        self._load()

    def reset_to_defaults(self, section: str | None = None) -> None:
        """Reset settings to defaults.

        Args:
            section: Optional section to reset (e.g., "appearance").
                     If None, resets all settings.
        """
        if section is None:
            old_data = self._data
            self._data = deepcopy(self._defaults)
            # Notify callbacks for all changed keys
            self._notify_changes_recursive("", old_data, self._data)
        elif section in self._defaults:
            old_section = self._data.get(section)
            self._data[section] = deepcopy(self._defaults[section])
            self._notify_changes_recursive(section, old_section, self._data[section])

    def _notify_changes_recursive(self, prefix: str, old: Any, new: Any) -> None:
        """Recursively notify callbacks for changed values."""
        if isinstance(old, dict) and isinstance(new, dict):
            all_keys = set(old.keys()) | set(new.keys())
            for key in all_keys:
                sub_prefix = f"{prefix}.{key}" if prefix else key
                old_val = old.get(key)
                new_val = new.get(key)
                if old_val != new_val:
                    if isinstance(old_val, dict) or isinstance(new_val, dict):
                        self._notify_changes_recursive(sub_prefix, old_val or {}, new_val or {})
                    else:
                        for callback in self._callbacks:
                            try:
                                callback(sub_prefix, old_val, new_val)
                            except Exception:
                                pass
        elif old != new:
            for callback in self._callbacks:
                try:
                    callback(prefix, old, new)
                except Exception:
                    pass

    def validate(self) -> list[str]:
        """Validate current settings against registered schemas.

        Returns:
            List of validation error messages. Empty list if valid.
        """
        errors: list[str] = []

        for section, schema in self._schemas.items():
            section_data = self._data.get(section, {})
            errors.extend(self._validate_section(section, section_data, schema))

        return errors

    def _validate_section(self, section: str, data: Any, schema: dict[str, Any]) -> list[str]:
        """Validate a section against its schema."""
        errors: list[str] = []

        if not isinstance(data, dict):
            if schema:  # Only error if schema expects fields
                errors.append(f"Section '{section}' must be a dictionary")
            return errors

        for key, field_schema in schema.items():
            full_key = f"{section}.{key}"
            value = data.get(key)

            # Check required
            if field_schema.get("required") and value is None:
                errors.append(f"Missing required setting: {full_key}")
                continue

            if value is None:
                continue

            # Check type
            expected_type = field_schema.get("type")
            if expected_type:
                # Try coercion first
                try:
                    coerced = _coerce_value(value, expected_type)
                    if not isinstance(coerced, expected_type):
                        errors.append(
                            f"Invalid type for '{full_key}': expected {expected_type.__name__}, "
                            f"got {type(value).__name__}"
                        )
                except (ValueError, TypeError):
                    errors.append(
                        f"Invalid type for '{full_key}': expected {expected_type.__name__}, "
                        f"got {type(value).__name__}"
                    )

            # Check allowed values
            allowed = field_schema.get("allowed")
            if allowed and value not in allowed:
                errors.append(f"Invalid value for '{full_key}': '{value}' not in {allowed}")

            # Check min/max
            min_val = field_schema.get("min")
            max_val = field_schema.get("max")
            if min_val is not None and isinstance(value, (int, float)) and value < min_val:
                errors.append(f"Value for '{full_key}' must be >= {min_val}")
            if max_val is not None and isinstance(value, (int, float)) and value > max_val:
                errors.append(f"Value for '{full_key}' must be <= {max_val}")

        return errors

    def register_schema(self, section: str, schema: dict[str, Any]) -> None:
        """Register a validation schema for a section.

        Schema format:
            {
                "field_name": {
                    "type": int,  # Expected Python type
                    "required": True,  # Whether field must be present
                    "default": 10,  # Default value
                    "allowed": ["a", "b", "c"],  # Allowed values
                    "min": 0,  # Minimum (for numbers)
                    "max": 100,  # Maximum (for numbers)
                }
            }

        Args:
            section: Section name (e.g., "general", "tools.repo-scanner")
            schema: Schema dictionary
        """
        self._schemas[section] = schema

        # Apply defaults from schema if not already set
        for field, field_schema in schema.items():
            if "default" in field_schema:
                full_key = f"{section}.{field}"
                if self.get_raw(full_key) is None:
                    self.set(full_key, field_schema["default"])

    def register_defaults(self, section: str, defaults: dict[str, Any]) -> None:
        """Register additional defaults for a section.

        Args:
            section: Section name
            defaults: Default values dict
        """
        if section not in self._defaults:
            self._defaults[section] = {}
        self._defaults[section].update(defaults)

        # Apply defaults to current data if not set
        for key, value in defaults.items():
            full_key = f"{section}.{key}"
            if self.get_raw(full_key) is None:
                self.set(full_key, value)

    def on_change(self, callback: ChangeCallback) -> Callable[[], None]:
        """Register a callback for setting changes.

        Args:
            callback: Function(key, old_value, new_value) called on changes

        Returns:
            Unsubscribe function to remove the callback
        """
        self._callbacks.append(callback)

        def unsubscribe() -> None:
            if callback in self._callbacks:
                self._callbacks.remove(callback)

        return unsubscribe

    def get_section(self, section: str) -> dict[str, Any]:
        """Get all values in a section as a dict."""
        value = self._data.get(section, {})
        return _expand_paths(deepcopy(value)) if isinstance(value, dict) else {}

    def all(self) -> dict[str, Any]:
        """Get all settings as a dict (with path expansion)."""
        return _expand_paths(deepcopy(self._data))

    @property
    def path(self) -> Path:
        """The config file path."""
        return self._path
