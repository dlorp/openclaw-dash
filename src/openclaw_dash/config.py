"""User configuration management.

Persists user preferences to ~/.config/openclaw-dash/config.toml
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# tomli-w for writing (tomllib is read-only)
import tomli_w

# tomllib is stdlib in 3.11+, use tomli as fallback for 3.10
try:
    import tomllib
except ImportError:
    import tomli as tomllib  # type: ignore[import-not-found,no-redef]

DEFAULT_CONFIG_DIR = Path.home() / ".config" / "openclaw-dash"
DEFAULT_CONFIG_PATH = DEFAULT_CONFIG_DIR / "config.toml"


@dataclass
class Config:
    """User configuration settings."""

    theme: str = "dark"
    refresh_interval: int = 30
    show_notifications: bool = True

    # File path for this config (not persisted)
    _path: Path = field(default=DEFAULT_CONFIG_PATH, repr=False, compare=False)

    def to_dict(self) -> dict[str, Any]:
        """Convert config to dictionary for serialization."""
        return {
            "theme": self.theme,
            "refresh_interval": self.refresh_interval,
            "show_notifications": self.show_notifications,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any], path: Path | None = None) -> Config:
        """Create config from dictionary."""
        return cls(
            theme=data.get("theme", "dark"),
            refresh_interval=data.get("refresh_interval", 30),
            show_notifications=data.get("show_notifications", True),
            _path=path or DEFAULT_CONFIG_PATH,
        )

    def save(self) -> None:
        """Save configuration to file."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._path, "wb") as f:
            tomli_w.dump(self.to_dict(), f)

    def update(self, **kwargs: Any) -> None:
        """Update config values and save."""
        for key, value in kwargs.items():
            if hasattr(self, key) and not key.startswith("_"):
                setattr(self, key, value)
        self.save()


def load_config(path: Path | None = None) -> Config:
    """Load configuration from file.

    Args:
        path: Optional custom config path. Defaults to ~/.config/openclaw-dash/config.toml

    Returns:
        Config object with loaded or default settings.
    """
    config_path = path or DEFAULT_CONFIG_PATH

    if not config_path.exists():
        # Return defaults, don't create file until save()
        return Config(_path=config_path)

    try:
        with open(config_path, "rb") as f:
            data = tomllib.load(f)
        return Config.from_dict(data, path=config_path)
    except (tomllib.TOMLDecodeError, OSError) as e:
        # If config is corrupt, return defaults but preserve path
        import sys

        print(f"Warning: Could not load config from {config_path}: {e}", file=sys.stderr)
        return Config(_path=config_path)


def save_config(config: Config, path: Path | None = None) -> None:
    """Save configuration to file.

    Args:
        config: Config object to save.
        path: Optional custom path. Uses config's internal path if not provided.
    """
    if path:
        config._path = path
    config.save()
