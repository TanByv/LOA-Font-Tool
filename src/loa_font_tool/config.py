"""Tiny JSON settings store (last-used values and presets)."""

import json
import os
from pathlib import Path


def default_path() -> Path:
    base = os.environ.get("APPDATA") or str(Path.home() / ".config")
    return Path(base) / "LOAFontTool" / "settings.json"


def load(path=None) -> dict:
    try:
        return json.loads(Path(path or default_path()).read_text(encoding="utf-8"))
    except Exception:
        return {}


def save(data: dict, path=None) -> None:
    p = Path(path or default_path())
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2), encoding="utf-8")
