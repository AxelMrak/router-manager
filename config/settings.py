"""Application settings with JSON file persistence."""

import json
import logging
import os
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class AppSettings:
    """Application settings with automatic JSON file persistence."""

    DEFAULT_CONFIG = {
        "router_host": "192.168.0.1",
        "router_username": "useradmin",
        "router_password": "",
        "polling_interval": 10,
        "theme": "dark",
        "window_geometry": None,
        "auto_login": True,
        "notifications_enabled": True,
    }

    def __init__(self) -> None:
        """Initialize settings, loading from disk if available."""
        self.config_path = self._get_config_path()
        self._data: dict[str, Any] = dict(self.DEFAULT_CONFIG)
        self.load()

    def _get_config_path(self) -> Path:
        """Determine config file path based on OS.

        Uses APPDATA on Windows, ~/.config on other platforms.
        """
        if os.name == "nt":
            base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
        else:
            base = Path.home() / ".config"
        config_dir = base / "router-manager"
        config_dir.mkdir(parents=True, exist_ok=True)
        return config_dir / "settings.json"

    def load(self) -> None:
        """Load settings from JSON file, ignoring errors."""
        if not self.config_path.exists():
            logger.debug("Config file not found at %s, using defaults", self.config_path)
            return

        try:
            text = self.config_path.read_text(encoding="utf-8")
            loaded = json.loads(text)
            if isinstance(loaded, dict):
                self._data = dict(self.DEFAULT_CONFIG)
                self._data.update(loaded)
                logger.debug("Settings loaded from %s", self.config_path)
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("Failed to load settings from %s: %s", self.config_path, e)

    def save(self) -> None:
        """Persist current settings to JSON file."""
        try:
            text = json.dumps(self._data, indent=2, ensure_ascii=False)
            self.config_path.write_text(text, encoding="utf-8")
            logger.debug("Settings saved to %s", self.config_path)
        except OSError as e:
            logger.error("Failed to save settings to %s: %s", self.config_path, e)

    def get(self, key: str, default: Any = None) -> Any:
        """Get a setting value.

        Args:
            key: Setting key.
            default: Default value if key is not set.

        Returns:
            Setting value or default.
        """
        return self._data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Set a setting value and persist to disk.

        Args:
            key: Setting key.
            value: New value.
        """
        self._data[key] = value
        self.save()

    def reset(self) -> None:
        """Reset all settings to defaults and save."""
        self._data = dict(self.DEFAULT_CONFIG)
        self.save()
        logger.info("Settings reset to defaults")