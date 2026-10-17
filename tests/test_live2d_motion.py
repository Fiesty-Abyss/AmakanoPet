"""Gaze, idle sway and expression blending for Live2D models (no OpenGL needed)."""

import json

import pytest

from app.renderers import live2d_motion as motion
from app.renderers.live2d_backend import load_expressions

RANGES = motion.symmetric_ranges({
    "ParamAngleX": (-30, 30), "ParamAngleY": (-30, 30), "ParamAngleZ": (-30, 30),
    "ParamBodyAngleX": (-10, 10), "ParamEyeBallX": (-1, 1), "ParamEyeBallY": (-1, 1),
    "ParamBreath": (0, 1), "Param": (-1, 1),
})


def test_symmetric_ranges_skip_one_sided_params():
    assert RANGES["ParamAngleX"] == 30
    assert "ParamBreath" not in RANGES


def test_far_cursor_only_turns_the_head_part_way():
    gx, gy = motion.gaze_target(-5000, -5000, 280, 360)  # far top-left, outside the window
    assert -1 <= gx < -0.99 and 0.99 < gy <= 1
    offsets = motion.gaze_offsets(gx, gy, RANGES)
    assert abs(offsets["ParamAngleX"]) <= 0.4 * 30 + 1e-6
    assert abs(offsets["ParamAngleY"]) <= 0.3 * 30 + 1e-6
    assert "ParamAngleZ" not in offsets  # no head tilt from the gaze
    assert abs(offsets["ParamEyeBallX"]) <= 0.6


def test_cursor_on_the_head_looks_ahead():
    gx, gy = motion.gaze_target(140, 0.22 * 360, 280, 360)
    assert gx == pytest.approx(0) and gy == pytest.approx(0)


def test_gaze_follows_smoothly_and_returns_when_cursor_rests():
    follower = motion.GazeFollower()
    follower.set_cursor((900, 0), (1.0, 0.0), t=0.0)
    x, _ = follower.step(0.05, 0.05)
    assert 0 < x < 0.5  # eases in instead of jumping
    for i in range(1, 40):
        x, _ = follower.step(0.05 + i * 0.05, 0.05)
    assert x > 0.95
    follower.set_cursor((900, 0), (1.0, 0.0), t=10.0)  # same position, resting
    for i in range(60):
        x, _ = follower.step(10.0 + i * 0.05, 0.05)
    assert abs(x) < 0.05


def test_idle_sway_is_small():
    for t in (0.0, 1.3, 2.7, 4.1, 9.9):
        offsets = motion.idle_offsets(t, RANGES)
        assert abs(offsets["ParamAngleX"]) <= 3.0 + 1e-6
        assert abs(offsets["ParamAngleZ"]) <= 2.1 + 1e-6
        assert 0.0 <= motion.breath_value(t) <= 1.0


@pytest.mark.parametrize(("blend", "value", "base", "weight", "expected"), [
    ("Add", 2.0, -1.0, 1.0, 1.0),
    ("Add", 2.0, -1.0, 0.5, 0.0),
    ("Multiply", 0.0, 0.8, 1.0, 0.0),
    ("Multiply", 0.5, 0.8, 0.5, 0.6),
    ("Overwrite", 0.3, 1.0, 1.0, 0.3),
    ("Overwrite", 0.0, 1.0, 0.25, 0.75),
])
def test_blend_modes(blend, value, base, weight, expected):
    assert motion.ExpressionParam("P", value, blend).apply(base, weight) == pytest.approx(expected)


def test_parse_expression_defaults():
    exp = motion.parse_expression("x", {"Parameters": [
        {"Id": "A", "Value": 1}, {"Id": "B", "Value": 0.5, "Blend": "Multiply"},
        {"Id": "C", "Value": "bad"}, {"Value": 1}, {"Id": "D", "Value": 1, "Blend": "?"}],
        "FadeInTime": 0.5})
    assert [(p.id, p.blend) for p in exp.params] == [("A", "Add"), ("B", "Multiply"),
                                                     ("D", "Add")]
    assert exp.fade_in == 0.5 and exp.fade_out == motion.DEFAULT_FADE_SECONDS


def test_player_fades_in_holds_and_fades_out():
    exp = motion.parse_expression("blush", {"Parameters": [{"Id": "Param", "Value": 2}]})
    player = motion.ExpressionPlayer({"blush": exp})
    base = {"Param": -1.0}
    player.play("blush", t=0.0, hold=2.5)
    t, seen = 0.0, []
    while t < 5.0:
        t += 0.1
        player.step(t, 0.1)
        seen.append(player.values(base).get("Param", -1.0))
    assert max(seen) == pytest.approx(1.0)
    peak = seen.index(max(seen))
    rising, after = seen[:peak + 1], seen[25:]
    assert all(a <= b + 1e-9 for a, b in zip(rising, rising[1:], strict=False))  # fades in
    assert all(a >= b - 1e-9 for a, b in zip(after, after[1:], strict=False))  # fades out
    assert any(-1.0 < v < 1.0 for v in after)
    assert seen[-1] == pytest.approx(-1.0)
    assert player.current is None


def test_player_crossfades_to_the_next_expression():
    a = motion.parse_expression("a", {"Parameters": [{"Id": "P", "Value": 1}]})
    b = motion.parse_expression("b", {"Parameters": [{"Id": "Q", "Value": 1}]})
    player = motion.ExpressionPlayer({"a": a, "b": b})
    player.play("a", 0.0)
    for i in range(20):
        player.step(i * 0.1, 0.1)
    player.play("b", 2.0)
    player.step(2.5, 0.5)
    values = player.values({})
    assert 0 < values["P"] < 1 and 0 < values["Q"] < 1
    assert player.current == "b"


def test_load_expressions_from_model3(tmp_path):
    (tmp_path / "smile.exp3.json").write_text(json.dumps(
        {"Type": "Live2D Expression", "Parameters": [{"Id": "P", "Value": 2, "Blend": "Add"}]}),
        encoding="utf-8")
    model = tmp_path / "m.model3.json"
    model.write_text(json.dumps({"Version": 3, "FileReferences": {"Expressions": [
        {"Name": "smile", "File": "smile.exp3.json"},
        {"Name": "missing", "File": "missing.exp3.json"}]}}), encoding="utf-8")
    expressions = load_expressions(model)
    assert list(expressions) == ["smile"]
    assert expressions["smile"].params[0].value == 2
