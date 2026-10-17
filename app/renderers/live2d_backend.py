"""Optional Live2D (Cubism 2 / 3+) renderer for user-supplied models.

Uses the third-party ``live2d-py`` package (MIT), which bundles the official
Live2D Cubism SDK. Its Cubism Core is covered by the Live2D Proprietary
Software License; AmakanoPet does not vendor it. Install it separately with
``pip install live2d-py`` (Python 3.11+).

The model is rendered into an offscreen OpenGL framebuffer and then painted
with QPainter, so the pet window stays a plain translucent widget.
"""

from __future__ import annotations

import contextlib
import functools
import importlib.util
import io
import logging
import math
from pathlib import Path
from typing import Any

from PySide6.QtCore import QCoreApplication, QRectF, QSize
from PySide6.QtGui import QImage, QOffscreenSurface, QOpenGLContext, QPainter, QSurfaceFormat
from PySide6.QtOpenGL import QOpenGLFramebufferObject, QOpenGLFramebufferObjectFormat

from app.renderers.sprite import SpriteSource
from app.theme import Theme

log = logging.getLogger(__name__)

INSTALL_HINT = "需要安装 live2d-py（pip install live2d-py，Python 3.11+）"
_lib: Any = None
_gl: _GLState | None = None


class Live2DError(RuntimeError):
    pass


@functools.cache
def live2d_available() -> bool:
    """True when the live2d-py package can be imported (checked without importing it)."""
    try:
        return importlib.util.find_spec("live2d") is not None
    except (ImportError, ValueError):
        return False


def load_library() -> Any:
    """Import and initialise live2d-py once (its import banner is silenced)."""
    global _lib
    if _lib is not None:
        return _lib
    if not live2d_available():
        raise Live2DError(INSTALL_HINT)
    with contextlib.redirect_stdout(io.StringIO()):
        import live2d  # type: ignore[import-not-found]
    live2d.init()
    with contextlib.suppress(Exception):
        live2d.enableLog(False)
    app = QCoreApplication.instance()
    if app is not None:
        app.aboutToQuit.connect(_dispose)
    _lib = live2d
    return _lib


def _dispose() -> None:
    global _lib, _gl
    if _lib is not None:
        with contextlib.suppress(Exception):
            _lib.dispose()
    _lib = None
    _gl = None


class _GLState:
    """One shared offscreen OpenGL context for every Live2D model.

    live2d-py compiles its shaders into the context that is current during
    ``glInit()``, so all models keep using that same context.
    """

    def __init__(self, lib: Any) -> None:
        self.context = QOpenGLContext()
        fmt = QSurfaceFormat.defaultFormat()
        fmt.setAlphaBufferSize(8)
        fmt.setStencilBufferSize(8)
        self.context.setFormat(fmt)
        if not self.context.create():
            raise Live2DError("无法创建 OpenGL 上下文（Live2D 需要 OpenGL 2.1 以上）")
        self.surface = QOffscreenSurface()
        self.surface.setFormat(self.context.format())
        self.surface.create()
        if not self.make_current():
            raise Live2DError("无法激活 OpenGL 上下文")
        try:
            lib.glInit()
        finally:
            self.done()

    def make_current(self) -> bool:
        return bool(self.context.makeCurrent(self.surface))

    def done(self) -> None:
        self.context.doneCurrent()


def _gl_state(lib: Any) -> _GLState:
    global _gl
    if _gl is None:
        _gl = _GLState(lib)
    return _gl


class Live2DSource(SpriteSource):
    """Renders a Cubism model; the model animates itself (breath, blink, idle motions)."""

    self_animated = True
    wants_gaze = True

    def __init__(self, model_json: Path, zoom: float = 1.0,
                 offset: tuple[float, float] = (0.0, 0.0)) -> None:
        self.model_json = Path(model_json)
        self._lib = load_library()
        self._gl = _gl_state(self._lib)
        self._model: Any = None
        self._fbo: QOpenGLFramebufferObject | None = None
        self._size = QSize()
        self._groups: dict[str, int] = {}
        if not self._gl.make_current():
            raise Live2DError("无法激活 OpenGL 上下文")
        try:
            model = self._lib.Model()
            model.LoadModelJson(str(self.model_json))
            model.SetScale(float(zoom))
            model.SetOffset(float(offset[0]), float(offset[1]))
            self._groups = dict(model.GetMotionGroups() or {})
            self._model = model
        except Exception as exc:  # live2d-py raises plain RuntimeError / C++ errors
            raise Live2DError(f"Live2D 模型加载失败：{exc}") from exc
        finally:
            self._gl.done()

    # ---- SpriteSource -----------------------------------------------------
    def natural_size(self) -> QSize:
        return QSize(280, 360)

    @property
    def motion_groups(self) -> dict[str, int]:
        return dict(self._groups)

    def render_image(self, width: int, height: int) -> QImage:
        """Advance the model and return the current frame as a QImage."""
        width, height = max(1, width), max(1, height)
        if self._model is None or not self._gl.make_current():
            raise Live2DError("无法激活 OpenGL 上下文")
        try:
            size = QSize(width, height)
            if self._fbo is None or self._size != size:
                fbo_format = QOpenGLFramebufferObjectFormat()
                fbo_format.setAttachment(QOpenGLFramebufferObject.Attachment.CombinedDepthStencil)
                self._fbo = QOpenGLFramebufferObject(size, fbo_format)
                self._size = size
                self._model.Resize(width, height)
            self._fbo.bind()
            self._gl.context.functions().glViewport(0, 0, width, height)
            self._lib.clearBuffer(0.0, 0.0, 0.0, 0.0)
            self._model.Update()
            self._model.Draw()
            image = self._fbo.toImage()
            self._fbo.release()
            return image
        finally:
            self._gl.done()

    def paint(self, painter: QPainter, rect: QRectF, eye_openness: float, theme: Theme) -> None:
        device = painter.device()
        dpr = device.devicePixelRatioF() if device is not None else 1.0
        image = self.render_image(math.ceil(rect.width() * dpr), math.ceil(rect.height() * dpr))
        painter.drawImage(rect, image)

    # ---- interaction ------------------------------------------------------
    def on_click(self) -> None:
        if self._model is None:
            return
        group = next((g for g in ("TapBody", "Tap", "tap_body") if self._groups.get(g)), None)
        with contextlib.suppress(Exception):
            if group is not None:
                self._model.StartRandomMotion(group, 2)
            elif self._groups:
                self._model.StartRandomMotion(None, 2)

    def look_at(self, x: float, y: float) -> None:
        """Make the model look towards a point in canvas pixels."""
        if self._model is not None:
            with contextlib.suppress(Exception):
                self._model.Drag(float(x), float(y))

    def close(self) -> None:
        if self._model is None:
            return
        if self._gl.make_current():
            self._fbo = None
            with contextlib.suppress(Exception):
                self._model.DestroyRenderer()
            self._gl.done()
        self._model = None
