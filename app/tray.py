"""System tray integration for AmakanoPet."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QObject, QRectF, Qt, Signal
from PySide6.QtGui import QAction, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import QMenu, QSystemTrayIcon, QWidget

from app.config import APP_DISPLAY_NAME
from app.renderers.mascot import paint_mascot
from app.theme import get_theme


def create_app_icon(size: int = 64) -> QIcon:
    """Application / tray icon drawn from the original mascot."""
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    paint_mascot(painter, QRectF(0, 0, size, size), get_theme(None))
    painter.end()
    return QIcon(pixmap)


class SystemTray(QObject):
    """Tray icon with show/hide, park, character switching, rescan and quit."""

    quit_requested = Signal()
    park_requested = Signal()
    rescan_requested = Signal()

    def __init__(self, window: QWidget, populate_models: Callable[[QMenu], None] | None = None,
                 parent: QObject | None = None) -> None:
        super().__init__(parent or window)
        self._window = window
        self._populate_models = populate_models
        self._tray_icon = QSystemTrayIcon(create_app_icon(), self)
        self._tray_icon.setToolTip(f"{APP_DISPLAY_NAME}（非官方同人）")

        self.menu = QMenu()
        self._visibility_action = QAction(self.menu)
        self._visibility_action.triggered.connect(self._toggle_window)
        self.menu.addAction(self._visibility_action)
        self.menu.addAction("打开乐园").triggered.connect(self.park_requested.emit)
        self.models_menu = self.menu.addMenu("切换桌宠")
        self.menu.addAction("重新扫描模型").triggered.connect(self.rescan_requested.emit)
        self.menu.addSeparator()
        self.menu.addAction("退出").triggered.connect(self.quit_requested.emit)

        self.menu.aboutToShow.connect(self.refresh_menu)
        self._tray_icon.setContextMenu(self.menu)
        self._tray_icon.activated.connect(self._on_activated)
        self.refresh_menu()

    @staticmethod
    def is_available() -> bool:
        return QSystemTrayIcon.isSystemTrayAvailable()

    def show(self) -> None:
        self._tray_icon.show()

    def hide(self) -> None:
        self._tray_icon.hide()

    def refresh_menu(self) -> None:
        self._visibility_action.setText("隐藏桌宠" if self._window.isVisible() else "显示桌宠")
        self.models_menu.clear()
        if self._populate_models is not None:
            self._populate_models(self.models_menu)

    def _toggle_window(self) -> None:
        toggle = getattr(self._window, "toggle_visibility", None)
        if toggle is not None:
            toggle()

    def _on_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self._toggle_window()
        elif reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.park_requested.emit()
