"""Live2D helpers that work without live2d-py or OpenGL."""

import json

from PySide6.QtGui import QColor, QImage, QPainter

from app.models import ModelLibrary
from app.renderers import live2d_backend
from app.renderers.live2d_backend import head_crop, model_groups, needs_blink_fallback

EYES = ["ParamAngleX", "ParamEyeLOpen", "ParamEyeROpen"]


def write_model3(path, blink_ids):
    path.write_text(json.dumps({
        "Version": 3,
        "FileReferences": {"Moc": "x.moc3"},
        "Groups": [{"Target": "Parameter", "Name": "EyeBlink", "Ids": blink_ids},
                   {"Target": "Parameter", "Name": "LipSync", "Ids": []}],
    }), encoding="utf-8")
    return path


def test_model_groups(tmp_path):
    model = write_model3(tmp_path / "a.model3.json", ["ParamEyeLOpen", "ParamEyeROpen"])
    assert model_groups(model)["EyeBlink"] == ["ParamEyeLOpen", "ParamEyeROpen"]
    assert model_groups(tmp_path / "missing.model3.json") == {}


def test_blink_fallback_only_when_group_is_empty(tmp_path):
    empty = write_model3(tmp_path / "empty.model3.json", [])
    full = write_model3(tmp_path / "full.model3.json", ["ParamEyeLOpen"])
    assert needs_blink_fallback(empty, EYES)
    assert not needs_blink_fallback(full, EYES)
    assert not needs_blink_fallback(empty, ["ParamAngleX"])  # no eye params to drive
    v2 = tmp_path / "model.json"
    v2.write_text("{}", encoding="utf-8")
    assert not needs_blink_fallback(v2, EYES)  # Cubism 2 handles blinking itself


def test_head_crop_finds_the_top_of_the_figure():
    image = QImage(200, 400, QImage.Format.Format_ARGB32)
    image.fill(QColor(0, 0, 0, 0))
    # a "figure" from y=100 down, centred at x=120. Drawn with QPainter: thousands of
    # QImage.setPixelColor calls crash PySide6 6.12 on Python 3.10 (None refcount underflow).
    painter = QPainter(image)
    painter.fillRect(90, 100, 60, 280, QColor("#7A5A48"))
    painter.end()
    crop = head_crop(image)
    assert crop.width() == crop.height()
    assert 60 <= crop.width() <= 100
    assert crop.pixelColor(crop.width() // 2, crop.height() // 2).alpha() == 255


def test_head_crop_of_empty_image_returns_it():
    image = QImage(10, 10, QImage.Format.Format_ARGB32)
    image.fill(QColor(0, 0, 0, 0))
    assert head_crop(image).size() == image.size()


def test_library_uses_cached_snapshot(tmp_path, monkeypatch):
    monkeypatch.setattr(live2d_backend, "live2d_available", lambda: True)
    root = tmp_path / "models"
    folder = root / "l2d"
    folder.mkdir(parents=True)
    write_model3(folder / "m.model3.json", [])
    library = ModelLibrary(root, tmp_path / "snaps")
    [entry] = library.scan()
    assert entry.snapshot is None and entry.card_image() is None
    path = library.snapshot_path(entry)
    path.parent.mkdir(parents=True)
    image = QImage(8, 8, QImage.Format.Format_ARGB32)
    image.fill(QColor("#FF0000"))
    image.save(str(path))
    [entry] = library.scan()
    assert entry.card_image() == path
    assert library.avatar_for("anything") is None
