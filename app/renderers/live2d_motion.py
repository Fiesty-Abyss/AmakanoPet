"""Gentle head / eye movement for Live2D models (pure Python, no OpenGL needed).

The Cubism sample framework that live2d-py follows drives the head with large
values: following the cursor turns the head up to the full parameter range
(±30°) and tilts it by up to ±30° (``ParamAngleZ = x·y·-30``), and its breath
sways the head by ±15° / ±8° / ±10°. That suits a model that fills a window
and follows the mouse inside it, but a desktop pet sees the cursor almost
always outside its small window, so the head ended up turned and tilted to the
extreme with the eyes pinned to a corner. These helpers keep the pose close to
the model's default (what Cubism Viewer shows) and move it softly.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

#: (parameter, share of the parameter's positive range used at full gaze)
GAZE_X = (("ParamAngleX", 0.40), ("ParamBodyAngleX", 0.25), ("ParamEyeBallX", 0.60))
GAZE_Y = (("ParamAngleY", 0.30), ("ParamEyeBallY", 0.50))
#: (parameter, share of the positive range, period in seconds) — slow idle sway
IDLE_SWAY = (("ParamAngleX", 0.10, 6.5345), ("ParamAngleY", 0.07, 3.5345),
             ("ParamAngleZ", 0.07, 5.5345), ("ParamBodyAngleX", 0.15, 15.5345))
BREATH = ("ParamBreath", 3.2345)
#: the head is roughly here in the canvas (fractions of width / height)
HEAD_POINT = (0.5, 0.22)
GAZE_SMOOTHING = 0.18  # seconds, time constant of the head / eye follow
GAZE_IDLE_SECONDS = 4.0  # look ahead again when the cursor rests this long


def soft(value: float) -> float:
    """Map any offset to -1..1 so far-away cursors only turn the head part way."""
    return math.tanh(1.4 * value)


def gaze_target(x: float, y: float, width: float, height: float) -> tuple[float, float]:
    """Cursor position in canvas pixels -> soft gaze direction (-1..1, +x right, +y up)."""
    width, height = max(1.0, width), max(1.0, height)
    dx = (x - HEAD_POINT[0] * width) / width
    dy = (HEAD_POINT[1] * height - y) / height
    return soft(dx), soft(dy)


@dataclass
class GazeFollower:
    """Smoothly follows the cursor and looks ahead again when it rests."""

    x: float = 0.0
    y: float = 0.0
    _target: tuple[float, float] = (0.0, 0.0)
    _last_cursor: tuple[float, float] | None = None
    _last_move: float = field(default=-1e9)

    def set_cursor(self, cursor: tuple[float, float], target: tuple[float, float],
                   t: float) -> None:
        if self._last_cursor is None or (abs(cursor[0] - self._last_cursor[0])
                                         + abs(cursor[1] - self._last_cursor[1])) > 1.0:
            self._last_move = t
        self._last_cursor = cursor
        self._target = target

    def step(self, t: float, dt: float) -> tuple[float, float]:
        tx, ty = self._target if t - self._last_move < GAZE_IDLE_SECONDS else (0.0, 0.0)
        k = 1.0 - math.exp(-max(0.0, dt) / GAZE_SMOOTHING)
        self.x += (tx - self.x) * k
        self.y += (ty - self.y) * k
        return self.x, self.y


def gaze_offsets(gx: float, gy: float, ranges: dict[str, float]) -> dict[str, float]:
    """Parameter offsets for a gaze direction; ``ranges`` maps id -> positive max."""
    out: dict[str, float] = {}
    for axis, table in ((gx, GAZE_X), (gy, GAZE_Y)):
        for param, share in table:
            if param in ranges:
                out[param] = out.get(param, 0.0) + axis * share * ranges[param]
    return out


def idle_offsets(t: float, ranges: dict[str, float]) -> dict[str, float]:
    """Small breathing sway around the default pose."""
    return {param: share * ranges[param] * math.sin(2 * math.pi * t / period)
            for param, share, period in IDLE_SWAY if param in ranges}


def breath_value(t: float) -> float:
    """``ParamBreath`` (0..1), the same rhythm as the Cubism sample framework."""
    return 0.5 + 0.5 * math.sin(2 * math.pi * t / BREATH[1])


def symmetric_ranges(params: dict[str, tuple[float, float]]) -> dict[str, float]:
    """id -> how far the parameter can move both ways from 0 (only for -a..+b ranges)."""
    return {pid: min(-lo, hi) for pid, (lo, hi) in params.items() if lo < 0.0 < hi}


# ---- expressions -------------------------------------------------------------
DEFAULT_FADE_SECONDS = 1.0  # Cubism default when an exp3.json has no FadeIn/OutTime


@dataclass(frozen=True)
class ExpressionParam:
    id: str
    value: float
    blend: str = "Add"  # Add | Multiply | Overwrite

    def apply(self, base: float, weight: float) -> float:
        """Blend into ``base`` with ``weight`` 0..1, as the Cubism SDK specifies."""
        if self.blend == "Multiply":
            return base * (1.0 + (self.value - 1.0) * weight)
        if self.blend == "Overwrite":
            return base * (1.0 - weight) + self.value * weight
        return base + self.value * weight


@dataclass(frozen=True)
class Expression:
    name: str
    params: tuple[ExpressionParam, ...]
    fade_in: float = DEFAULT_FADE_SECONDS
    fade_out: float = DEFAULT_FADE_SECONDS


def parse_expression(name: str, data: dict) -> Expression:
    """Build an :class:`Expression` from the JSON of an ``.exp3.json`` file."""
    params = []
    for item in data.get("Parameters") or []:
        if not isinstance(item, dict) or not isinstance(item.get("Id"), str):
            continue
        blend = item.get("Blend", "Add")
        if blend not in ("Add", "Multiply", "Overwrite"):
            blend = "Add"
        try:
            params.append(ExpressionParam(item["Id"], float(item.get("Value", 0.0)), blend))
        except (TypeError, ValueError):
            continue

    def seconds(key: str) -> float:
        try:
            value = float(data.get(key, DEFAULT_FADE_SECONDS))
        except (TypeError, ValueError):
            return DEFAULT_FADE_SECONDS
        return value if value >= 0 else DEFAULT_FADE_SECONDS

    return Expression(name, tuple(params), seconds("FadeInTime"), seconds("FadeOutTime"))


@dataclass
class _Active:
    expression: Expression
    weight: float = 0.0
    target: float = 1.0
    until: float | None = None  # model time when it starts fading out


@dataclass
class ExpressionPlayer:
    """Plays exp3 expressions with smooth fade in *and* fade out.

    live2d-py's ``ResetExpression`` and timed ``SetExpression`` snap the face
    straight back to neutral; here an expression fades out over its
    ``FadeOutTime`` while the next one fades in.
    """

    expressions: dict[str, Expression] = field(default_factory=dict)
    _active: list[_Active] = field(default_factory=list)

    @property
    def names(self) -> list[str]:
        return list(self.expressions)

    @property
    def current(self) -> str | None:
        playing = [a for a in self._active if a.target > 0]
        return playing[-1].expression.name if playing else None

    def play(self, name: str, t: float, hold: float | None = None) -> None:
        expression = self.expressions[name]
        for active in self._active:
            active.target = 0.0
        existing = next((a for a in self._active if a.expression.name == name), None)
        if existing is not None:
            self._active.remove(existing)
        entry = existing or _Active(expression)
        entry.target, entry.until = 1.0, (t + hold if hold is not None else None)
        self._active.append(entry)

    def stop(self) -> None:
        for active in self._active:
            active.target = 0.0

    def step(self, t: float, dt: float) -> None:
        for active in list(self._active):
            if active.until is not None and t >= active.until:
                active.target, active.until = 0.0, None
            fade = active.expression.fade_in if active.target > 0 else active.expression.fade_out
            delta = dt / fade if fade > 0 else 1.0
            if active.weight < active.target:
                active.weight = min(active.target, active.weight + delta)
            else:
                active.weight = max(active.target, active.weight - delta)
            if active.target == 0.0 and active.weight == 0.0:
                self._active.remove(active)

    def values(self, base: dict[str, float]) -> dict[str, float]:
        """New values for the parameters touched by the active expressions."""
        out: dict[str, float] = {}
        for active in self._active:
            w = smoothstep(active.weight)
            for param in active.expression.params:
                current = out.get(param.id, base.get(param.id, 0.0))
                out[param.id] = param.apply(current, w)
        return out


def smoothstep(x: float) -> float:
    x = min(1.0, max(0.0, x))
    return x * x * (3.0 - 2.0 * x)
