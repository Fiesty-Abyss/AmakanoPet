from pathlib import Path

from PySide6.QtCore import QPoint

from app.config import BUILTIN_MASCOT, THEME_FOLLOW, clamp_scale


def test_defaults(settings):
    assert settings.current_model == BUILTIN_MASCOT
    assert settings.always_on_top is True
    assert settings.animations_enabled is True
    assert settings.theme_mode == THEME_FOLLOW
    state = settings.load_window_state()
    assert state.position is None and state.scale == 1.0


def test_roundtrip(settings, tmp_path):
    settings.save_window_state(QPoint(120, 80), 1.3)
    settings.current_model = "group/kanon"
    settings.always_on_top = False
    settings.animations_enabled = False
    settings.theme_mode = "autumn"
    settings.last_tab = "amakano2"
    settings.model_root = tmp_path / "elsewhere"
    state = settings.load_window_state()
    assert state.position == QPoint(120, 80)
    assert state.scale == 1.3
    assert settings.current_model == "group/kanon"
    assert settings.always_on_top is False
    assert settings.animations_enabled is False
    assert settings.theme_mode == "autumn"
    assert settings.last_tab == "amakano2"
    assert settings.model_root == Path(tmp_path / "elsewhere")


def test_invalid_values_fall_back(settings):
    settings.theme_mode = "neon"
    assert settings.theme_mode == THEME_FOLLOW
    settings.model_root = None
    assert settings.model_root.name == "models"
    assert clamp_scale("abc") == 1.0
    assert clamp_scale(9) == 2.0
    assert clamp_scale(0.01) == 0.5
