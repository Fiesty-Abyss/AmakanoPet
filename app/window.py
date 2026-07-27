"""Transparent, frameless desktop pet window."""

from PySide6.QtCore import QPoint, Qt, Signal
from PySide6.QtGui import (
    QColor,
    QContextMenuEvent,
    QKeyEvent,
    QMouseEvent,
    QPainter,
    QPaintEvent,
    QWheelEvent,
)
from PySide6.QtWidgets import QMenu, QWidget

from app.config import (
    APP_NAME,
    MAX_SCALE,
    MIN_SCALE,
    SCALE_STEP,
    WINDOW_HEIGHT,
    WINDOW_WIDTH,
    SettingsStore,
)


class PetWindow(QWidget):
    """Minimal always-on-top window that can be dragged around the desktop."""

    quit_requested = Signal()

    def __init__(self, settings: SettingsStore | None = None) -> None:
        super().__init__()
        self._settings = settings or SettingsStore()
        self._drag_offset: QPoint | None = None
        state = self._settings.load_window_state()
        self._scale = state.scale

        self.setWindowTitle(APP_NAME)
        self._apply_size()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        if state.position is not None:
            self.move(state.position)

    @property
    def scale(self) -> float:
        return self._scale

    def _apply_size(self) -> None:
        self.setFixedSize(
            round(WINDOW_WIDTH * self._scale),
            round(WINDOW_HEIGHT * self._scale),
        )

    def save_window_state(self) -> None:
        self._settings.save_window_state(self.pos(), self._scale)

    def set_scale(self, scale: float) -> None:
        new_scale = round(min(MAX_SCALE, max(MIN_SCALE, scale)), 1)
        if new_scale == self._scale:
            return

        old_center = self.frameGeometry().center()
        self._scale = new_scale
        self._apply_size()
        self.move(old_center - self.rect().center())
        self.save_window_state()
        self.update()

    def show_window(self) -> None:
        self.show()
        self.raise_()
        self.activateWindow()

    def hide_to_tray(self) -> None:
        self.save_window_state()
        self.hide()

    def toggle_visibility(self) -> None:
        if self.isVisible():
            self.hide_to_tray()
        else:
            self.show_window()

    def paintEvent(self, event: QPaintEvent) -> None:
        """Draw a simple translucent placeholder until character art is added."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(255, 182, 193, 190))
        painter.drawRoundedRect(self.rect().adjusted(10, 10, -10, -10), 32, 32)

        painter.setPen(QColor(70, 45, 55))
        painter.drawText(
            self.rect(),
            Qt.AlignmentFlag.AlignCenter,
            f"{APP_NAME}\n拖动窗口\nCtrl + 滚轮缩放",
        )
        super().paintEvent(event)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_offset = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if (
            self._drag_offset is not None
            and event.buttons() & Qt.MouseButton.LeftButton
        ):
            self.move(event.globalPosition().toPoint() - self._drag_offset)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_offset = None
            self.save_window_state()
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key.Key_Escape:
            self.hide_to_tray()
            event.accept()
            return
        super().keyPressEvent(event)

    def wheelEvent(self, event: QWheelEvent) -> None:
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            direction = 1 if event.angleDelta().y() > 0 else -1
            self.set_scale(self._scale + direction * SCALE_STEP)
            event.accept()
            return
        super().wheelEvent(event)

    def contextMenuEvent(self, event: QContextMenuEvent) -> None:
        menu = QMenu(self)
        visibility_action = menu.addAction(
            "隐藏窗口" if self.isVisible() else "显示窗口"
        )
        visibility_action.triggered.connect(self.toggle_visibility)
        menu.addSeparator()
        quit_action = menu.addAction("退出")
        quit_action.triggered.connect(self.quit_requested.emit)
        menu.exec(event.globalPos())
        event.accept()
