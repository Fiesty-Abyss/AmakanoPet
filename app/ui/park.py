"""乐园 (park) window: game tabs → heroine cards → profile pages."""

from __future__ import annotations

import html
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QPushButton,
    QScrollArea,
    QSlider,
    QStackedWidget,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from app import __version__
from app.catalog import Catalog, Heroine, Title
from app.config import APP_DISPLAY_NAME, BUILTIN_MASCOT, THEME_FOLLOW, SettingsStore
from app.models import ModelEntry, ModelLibrary
from app.theme import THEMES, Theme, get_theme, stylesheet
from app.ui.widgets import ClickableFrame, FlowLayout, avatar_pixmap, chip

REPO_URL = "https://github.com/Fiesty-Abyss/AmakanoPet"
TAB_MODELS = "models"
TAB_SETTINGS = "settings"
TAB_ABOUT = "about"


def _label(text: str, name: str | None = None, wrap: bool = False) -> QLabel:
    label = QLabel(text)
    if name:
        label.setObjectName(name)
    label.setWordWrap(wrap)
    return label


LINK_COLOR = "#C94F78"  # readable rose on every seasonal background


def _links_html(items: list[tuple[str, str]]) -> str:
    return " · ".join(
        f'<a style="color:{LINK_COLOR}; text-decoration:none;" '
        f'href="{html.escape(url, quote=True)}">{html.escape(text)}</a>'
        for text, url in items
    )


def _source_label(url: str) -> str:
    host, _, path = url.split("//", 1)[-1].partition("/")
    if host == "vndb.org":
        return "VNDB 角色" if path.startswith("c") else "VNDB 作品"
    if host == "store.steampowered.com":
        return "Steam"
    if host.startswith("azarashi-soft"):
        return "官方角色页" if "character" in path else "官方网站"
    return host


def _source_links(urls: tuple[str, ...]) -> list[tuple[str, str]]:
    seen: dict[str, int] = {}
    items = []
    for url in urls:
        label = _source_label(url)
        seen[label] = seen.get(label, 0) + 1
        items.append((label if seen[label] == 1 else f"{label} {seen[label]}", url))
    return items


def short_title(title: Title) -> str:
    """Compact tab caption, e.g. アマカノ〜Second Season〜+ → アマカノ SS+."""
    return title.name_ja.replace("〜Second Season〜", " SS").replace("～Second Season～", " SS")


def _scroll(widget: QWidget) -> QScrollArea:
    area = QScrollArea()
    area.setWidgetResizable(True)
    area.setFrameShape(QFrame.Shape.NoFrame)
    area.setWidget(widget)
    return area


class HeroineCard(ClickableFrame):
    CARD_W, CARD_H, AVATAR = 196, 248, 112

    def __init__(self, heroine: Heroine, image: Path | None, parent: QWidget | None = None):
        super().__init__(parent)
        self.heroine = heroine
        self.setObjectName("Card")
        self.setFixedSize(self.CARD_W, self.CARD_H)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 16, 12, 12)
        layout.setSpacing(4)
        self.avatar = QLabel()
        self.avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.avatar.setPixmap(avatar_pixmap(heroine.initial, heroine.color, self.AVATAR, image))
        layout.addWidget(self.avatar)
        layout.addSpacing(6)
        name = _label(heroine.name_ja, "CardName")
        name.setStyleSheet("font-size: 17px; font-weight: 700;")
        name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(name)
        zh = _label(heroine.name_zh, "Muted")
        zh.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(zh)
        cv = _label(f"CV {heroine.cv}", "Muted")
        cv.setAlignment(Qt.AlignmentFlag.AlignCenter)
        cv.setStyleSheet("font-size: 12px;")
        layout.addWidget(cv)
        stripe = QFrame()
        stripe.setFixedHeight(4)
        stripe.setStyleSheet(f"background: {heroine.color}; border-radius: 2px;")
        layout.addStretch(1)
        layout.addWidget(stripe)
        self.setToolTip(f"查看 {heroine.name_ja} 的资料")


