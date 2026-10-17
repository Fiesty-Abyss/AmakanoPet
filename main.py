"""AmakanoPet application entry point."""

from __future__ import annotations

import argparse
import sys

from PySide6.QtWidgets import QApplication

from app import __version__
from app.config import APP_DISPLAY_NAME, APP_NAME
from app.controller import AppController


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="amakanopet", description="非官方同人桌宠 AmakanoPet")
    parser.add_argument("--park", action="store_true", help="启动时同时打开乐园")
    parser.add_argument("--version", action="version", version=f"AmakanoPet {__version__}")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    app = QApplication(sys.argv[:1])
    app.setApplicationName(APP_NAME)  # also decides the settings / model folder location
    app.setApplicationDisplayName(APP_DISPLAY_NAME)
    app.setApplicationVersion(__version__)
    app.setQuitOnLastWindowClosed(False)

    controller = AppController()
    controller.start()
    if args.park or controller.tray is None:
        # Without a tray the 乐园 is the only way to reach settings, so open it.
        controller.open_park()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
