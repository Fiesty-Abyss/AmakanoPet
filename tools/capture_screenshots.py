"""Capture real screenshots of the running app (offscreen) for the README.

    QT_QPA_PLATFORM=offscreen python tools/capture_screenshots.py docs/screenshots

It starts the real AppController with a temporary config / model folder, drives
the UI and saves QWidget.grab() renders. Only original placeholder art is used.
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from PySide6.QtCore import QSettings, QStandardPaths  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from app.config import SettingsStore  # noqa: E402
from app.controller import AppController  # noqa: E402


def settle(app: QApplication, ms: int = 120) -> None:
    from PySide6.QtCore import QEventLoop, QTimer

    loop = QEventLoop()
    QTimer.singleShot(ms, loop.quit)
    loop.exec()
    app.processEvents()


def main() -> int:
    out = Path(sys.argv[1] if len(sys.argv) > 1 else ROOT / "docs" / "screenshots")
    out.mkdir(parents=True, exist_ok=True)
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
