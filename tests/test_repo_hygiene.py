"""Guard rails: model files and game assets must never be committed."""

import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN_SUFFIXES = (
    ".moc", ".moc3", ".model.json", ".model3.json", ".physics3.json", ".exp3.json",
    ".motion3.json", ".mtn", ".cdi3.json", ".pose3.json", ".vtube.json", ".psb",
    ".zip", ".7z", ".rar", ".ogg", ".wav", ".mp3",
)


def tracked_files() -> list[str]:
    if shutil.which("git") is None or not (ROOT / ".git").exists():
        pytest.skip("not a git checkout")
    out = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True,
                         check=True)
    return out.stdout.splitlines()


def test_no_model_or_asset_files_are_tracked():
    bad = [f for f in tracked_files() if f.lower().endswith(FORBIDDEN_SUFFIXES)
           or f.split("/")[0] in {"private-models", "models", "user-models"}]
    assert bad == []


def test_images_only_live_in_docs_screenshots():
    images = [f for f in tracked_files() if f.lower().endswith((".png", ".jpg", ".jpeg", ".webp"))]
    assert all(f.startswith("docs/screenshots/") for f in images), images
