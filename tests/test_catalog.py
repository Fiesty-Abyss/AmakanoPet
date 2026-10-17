import json
import re
from importlib import resources

from app.catalog import Catalog
from app.theme import THEMES

RAW = json.loads(resources.files("app.data").joinpath("amakano.json").read_text("utf-8"))
FORBIDDEN_KEYS = {"three_sizes", "bust", "waist", "hip", "cup", "measurements", "h_scenes"}


def test_loads_all_titles_and_heroines():
    catalog = Catalog.load()
    assert len(catalog.titles) == 7
    assert len(catalog.heroines) == 16


def test_ids_are_unique():
    title_ids = [t["id"] for t in RAW["titles"]]
    heroine_ids = [h["id"] for h in RAW["heroines"]]
    assert len(title_ids) == len(set(title_ids))
    assert len(heroine_ids) == len(set(heroine_ids))


def test_title_references_resolve_and_every_heroine_appears():
    catalog = Catalog.load()
    referenced = set()
    for title in catalog.titles:
        assert title.heroine_ids, title.id
        for heroine_id in title.heroine_ids:
            assert heroine_id in catalog.heroines, (title.id, heroine_id)
            referenced.add(heroine_id)
    assert referenced == set(catalog.heroines)


def test_seasons_have_themes():
    for title in Catalog.load().titles:
        assert title.season in THEMES


def test_every_entry_has_sources_and_links():
    for title in RAW["titles"]:
        assert title["links"], title["id"]
        for link in title["links"]:
            assert link["url"].startswith("https://")
    for heroine in RAW["heroines"]:
        assert heroine["sources"], heroine["id"]
        assert all(url.startswith("https://") for url in heroine["sources"])


def test_profile_fields_are_valid():
    for heroine in RAW["heroines"]:
        if heroine.get("birthday"):
            month, day = map(int, heroine["birthday"].split("-"))
            assert 1 <= month <= 12 and 1 <= day <= 31, heroine["id"]
        if heroine.get("height_cm") is not None:
            assert 130 <= heroine["height_cm"] <= 190, heroine["id"]
        assert re.fullmatch(r"#[0-9A-Fa-f]{6}", heroine["color"]), heroine["id"]
        assert heroine["summary"].strip()
        assert heroine["cv"].strip()


def test_all_ages_only():
    for heroine in RAW["heroines"]:
        assert not FORBIDDEN_KEYS & set(heroine), heroine["id"]


def test_no_image_or_audio_urls_in_data():
    text = json.dumps(RAW)
    assert not re.search(r"\.(png|jpe?g|webp|gif|ogg|mp3|wav|psb|zip|rar|7z)\b", text, re.I)


def test_lookup_helpers():
    catalog = Catalog.load()
    chitose = catalog.heroine("amakano2.chitose")
    assert chitose is not None
    assert chitose.birthday_text.endswith("日")
    assert [t.id for t in catalog.titles_of("amakano2.chitose")][0] == "amakano2"
    assert catalog.season_of("amakano2.chitose") == "autumn"
    assert catalog.season_of("amakano.sayuki") == "winter"
    assert catalog.season_of("unknown") == "sweet"
