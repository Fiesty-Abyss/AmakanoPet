"""Capture real screenshots of the running app (offscreen) for the README.

    QT_QPA_PLATFORM=offscreen python tools/capture_screenshots.py docs/screenshots

    # Live2D shots of a model you are allowed to show (needs OpenGL: xcb + Xvfb):
    QT_QPA_PLATFORM=xcb xvfb-run -a python tools/capture_screenshots.py docs/screenshots \
        --live2d /path/to/model-folder --prefix shion

It starts the real AppController with a temporary config / model folder, drives
the UI and saves QWidget.grab() renders. Only original placeholder art is used.
"""

from __future__ import annotations

import argparse
import os
import random
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from PySide6.QtCore import QPoint, QSettings, QStandardPaths  # noqa: E402
from PySide6.QtGui import QCursor  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from app.config import SettingsStore  # noqa: E402
from app.controller import AppController  # noqa: E402


def settle(app: QApplication, ms: int = 120) -> None:
    from PySide6.QtCore import QEventLoop, QTimer

    loop = QEventLoop()
    QTimer.singleShot(ms, loop.quit)
    loop.exec()
    app.processEvents()


def capture_live2d(app: QApplication, out: Path, model_dir: Path, prefix: str) -> int:
    """Screenshots of a user-supplied Live2D model (temp copy only, never the repo)."""
    tmp = Path(tempfile.mkdtemp(prefix="amakanopet-l2d-shots-"))
    models = tmp / "models"
    shutil.copytree(model_dir, models / model_dir.name)
    settings = SettingsStore(QSettings(str(tmp / "settings.ini"), QSettings.Format.IniFormat))
    settings.model_root = models
    controller = AppController(settings, enable_tray=False)
    controller.library.snapshot_dir = tmp / "snapshots"
    controller.rescan()
    entry = next((e for e in controller.library.entries if e.renderer == "live2d"), None)
    if entry is None or not controller.apply_model(entry.key):
        print("Live2D 模型加载失败：", controller.last_error, file=sys.stderr)
        return 1
    controller.start()
    window = controller.window
    # the cursor rests on the pet's face, so it looks at the viewer
    QCursor.setPos(window.mapToGlobal(QPoint(window.width() // 2, int(window.height() * 0.22))))
    settle(app, 2500)  # physics settles, avatar snapshot is taken
    controller.window.grab().save(str(out / f"pet-live2d-{prefix}.png"))
    random.seed(0)  # reproducible pick of the click expression / motion
    controller.renderer.hop()  # click: motion or expression
    settle(app, 1200)
    controller.window.grab().save(str(out / f"pet-live2d-{prefix}-click.png"))
    park = controller.open_park()
    park.resize(1040, 720)
    shots = [("models-live2d.png", lambda: park.show_tab("models"))]
    if entry.character:
        heroine_title = controller.catalog.titles_of(entry.character)[0].id
        shots += [
            (f"park-{heroine_title}-live2d.png", lambda: (park.show_tab(heroine_title),
                                                         park.title_pages[heroine_title]
                                                         .show_overview())),
            (f"profile-{prefix}-live2d.png", lambda: park.show_heroine(entry.character)),
        ]
    for name, action in shots:
        action()
        settle(app, 200)
        park.grab().save(str(out / name))
    for path in sorted(out.glob(f"*{prefix}*.png")) + sorted(out.glob("*-live2d.png")):
        print(path)
    controller.quit()
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("out", nargs="?", default=str(ROOT / "docs" / "screenshots"))
    parser.add_argument("--live2d", type=Path, help="只截取这个 Live2D 模型文件夹的画面")
    parser.add_argument("--prefix", default="model", help="Live2D 截图文件名前缀")
    args = parser.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    if args.live2d:
        QStandardPaths.setTestModeEnabled(True)
        app = QApplication(sys.argv[:1])
        app.setApplicationName("AmakanoPet")
        return capture_live2d(app, out, args.live2d.resolve(), args.prefix)
    tmp = Path(tempfile.mkdtemp(prefix="amakanopet-shots-"))
    models = tmp / "models"
    # an original demo model bound to a heroine, to show how binding looks
    subprocess.run([sys.executable, str(ROOT / "tools" / "make_demo_model.py"), str(models),
                    "--character", "amakano3.kanon", "--theme", "summer"], check=True)
    (models / "broken-example").mkdir(parents=True)
    (models / "broken-example" / "pet.json").write_text('{"sprite": {"idle": "missing.png"}}',
                                                        encoding="utf-8")

    QStandardPaths.setTestModeEnabled(True)
    app = QApplication(sys.argv[:1])
    app.setApplicationName("AmakanoPet")
    settings = SettingsStore(QSettings(str(tmp / "settings.ini"), QSettings.Format.IniFormat))
    settings.model_root = models
    controller = AppController(settings, enable_tray=False)
    controller.start()
    settle(app, 1700)  # let the idle animation run a little
    controller.window.grab().save(str(out / "pet-mascot.png"))

    park = controller.open_park()
    park.resize(1040, 720)
    shots = [
        ("park-amakano.png", lambda: park.show_tab("amakano")),
        ("park-amakano2.png", lambda: park.show_tab("amakano2")),
        ("park-amakano3.png", lambda: park.show_tab("amakano3")),
        ("profile-chitose.png", lambda: park.show_heroine("amakano2.chitose")),
        ("profile-sayuki.png", lambda: park.show_heroine("amakano.sayuki")),
        ("profile-kanon-bound.png", lambda: park.show_heroine("amakano3.kanon")),
        ("models.png", lambda: park.show_tab("models")),
        ("settings.png", lambda: park.show_tab("settings")),
        ("about.png", lambda: park.show_tab("about")),
    ]
    for name, action in shots:
        action()
        settle(app)
        park.grab().save(str(out / name))

    controller.apply_model("demo-mascot")
    settle(app, 900)
    controller.window.grab().save(str(out / "pet-user-model.png"))
    for path in sorted(out.glob("*.png")):
        print(path)
    controller.quit()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
