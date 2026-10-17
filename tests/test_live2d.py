"""Live2D integration tests.

They need the optional ``live2d-py`` package, a real OpenGL context (run under
``xvfb-run`` with ``QT_QPA_PLATFORM=xcb``) and a freely licensed sample model,
given by the ``AMAKANOPET_LIVE2D_SAMPLE`` environment variable (path to a
``*.model3.json``). The sample is downloaded at test time and never committed,
see ``tools/fetch_live2d_sample.sh``.
"""

from __future__ import annotations

import json
import os
import shutil
from pathlib import Path

import pytest

from app.renderers.live2d_backend import live2d_available

SAMPLE = os.environ.get("AMAKANOPET_LIVE2D_SAMPLE", "")

pytestmark = [
    pytest.mark.skipif(not live2d_available(), reason="live2d-py 未安装"),
    pytest.mark.skipif(not SAMPLE or not Path(SAMPLE).is_file(),
                       reason="未设置 AMAKANOPET_LIVE2D_SAMPLE"),
    pytest.mark.skipif(os.environ.get("QT_QPA_PLATFORM") == "offscreen",
                       reason="需要真实 OpenGL（xcb + Xvfb）"),
]


def visible_pixels(image) -> int:
    return sum(
        1 for y in range(0, image.height(), 4) for x in range(0, image.width(), 4)
        if image.pixelColor(x, y).alpha() > 16
    )


def test_render_sample_model(qapp):
    from app.renderers.live2d_backend import Live2DSource

    source = Live2DSource(Path(SAMPLE))
    try:
        frames = [source.render_image(280, 360) for _ in range(10)]
        assert frames[-1].width() == 280 and frames[-1].height() == 360
        assert visible_pixels(frames[-1]) > 300
        source.on_click()
        source.look_at(10, 10)
        assert visible_pixels(source.render_image(280, 360)) > 300
    finally:
        source.close()


def test_controller_uses_live2d_model(qtbot, settings):
    from app.controller import AppController
    from app.renderers.live2d_backend import Live2DSource

    target = settings.model_root / "sample"
    shutil.copytree(Path(SAMPLE).parent, target)  # temp copy only
    (target / "pet.json").write_text(json.dumps({
        "format": 1, "name": "Live2D 官方示例", "renderer": "live2d",
        "live2d": {"model": Path(SAMPLE).name},
    }), encoding="utf-8")
    controller = AppController(settings, enable_tray=False)
    qtbot.addWidget(controller.window)
    assert controller.apply_model("sample"), controller.last_error
    assert isinstance(controller.renderer.source, Live2DSource)
    controller.window.show()
    qtbot.wait(300)
    assert visible_pixels(controller.window.grab().toImage()) > 300
    controller.apply_model("builtin:mascot")