class ProfilePage(QWidget):
    """Scrollable heroine profile. Content is rebuilt by show_heroine()."""

    back_requested = Signal()
    set_pet_requested = Signal(str)
    open_folder_requested = Signal()

    def __init__(self, catalog: Catalog, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.catalog = catalog
        self.heroine: Heroine | None = None
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        bar = QHBoxLayout()
        bar.setContentsMargins(24, 12, 24, 0)
        self.back_button = QPushButton("← 返回角色一览")
        self.back_button.setObjectName("Ghost")
        self.back_button.clicked.connect(self.back_requested.emit)
        bar.addWidget(self.back_button)
        bar.addStretch(1)
        outer.addLayout(bar)
        self.body = QWidget()
        self.area = _scroll(self.body)
        outer.addWidget(self.area)

    def show_heroine(self, heroine: Heroine, models: list[ModelEntry]) -> None:
        self.heroine = heroine
        self.body = QWidget()
        self._build(heroine, models)
        self.area.setWidget(self.body)  # QScrollArea deletes the previous body
        self.area.verticalScrollBar().setValue(0)

    def _build(self, h: Heroine, models: list[ModelEntry]) -> None:
        root = QHBoxLayout(self.body)
        root.setContentsMargins(24, 16, 24, 24)
        root.setSpacing(24)

        # left column: avatar + binding
        left = QVBoxLayout()
        left.setSpacing(10)
        image = next((m.card_image() for m in models if not m.errors and m.card_image()), None)
        avatar = QLabel()
        avatar.setPixmap(avatar_pixmap(h.initial, h.color, 200, image))
        avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        left.addWidget(avatar)
        swatch = _label(f"代表色 {h.color}", "Muted")
        swatch.setAlignment(Qt.AlignmentFlag.AlignCenter)
        left.addWidget(swatch)
        panel = QFrame()
        panel.setObjectName("Panel")
        panel.setFixedWidth(220)
        pl = QVBoxLayout(panel)
        pl.addWidget(_label("我的模型", "SectionHeading"))
        usable = [m for m in models if m.supported]
        if usable:
            for model in usable:
                button = QPushButton(f"设为桌宠：{model.name}")
                button.clicked.connect(lambda _=False, k=model.key: self.set_pet_requested.emit(k))
                pl.addWidget(button)
        else:
            hint = _label(
                "还没有绑定这个角色的模型。在模型文件夹里新建一个文件夹，放入自己的立绘，"
                f"并在 pet.json 中写上\n\"character\": \"{h.id}\"",
                "Muted", wrap=True,
            )
            hint.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            pl.addWidget(hint)
        folder_button = QPushButton("打开模型文件夹")
        folder_button.setObjectName("Ghost")
        folder_button.clicked.connect(self.open_folder_requested.emit)
        pl.addWidget(folder_button)
        left.addWidget(panel)
        left.addStretch(1)
        root.addLayout(left)

        # right column: facts and text
        right = QVBoxLayout()
        right.setSpacing(8)
        right.addWidget(_label(h.name_ja, "NameJa"))
        right.addWidget(_label(f"{h.reading}　/　{h.romaji}", "Muted"))
        zh_line = QHBoxLayout()
        zh_line.addWidget(_label(f"中文名：{h.name_zh}"))
        zh_line.addWidget(chip("官方中文名" if h.name_zh_official else "常见译名"))
        zh_line.addStretch(1)
        right.addLayout(zh_line)

        facts = QFrame()
        facts.setObjectName("Panel")
        grid = QGridLayout(facts)
        grid.setHorizontalSpacing(24)
        rows = [
            ("学年", h.school_year or "—"),
            ("生日", h.birthday_text),
            ("身高", f"{h.height_cm} cm" if h.height_cm else "未公开"),
            ("血型", h.blood_type or "未公开"),
            ("CV", f"{h.cv}（{h.cv_romaji}）" if h.cv_romaji else h.cv),
            ("登场", "、".join(t.name_ja for t in self.catalog.titles_of(h.id))),
        ]
        for i, (key, value) in enumerate(rows):
            grid.addWidget(_label(key, "Muted"), i // 2, (i % 2) * 2)
            grid.addWidget(_label(value, wrap=True), i // 2, (i % 2) * 2 + 1)
        right.addWidget(facts)

        if h.traits:
            right.addWidget(_label("关键词", "SectionHeading"))
            chips = QWidget()
            flow = FlowLayout(chips)
            for trait in h.traits:
                flow.addWidget(chip(trait))
            right.addWidget(chips)
        right.addWidget(_label("角色简介", "SectionHeading"))
        right.addWidget(_label(h.summary, wrap=True))
        if h.amae:
            right.addWidget(_label("撒娇方式", "SectionHeading"))
            right.addWidget(_label(h.amae, wrap=True))
        right.addWidget(_label("资料来源", "SectionHeading"))
        sources = _label(_links_html(_source_links(h.sources)), wrap=True)
        sources.setOpenExternalLinks(True)
        right.addWidget(sources)
        note = _label("以上为维护者根据公开资料用自己的话整理，非官方介绍。", "Muted", wrap=True)
        note.setStyleSheet("font-size: 12px;")
        right.addWidget(note)
        right.addStretch(1)
        root.addLayout(right, 1)


class TitlePage(QStackedWidget):
    """One game tab: overview with heroine cards, and a profile page."""

    set_pet_requested = Signal(str)
    open_folder_requested = Signal()

    def __init__(self, title: Title, catalog: Catalog, library: ModelLibrary,
                 parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.title = title
        self.catalog = catalog
        self.library = library
        self.cards: list[HeroineCard] = []
        self.overview = QWidget()
        self.overview_area = _scroll(self.overview)
        self.addWidget(self.overview_area)
        self.profile = ProfilePage(catalog)
        self.profile.back_requested.connect(self.show_overview)
        self.profile.set_pet_requested.connect(self.set_pet_requested.emit)
        self.profile.open_folder_requested.connect(self.open_folder_requested.emit)
        self.addWidget(self.profile)
        self.rebuild()

    def rebuild(self) -> None:
        self.overview = QWidget()
        self.cards = []
        layout = QVBoxLayout(self.overview)
        layout.setContentsMargins(28, 20, 28, 24)
        layout.setSpacing(8)
        t = self.title
        head = QHBoxLayout()
        head.addWidget(_label(t.name_ja, "TitleJa"))
        head.addSpacing(8)
        head.addWidget(chip(f"{t.season_label} · {t.released[:4]}"))
        head.addStretch(1)
        layout.addLayout(head)
        layout.addWidget(_label(f"{t.name_en.upper()}　{t.name_zh}（译名）", "TitleEn"))
        layout.addWidget(_label(t.setting, wrap=True))
        if t.notes:
            layout.addWidget(_label(t.notes, "Muted", wrap=True))
        links = _label(_links_html([(x.label, x.url) for x in t.links]))
        links.setOpenExternalLinks(True)
        layout.addWidget(links)
        layout.addSpacing(10)
        layout.addWidget(_label("女主角", "SectionHeading"))
        grid = QGridLayout()
        grid.setSpacing(16)
        grid.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        for i, heroine in enumerate(self.catalog.heroines_of(t)):
            card = HeroineCard(heroine, self.library.avatar_for(heroine.id))
            card.clicked.connect(lambda h=heroine: self.show_heroine(h))
            grid.addWidget(card, i // 4, i % 4)
            self.cards.append(card)
        layout.addLayout(grid)
        layout.addStretch(1)
        self.overview_area.setWidget(self.overview)
        if self.currentIndex() == 1 and self.profile.heroine is not None:
            self.show_heroine(self.profile.heroine)

    def show_heroine(self, heroine: Heroine) -> None:
        self.profile.show_heroine(heroine, self.library.for_character(heroine.id))
        self.setCurrentIndex(1)

    def show_overview(self) -> None:
        self.setCurrentIndex(0)


class ModelsPage(QWidget):
    set_pet_requested = Signal(str)
    open_folder_requested = Signal()
    rescan_requested = Signal()

    def __init__(self, library: ModelLibrary, catalog: Catalog, settings: SettingsStore,
                 parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.library = library
        self.catalog = catalog
        self.settings = settings
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 20, 28, 24)
        layout.addWidget(_label("我的模型", "TitleJa"))
        self.root_label = _label("", "Muted", wrap=True)
        self.root_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(self.root_label)
        layout.addWidget(_label(
            "AmakanoPet 不附带任何角色立绘。请把自己有权使用的图片放进模型文件夹，"
            "格式见 docs/MODEL_FORMAT.md。", wrap=True))
        self.list = QListWidget()
        self.list.itemDoubleClicked.connect(lambda _item: self._use_selected())
        layout.addWidget(self.list, 1)
        buttons = QHBoxLayout()
        self.use_button = QPushButton("设为桌宠")
        self.use_button.clicked.connect(self._use_selected)
        mascot = QPushButton("换回糯糯")
        mascot.setObjectName("Ghost")
        mascot.clicked.connect(lambda: self.set_pet_requested.emit(BUILTIN_MASCOT))
        folder = QPushButton("打开模型文件夹")
        folder.setObjectName("Ghost")
        folder.clicked.connect(self.open_folder_requested.emit)
        rescan = QPushButton("重新扫描")
        rescan.setObjectName("Ghost")
        rescan.clicked.connect(self.rescan_requested.emit)
        for b in (self.use_button, mascot, folder, rescan):
            buttons.addWidget(b)
        buttons.addStretch(1)
        layout.addLayout(buttons)
        self.list.currentItemChanged.connect(lambda *_: self._update_buttons())
        self.refresh()

    def refresh(self) -> None:
        self.root_label.setText(f"模型文件夹：{self.library.root}")
        self.list.clear()
        current = self.settings.current_model
        mascot = QListWidgetItem(("● " if current == BUILTIN_MASCOT else "") +
                                 "糯糯（内置原创占位形象）\n    可用 · 随主题换装")
        mascot.setData(Qt.ItemDataRole.UserRole, BUILTIN_MASCOT)
        self.list.addItem(mascot)
        for entry in self.library.entries:
            heroine = self.catalog.heroine(entry.character) if entry.character else None
            bound = f" · 绑定：{heroine.name_ja}" if heroine else ""
            mark = "● " if entry.key == current else ""
            item = QListWidgetItem(f"{mark}{entry.name}　[{entry.key}]\n    {entry.status}{bound}")
            item.setData(Qt.ItemDataRole.UserRole, entry.key)
            if not entry.supported:
                item.setForeground(Qt.GlobalColor.gray)
            self.list.addItem(item)
        if not self.library.entries:
            empty = QListWidgetItem("（模型文件夹里还没有模型）")
            empty.setFlags(Qt.ItemFlag.NoItemFlags)
            self.list.addItem(empty)
        self._update_buttons()

    def _selected_key(self) -> str | None:
        item = self.list.currentItem()
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    def _update_buttons(self) -> None:
        key = self._selected_key()
        entry = self.library.get(key) if key and key != BUILTIN_MASCOT else None
        self.use_button.setEnabled(key == BUILTIN_MASCOT or bool(entry and entry.supported))

    def _use_selected(self) -> None:
        key = self._selected_key()
        if key == BUILTIN_MASCOT or (key and (e := self.library.get(key)) and e.supported):
            self.set_pet_requested.emit(key)


class SettingsPage(QWidget):
    model_root_changed = Signal(str)
    theme_mode_changed = Signal(str)
    always_on_top_changed = Signal(bool)
    animations_changed = Signal(bool)
    scale_changed = Signal(float)

    def __init__(self, settings: SettingsStore, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.settings = settings
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 20, 28, 24)
        layout.setSpacing(10)
        layout.addWidget(_label("设置", "TitleJa"))

        layout.addWidget(_label("模型文件夹", "SectionHeading"))
        row = QHBoxLayout()
        self.root_edit = QLineEdit(str(settings.model_root))
        self.root_edit.setReadOnly(True)
        row.addWidget(self.root_edit, 1)
        browse = QPushButton("更改…")
        browse.clicked.connect(self._browse)
        reset = QPushButton("恢复默认")
        reset.setObjectName("Ghost")
        reset.clicked.connect(lambda: self.model_root_changed.emit(""))
        row.addWidget(browse)
        row.addWidget(reset)
        layout.addLayout(row)

        layout.addWidget(_label("乐园主题", "SectionHeading"))
        self.theme_combo = QComboBox()
        self.theme_combo.addItem("跟随作品季节", THEME_FOLLOW)
        for key, theme in THEMES.items():
            self.theme_combo.addItem(theme.label, key)
        self.theme_combo.setCurrentIndex(max(0, self.theme_combo.findData(settings.theme_mode)))
        self.theme_combo.currentIndexChanged.connect(
            lambda _i: self.theme_mode_changed.emit(self.theme_combo.currentData()))
        layout.addWidget(self.theme_combo)

        layout.addWidget(_label("桌宠", "SectionHeading"))
        self.top_check = QCheckBox("窗口始终置顶")
        self.top_check.setChecked(settings.always_on_top)
        self.top_check.toggled.connect(self.always_on_top_changed.emit)
        layout.addWidget(self.top_check)
        self.anim_check = QCheckBox("呼吸 / 浮动 / 眨眼动画")
        self.anim_check.setChecked(settings.animations_enabled)
        self.anim_check.toggled.connect(self.animations_changed.emit)
        layout.addWidget(self.anim_check)
        scale_row = QHBoxLayout()
        scale_row.addWidget(_label("大小"))
        self.scale_slider = QSlider(Qt.Orientation.Horizontal)
        self.scale_slider.setRange(5, 20)
        self.scale_slider.setValue(round(settings.load_window_state().scale * 10))
        self.scale_value = _label(f"{self.scale_slider.value() / 10:.1f}×", "Muted")
        self.scale_slider.valueChanged.connect(self._on_scale)
        scale_row.addWidget(self.scale_slider, 1)
        scale_row.addWidget(self.scale_value)
        layout.addLayout(scale_row)
        layout.addWidget(_label("提示：在桌宠上按住 Ctrl 滚动滚轮也可以缩放；双击桌宠打开乐园。",
                                "Muted", wrap=True))
        layout.addStretch(1)

    def _browse(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "选择模型文件夹", self.root_edit.text())
        if folder:
            self.model_root_changed.emit(folder)

    def _on_scale(self, value: int) -> None:
        self.scale_value.setText(f"{value / 10:.1f}×")
        self.scale_changed.emit(value / 10)

    def set_model_root(self, path: Path) -> None:
        self.root_edit.setText(str(path))

    def set_scale(self, scale: float) -> None:
        self.scale_slider.blockSignals(True)
        self.scale_slider.setValue(round(scale * 10))
        self.scale_value.setText(f"{scale:.1f}×")
        self.scale_slider.blockSignals(False)


class AboutPage(QWidget):
    def __init__(self, catalog: Catalog, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 20, 28, 24)
        layout.setSpacing(10)
        layout.addWidget(_label(f"AmakanoPet v{__version__}", "TitleJa"))
        layout.addWidget(_label("アマカノ（甜蜜女友）系列的非官方同人桌宠与角色乐园。", wrap=True))
        layout.addWidget(_label("声明", "SectionHeading"))
        for text in (
            "本项目是粉丝自制的非官方作品，与あざらしそふと（Azarashi Soft）及其关联公司无关，"
            "也未获得其认可。作品名、角色名等版权与商标归各权利方所有。",
            "程序不包含、不下载任何官方立绘、Logo、语音或游戏解包资源。桌宠形象需要用户自备，"
            "请只使用你有权使用的素材，且不要再分发他人的素材。",
            "乐园中的角色资料为维护者根据公开信息自行撰写，仅含全年龄内容。",
            f"资料更新：{catalog.updated}",
        ):
            layout.addWidget(_label(text, wrap=True))
        layout.addWidget(_label("开源", "SectionHeading"))
        links = _label(_links_html([("源代码（MIT License）", REPO_URL),
                                    ("问题反馈", REPO_URL + "/issues")]))
        links.setOpenExternalLinks(True)
        layout.addWidget(links)
        layout.addStretch(1)


class ParkWindow(QMainWindow):
    set_pet_requested = Signal(str)
    open_folder_requested = Signal()
    rescan_requested = Signal()

    def __init__(self, catalog: Catalog, library: ModelLibrary, settings: SettingsStore,
                 parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.catalog = catalog
        self.library = library
        self.settings = settings
        self.setWindowTitle(f"{APP_DISPLAY_NAME}（非官方同人）")
        self.resize(1040, 720)
        self.setMinimumSize(860, 600)

        root = QWidget()
        root.setObjectName("ParkRoot")
        layout = QVBoxLayout(root)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        header = QWidget()
        header.setObjectName("HeaderBand")
        hl = QHBoxLayout(header)
        hl.setContentsMargins(24, 14, 24, 14)
        self.motif = _label("♡", "Wordmark")
        hl.addWidget(self.motif)
        hl.addWidget(_label("AmakanoPet 乐园", "Wordmark"))
        badge = _label("非官方同人", "Unofficial")
        hl.addWidget(badge, 0, Qt.AlignmentFlag.AlignVCenter)
        hl.addStretch(1)
        hl.addWidget(_label("用户自备模型 · 不含官方素材", "Muted"))
        layout.addWidget(header)

        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.title_pages: dict[str, TitlePage] = {}
        for title in catalog.titles:
            page = TitlePage(title, catalog, library)
            page.set_pet_requested.connect(self.set_pet_requested.emit)
            page.open_folder_requested.connect(self.open_folder_requested.emit)
            self.title_pages[title.id] = page
            self.tabs.addTab(page, short_title(title))
            self.tabs.setTabToolTip(self.tabs.count() - 1, f"{title.name_zh}（{title.released}）")
        self.models_page = ModelsPage(library, catalog, settings)
        self.models_page.set_pet_requested.connect(self.set_pet_requested.emit)
        self.models_page.open_folder_requested.connect(self.open_folder_requested.emit)
        self.models_page.rescan_requested.connect(self.rescan_requested.emit)
        self.tabs.addTab(self.models_page, "我的模型")
        self.settings_page = SettingsPage(settings)
        self.tabs.addTab(self.settings_page, "设置")
        self.about_page = AboutPage(catalog)
        self.tabs.addTab(self.about_page, "关于")
        self._tab_keys = [t.id for t in catalog.titles] + [TAB_MODELS, TAB_SETTINGS, TAB_ABOUT]
        layout.addWidget(self.tabs, 1)
        self.setCentralWidget(root)

        self.tabs.currentChanged.connect(self._on_tab_changed)
        self.settings_page.theme_mode_changed.connect(lambda _m: self.apply_theme())
        last = settings.last_tab
        if last in self._tab_keys:
            self.tabs.setCurrentIndex(self._tab_keys.index(last))
        self.apply_theme()

    # ---- navigation -------------------------------------------------------
    def current_tab_key(self) -> str:
        return self._tab_keys[self.tabs.currentIndex()]

    def show_tab(self, key: str) -> None:
        if key in self._tab_keys:
            self.tabs.setCurrentIndex(self._tab_keys.index(key))

    def show_heroine(self, heroine_id: str) -> bool:
        heroine = self.catalog.heroine(heroine_id)
        titles = self.catalog.titles_of(heroine_id)
        if heroine is None or not titles:
            return False
        self.show_tab(titles[0].id)
        self.title_pages[titles[0].id].show_heroine(heroine)
        return True

    def _on_tab_changed(self, _index: int) -> None:
        self.settings.last_tab = self.current_tab_key()
        self.apply_theme()

    # ---- theme ------------------------------------------------------------
    def current_theme(self) -> Theme:
        mode = self.settings.theme_mode
        if mode != THEME_FOLLOW:
            return get_theme(mode)
        title = self.catalog.title(self.current_tab_key())
        return get_theme(title.season if title else None)

    def apply_theme(self) -> None:
        theme = self.current_theme()
        self.motif.setText(theme.motif)
        self.setStyleSheet(stylesheet(theme))

    # ---- refresh ----------------------------------------------------------
    def refresh_models(self) -> None:
        for page in self.title_pages.values():
            page.rebuild()
        self.models_page.refresh()
        self.settings_page.set_model_root(self.library.root)

    def closeEvent(self, event: QCloseEvent) -> None:  # hide instead of quitting the app
        self.hide()
        event.ignore()
