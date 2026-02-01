"""Tests for config module."""

from pathlib import Path

import pytest

from openclaw_dash.config import Config, load_config, save_config


@pytest.fixture
def temp_config_path(tmp_path: Path) -> Path:
    """Return a temporary config file path."""
    return tmp_path / "config.toml"


class TestConfig:
    """Tests for Config dataclass."""

    def test_default_values(self):
        """Config has sensible defaults."""
        config = Config()
        assert config.theme == "dark"
        assert config.refresh_interval == 30
        assert config.show_notifications is True

    def test_to_dict(self):
        """Config serializes to dictionary."""
        config = Config(theme="light", refresh_interval=60, show_notifications=False)
        data = config.to_dict()
        assert data == {
            "theme": "light",
            "refresh_interval": 60,
            "show_notifications": False,
        }

    def test_from_dict(self):
        """Config deserializes from dictionary."""
        data = {"theme": "nord", "refresh_interval": 15, "show_notifications": True}
        config = Config.from_dict(data)
        assert config.theme == "nord"
        assert config.refresh_interval == 15
        assert config.show_notifications is True

    def test_from_dict_partial(self):
        """Config uses defaults for missing keys."""
        data = {"theme": "custom"}
        config = Config.from_dict(data)
        assert config.theme == "custom"
        assert config.refresh_interval == 30  # default
        assert config.show_notifications is True  # default

    def test_update(self, temp_config_path: Path):
        """Config.update() modifies values and saves."""
        config = Config(_path=temp_config_path)
        config.update(theme="light", refresh_interval=45)

        assert config.theme == "light"
        assert config.refresh_interval == 45
        assert temp_config_path.exists()

    def test_update_ignores_private(self, temp_config_path: Path):
        """Config.update() ignores private attributes."""
        config = Config(_path=temp_config_path)
        original_path = config._path
        config.update(_path=Path("/bogus"))
        assert config._path == original_path


class TestLoadConfig:
    """Tests for load_config function."""

    def test_load_nonexistent_returns_defaults(self, temp_config_path: Path):
        """Loading from nonexistent file returns defaults."""
        config = load_config(temp_config_path)
        assert config.theme == "dark"
        assert config.refresh_interval == 30
        assert config._path == temp_config_path

    def test_load_existing_file(self, temp_config_path: Path):
        """Loading from existing file works."""
        # Create a config file
        temp_config_path.parent.mkdir(parents=True, exist_ok=True)
        temp_config_path.write_text(
            'theme = "nord"\nrefresh_interval = 45\nshow_notifications = false\n'
        )

        config = load_config(temp_config_path)
        assert config.theme == "nord"
        assert config.refresh_interval == 45
        assert config.show_notifications is False

    def test_load_corrupt_file_returns_defaults(self, temp_config_path: Path):
        """Loading corrupt file returns defaults with warning."""
        temp_config_path.parent.mkdir(parents=True, exist_ok=True)
        temp_config_path.write_text("this is not valid toml {{{{")

        config = load_config(temp_config_path)
        assert config.theme == "dark"  # default
        assert config._path == temp_config_path


class TestSaveConfig:
    """Tests for save_config function."""

    def test_save_creates_file(self, temp_config_path: Path):
        """save_config creates file and parent directories."""
        nested_path = temp_config_path.parent / "nested" / "config.toml"
        config = Config(theme="light", refresh_interval=60, show_notifications=False)

        save_config(config, nested_path)

        assert nested_path.exists()
        content = nested_path.read_text()
        assert 'theme = "light"' in content
        assert "refresh_interval = 60" in content
        assert "show_notifications = false" in content

    def test_save_roundtrip(self, temp_config_path: Path):
        """Config survives save/load roundtrip."""
        original = Config(
            theme="custom-theme",
            refresh_interval=120,
            show_notifications=False,
            _path=temp_config_path,
        )
        original.save()

        loaded = load_config(temp_config_path)
        assert loaded.theme == original.theme
        assert loaded.refresh_interval == original.refresh_interval
        assert loaded.show_notifications == original.show_notifications
