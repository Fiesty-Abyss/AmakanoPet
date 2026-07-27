"""Application configuration."""

from dataclasses import dataclass

from PySide6.QtCore import QPoint, QSettings, QStandardPaths

APP_NAME = "AmakanoPet"
ORGANIZATION_NAME = "Fiesty-Abyss"
WINDOW_WIDTH = 280
WINDOW_HEIGHT = 360
MIN_SCALE = 0.5
MAX_SCALE = 2.0
SCALE_STEP = 0.1


@dataclass(frozen=True)
class WindowState:
    position: QPoint | None
    scale: float


class SettingsStore:
    """Persist the small amount of desktop-pet state in a user config file."""

    def __init__(self, settings: QSettings | None = None) -> None:
        if settings is None:
            config_dir = QStandardPaths.writableLocation(
                QStandardPaths.StandardLocation.AppConfigLocation
            )
            settings = QSettings(f"{config_dir}/settings.ini", QSettings.Format.IniFormat)
        self._settings = settings

    def load_window_state(self) -> WindowState:
        raw_position = self._settings.value("window/position")
        position = raw_position if isinstance(raw_position, QPoint) else None

        try:
            scale = float(self._settings.value("window/scale", 1.0))
        except (TypeError, ValueError):
            scale = 1.0
        scale = min(MAX_SCALE, max(MIN_SCALE, scale))
        return WindowState(position=position, scale=scale)

    def save_window_state(self, position: QPoint, scale: float) -> None:
        self._settings.setValue("window/position", position)
        self._settings.setValue("window/scale", scale)
        self._settings.sync()
