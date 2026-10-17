from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QSettings, QStandardPaths  # noqa: E402
from PySide6.QtGui import QColor, QImage  # noqa: E402

from app.config import SettingsStore  # noqa: E402

QStandardPaths.setTestModeEnabled(True)


@pytest.fixture
def settings(tmp_path: Path) -> SettingsStore:
    store = SettingsStore(QSettings(str(tmp_path / "settings.ini"), QSettings.Format.IniFormat))
    store.model_root = tmp_path / "models"
    return store


def write_png(path: Path, color: str = "#DC6A8E", size: tuple[int, int] = (40, 60)) -> Path:
    """Generate a tiny solid-colour test image (no real artwork is used in tests)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    image = QImage(size[0], size[1], QImage.Format.Format_ARGB32)
    image.fill(QColor(color))
    assert image.save(str(path))
    return path


def write_manifest(folder: Path, data: dict) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / "pet.json"
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return path


@pytest.fixture
def model_root(tmp_path: Path) -> Path:
    root = tmp_path / "models"
    root.mkdir()
    return root
