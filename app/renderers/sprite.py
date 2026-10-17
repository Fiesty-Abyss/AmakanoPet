"""Sprite renderer: user PNG frames or the procedural mascot, with idle animation."""

from __future__ import annotations

import time
from pathlib import Path

from PySide6.QtCore import QObject, QRectF, QSize, Qt, QTimer, Signal
from PySide6.QtGui import QPainter, QPixmap

from app.renderers.animation import BlinkScheduler, bob_offset, breathing_scale, hop_offset
from app.renderers.mascot import paint_mascot
from app.theme import Theme, get_theme


class SpriteSource:
    """Something that can paint one frame of the pet."""

    def natural_size(self) -> QSize:
        raise NotImplementedError

    def paint(self, painter: QPainter, rect: QRectF, eye_openness: float, theme: Theme) -> None:
        raise NotImplementedError

    @property
    def has_blink(self) -> bool:
        return False


class MascotSource(SpriteSource):
    def natural_size(self) -> QSize:
        return QSize(260, 260)

    def paint(self, painter: QPainter, rect: QRectF, eye_openness: float, theme: Theme) -> None:
        paint_mascot(painter, rect, theme, eye_openness)

    @property
    def has_blink(self) -> bool:
        return True


class ImageSource(SpriteSource):
    """User-supplied idle image plus optional "eyes closed" frames."""

    MAX_EDGE = 1600  # downscale huge images once to keep painting cheap

    def __init__(self, idle: Path, blink: list[Path] | None = None) -> None:
        self.idle = self._load(idle)
        if self.idle.isNull():
            raise ValueError(f"无法读取图片：{idle}")
        self.blink = [p for p in (self._load(b) for b in (blink or [])) if not p.isNull()]

    @classmethod
    def _load(cls, path: Path) -> QPixmap:
        pixmap = QPixmap(str(path))
        if not pixmap.isNull() and max(pixmap.width(), pixmap.height()) > cls.MAX_EDGE:
            pixmap = pixmap.scaled(cls.MAX_EDGE, cls.MAX_EDGE, Qt.AspectRatioMode.KeepAspectRatio,
                                   Qt.TransformationMode.SmoothTransformation)
        return pixmap

    @property
    def has_blink(self) -> bool:
        return bool(self.blink)

    def natural_size(self) -> QSize:
        return self.idle.size()

    def paint(self, painter: QPainter, rect: QRectF, eye_openness: float, theme: Theme) -> None:
        frame = self.idle
        if self.blink and eye_openness < 0.35:
            frame = self.blink[0] if eye_openness > 0.1 or len(self.blink) == 1 else self.blink[-1]
        target = QSize(int(rect.width()), int(rect.height()))
        scaled = frame.size().scaled(target, Qt.AspectRatioMode.KeepAspectRatio)
        x = rect.x() + (rect.width() - scaled.width()) / 2
        y = rect.bottom() - scaled.height()
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        painter.drawPixmap(QRectF(x, y, scaled.width(), scaled.height()), frame,
                           QRectF(frame.rect()))


class SpriteRenderer(QObject):
    """Drives breathing / bobbing / blinking and paints the current frame."""

    frame_ready = Signal()
    FPS = 30

    def __init__(self, source: SpriteSource | None = None, theme: Theme | None = None,
                 parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._source: SpriteSource = source or MascotSource()
        self._theme = theme or get_theme(None)
        self._t0 = time.monotonic()
        self._hop_started: float | None = None
        self._blink = BlinkScheduler()
        self._animated = True
        self._timer = QTimer(self)
        self._timer.setInterval(int(1000 / self.FPS))
        self._timer.timeout.connect(self.frame_ready.emit)

    # ---- configuration ----------------------------------------------------
    @property
    def source(self) -> SpriteSource:
        return self._source

    def set_source(self, source: SpriteSource) -> None:
        self._source = source
        self.frame_ready.emit()

    def set_theme(self, theme: Theme) -> None:
        self._theme = theme
        self.frame_ready.emit()

    @property
    def theme(self) -> Theme:
        return self._theme

    def set_animated(self, enabled: bool) -> None:
        self._animated = enabled
        if enabled:
            self.start()
        else:
            self._timer.stop()
            self.frame_ready.emit()

    def start(self) -> None:
        if self._animated and not self._timer.isActive():
            self._timer.start()

    def stop(self) -> None:
        self._timer.stop()

    def hop(self) -> None:
        self._hop_started = self.elapsed()

    def elapsed(self) -> float:
        return time.monotonic() - self._t0

    # ---- painting ---------------------------------------------------------
    def paint(self, painter: QPainter, rect: QRectF, t: float | None = None) -> None:
        t = self.elapsed() if t is None else t
        scale_px = rect.height() / 360.0
        if self._animated:
            stretch = breathing_scale(t)
            offset = bob_offset(t) * scale_px
            if self._hop_started is not None:
                hop = hop_offset(t - self._hop_started) * scale_px
                if hop == 0.0:
                    self._hop_started = None
                offset += hop
            eyes = self._blink.openness(t) if self._source.has_blink else 1.0
        else:
            stretch, offset, eyes = 1.0, 0.0, 1.0

        margin = rect.height() * 0.03
        inner = rect.adjusted(margin, margin, -margin, -margin)
        painter.save()
        # squash/stretch anchored at the bottom centre
        painter.translate(inner.center().x(), inner.bottom())
        painter.scale(1.0 / (1.0 + (stretch - 1.0) * 0.5), stretch)
        painter.translate(-inner.center().x(), -inner.bottom())
        painter.translate(0, offset)
        self._source.paint(painter, inner.adjusted(0, 6 * scale_px, 0, 0), eyes, self._theme)
        painter.restore()
