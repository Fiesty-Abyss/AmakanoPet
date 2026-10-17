"""Transparent, frameless desktop pet window."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QPoint, QRectF, Qt, Signal
from PySide6.QtGui import (
    QContextMenuEvent,
    QCursor,
    QKeyEvent,
    QMouseEvent,
    QPainter,
    QPaintEvent,
    QWheelEvent,
)
from PySide6.QtWidgets import QApplication, QMenu, QWidget

from app.config import (
    APP_NAME,
    SCALE_STEP,
    WINDOW_HEIGHT,
    WINDOW_WIDTH,
    SettingsStore,
    clamp_scale,
)
from app.renderers import SpriteRenderer


class PetWindow(QWidget):
    """Always-on-top transparent window that renders the pet and can be dragged."""

    quit_requested = Signal()
    park_requested = Signal()
    scale_changed = Signal(float)

    def __init__(self, settings: SettingsStore | None = None,
                 renderer: SpriteRenderer | None = None) -> None:
        super().__init__()
        self._settings = settings or SettingsStore()
        self.renderer = renderer or SpriteRenderer(parent=self)
        self.renderer.frame_ready.connect(self._on_frame)
        self._press_pos: QPoint | None = None
        self._drag_offset: QPoint | None = None
        self._dragging = False
        self._model_scale = 1.0
        self.menu_extender: Callable[[QMenu], None] | None = None
        state = self._settings.load_window_state()
        self._scale = state.scale

        self.setWindowTitle(APP_NAME)
        self._apply_size()
        self._apply_flags(self._settings.always_on_top)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setToolTip("双击打开乐园 · Ctrl+滚轮缩放 · 右键菜单")
        if state.position is not None:
            self.move(state.position)
        self.renderer.set_animated(self._settings.animations_enabled)

    # ---- geometry ---------------------------------------------------------
    @property
    def scale(self) -> float:
        return self._scale

    def _apply_size(self) -> None:
        factor = self._scale * self._model_scale
        self.setFixedSize(round(WINDOW_WIDTH * factor), round(WINDOW_HEIGHT * factor))

    def _apply_flags(self, on_top: bool) -> None:
        flags = Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool
        if on_top:
            flags |= Qt.WindowType.WindowStaysOnTopHint
        self.setWindowFlags(flags)

    def set_always_on_top(self, on_top: bool) -> None:
        visible = self.isVisible()
        self._apply_flags(on_top)
        if visible:
            self.show()

    def set_model_scale(self, factor: float) -> None:
        """Per-model size factor from pet.json (multiplied with the user scale)."""
        factor = min(3.0, max(0.3, factor))
        if factor != self._model_scale:
            self._resize_keeping_center(lambda: setattr(self, "_model_scale", factor))

    def _resize_keeping_center(self, change: Callable[[], None]) -> None:
        old_center = self.frameGeometry().center()
        change()
        self._apply_size()
        self.move(old_center - self.rect().center())
        self.update()

    def save_window_state(self) -> None:
        self._settings.save_window_state(self.pos(), self._scale)

    def set_scale(self, scale: float) -> None:
        new_scale = clamp_scale(scale, self._scale)
        if new_scale == self._scale:
            return
        self._resize_keeping_center(lambda: setattr(self, "_scale", new_scale))
        self.save_window_state()
        self.scale_changed.emit(new_scale)

    # ---- visibility -------------------------------------------------------
    def show_window(self) -> None:
        self.show()
        self.raise_()
        self.activateWindow()
        self.renderer.start()

    def hide_to_tray(self) -> None:
        self.save_window_state()
        self.hide()
        self.renderer.stop()

    def toggle_visibility(self) -> None:
        if self.isVisible():
            self.hide_to_tray()
        else:
            self.show_window()

    # ---- painting ---------------------------------------------------------
    def _on_frame(self) -> None:
        source = self.renderer.source
        if source.wants_gaze and self.isVisible():
            pos = self.mapFromGlobal(QCursor.pos())
            dpr = self.devicePixelRatioF()
            source.look_at(pos.x() * dpr, pos.y() * dpr)
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.renderer.paint(painter, QRectF(self.rect()))
        painter.end()

    # ---- interaction ------------------------------------------------------
    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._press_pos = event.globalPosition().toPoint()
            self._drag_offset = self._press_pos - self.frameGeometry().topLeft()
            self._dragging = False
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._drag_offset is not None and event.buttons() & Qt.MouseButton.LeftButton:
            pos = event.globalPosition().toPoint()
            if not self._dragging and self._press_pos is not None:
                moved = (pos - self._press_pos).manhattanLength()
                self._dragging = moved >= QApplication.startDragDistance()
            if self._dragging:
                self.move(pos - self._drag_offset)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            if self._dragging:
                self.save_window_state()
            else:
                self.renderer.hop()
            self._drag_offset = None
            self._press_pos = None
            self._dragging = False
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.park_requested.emit()
            event.accept()
            return
        super().mouseDoubleClickEvent(event)

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

    def build_context_menu(self) -> QMenu:
        menu = QMenu(self)
        menu.addAction("打开乐园").triggered.connect(self.park_requested.emit)
        if self.menu_extender is not None:
            self.menu_extender(menu)
        menu.addSeparator()
        menu.addAction("隐藏桌宠").triggered.connect(self.hide_to_tray)
        menu.addAction("退出").triggered.connect(self.quit_requested.emit)
        return menu

    def contextMenuEvent(self, event: QContextMenuEvent) -> None:
        self.build_context_menu().exec(event.globalPos())
        event.accept()
