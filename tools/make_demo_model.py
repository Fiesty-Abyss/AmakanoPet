"""Generate an original demo model folder to try the pet.json format.

The images are rendered from the built-in procedural mascot, so no character
artwork is involved. Usage:

    python tools/make_demo_model.py <模型文件夹> [--character amakano3.kanon] [--theme summer]
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PySide6.QtCore import QRectF  # noqa: E402
from PySide6.QtGui import QColor, QGuiApplication, QImage, QPainter  # noqa: E402

from app.renderers.mascot import paint_mascot  # noqa: E402
from app.theme import THEMES, get_theme  # noqa: E402


def render(path: Path, theme_key: str, eyes: float, size: tuple[int, int]) -> None:
    image = QImage(size[0], size[1], QImage.Format.Format_ARGB32)
    image.fill(QColor(0, 0, 0, 0))
    painter = QPainter(image)
    paint_mascot(painter, QRectF(0, 0, size[0], size[1]), get_theme(theme_key), eyes)
    painter.end()
    image.save(str(path))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("root", type=Path, help="模型根目录（会在其中新建一个子文件夹）")
    parser.add_argument("--name", default="示例模型（原创占位图）")
    parser.add_argument("--folder", default="demo-mascot")
    parser.add_argument("--character", default=None, help="绑定的角色 id，如 amakano3.kanon")
    parser.add_argument("--theme", default="summer", choices=sorted(THEMES))
    args = parser.parse_args()

    app = QGuiApplication(sys.argv[:1])  # noqa: F841 (needed for QPainter text/fonts)
    folder = args.root / args.folder
    folder.mkdir(parents=True, exist_ok=True)
    render(folder / "idle.png", args.theme, 1.0, (560, 720))
    render(folder / "blink.png", args.theme, 0.0, (560, 720))
    render(folder / "avatar.png", args.theme, 1.0, (256, 256))
    manifest = {
        "format": 1,
        "name": args.name,
        "renderer": "sprite",
        "sprite": {"idle": "idle.png", "blink": ["blink.png"]},
        "avatar": "avatar.png",
        "scale": 1.0,
        "author": "AmakanoPet",
        "license": "MIT（由内置原创吉祥物生成）",
    }
    if args.character:
        manifest["character"] = args.character
    (folder / "pet.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
                                     encoding="utf-8")
    print(f"已生成：{folder}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
