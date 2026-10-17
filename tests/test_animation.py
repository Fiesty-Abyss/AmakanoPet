import random

import pytest

from app.renderers.animation import (
    BLINK_DURATION,
    BlinkScheduler,
    bob_offset,
    breathing_scale,
    hop_offset,
)


def test_breathing_stays_subtle():
    values = [breathing_scale(t / 10) for t in range(200)]
    assert max(values) <= 1.02 and min(values) >= 0.98
    assert breathing_scale(0) == pytest.approx(1.0)


def test_bob_goes_up_only():
    values = [bob_offset(t / 10) for t in range(100)]
    assert max(values) <= 0.0
    assert min(values) < -1.0


def test_hop_is_a_parabola():
    assert hop_offset(-0.1) == 0.0
    assert hop_offset(10) == 0.0
    assert hop_offset(0.225) < hop_offset(0.05) < 0


def test_blink_closes_then_reopens():
    blink = BlinkScheduler(rng=random.Random(1), next_blink=1.0)
    assert blink.openness(0.5) == 1.0
    assert blink.openness(1.0) == pytest.approx(1.0)
    assert blink.eyes_closed(1.0 + BLINK_DURATION / 2)
    assert blink.openness(1.0 + BLINK_DURATION + 0.01) == 1.0
    assert blink.next_blink > 1.0 + BLINK_DURATION


def test_blinks_keep_happening():
    blink = BlinkScheduler(rng=random.Random(7))
    closed = sum(blink.eyes_closed(i / 30) for i in range(30 * 60))
    assert closed > 10  # roughly every few seconds over a minute
