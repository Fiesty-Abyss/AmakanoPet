"""Application configuration and persisted settings."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QPoint, QSettings, QStandardPaths

APP_NAME = "AmakanoPet"
APP_DISPLAY_NAME = "AmakanoPet 乐园"
ORGANIZATION_NAME = "Fiesty-Abyss"
WINDOW_WIDTH = 280
WINDOW_HEIGHT = 360
MIN_SCALE = 0.5
MAX_SCALE = 2.0
SCALE_STEP = 0.1

BUILTIN_MASCOT = "builtin:mascot"
THEME_FOLLOW = "follow"
THEME_CHOICES = (THEME_FOLLOW, "sweet", "winter", "autumn", "summer")


def clamp_scale(value: object, default: float = 1.0) -> float:
    try:
        scale = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        scale = default
    return round(min(MAX_SCALE, max(MIN_SCALE, scale)), 1)


def default_model_root() -> Path:
    """Where users drop their own models (outside the program directory)."""
    base = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation)
    if not base:
        base = str(Path.home() / ".amakanopet")
    return Path(base) / "models"


@dataclass(frozen=True)
class WindowState:
    position: QPoint | None
    scale: float


class SettingsStore:
    """Persist the desktop-pet state in a user config file (INI)."""

    def __init__(self, settings: QSettings | None = None) -> None:
        if settings is None:
            config_dir = QStandardPaths.writableLocation(
                QStandardPaths.StandardLocation.AppConfigLocation
            )
            settings = QSettings(f"{config_dir}/settings.ini", QSettings.Format.IniFormat)
        self._settings = settings

    # ---- window -----------------------------------------------------------
    def load_window_state(self) -> WindowState:
        raw_position = self._settings.value("window/position")
        position = raw_position if isinstance(raw_position, QPoint) else None
        scale = clamp_scale(self._settings.value("window/scale", 1.0))
        return WindowState(position=position, scale=scale)

    def save_window_state(self, position: QPoint, scale: float) -> None:
        self._settings.setValue("window/position", position)
        self._settings.setValue("window/scale", scale)
        self._settings.sync()

    def reset_window_position(self) -> None:
        self._settings.remove("window/position")
        self._settings.sync()

    # ---- generic helpers --------------------------------------------------
    def _bool(self, key: str, default: bool) -> bool:
        value = self._settings.value(key, default)
        if isinstance(value, str):
            return value.strip().lower() in {"1", "true", "yes", "on"}
        return bool(value)

    def _set(self, key: str, value: object) -> None:
        self._settings.setValue(key, value)
        self._settings.sync()

    # ---- pet / park -------------------------------------------------------
    @property
    def current_model(self) -> str:
        return str(self._settings.value("pet/model", BUILTIN_MASCOT) or BUILTIN_MASCOT)

    @current_model.setter
    def current_model(self, key: str) -> None:
        self._set("pet/model", key or BUILTIN_MASCOT)

    @property
    def model_root(self) -> Path:
        raw = self._settings.value("pet/model_root", "")
        return Path(str(raw)) if raw else default_model_root()

    @model_root.setter
    def model_root(self, path: Path | str | None) -> None:
        self._set("pet/model_root", str(path) if path else "")

    @property
    def always_on_top(self) -> bool:
        return self._bool("window/always_on_top", True)

    @always_on_top.setter
    def always_on_top(self, value: bool) -> None:
        self._set("window/always_on_top", bool(value))

    @property
    def animations_enabled(self) -> bool:
        return self._bool("pet/animations", True)

    @animations_enabled.setter
    def animations_enabled(self, value: bool) -> None:
        self._set("pet/animations", bool(value))

    @property
    def theme_mode(self) -> str:
        value = str(self._settings.value("park/theme", THEME_FOLLOW))
        return value if value in THEME_CHOICES else THEME_FOLLOW

    @theme_mode.setter
    def theme_mode(self, value: str) -> None:
        self._set("park/theme", value if value in THEME_CHOICES else THEME_FOLLOW)

    @property
    def last_tab(self) -> str:
        return str(self._settings.value("park/last_tab", "") or "")

    @last_tab.setter
    def last_tab(self, value: str) -> None:
        self._set("park/last_tab", value)
