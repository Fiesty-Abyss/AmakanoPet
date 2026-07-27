"""AmakanoPet application entry point."""

import sys

from PySide6.QtWidgets import QApplication

from app.config import APP_NAME
from app.tray import SystemTray
from app.window import PetWindow


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setQuitOnLastWindowClosed(False)

    window = PetWindow()
    tray = SystemTray(window)

    def quit_application() -> None:
        window.save_window_state()
        tray.hide()
        app.quit()

    window.quit_requested.connect(quit_application)
    tray.quit_requested.connect(quit_application)
    tray.show()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
