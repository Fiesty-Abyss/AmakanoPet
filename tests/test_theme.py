from app.theme import DEFAULT_THEME, THEMES, get_theme, stylesheet


def test_known_and_fallback_themes():
    assert get_theme("winter").accent == "#5B8DB8"
    assert get_theme("summer").accent == "#26B2CA"
    assert get_theme("autumn").accent == "#A45B47"
    assert get_theme(None).key == DEFAULT_THEME
    assert get_theme("nope").key == DEFAULT_THEME


def test_stylesheet_uses_theme_colours():
    for theme in THEMES.values():
        qss = stylesheet(theme)
        assert theme.primary in qss and theme.paper in qss and theme.tint in qss
