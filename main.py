"""AmakanoPet application entry point."""

import sys

from PySide6.QtWidgets import QApplication

from app.config import APP_NAME
from app.window import PetWindow


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)

    window = PetWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
