"""Seasonal colour themes (original implementation of the research style guide)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Theme:
    key: str
    label: str
    primary: str  # accent buttons, highlights
    primary_strong: str
    paper: str  # window background
    paper_alt: str  # cards
    ink: str  # main text
    ink_soft: str  # secondary text
    tint: str  # seasonal tint (header band)
    accent: str  # seasonal secondary accent
    motif: str  # small decorative glyph used by the UI and mascot

    def qcolor_hex(self, name: str) -> str:
        return getattr(self, name)


THEMES: dict[str, Theme] = {
    "sweet": Theme("sweet", "甜点（默认）", "#DC6A8E", "#E73357", "#FDF7E6", "#FFFDF8",
                   "#4B2814", "#A79681", "#F6E3E8", "#F0B9C8", "♡"),
    "winter": Theme("winter", "冬・雪国温泉街", "#DC6A8E", "#C94F78", "#F7FAFC", "#FFFFFF",
                    "#3E2A20", "#8C99A6", "#CFE6F2", "#5B8DB8", "❄"),
    "autumn": Theme("autumn", "秋・古都茶屋街", "#F25C7A", "#D9405F", "#F8EFE4", "#FFFBF5",
                    "#561814", "#A18F8B", "#F0DCC8", "#A45B47", "❦"),
    "summer": Theme("summer", "夏・海与温泉", "#DC6A8E", "#E73357", "#FDF7E6", "#FFFFFF",
                    "#4B2814", "#A79681", "#D9F1F5", "#26B2CA", "✿"),
}

DEFAULT_THEME = "sweet"


def get_theme(key: str | None) -> Theme:
    return THEMES.get(key or DEFAULT_THEME, THEMES[DEFAULT_THEME])


def stylesheet(theme: Theme) -> str:
    """Qt style sheet for the 乐园 window."""
    t = theme
    return f"""
    QWidget {{ color: {t.ink}; font-size: 14px; }}
    QMainWindow, QWidget#ParkRoot {{ background: {t.paper}; }}
    QWidget#HeaderBand {{ background: {t.tint}; border-bottom: 2px solid {t.primary}; }}
    QLabel#Wordmark {{ font-size: 24px; font-weight: 700; color: {t.ink}; }}
    QLabel#Unofficial {{ color: #FFFFFF; background: {t.primary_strong};
        border-radius: 9px; padding: 2px 10px; font-size: 12px; font-weight: 700; }}
    QLabel#Muted, QLabel#SubTitle {{ color: {t.ink_soft}; }}
    QLabel#TitleJa {{ font-size: 22px; font-weight: 700; }}
    QLabel#TitleEn {{ color: {t.ink_soft}; font-size: 12px; letter-spacing: 2px; }}
    QLabel#SectionHeading {{ font-size: 16px; font-weight: 700; color: {t.primary_strong}; }}
    QLabel#NameJa {{ font-size: 26px; font-weight: 700; }}
    QLabel#Chip {{ background: {t.tint}; color: {t.ink}; border-radius: 10px; padding: 3px 10px; }}
    QFrame#Card {{ background: {t.paper_alt}; border: 1px solid {t.tint}; border-radius: 18px; }}
    QFrame#Card:hover {{ border: 2px solid {t.primary}; }}
    QFrame#Panel {{ background: {t.paper_alt}; border: 1px solid {t.tint}; border-radius: 18px; }}
    QTabWidget::pane {{ border: none; }}
    QTabBar::tab {{ background: transparent; color: {t.ink_soft}; padding: 8px 14px;
        margin: 4px 2px; border-radius: 14px; }}
    QTabBar::tab:selected {{ background: {t.primary}; color: #FFFFFF; font-weight: 700; }}
    QTabBar::tab:hover:!selected {{ background: {t.tint}; color: {t.ink}; }}
    QPushButton {{ background: {t.primary}; color: #FFFFFF; border: none; border-radius: 14px;
        padding: 7px 16px; font-weight: 700; }}
    QPushButton:hover {{ background: {t.primary_strong}; }}
    QPushButton:disabled {{ background: {t.tint}; color: {t.ink_soft}; }}
    QPushButton#Ghost {{ background: transparent; color: {t.primary_strong};
        border: 1px solid {t.primary}; }}
    QPushButton#Ghost:hover {{ background: {t.tint}; }}
    QScrollArea {{ background: transparent; border: none; }}
    QScrollArea > QWidget > QWidget {{ background: transparent; }}
    QListWidget, QLineEdit, QComboBox, QTextBrowser {{ background: {t.paper_alt};
        border: 1px solid {t.tint}; border-radius: 10px; padding: 4px; }}
    QListWidget::item {{ padding: 8px; border-radius: 8px; }}
    QListWidget::item:selected {{ background: {t.tint}; color: {t.ink}; }}
    QSlider::groove:horizontal {{ height: 6px; background: {t.tint}; border-radius: 3px; }}
    QSlider::handle:horizontal {{ background: {t.primary}; width: 16px; margin: -5px 0;
        border-radius: 8px; }}
    a {{ color: {t.primary_strong}; }}
    """
