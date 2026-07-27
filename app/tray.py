"""System tray integration for AmakanoPet."""

from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtGui import QAction, QColor, QFont, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import QMenu, QSystemTrayIcon

from app.config import APP_NAME
from app.window import PetWindow


def create_placeholder_icon() -> QIcon:
    """Create an in-memory icon until a final application icon is available."""
    pixmap = QPixmap(64, 64)
    pixmap.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor("#ef7da0"))
    painter.drawEllipse(4, 4, 56, 56)

    font = QFont()
    font.setBold(True)
    font.setPixelSize(26)
    painter.setFont(font)
    painter.setPen(QColor("#ffffff"))
    painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "AP")
    painter.end()
    return QIcon(pixmap)


class SystemTray(QObject):
    """Own the tray icon and keep its actions synchronized with the window."""

    quit_requested = Signal()

    def __init__(self, window: PetWindow) -> None:
        super().__init__(window)
        self._window = window
        self._tray_icon = QSystemTrayIcon(create_placeholder_icon(), self)
        self._tray_icon.setToolTip(APP_NAME)

        self._menu = QMenu()
        self._visibility_action = QAction(self._menu)
        self._visibility_action.triggered.connect(self._window.toggle_visibility)
        self._menu.addAction(self._visibility_action)
        self._menu.addSeparator()

        quit_action = self._menu.addAction("退出")
        quit_action.triggered.connect(lambda: self.quit_requested.emit())

        self._menu.aboutToShow.connect(self._update_visibility_action)
        self._tray_icon.setContextMenu(self._menu)
        self._tray_icon.activated.connect(self._on_activated)
        self._update_visibility_action()

    def show(self) -> None:
        self._tray_icon.show()

    def hide(self) -> None:
        self._tray_icon.hide()

    def _update_visibility_action(self) -> None:
        self._visibility_action.setText(
            "隐藏窗口" if self._window.isVisible() else "显示窗口"
        )

    def _on_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason in (
            QSystemTrayIcon.ActivationReason.Trigger,
            QSystemTrayIcon.ActivationReason.DoubleClick,
        ):
            self._window.toggle_visibility()
            self._update_visibility_action()
