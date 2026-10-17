"""Small reusable widgets: flow layout, generated avatars, clickable cards."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QPoint, QRect, QRectF, QSize, Qt, Signal
from PySide6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QLinearGradient,
    QMouseEvent,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
)
from PySide6.QtWidgets import QFrame, QLabel, QLayout, QLayoutItem, QSizePolicy, QWidget


class FlowLayout(QLayout):
    """Left-to-right layout that wraps, used for trait chips."""

    def __init__(self, parent: QWidget | None = None, spacing: int = 6) -> None:
        super().__init__(parent)
        self._items: list[QLayoutItem] = []
        self._spacing = spacing
        self.setContentsMargins(0, 0, 0, 0)

    def addItem(self, item: QLayoutItem) -> None:
        self._items.append(item)

    def count(self) -> int:
        return len(self._items)

    def itemAt(self, index: int) -> QLayoutItem | None:
        return self._items[index] if 0 <= index < len(self._items) else None

    def takeAt(self, index: int) -> QLayoutItem | None:
        return self._items.pop(index) if 0 <= index < len(self._items) else None

    def expandingDirections(self) -> Qt.Orientation:
        return Qt.Orientation(0)

    def hasHeightForWidth(self) -> bool:
        return True

    def heightForWidth(self, width: int) -> int:
        return self._do_layout(QRect(0, 0, width, 0), dry_run=True)

    def setGeometry(self, rect: QRect) -> None:
        super().setGeometry(rect)
        self._do_layout(rect, dry_run=False)

    def sizeHint(self) -> QSize:
        return self.minimumSize()

    def minimumSize(self) -> QSize:
        size = QSize()
        for item in self._items:
            size = size.expandedTo(item.minimumSize())
        return size

    def _do_layout(self, rect: QRect, dry_run: bool) -> int:
        x, y, line_height = rect.x(), rect.y(), 0
        for item in self._items:
            hint = item.sizeHint()
            next_x = x + hint.width() + self._spacing
            if next_x - self._spacing > rect.right() and line_height > 0:
                x = rect.x()
                y += line_height + self._spacing
                next_x = x + hint.width() + self._spacing
                line_height = 0
            if not dry_run:
                item.setGeometry(QRect(QPoint(x, y), hint))
            x = next_x
            line_height = max(line_height, hint.height())
        return y + line_height - rect.y()


def chip(text: str) -> QLabel:
    label = QLabel(text)
    label.setObjectName("Chip")
    return label


def initial_avatar(initial: str, color: str, size: int, ring: str = "#FFFFFF") -> QPixmap:
    """Original generated avatar: a gradient circle with the heroine's initial."""
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
    base = QColor(color)
    grad = QLinearGradient(0, 0, size, size)
    grad.setColorAt(0.0, base.lighter(135))
    grad.setColorAt(1.0, base)
    rect = QRectF(2, 2, size - 4, size - 4)
    painter.setPen(QPen(QColor(ring), max(2.0, size * 0.035)))
    painter.setBrush(QBrush(grad))
    painter.drawEllipse(rect)
    # small decorative highlight
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor(255, 255, 255, 60))
    painter.drawEllipse(QRectF(size * 0.18, size * 0.12, size * 0.38, size * 0.22))
    font = QFont()
    font.setBold(True)
    font.setPixelSize(int(size * 0.44))
    painter.setFont(font)
    text = QColor("#FFFFFF") if base.lightnessF() < 0.72 else QColor("#4B2814")
    painter.setPen(text)
    painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, initial[:1])
    painter.end()
    return pixmap


def image_avatar(path: Path, size: int, ring: str = "#FFFFFF") -> QPixmap | None:
    """Round-crop a user-supplied image (top-aligned, so faces stay visible)."""
    source = QPixmap(str(path))
    if source.isNull():
        return None
    scaled = source.scaled(size, size, Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                           Qt.TransformationMode.SmoothTransformation)
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
    clip = QPainterPath()
    clip.addEllipse(QRectF(2, 2, size - 4, size - 4))
    painter.setClipPath(clip)
    painter.fillRect(pixmap.rect(), QColor("#FFFFFF"))
    painter.drawPixmap(int((size - scaled.width()) / 2), 0, scaled)
    painter.setClipping(False)
    painter.setPen(QPen(QColor(ring), max(2.0, size * 0.035)))
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.drawEllipse(QRectF(2, 2, size - 4, size - 4))
    painter.end()
    return pixmap


def avatar_pixmap(initial: str, color: str, size: int, image: Path | None = None,
                  ring: str = "#FFFFFF") -> QPixmap:
    if image is not None:
        pixmap = image_avatar(image, size, ring)
        if pixmap is not None:
            return pixmap
    return initial_avatar(initial, color, size, ring)


class ClickableFrame(QFrame):
    clicked = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton and self.rect().contains(
            event.position().toPoint()
        ):
            self.clicked.emit()
            event.accept()
            return
        super().mouseReleaseEvent(event)
