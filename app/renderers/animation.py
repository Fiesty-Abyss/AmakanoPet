"""Pure animation maths, kept free of Qt so it can be unit-tested."""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field

BREATH_PERIOD = 3.6  # seconds
BREATH_AMPLITUDE = 0.014  # vertical stretch ratio
BOB_PERIOD = 2.8
BOB_AMPLITUDE = 4.0  # pixels at scale 1.0
BLINK_DURATION = 0.16
BLINK_INTERVAL = (2.6, 5.8)
HOP_DURATION = 0.45
HOP_HEIGHT = 18.0


def breathing_scale(t: float, period: float = BREATH_PERIOD,
                    amplitude: float = BREATH_AMPLITUDE) -> float:
    """Vertical scale factor around 1.0; horizontal uses the inverse half for volume."""
    return 1.0 + amplitude * math.sin(2 * math.pi * t / period)


def bob_offset(t: float, period: float = BOB_PERIOD, amplitude: float = BOB_AMPLITUDE) -> float:
    """Gentle up/down float in pixels (negative = up)."""
    return -amplitude * (0.5 - 0.5 * math.cos(2 * math.pi * t / period))


def hop_offset(elapsed: float, duration: float = HOP_DURATION, height: float = HOP_HEIGHT) -> float:
    """A single parabolic hop after a click; 0 when finished."""
    if elapsed < 0 or elapsed >= duration:
        return 0.0
    x = elapsed / duration
    return -4 * height * x * (1 - x)


@dataclass
class BlinkScheduler:
    """Decides when the eyes are closed. Openness is 1.0 (open) .. 0.0 (closed)."""

    rng: random.Random = field(default_factory=random.Random)
    interval: tuple[float, float] = BLINK_INTERVAL
    duration: float = BLINK_DURATION
    next_blink: float = 1.5
    _start: float | None = None

    def openness(self, t: float) -> float:
        if self._start is None and t >= self.next_blink:
            self._start = t
        if self._start is not None:
            phase = (t - self._start) / self.duration
            if phase >= 1.0:
                self._start = None
                self.next_blink = t + self.rng.uniform(*self.interval)
                # occasional double blink
                if self.rng.random() < 0.18:
                    self.next_blink = t + 0.22
                return 1.0
            return abs(1.0 - 2.0 * phase)  # 1 -> 0 -> 1
        return 1.0

    def eyes_closed(self, t: float) -> bool:
        return self.openness(t) < 0.35
