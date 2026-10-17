from PySide6.QtCore import QPoint, Qt

from app.catalog import Catalog
from app.config import BUILTIN_MASCOT
from app.controller import AppController
from app.models import ModelLibrary
from app.ui.park import HeroineCard, ParkWindow, short_title
from app.window import PetWindow
from tests.conftest import write_manifest, write_png


def make_park(qtbot, settings):
    library = ModelLibrary(settings.model_root)
    library.scan()
    park = ParkWindow(Catalog.load(), library, settings)
    qtbot.addWidget(park)
    return park


def test_park_has_title_tabs_and_cards(qtbot, settings):
    park = make_park(qtbot, settings)
    catalog = park.catalog
    assert park.tabs.count() == len(catalog.titles) + 3
    for title in catalog.titles:
        page = park.title_pages[title.id]
        assert len(page.cards) == len(title.heroine_ids)
    assert short_title(catalog.title("amakano-ss-plus")) == "アマカノ SS+"


def test_card_click_opens_profile_and_back(qtbot, settings):
    park = make_park(qtbot, settings)
    park.show()
    park.show_tab("amakano3")
    page = park.title_pages["amakano3"]
    card = page.cards[0]
    qtbot.mouseClick(card, Qt.MouseButton.LeftButton)
    assert page.currentIndex() == 1
    assert page.profile.heroine.id == card.heroine.id
    qtbot.mouseClick(page.profile.back_button, Qt.MouseButton.LeftButton)
    assert page.currentIndex() == 0


def test_theme_follows_tab_season_and_persists_tab(qtbot, settings):
    park = make_park(qtbot, settings)
    park.show_tab("amakano")
    assert park.current_theme().key == "winter"
    park.show_tab("amakano2")
    assert park.current_theme().key == "autumn"
    assert settings.last_tab == "amakano2"
    park.show_tab("amakano3")
    assert park.current_theme().key == "summer"
    settings.theme_mode = "winter"
    assert park.current_theme().key == "winter"


def test_show_heroine_jumps_to_first_title(qtbot, settings):
    park = make_park(qtbot, settings)
    assert park.show_heroine("amakano.koharu")
    assert park.current_tab_key() == "amakano"
    assert not park.show_heroine("missing")


def test_user_avatar_is_used_on_card(qtbot, settings):
    folder = settings.model_root / "kanon"
    write_png(folder / "idle.png", "#00AA00")
    write_manifest(folder, {"character": "amakano3.kanon", "sprite": {"idle": "idle.png"}})
    park = make_park(qtbot, settings)
    card = next(c for c in park.title_pages["amakano3"].cards if c.heroine.id == "amakano3.kanon")
    image = card.avatar.pixmap().toImage()
    centre = image.pixelColor(HeroineCard.AVATAR // 2, HeroineCard.AVATAR // 2)
    assert centre.green() > 150 and centre.red() < 60


def test_pet_window_scale_and_drag(qtbot, settings):
    window = PetWindow(settings)
    qtbot.addWidget(window)
    window.show()
    width = window.width()
    window.set_scale(1.5)
    assert window.width() > width
    assert settings.load_window_state().scale == 1.5
    window.set_scale(10)
    assert window.scale == 2.0
    with qtbot.waitSignal(window.park_requested):
        qtbot.mouseDClick(window, Qt.MouseButton.LeftButton, pos=QPoint(100, 200))


def test_pet_context_menu_has_entries(qtbot, settings):
    controller = AppController(settings, enable_tray=False)
    qtbot.addWidget(controller.window)
    texts = [a.text() for a in controller.window.build_context_menu().actions()]
    assert "打开乐园" in texts and "退出" in texts and "切换桌宠" in texts


def test_controller_switches_models_and_theme(qtbot, settings):
    folder = settings.model_root / "chitose"
    write_png(folder / "idle.png")
    write_manifest(folder, {"character": "amakano2.chitose", "sprite": {"idle": "idle.png"},
                            "scale": 1.5})
    controller = AppController(settings, enable_tray=False)
    qtbot.addWidget(controller.window)
    assert controller.renderer.theme.key == "sweet"
    assert controller.apply_model("chitose")
    assert settings.current_model == "chitose"
    assert controller.renderer.theme.key == "autumn"
    assert not controller.apply_model("does-not-exist")
    assert settings.current_model == BUILTIN_MASCOT
    park = controller.open_park("amakano2.chitose")
    qtbot.addWidget(park)
    assert park.title_pages["amakano2"].currentIndex() == 1


def test_rescan_falls_back_when_model_removed(qtbot, settings):
    folder = settings.model_root / "tmp"
    write_png(folder / "idle.png")
    controller = AppController(settings, enable_tray=False)
    qtbot.addWidget(controller.window)
    controller.apply_model("tmp")
    (folder / "idle.png").unlink()
    controller.rescan()
    assert settings.current_model == BUILTIN_MASCOT
