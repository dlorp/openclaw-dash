"""Tests for SettingsManager."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from openclaw_dash.settings_manager import (
    SettingsManager,
    _coerce_value,
    _expand_paths,
    _get_nested,
    _set_nested,
)

# --- Helper function tests ---


class TestCoerceValue:
    """Tests for _coerce_value function."""

    def test_string_to_bool_true(self) -> None:
        assert _coerce_value("true", bool) is True
        assert _coerce_value("True", bool) is True
        assert _coerce_value("TRUE", bool) is True
        assert _coerce_value("yes", bool) is True
        assert _coerce_value("1", bool) is True
        assert _coerce_value("on", bool) is True

    def test_string_to_bool_false(self) -> None:
        assert _coerce_value("false", bool) is False
        assert _coerce_value("False", bool) is False
        assert _coerce_value("no", bool) is False
        assert _coerce_value("0", bool) is False
        assert _coerce_value("off", bool) is False

    def test_string_to_bool_invalid(self) -> None:
        with pytest.raises(ValueError):
            _coerce_value("maybe", bool)

    def test_string_to_int(self) -> None:
        assert _coerce_value("42", int) == 42
        assert _coerce_value("-10", int) == -10

    def test_string_to_float(self) -> None:
        assert _coerce_value("3.14", float) == 3.14
        assert _coerce_value("42", float) == 42.0

    def test_bool_to_int(self) -> None:
        assert _coerce_value(True, int) == 1
        assert _coerce_value(False, int) == 0

    def test_same_type_passthrough(self) -> None:
        assert _coerce_value(True, bool) is True
        assert _coerce_value(42, int) == 42
        assert _coerce_value("hello", str) == "hello"

    def test_none_passthrough(self) -> None:
        assert _coerce_value(None, bool) is None
        assert _coerce_value(None, int) is None

    def test_single_to_list(self) -> None:
        assert _coerce_value("item", list) == ["item"]
        assert _coerce_value(42, list) == [42]


class TestExpandPaths:
    """Tests for _expand_paths function."""

    def test_expand_string(self) -> None:
        result = _expand_paths("~/test")
        assert not result.startswith("~/")

    def test_expand_dict(self) -> None:
        data = {"path": "~/foo", "other": "bar"}
        result = _expand_paths(data)
        assert not result["path"].startswith("~/")
        assert result["other"] == "bar"

    def test_expand_list(self) -> None:
        data = ["~/a", "~/b", "regular"]
        result = _expand_paths(data)
        assert not result[0].startswith("~/")
        assert result[2] == "regular"

    def test_expand_nested(self) -> None:
        data = {"level1": {"path": "~/nested"}}
        result = _expand_paths(data)
        assert not result["level1"]["path"].startswith("~/")


class TestNestedHelpers:
    """Tests for _get_nested and _set_nested."""

    def test_get_nested_simple(self) -> None:
        data = {"a": {"b": {"c": 42}}}
        assert _get_nested(data, ["a", "b", "c"]) == 42

    def test_get_nested_missing(self) -> None:
        data = {"a": {"b": 1}}
        assert _get_nested(data, ["a", "x", "y"]) is None
        assert _get_nested(data, ["a", "x", "y"], "default") == "default"

    def test_get_nested_non_dict(self) -> None:
        data = {"a": "string"}
        assert _get_nested(data, ["a", "b"]) is None

    def test_set_nested_create(self) -> None:
        data: dict[str, Any] = {}
        _set_nested(data, ["a", "b", "c"], 42)
        assert data == {"a": {"b": {"c": 42}}}

    def test_set_nested_overwrite(self) -> None:
        data = {"a": {"b": 1}}
        _set_nested(data, ["a", "b"], 2)
        assert data["a"]["b"] == 2

    def test_set_nested_replace_non_dict(self) -> None:
        data: dict[str, Any] = {"a": "string"}
        _set_nested(data, ["a", "b"], 42)
        assert data == {"a": {"b": 42}}


# --- SettingsManager tests ---


@pytest.fixture
def temp_config_path(tmp_path: Path) -> Path:
    """Create a temporary config file path."""
    return tmp_path / "config.toml"


@pytest.fixture
def settings(temp_config_path: Path) -> SettingsManager:
    """Create a SettingsManager with a temp config."""
    return SettingsManager(config_path=temp_config_path)


class TestSettingsManagerBasic:
    """Basic SettingsManager tests."""

    def test_init_creates_defaults(self, settings: SettingsManager) -> None:
        """Should initialize with default settings."""
        assert settings.get("general.refresh_interval") == 30
        assert settings.get("appearance.theme") == "dark"

    def test_init_loads_existing_file(self, temp_config_path: Path) -> None:
        """Should load settings from existing file."""
        temp_config_path.parent.mkdir(parents=True, exist_ok=True)
        temp_config_path.write_text(
            '[general]\nrefresh_interval = 60\n[appearance]\ntheme = "light"\n'
        )

        settings = SettingsManager(config_path=temp_config_path)
        assert settings.get("general.refresh_interval") == 60
        assert settings.get("appearance.theme") == "light"

    def test_init_merges_with_defaults(self, temp_config_path: Path) -> None:
        """Should merge loaded settings with defaults."""
        temp_config_path.parent.mkdir(parents=True, exist_ok=True)
        temp_config_path.write_text("[general]\nrefresh_interval = 60\n")

        settings = SettingsManager(config_path=temp_config_path)
        assert settings.get("general.refresh_interval") == 60
        # Default should still be present
        assert settings.get("appearance.theme") == "dark"

    def test_get_missing_returns_default(self, settings: SettingsManager) -> None:
        """Should return default for missing keys."""
        assert settings.get("nonexistent.key") is None
        assert settings.get("nonexistent.key", "fallback") == "fallback"

    def test_get_path_expansion(self, temp_config_path: Path) -> None:
        """Should expand ~ in path values."""
        temp_config_path.parent.mkdir(parents=True, exist_ok=True)
        temp_config_path.write_text('[general]\ndata_dir = "~/data"\n')

        settings = SettingsManager(config_path=temp_config_path)
        result = settings.get("general.data_dir")
        assert not result.startswith("~/")
        assert "data" in result


class TestSettingsManagerSetAndSave:
    """Tests for set() and save()."""

    def test_set_simple_value(self, settings: SettingsManager) -> None:
        """Should set a simple value."""
        settings.set("appearance.theme", "light")
        assert settings.get("appearance.theme") == "light"

    def test_set_nested_value(self, settings: SettingsManager) -> None:
        """Should set a deeply nested value."""
        settings.set("tools.repo-scanner.skip_docstrings", True)
        assert settings.get("tools.repo-scanner.skip_docstrings") is True

    def test_set_creates_intermediate_dicts(self, settings: SettingsManager) -> None:
        """Should create intermediate dictionaries."""
        settings.set("new.deeply.nested.key", "value")
        assert settings.get("new.deeply.nested.key") == "value"

    def test_save_creates_file(self, settings: SettingsManager, temp_config_path: Path) -> None:
        """Should create config file on save."""
        assert not temp_config_path.exists()
        settings.save()
        assert temp_config_path.exists()

    def test_save_preserves_values(self, temp_config_path: Path) -> None:
        """Should preserve values across save/load."""
        settings = SettingsManager(config_path=temp_config_path)
        settings.set("tools.my-tool.enabled", True)
        settings.set("appearance.font_size", 16)
        settings.save()

        # Load in new instance
        settings2 = SettingsManager(config_path=temp_config_path)
        assert settings2.get("tools.my-tool.enabled") is True
        assert settings2.get("appearance.font_size") == 16

    def test_save_atomic(self, settings: SettingsManager, temp_config_path: Path) -> None:
        """Should use atomic write (temp file + rename)."""
        settings.save()
        # File should exist and be valid
        assert temp_config_path.exists()
        content = temp_config_path.read_text()
        assert "[general]" in content or "[appearance]" in content


class TestSettingsManagerValidation:
    """Tests for schema validation."""

    def test_register_schema(self, settings: SettingsManager) -> None:
        """Should register and apply schema defaults."""
        schema = {
            "max_files": {"type": int, "default": 100},
            "enabled": {"type": bool, "default": True},
        }
        settings.register_schema("tools.scanner", schema)

        assert settings.get("tools.scanner.max_files") == 100
        assert settings.get("tools.scanner.enabled") is True

    def test_validate_type_error(self, settings: SettingsManager) -> None:
        """Should catch type validation errors."""
        schema = {"count": {"type": int}}
        settings.register_schema("test", schema)
        settings.set("test.count", "not a number")

        errors = settings.validate()
        assert any("count" in e and "int" in e for e in errors)

    def test_validate_required_missing(self, settings: SettingsManager) -> None:
        """Should catch missing required fields."""
        schema = {"api_key": {"type": str, "required": True}}
        settings.register_schema("test", schema)

        errors = settings.validate()
        assert any("api_key" in e and "required" in e.lower() for e in errors)

    def test_validate_allowed_values(self, settings: SettingsManager) -> None:
        """Should validate against allowed values."""
        schema = {"level": {"type": str, "allowed": ["debug", "info", "error"]}}
        settings.register_schema("test", schema)
        settings.set("test.level", "invalid")

        errors = settings.validate()
        assert any("level" in e and "invalid" in e for e in errors)

    def test_validate_min_max(self, settings: SettingsManager) -> None:
        """Should validate min/max constraints."""
        schema = {"port": {"type": int, "min": 1, "max": 65535}}
        settings.register_schema("test", schema)

        settings.set("test.port", 0)
        errors = settings.validate()
        assert any("port" in e and ">=" in e for e in errors)

        settings.set("test.port", 70000)
        errors = settings.validate()
        assert any("port" in e and "<=" in e for e in errors)

        settings.set("test.port", 8080)
        errors = settings.validate()
        assert not any("port" in e for e in errors)

    def test_validate_type_coercion(self, settings: SettingsManager) -> None:
        """Should coerce values during set based on schema."""
        schema = {"enabled": {"type": bool}}
        settings.register_schema("test", schema)
        settings.set("test.enabled", "true")

        assert settings.get("test.enabled") is True
        assert settings.validate() == []


class TestSettingsManagerCallbacks:
    """Tests for change callbacks."""

    def test_on_change_callback(self, settings: SettingsManager) -> None:
        """Should call callback on value change."""
        changes: list[tuple[str, Any, Any]] = []

        def track_change(key: str, old: Any, new: Any) -> None:
            changes.append((key, old, new))

        settings.on_change(track_change)
        settings.set("appearance.theme", "light")

        assert len(changes) == 1
        assert changes[0] == ("appearance.theme", "dark", "light")

    def test_on_change_no_callback_if_same_value(self, settings: SettingsManager) -> None:
        """Should not call callback if value unchanged."""
        changes: list[tuple[str, Any, Any]] = []
        settings.on_change(lambda k, o, n: changes.append((k, o, n)))

        settings.set("appearance.theme", "dark")  # Same as default
        assert len(changes) == 0

    def test_unsubscribe(self, settings: SettingsManager) -> None:
        """Should be able to unsubscribe from callbacks."""
        changes: list[str] = []
        unsubscribe = settings.on_change(lambda k, o, n: changes.append(k))

        settings.set("appearance.theme", "light")
        assert len(changes) == 1

        unsubscribe()
        settings.set("appearance.theme", "dark")
        assert len(changes) == 1  # No new changes

    def test_callback_error_doesnt_break(self, settings: SettingsManager) -> None:
        """Should continue if callback raises exception."""

        def bad_callback(key: str, old: Any, new: Any) -> None:
            raise ValueError("oops")

        good_changes: list[str] = []
        settings.on_change(bad_callback)
        settings.on_change(lambda k, o, n: good_changes.append(k))

        # Should not raise, and good callback should still be called
        settings.set("appearance.theme", "light")
        assert len(good_changes) == 1


class TestSettingsManagerResetDefaults:
    """Tests for reset_to_defaults()."""

    def test_reset_all(self, settings: SettingsManager) -> None:
        """Should reset all settings to defaults."""
        settings.set("appearance.theme", "light")
        settings.set("general.refresh_interval", 60)
        settings.set("tools.custom.value", 123)

        settings.reset_to_defaults()

        assert settings.get("appearance.theme") == "dark"
        assert settings.get("general.refresh_interval") == 30
        # Custom tools section gets reset to empty
        assert settings.get("tools.custom.value") is None

    def test_reset_section(self, settings: SettingsManager) -> None:
        """Should reset only specified section."""
        settings.set("appearance.theme", "light")
        settings.set("general.refresh_interval", 60)

        settings.reset_to_defaults("appearance")

        assert settings.get("appearance.theme") == "dark"
        assert settings.get("general.refresh_interval") == 60  # Unchanged

    def test_reset_triggers_callbacks(self, settings: SettingsManager) -> None:
        """Should trigger callbacks on reset."""
        changes: list[tuple[str, Any, Any]] = []
        settings.on_change(lambda k, o, n: changes.append((k, o, n)))

        settings.set("appearance.theme", "light")
        changes.clear()

        settings.reset_to_defaults("appearance")
        assert any(k == "appearance.theme" for k, _, _ in changes)


class TestSettingsManagerMisc:
    """Miscellaneous tests."""

    def test_get_section(self, settings: SettingsManager) -> None:
        """Should return a section as dict."""
        section = settings.get_section("appearance")
        assert isinstance(section, dict)
        assert "theme" in section

    def test_all(self, settings: SettingsManager) -> None:
        """Should return all settings."""
        all_settings = settings.all()
        assert "general" in all_settings
        assert "appearance" in all_settings
        assert all_settings["appearance"]["theme"] == "dark"

    def test_path_property(self, settings: SettingsManager, temp_config_path: Path) -> None:
        """Should expose config path."""
        assert settings.path == temp_config_path

    def test_reload(self, temp_config_path: Path) -> None:
        """Should reload settings from file."""
        settings = SettingsManager(config_path=temp_config_path)
        settings.set("appearance.theme", "light")
        settings.save()

        # Modify file externally
        content = temp_config_path.read_text().replace("light", "ocean")
        temp_config_path.write_text(content)

        settings.reload()
        assert settings.get("appearance.theme") == "ocean"

    def test_get_raw_no_expansion(self, temp_config_path: Path) -> None:
        """get_raw should not expand paths."""
        temp_config_path.parent.mkdir(parents=True, exist_ok=True)
        temp_config_path.write_text('[general]\npath = "~/data"\n')

        settings = SettingsManager(config_path=temp_config_path)
        assert settings.get_raw("general.path") == "~/data"
        assert settings.get("general.path") != "~/data"

    def test_delete(self, settings: SettingsManager) -> None:
        """Should delete a key."""
        settings.set("tools.test.value", 42)
        assert settings.get("tools.test.value") == 42

        result = settings.delete("tools.test.value")
        assert result is True
        assert settings.get("tools.test.value") is None

    def test_delete_nonexistent(self, settings: SettingsManager) -> None:
        """Should return False for deleting nonexistent key."""
        result = settings.delete("nonexistent.key")
        assert result is False

    def test_register_defaults(self, settings: SettingsManager) -> None:
        """Should register additional defaults."""
        settings.register_defaults("tools.my-tool", {"timeout": 30, "retries": 3})

        assert settings.get("tools.my-tool.timeout") == 30
        assert settings.get("tools.my-tool.retries") == 3

    def test_corrupt_config_uses_defaults(self, temp_config_path: Path) -> None:
        """Should use defaults if config file is corrupt."""
        temp_config_path.parent.mkdir(parents=True, exist_ok=True)
        temp_config_path.write_text("not valid toml {{{}}")

        # Should not raise, should use defaults
        with patch("sys.stderr"):  # Suppress warning
            settings = SettingsManager(config_path=temp_config_path)

        assert settings.get("appearance.theme") == "dark"
