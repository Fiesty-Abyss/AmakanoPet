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
import json
import logging
import math
import random
import time
from pathlib import Path
from typing import Any

from PySide6.QtCore import QCoreApplication, QRectF, QSize
from PySide6.QtGui import QImage, QOffscreenSurface, QOpenGLContext, QPainter, QSurfaceFormat
from PySide6.QtOpenGL import QOpenGLFramebufferObject, QOpenGLFramebufferObjectFormat

from app.renderers import live2d_motion as motion
from app.renderers.animation import BlinkScheduler
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


EYE_OPEN_PARAMS = ("ParamEyeLOpen", "ParamEyeROpen")
CLICK_EXPRESSION_SECONDS = 2.5


def model_groups(model_json: Path) -> dict[str, list[str]]:
    """Read the ``Groups`` section (EyeBlink / LipSync ids) of a Cubism 3+ model3.json."""
    try:
        data = json.loads(Path(model_json).read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return {}
    groups: dict[str, list[str]] = {}
    for group in data.get("Groups") or []:
        if isinstance(group, dict) and isinstance(group.get("Name"), str):
            ids = group.get("Ids") or []
            groups[group["Name"]] = [i for i in ids if isinstance(i, str)]
    return groups


def needs_blink_fallback(model_json: Path, param_ids: list[str]) -> bool:
    """True for Cubism 3+ models whose EyeBlink group is empty but that have eye params.

    Models exported without an EyeBlink group (common for first models made
    for VTube Studio, which drives the eyes by face tracking) would otherwise
    never blink in AmakanoPet.
    """
    if not str(model_json).endswith(".model3.json"):
        return False
    if model_groups(model_json).get("EyeBlink"):
        return False
    return all(p in param_ids for p in EYE_OPEN_PARAMS)


def load_expressions(model_json: Path) -> dict[str, motion.Expression]:
    """Read the exp3.json files listed in a model3.json (name -> Expression)."""
    model_json = Path(model_json)
    try:
        data = json.loads(model_json.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return {}
    out: dict[str, motion.Expression] = {}
    for item in (data.get("FileReferences") or {}).get("Expressions") or []:
        if not isinstance(item, dict) or not isinstance(item.get("File"), str):
            continue
        name = item.get("Name") if isinstance(item.get("Name"), str) else Path(item["File"]).stem
        try:
            exp = json.loads((model_json.parent / item["File"]).read_text(encoding="utf-8-sig"))
        except (OSError, ValueError):
            log.warning("无法读取表情文件：%s", item["File"])
            continue
        if isinstance(exp, dict):
            out[name] = motion.parse_expression(name, exp)
    return out


def head_crop(image: QImage, ratio: float = 0.3) -> QImage:
    """Square crop around the top of the visible figure, used as a card avatar."""
    width, height = image.width(), image.height()
    step = max(1, min(width, height) // 160)
    top = bottom = left = right = None
    for y in range(0, height, step):
        for x in range(0, width, step):
            if image.pixelColor(x, y).alpha() > 24:
                top = y if top is None else top
                bottom = y
                left = x if left is None or x < left else left
                right = x if right is None or x > right else right
    if top is None or bottom is None or left is None or right is None:
        return image
    side = max(16, int((bottom - top) * ratio))
    # centre on the visible pixels of the top band (the head)
    band = [x for y in range(top, min(height, top + side), step)
            for x in range(0, width, step) if image.pixelColor(x, y).alpha() > 24]
    centre = sum(band) // len(band) if band else (left + right) // 2
    x0 = min(max(0, centre - side // 2), max(0, width - side))
    y0 = max(0, top - side // 12)
    return image.copy(x0, y0, side, side)


def _gl_state(lib: Any) -> _GLState:
    global _gl
    if _gl is None:
        _gl = _GLState(lib)
    return _gl


class Live2DSource(SpriteSource):
    """Renders a Cubism model with idle motions, blinking, breathing and a soft gaze."""

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
        self._expressions = []
        self._blink = None
        self._t0 = time.monotonic()
        self._last_t = 0.0
        self._expression_until: float | None = None
        self._gaze = motion.GazeFollower()
        self._ranges: dict[str, float] = {}
        self._has_breath = False
        self._v3 = False
        self._player = motion.ExpressionPlayer()
        if not self._gl.make_current():
            raise Live2DError("无法激活 OpenGL 上下文")
        try:
            model = self._lib.Model()
            model.LoadModelJson(str(self.model_json))
            model.SetScale(float(zoom))
            model.SetOffset(float(offset[0]), float(offset[1]))
            self._groups = dict(model.GetMotionGroups() or {})
            self._expressions: list[str] = list(model.GetExpressions() or [])
            self._blink: BlinkScheduler | None = None
            if needs_blink_fallback(self.model_json, list(model.GetParamIds() or [])):
                self._blink = BlinkScheduler()
                log.info("模型未定义 EyeBlink 参数组，使用 AmakanoPet 的眨眼：%s", self.model_json)
            ids = list(model.GetParamIds() or [])
            self._v3 = bool(model.IsV3()) and str(self.model_json).endswith(".model3.json")
            if self._v3:
                # we drive breath and gaze ourselves (see live2d_motion)
                model.SetAutoBreath(False)
                self._ranges = motion.symmetric_ranges({
                    pid: (model.GetParamMinByIndex(i), model.GetParamMaxByIndex(i))
                    for i, pid in enumerate(ids)})
                self._has_breath = motion.BREATH[0] in ids
                self._player = motion.ExpressionPlayer(load_expressions(self.model_json))
                if self._player.names:
                    self._expressions = self._player.names
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
            self._update(time.monotonic() - self._t0)
            self._model.Draw()
            image = self._fbo.toImage()
            self._fbo.release()
            return image
        finally:
            self._gl.done()

    @property
    def uses_fallback_blink(self) -> bool:
        return self._blink is not None

    @property
    def expressions(self) -> list[str]:
        return list(self._expressions)

    def _update(self, t: float) -> None:
        """Advance the model by one frame.

        Cubism 3+ models run the framework steps one by one: motion, blink,
        expressions (blended with each exp3 parameter's Add / Multiply /
        Overwrite mode, fading in and out), then our gentle gaze and breathing,
        and only then physics, so the hair follows the head.
        """
        dt = min(0.1, max(0.0, t - self._last_t))
        self._last_t = t
        model = self._model
        if not self._v3:
            model.Update()
            self._apply_extras(t)
            return
        model.LoadParameters()  # values saved after the last motion step
        if self._groups.get("Idle") and model.IsMotionFinished():
            with contextlib.suppress(Exception):
                model.StartRandomMotion("Idle", 1)
        model.UpdateMotion(dt)
        model.SaveParameters()
        if self._blink is None:
            model.UpdateBlink(dt)  # the model's own EyeBlink group, if any
        if self._player.names:
            self._player.step(t, dt)
            base = {pid: model.GetParamValueById(pid)
                    for e in self._player.expressions.values() for pid in (p.id for p in e.params)}
            for pid, value in self._player.values(base).items():
                model.SetParamById(pid, value)
        else:
            model.UpdateExpression(dt)
        gx, gy = self._gaze.step(t, dt)
        offsets = motion.idle_offsets(t, self._ranges)
        for pid, value in motion.gaze_offsets(gx, gy, self._ranges).items():
            offsets[pid] = offsets.get(pid, 0.0) + value
        for pid, value in offsets.items():
            model.AddParamById(pid, value)
        if self._has_breath:
            model.SetParamById(motion.BREATH[0], motion.breath_value(t))
        self._apply_extras(t)
        model.UpdatePhysics(dt)
        model.UpdatePose(dt)

    def _apply_extras(self, t: float) -> None:
        """Fallback blink and the end of a click expression."""
        if self._blink is not None:
            openness = self._blink.openness(t)
            for param in EYE_OPEN_PARAMS:
                # multiply with whatever the model already set (e.g. expressions)
                current = self._model.GetParamValueById(param)
                self._model.SetParamById(param, current * openness)
        if self._expression_until is not None and t >= self._expression_until:
            self._expression_until = None
            with contextlib.suppress(Exception):
                self._model.ResetExpression()

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
            elif self._player.names:
                # models without motions: show a random expression for a moment
                choices = [n for n in self._player.names if n != self._player.current]
                self._player.play(random.choice(choices or self._player.names),
                                  time.monotonic() - self._t0, hold=CLICK_EXPRESSION_SECONDS)
            elif self._expressions:
                self._model.SetExpression(random.choice(self._expressions))
                self._expression_until = (time.monotonic() - self._t0
                                          + CLICK_EXPRESSION_SECONDS)

    def look_at(self, x: float, y: float) -> None:
        """Make the model look towards a point in canvas pixels."""
        if self._model is None:
            return
        if not self._v3:
            with contextlib.suppress(Exception):
                self._model.Drag(float(x), float(y))
            return
        size = self._size if self._size.isValid() else self.natural_size()
        target = motion.gaze_target(x, y, size.width(), size.height())
        self._gaze.set_cursor((x, y), target, time.monotonic() - self._t0)

    def snapshot(self, path: Path, width: int = 560, height: int = 720) -> bool:
        """Save a head shot of the current frame (for cards when no avatar is given)."""
        image = head_crop(self.render_image(width, height))
        path.parent.mkdir(parents=True, exist_ok=True)
        return bool(image.save(str(path)))

    def close(self) -> None:
        if self._model is None:
            return
        if self._gl.make_current():
            self._fbo = None
            with contextlib.suppress(Exception):
                self._model.DestroyRenderer()
            self._gl.done()
        self._model = None
