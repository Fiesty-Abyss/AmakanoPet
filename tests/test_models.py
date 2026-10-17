from pathlib import Path

from app.models import ModelLibrary
from app.renderers import live2d_backend
from tests.conftest import write_manifest, write_png


def scan(root: Path):
    library = ModelLibrary(root)
    library.scan()
    return library


def test_missing_root_is_empty(tmp_path):
    assert scan(tmp_path / "nope").entries == []


def test_manifest_model(model_root):
    folder = model_root / "kanon"
    write_png(folder / "idle.png")
    write_png(folder / "blink.png", "#000000")
    write_png(folder / "avatar.png", "#FFFFFF")
    write_manifest(folder, {
        "format": 1, "name": "测试模型", "character": "amakano3.kanon", "renderer": "sprite",
        "sprite": {"idle": "idle.png", "blink": ["blink.png"]}, "avatar": "avatar.png",
        "scale": 1.2, "author": "me", "license": "CC0",
    })
    library = scan(model_root)
    [entry] = library.entries
    assert entry.key == "kanon"
    assert entry.supported, entry.errors
    assert entry.name == "测试模型"
    assert entry.blink and entry.blink[0].name == "blink.png"
    assert entry.scale == 1.2
    assert library.for_character("amakano3.kanon") == [entry]
    assert library.avatar_for("amakano3.kanon").name == "avatar.png"


def test_folder_without_manifest_is_autodetected(model_root):
    folder = model_root / "group" / "simple"
    write_png(folder / "idle.png")
    write_png(folder / "blink1.png")
    [entry] = scan(model_root).entries
    assert entry.key == "group/simple"
    assert entry.supported
    assert len(entry.blink) == 1
    assert entry.warnings


def test_path_traversal_is_rejected(model_root, tmp_path):
    write_png(tmp_path / "outside.png")
    write_manifest(model_root / "evil", {"sprite": {"idle": "../../outside.png"}})
    [entry] = scan(model_root).entries
    assert not entry.supported
    assert any(".." in e for e in entry.errors)


def test_absolute_path_is_rejected(model_root, tmp_path):
    outside = write_png(tmp_path / "abs.png")
    write_manifest(model_root / "abs", {"sprite": {"idle": str(outside)}})
    [entry] = scan(model_root).entries
    assert entry.errors


def test_missing_file_and_bad_type(model_root):
    folder = model_root / "bad"
    (folder).mkdir()
    (folder / "idle.gif").write_bytes(b"GIF89a")
    write_manifest(folder, {"sprite": {"idle": "idle.gif", "blink": "nope.png"}})
    [entry] = scan(model_root).entries
    assert len(entry.errors) == 2


def test_invalid_json_and_format(model_root):
    (model_root / "broken").mkdir()
    (model_root / "broken" / "pet.json").write_text("{not json", encoding="utf-8")
    write_manifest(model_root / "future", {"format": 99})
    write_manifest(model_root / "list", [1, 2])  # type: ignore[arg-type]
    entries = {e.key: e for e in scan(model_root).entries}
    assert entries["broken"].errors and entries["future"].errors and entries["list"].errors


def test_bad_scale_and_unknown_renderer(model_root):
    write_png(model_root / "a" / "idle.png")
    write_manifest(model_root / "a", {"sprite": {"idle": "idle.png"}, "scale": 100})
    write_manifest(model_root / "b", {"renderer": "spine"})
    entries = {e.key: e for e in scan(model_root).entries}
    assert entries["a"].errors and entries["b"].errors


def test_live2d_without_library_is_unsupported(model_root, monkeypatch):
    monkeypatch.setattr(live2d_backend, "live2d_available", lambda: False)
    folder = model_root / "l2d"
    folder.mkdir()
    (folder / "hiyori.model3.json").write_text("{}", encoding="utf-8")
    [entry] = scan(model_root).entries
    assert entry.renderer == "live2d"
    assert entry.live2d_model.name == "hiyori.model3.json"
    assert not entry.supported
    assert "live2d-py" in entry.status


def test_live2d_with_library_is_supported(model_root, monkeypatch):
    monkeypatch.setattr(live2d_backend, "live2d_available", lambda: True)
    folder = model_root / "l2d"
    folder.mkdir()
    (folder / "model.json").write_text("{}", encoding="utf-8")  # Cubism 2
    write_png(folder / "avatar.png")
    [entry] = scan(model_root).entries
    assert entry.supported
    assert entry.status == "可用（Live2D）"
    assert entry.card_image().name == "avatar.png"


def test_live2d_manifest_options(model_root, monkeypatch):
    monkeypatch.setattr(live2d_backend, "live2d_available", lambda: True)
    good = model_root / "good"
    good.mkdir()
    (good / "m.model3.json").write_text("{}", encoding="utf-8")
    write_manifest(good, {"renderer": "live2d", "character": "amakano.mizuki",
                          "live2d": {"model": "m.model3.json", "zoom": 1.4, "offset": [0, -0.2]}})
    auto = model_root / "auto"
    auto.mkdir()
    (auto / "x.model3.json").write_text("{}", encoding="utf-8")
    write_manifest(auto, {"renderer": "live2d"})
    bad = model_root / "bad"
    bad.mkdir()
    (bad / "tex.png").write_bytes(b"x")
    write_manifest(bad, {"renderer": "live2d",
                         "live2d": {"model": "tex.png", "zoom": 0, "offset": [9]}})
    entries = {e.key: e for e in scan(model_root).entries}
    assert entries["good"].supported
    assert entries["good"].live2d_zoom == 1.4
    assert entries["good"].live2d_offset == (0.0, -0.2)
    assert entries["auto"].live2d_model.name == "x.model3.json"
    assert len(entries["bad"].errors) == 3


def test_hidden_and_deep_folders_are_skipped(model_root):
    write_png(model_root / ".hidden" / "idle.png")
    write_png(model_root / "_draft" / "idle.png")
    write_png(model_root / "a" / "b" / "c" / "d" / "idle.png")
    write_png(model_root / "a" / "b" / "c" / "idle.png")
    keys = [e.key for e in scan(model_root).entries]
    assert keys == ["a/b/c"]


def test_model_subfolders_are_not_scanned_separately(model_root):
    write_png(model_root / "m" / "idle.png")
    write_png(model_root / "m" / "extra" / "idle.png")
    assert [e.key for e in scan(model_root).entries] == ["m"]
