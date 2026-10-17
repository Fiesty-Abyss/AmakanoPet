"""Read-only catalogue of Amakano titles and heroines (bundled JSON, text only)."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from importlib import resources
from pathlib import Path

SEASON_LABELS = {"winter": "冬", "summer": "夏", "autumn": "秋", "spring": "春"}


@dataclass(frozen=True)
class Link:
    label: str
    url: str


@dataclass(frozen=True)
class Heroine:
    id: str
    name_ja: str
    reading: str
    romaji: str
    name_zh: str
    name_zh_official: bool
    school_year: str
    birthday: str | None
    height_cm: int | None
    blood_type: str | None
    cv: str
    cv_romaji: str
    traits: tuple[str, ...]
    summary: str
    amae: str | None
    color: str
    initial: str
    sources: tuple[str, ...]

    @property
    def birthday_text(self) -> str:
        if not self.birthday:
            return "未公开"
        month, day = self.birthday.split("-")
        return f"{int(month)} 月 {int(day)} 日"


@dataclass(frozen=True)
class Title:
    id: str
    name_ja: str
    name_en: str
    name_zh: str
    released: str
    season: str
    setting: str
    notes: str
    heroine_ids: tuple[str, ...]
    links: tuple[Link, ...] = field(default_factory=tuple)

    @property
    def season_label(self) -> str:
        return SEASON_LABELS.get(self.season, self.season)


class Catalog:
    def __init__(self, data: dict) -> None:
        self.schema = data.get("schema", 1)
        self.updated = data.get("updated", "")
        self.disclaimer = data.get("disclaimer", "")
        self.heroines: dict[str, Heroine] = {}
        for raw in data.get("heroines", []):
            heroine = Heroine(
                id=raw["id"], name_ja=raw["name_ja"], reading=raw.get("reading", ""),
                romaji=raw.get("romaji", ""), name_zh=raw.get("name_zh", ""),
                name_zh_official=bool(raw.get("name_zh_official", False)),
                school_year=raw.get("school_year", ""), birthday=raw.get("birthday"),
                height_cm=raw.get("height_cm"), blood_type=raw.get("blood_type"),
                cv=raw.get("cv", ""), cv_romaji=raw.get("cv_romaji", ""),
                traits=tuple(raw.get("traits", [])), summary=raw.get("summary", ""),
                amae=raw.get("amae"), color=raw.get("color", "#DC6A8E"),
                initial=raw.get("initial") or raw["name_ja"][:1],
                sources=tuple(raw.get("sources", [])),
            )
            self.heroines[heroine.id] = heroine
        self.titles: list[Title] = [
            Title(
                id=raw["id"], name_ja=raw["name_ja"], name_en=raw.get("name_en", ""),
                name_zh=raw.get("name_zh", ""), released=raw.get("released", ""),
                season=raw.get("season", "winter"), setting=raw.get("setting", ""),
                notes=raw.get("notes", ""), heroine_ids=tuple(raw.get("heroines", [])),
                links=tuple(Link(x["label"], x["url"]) for x in raw.get("links", [])),
            )
            for raw in data.get("titles", [])
        ]

    @classmethod
    def load(cls, path: Path | None = None) -> Catalog:
        if path is None:
            text = resources.files("app.data").joinpath("amakano.json").read_text("utf-8")
        else:
            text = Path(path).read_text("utf-8")
        return cls(json.loads(text))

    def title(self, title_id: str) -> Title | None:
        return next((t for t in self.titles if t.id == title_id), None)

    def heroine(self, heroine_id: str) -> Heroine | None:
        return self.heroines.get(heroine_id)

    def heroines_of(self, title: Title) -> list[Heroine]:
        return [self.heroines[h] for h in title.heroine_ids if h in self.heroines]

    def titles_of(self, heroine_id: str) -> list[Title]:
        return [t for t in self.titles if heroine_id in t.heroine_ids]

    def season_of(self, heroine_id: str) -> str:
        """Season of the heroine's first (main) title."""
        titles = self.titles_of(heroine_id)
        return titles[0].season if titles else "sweet"
