"""Wire settings, model library, renderer, pet window, tray and 乐园 together."""

from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import QObject, QUrl
from PySide6.QtGui import QActionGroup, QDesktopServices
from PySide6.QtWidgets import QApplication, QMenu

from app.catalog import Catalog
from app.config import BUILTIN_MASCOT, THEME_FOLLOW, SettingsStore
from app.models import ModelEntry, ModelLibrary
from app.renderers import ImageSource, MascotSource, SpriteRenderer, SpriteSource
from app.theme import Theme, get_theme
from app.tray import SystemTray, create_app_icon
from app.ui.park import ParkWindow
from app.window import PetWindow

log = logging.getLogger(__name__)


class AppController(QObject):
    def __init__(self, settings: SettingsStore | None = None, catalog: Catalog | None = None,
                 enable_tray: bool = True) -> None:
        super().__init__()
        self.settings = settings or SettingsStore()
        self.catalog = catalog or Catalog.load()
        self.library = ModelLibrary(self.settings.model_root)
        self._ensure_root()
        self.library.scan()

        self.renderer = SpriteRenderer()
        self.window = PetWindow(self.settings, self.renderer)
        self.window.setWindowIcon(create_app_icon())
        self.window.menu_extender = self._extend_pet_menu
        self.window.park_requested.connect(self.open_park)
        self.window.quit_requested.connect(self.quit)
        self._park: ParkWindow | None = None

        self.tray: SystemTray | None = None
        if enable_tray and SystemTray.is_available():
            self.tray = SystemTray(self.window, self._populate_model_menu)
            self.tray.park_requested.connect(self.open_park)
            self.tray.rescan_requested.connect(self.rescan)
            self.tray.quit_requested.connect(self.quit)

        self.current: ModelEntry | None = None
        self.last_error = ""
        self.apply_model(self.settings.current_model, persist=False)

    # ---- startup ----------------------------------------------------------
    def _ensure_root(self) -> None:
        try:
            self.library.ensure_root()
        except OSError as exc:  # read-only location etc.
            log.warning("无法创建模型文件夹 %s：%s", self.library.root, exc)

    def start(self) -> None:
        if self.tray is not None:
            self.tray.show()
        self.window.show_window()

    # ---- models -----------------------------------------------------------
    def pet_theme(self) -> Theme:
        mode = self.settings.theme_mode
        if mode != THEME_FOLLOW:
            return get_theme(mode)
        if self.current is not None and self.current.character:
            return get_theme(self.catalog.season_of(self.current.character))
        return get_theme(None)

    def _make_source(self, entry: ModelEntry) -> SpriteSource:
        if entry.renderer == "live2d" and entry.live2d_model is not None:
            from app.renderers.live2d_backend import Live2DSource

            return Live2DSource(entry.live2d_model, entry.live2d_zoom, entry.live2d_offset)
        if entry.idle is None:
            raise ValueError(f"模型缺少待机图：{entry.key}")
        return ImageSource(entry.idle, entry.blink)

    def apply_model(self, key: str, persist: bool = True) -> bool:
        entry = None if key == BUILTIN_MASCOT else self.library.get(key)
        ok = True
        self.last_error = ""
        if entry is not None and entry.supported:
            try:
                self.renderer.set_source(self._make_source(entry))
                self.current = entry
                self.window.set_model_scale(entry.scale)
            except (ValueError, RuntimeError) as exc:  # Live2DError is a RuntimeError
                log.warning("%s", exc)
                self.last_error = str(exc)
                ok = False
        else:
            ok = key == BUILTIN_MASCOT
        if entry is None or not ok:
            self.renderer.set_source(MascotSource())
            self.current = None
            self.window.set_model_scale(1.0)
            key = BUILTIN_MASCOT
        self.renderer.set_theme(self.pet_theme())
        if persist:
            self.settings.current_model = key
        if self._park is not None:
            self._park.models_page.refresh()
            self._park.models_page.show_message(
                f"切换失败，已换回糯糯：{self.last_error}" if self.last_error else "")
        return ok

    def rescan(self) -> None:
        self.library.scan()
        current = self.settings.current_model
        if current != BUILTIN_MASCOT and self.library.get(current) is None:
            self.apply_model(BUILTIN_MASCOT)
        if self._park is not None:
            self._park.refresh_models()

    def set_model_root(self, path: str) -> None:
        self.settings.model_root = path or None
        self.library.root = self.settings.model_root
        self._ensure_root()
        self.rescan()

    def open_model_folder(self) -> None:
        self._ensure_root()
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(Path(self.library.root))))

    # ---- menus ------------------------------------------------------------
    def _populate_model_menu(self, menu: QMenu) -> None:
        group = QActionGroup(menu)
        current = self.settings.current_model
        mascot = menu.addAction("糯糯（内置）")
        mascot.setCheckable(True)
        mascot.setChecked(current == BUILTIN_MASCOT)
        mascot.triggered.connect(lambda: self.apply_model(BUILTIN_MASCOT))
        group.addAction(mascot)
        usable = [e for e in self.library.entries if e.supported]
        if usable:
            menu.addSeparator()
        for entry in usable:
            action = menu.addAction(entry.name)
            action.setCheckable(True)
            action.setChecked(entry.key == current)
            action.triggered.connect(lambda _=False, k=entry.key: self.apply_model(k))
            group.addAction(action)
        menu.addSeparator()
        menu.addAction("打开模型文件夹").triggered.connect(self.open_model_folder)

    def _extend_pet_menu(self, menu: QMenu) -> None:
        self._populate_model_menu(menu.addMenu("切换桌宠"))
        if self.current is not None and self.current.character:
            heroine = self.catalog.heroine(self.current.character)
            if heroine is not None:
                menu.addAction(f"查看 {heroine.name_ja} 的资料").triggered.connect(
                    lambda: self.open_park(heroine.id))
        menu.addAction("重新扫描模型").triggered.connect(self.rescan)

    # ---- 乐园 -------------------------------------------------------------
    def park(self) -> ParkWindow:
        if self._park is None:
            park = ParkWindow(self.catalog, self.library, self.settings)
            park.setWindowIcon(create_app_icon())
            park.set_pet_requested.connect(self.apply_model)
            park.open_folder_requested.connect(self.open_model_folder)
            park.rescan_requested.connect(self.rescan)
            sp = park.settings_page
            sp.model_root_changed.connect(self.set_model_root)
            sp.theme_mode_changed.connect(self._on_theme_mode)
            sp.always_on_top_changed.connect(self._on_always_on_top)
            sp.animations_changed.connect(self._on_animations)
            sp.scale_changed.connect(self.window.set_scale)
            self.window.scale_changed.connect(sp.set_scale)
            self._park = park
        return self._park

    def open_park(self, heroine_id: str | None = None) -> ParkWindow:
        park = self.park()
        if heroine_id:
            park.show_heroine(heroine_id)
        park.show()
        park.raise_()
        park.activateWindow()
        return park

    def _on_theme_mode(self, mode: str) -> None:
        self.settings.theme_mode = mode
        self.renderer.set_theme(self.pet_theme())
        if self._park is not None:
            self._park.apply_theme()

    def _on_always_on_top(self, value: bool) -> None:
        self.settings.always_on_top = value
        self.window.set_always_on_top(value)

    def _on_animations(self, value: bool) -> None:
        self.settings.animations_enabled = value
        self.renderer.set_animated(value)

    # ---- shutdown ---------------------------------------------------------
    def quit(self) -> None:
        self.window.save_window_state()
        if self.tray is not None:
            self.tray.hide()
        app = QApplication.instance()
        if app is not None:
            app.quit()
