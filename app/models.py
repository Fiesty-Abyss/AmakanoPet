"""Discover user-supplied pet models in a local folder.

AmakanoPet never ships character art. Users put their own models into the
model root folder (see docs/MODEL_FORMAT.md). Each model is a sub-folder that
contains a ``pet.json`` manifest, an ``idle.png`` or a Live2D model json.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path

MANIFEST_NAME = "pet.json"
MANIFEST_FORMAT = 1
IMAGE_SUFFIXES = {".png", ".webp", ".jpg", ".jpeg"}
MAX_IMAGE_BYTES = 20 * 1024 * 1024
MAX_MANIFEST_BYTES = 256 * 1024
MAX_DEPTH = 3
KNOWN_RENDERERS = {"sprite", "live2d"}


def supported_renderers() -> set[str]:
    """Sprites always work; Live2D needs the optional live2d-py package."""
    from app.renderers.live2d_backend import live2d_available

    return {"sprite", "live2d"} if live2d_available() else {"sprite"}


@dataclass
class ModelEntry:
    key: str  # folder path relative to the model root, using "/" separators
    name: str
    folder: Path
    renderer: str = "sprite"
    character: str | None = None  # heroine id from the catalog, e.g. "amakano3.kanon"
    idle: Path | None = None
    blink: list[Path] = field(default_factory=list)
    avatar: Path | None = None
    live2d_model: Path | None = None
    live2d_zoom: float = 1.0
    live2d_offset: tuple[float, float] = (0.0, 0.0)
    scale: float = 1.0
    author: str = ""
    license: str = ""
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def supported(self) -> bool:
        return not self.errors and self.renderer in supported_renderers()

    @property
    def status(self) -> str:
        if self.errors:
            return "错误：" + "；".join(self.errors)
        if self.renderer not in supported_renderers():
            if self.renderer == "live2d":
                from app.renderers.live2d_backend import INSTALL_HINT

                return f"Live2D 模型暂不可用：{INSTALL_HINT}"
            return f"暂不支持的渲染器：{self.renderer}"
        return "可用（Live2D）" if self.renderer == "live2d" else "可用"

    def card_image(self) -> Path | None:
        """Image to show on heroine cards: avatar first, then the idle frame."""
        return self.avatar or self.idle


def _safe_child(folder: Path, value: object, errors: list[str], label: str,
                images_only: bool = True) -> Path | None:
    """Resolve a manifest-relative path, refusing anything outside the model folder."""
    if value in (None, ""):
        return None
    if not isinstance(value, str):
        errors.append(f"{label} 必须是字符串路径")
        return None
    candidate = Path(value)
    if candidate.is_absolute() or ".." in candidate.parts:
        errors.append(f"{label} 不能使用绝对路径或 ..：{value}")
        return None
    path = (folder / candidate).resolve()
    try:
        path.relative_to(folder.resolve())
    except ValueError:
        errors.append(f"{label} 指向模型文件夹之外：{value}")
        return None
    if not path.is_file():
        errors.append(f"{label} 文件不存在：{value}")
        return None
    if images_only:
        if path.suffix.lower() not in IMAGE_SUFFIXES:
            errors.append(f"{label} 只支持 png / webp / jpg：{value}")
            return None
        if path.stat().st_size > MAX_IMAGE_BYTES:
            errors.append(f"{label} 超过 20 MB：{value}")
            return None
    return path


def _find_live2d(folder: Path) -> Path | None:
    for pattern in ("*.model3.json", "*.model.json", "model.json"):
        matches = sorted(folder.glob(pattern))
        if matches:
            return matches[0]
    return None


def parse_model_folder(folder: Path, root: Path) -> ModelEntry | None:
    """Return a ModelEntry for ``folder`` or None when it is not a model folder."""
    key = folder.relative_to(root).as_posix() if folder != root else "."
    manifest_path = folder / MANIFEST_NAME
    if manifest_path.is_file():
        return _parse_manifest(folder, key, manifest_path)

    idle = folder / "idle.png"
    if idle.is_file():
        entry = ModelEntry(key=key, name=folder.name, folder=folder)
        errors: list[str] = []
        entry.idle = _safe_child(folder, "idle.png", errors, "idle")
        blinks = sorted(folder.glob("blink*.png"))
        entry.blink = [b for b in blinks if b.stat().st_size <= MAX_IMAGE_BYTES]
        avatar = folder / "avatar.png"
        entry.avatar = avatar if avatar.is_file() else None
        entry.errors = errors
        entry.warnings.append("未找到 pet.json，已按默认文件名自动识别")
        return entry

    live2d = _find_live2d(folder)
    if live2d is not None:
        entry = ModelEntry(key=key, name=folder.name, folder=folder, renderer="live2d",
                           live2d_model=live2d)
        avatar = folder / "avatar.png"
        entry.avatar = avatar if avatar.is_file() else None
        entry.warnings.append("未找到 pet.json，已自动识别 Live2D 模型文件")
        return entry
    return None


def _parse_manifest(folder: Path, key: str, manifest_path: Path) -> ModelEntry:
    entry = ModelEntry(key=key, name=folder.name, folder=folder)
    if manifest_path.stat().st_size > MAX_MANIFEST_BYTES:
        entry.errors.append("pet.json 过大")
        return entry
    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        entry.errors.append(f"pet.json 无法解析：{exc}")
        return entry
    if not isinstance(data, dict):
        entry.errors.append("pet.json 顶层必须是对象")
        return entry

    fmt = data.get("format", MANIFEST_FORMAT)
    if fmt != MANIFEST_FORMAT:
        entry.errors.append(f"不支持的 format：{fmt}（当前为 {MANIFEST_FORMAT}）")
        return entry

    errors = entry.errors
    name = data.get("name")
    if isinstance(name, str) and name.strip():
        entry.name = name.strip()[:60]
    character = data.get("character")
    if isinstance(character, str) and character.strip():
        entry.character = character.strip()
    for attr in ("author", "license"):
        value = data.get(attr)
        if isinstance(value, str):
            setattr(entry, attr, value.strip()[:120])
    scale = data.get("scale", 1.0)
    if isinstance(scale, (int, float)) and not isinstance(scale, bool) and 0.1 <= scale <= 5:
        entry.scale = float(scale)
    else:
        errors.append("scale 必须是 0.1 到 5 之间的数字")

    renderer = data.get("renderer", "sprite")
    if renderer not in KNOWN_RENDERERS:
        errors.append(f"未知渲染器：{renderer}")
        return entry
    entry.renderer = renderer
    entry.avatar = _safe_child(folder, data.get("avatar"), errors, "avatar")

    if renderer == "sprite":
        sprite = data.get("sprite")
        if not isinstance(sprite, dict):
            errors.append("renderer 为 sprite 时需要 sprite 对象")
            return entry
        entry.idle = _safe_child(folder, sprite.get("idle"), errors, "sprite.idle")
        if entry.idle is None and not any(e.startswith("sprite.idle") for e in errors):
            errors.append("缺少 sprite.idle")
        blink = sprite.get("blink", [])
        if isinstance(blink, str):
            blink = [blink]
        if not isinstance(blink, list):
            errors.append("sprite.blink 必须是字符串或字符串数组")
            blink = []
        for i, item in enumerate(blink[:4]):
            path = _safe_child(folder, item, errors, f"sprite.blink[{i}]")
            if path is not None:
                entry.blink.append(path)
    else:
        _parse_live2d(folder, data.get("live2d"), entry)
    return entry


def _parse_live2d(folder: Path, live2d: object, entry: ModelEntry) -> None:
    errors = entry.errors
    if live2d is None:
        live2d = {}
    if not isinstance(live2d, dict):
        errors.append("live2d 必须是对象")
        return
    model = live2d.get("model")
    if model in (None, ""):
        found = _find_live2d(folder)
        if found is None:
            errors.append("缺少 live2d.model")
            return
        entry.live2d_model = found
    else:
        entry.live2d_model = _safe_child(folder, model, errors, "live2d.model",
                                         images_only=False)
        if entry.live2d_model is not None and not entry.live2d_model.name.endswith(".json"):
            errors.append("live2d.model 应为 .model3.json 或 .model.json 文件")
            entry.live2d_model = None
    zoom = live2d.get("zoom", 1.0)
    if isinstance(zoom, (int, float)) and not isinstance(zoom, bool) and 0.1 <= zoom <= 10:
        entry.live2d_zoom = float(zoom)
    else:
        errors.append("live2d.zoom 必须是 0.1 到 10 之间的数字")
    offset = live2d.get("offset", [0, 0])
    if (isinstance(offset, list) and len(offset) == 2
            and all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in offset)
            and all(-5 <= v <= 5 for v in offset)):
        entry.live2d_offset = (float(offset[0]), float(offset[1]))
    else:
        errors.append("live2d.offset 必须是 [x, y]，取值 -5 到 5")


class ModelLibrary:
    """Scan the model root folder."""

    def __init__(self, root: Path) -> None:
        self.root = Path(root)
        self.entries: list[ModelEntry] = []

    def ensure_root(self) -> None:
        self.root.mkdir(parents=True, exist_ok=True)

    def scan(self) -> list[ModelEntry]:
        found: list[ModelEntry] = []
        if not self.root.is_dir():
            self.entries = []
            return self.entries
        root = self.root
        for current, dirs, _files in os.walk(root, followlinks=False):
            folder = Path(current)
            depth = len(folder.relative_to(root).parts)
            dirs[:] = sorted(d for d in dirs if not d.startswith((".", "_")))
            if depth == 0:
                continue
            entry = parse_model_folder(folder, root)
            if entry is not None:
                found.append(entry)
                dirs[:] = []  # a model folder's sub-folders belong to it
            elif depth >= MAX_DEPTH:
                dirs[:] = []
        self.entries = sorted(found, key=lambda e: e.key)
        return self.entries

    def get(self, key: str) -> ModelEntry | None:
        return next((e for e in self.entries if e.key == key), None)

    def for_character(self, heroine_id: str) -> list[ModelEntry]:
        return [e for e in self.entries if e.character == heroine_id]

    def avatar_for(self, heroine_id: str) -> Path | None:
        for entry in self.for_character(heroine_id):
            if not entry.errors and entry.card_image() is not None:
                return entry.card_image()
        return None
