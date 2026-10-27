"""Locating the game, installing the mod, backups and reverting."""

from __future__ import annotations

import contextlib
import ctypes
import hashlib
import json
import os
import re
import shutil
from collections.abc import Callable
from pathlib import Path

GAME_FOLDER = "Lost Ark"


def is_admin() -> bool:
    try:
        # pyrefly: ignore[missing-attribute]
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except (AttributeError, OSError):
        return False


def _steam_libraries() -> list[Path]:
    libs: list[Path] = []
    with contextlib.suppress(ImportError, OSError):
        import winreg

        with winreg.OpenKey(  # pyrefly: ignore[missing-attribute]
            winreg.HKEY_CURRENT_USER,  # pyrefly: ignore[missing-attribute]
            r"Software\Valve\Steam",
        ) as k:
            # pyrefly: ignore[missing-attribute]
            steam = Path(winreg.QueryValueEx(k, "SteamPath")[0])
        libs.append(steam)
        vdf = steam / "steamapps" / "libraryfolders.vdf"
        if vdf.exists():
            text = vdf.read_text(encoding="utf-8", errors="replace")
            libs += [
                Path(m.replace("\\\\", "\\"))
                for m in re.findall(r'"path"\s+"([^"]+)"', text)
            ]
    pf = os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")
    libs.append(Path(pf) / "Steam")
    return libs


def find_game_dir() -> Path | None:
    seen = set()
    for lib in _steam_libraries():
        d = lib / "steamapps" / "common" / GAME_FOLDER / "EFGame"
        if d not in seen:
            seen.add(d)
            if (d / "font.lpk").exists():
                return d
    return None


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _paths(game_dir: Path):
    return (
        game_dir / "font.lpk",
        game_dir / "font.lpk.bak",
        game_dir / "font.lpk.modinfo.json",
    )


def _recorded_hash(info: Path) -> str | None:
    try:
        return json.loads(info.read_text())["mod_sha256"]
    except (OSError, ValueError, KeyError, TypeError):
        return None


def current_is_modded(game_dir: Path, scan_result: bool | None) -> bool | None:
    """True/False if known; None if undeterminable. scan_result comes from inspecting
    the archive's entry names (lpk.is_modded)."""
    font, _, info = _paths(game_dir)
    if scan_result is not None:
        return scan_result
    rec = _recorded_hash(info)
    if rec is not None and font.exists():
        return sha256(font) == rec
    return None


def install(
    mod: Path, game_dir: Path, modded_now: bool | None, log: Callable[[str], None]
) -> None:
    font, bak, info = _paths(game_dir)
    if not font.exists():
        raise FileNotFoundError(f"{font} does not exist.")

    if modded_now:
        if not bak.exists():
            raise RuntimeError(
                "The game's font.lpk is already modded but no backup exists.\n"
                "Verify game files in Steam, then try again."
            )
        log("Game file is already modded - keeping the existing backup.")
    elif modded_now is None and bak.exists():
        log("Could not tell whether font.lpk is modded - keeping the existing backup.")
    else:
        if bak.exists():
            log(
                "Refreshing backup (game file is original, possibly updated since last time)."
            )
        shutil.copy2(font, bak)
        log("Created backup: font.lpk.bak")

    shutil.copy2(mod, font)
    info.write_text(json.dumps({"mod_sha256": sha256(font)}), encoding="utf-8")
    log("Installed modded font.lpk")


def revert(game_dir: Path, log: Callable[[str], None]) -> None:
    font, bak, info = _paths(game_dir)
    if not bak.exists():
        raise FileNotFoundError(
            "No backup found. Use 'Verify integrity of game files' in Steam instead."
        )
    shutil.copy2(bak, font)
    bak.unlink()
    info.unlink(missing_ok=True)
    log("Restored original font.lpk from backup.")
