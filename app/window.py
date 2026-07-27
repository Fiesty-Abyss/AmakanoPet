"""Transparent, frameless desktop pet window."""

from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QColor, QKeyEvent, QMouseEvent, QPainter, QPaintEvent
from PySide6.QtWidgets import QWidget

from app.config import APP_NAME, WINDOW_HEIGHT, WINDOW_WIDTH


class PetWindow(QWidget):
    """Minimal always-on-top window that can be dragged around the desktop."""

    def __init__(self) -> None:
        super().__init__()
        self._drag_offset: QPoint | None = None

        self.setWindowTitle(APP_NAME)
        self.setFixedSize(WINDOW_WIDTH, WINDOW_HEIGHT)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

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
            f"{APP_NAME}\nDrag me",
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
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key.Key_Escape:
            self.close()
            return
        super().keyPressEvent(event)
