from __future__ import annotations

import queue
import tempfile
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox

from . import config, fontmap, gameinstall, lpk, ui

FONT_EXT = (".ttf", ".otf", ".ttc")
FONT_MAGIC = (b"\x00\x01\x00\x00", b"OTTO", b"true", b"ttcf")
ROOT_LABEL = "(root)"
FONTS_DIR = "Binaries\\Fonts"
DEFAULT_LANGUAGES = [
    "English",
    "French",
    "German",
    "Spanish",
    "Russian",
    "Japanese",
    "Chinese",
    "Taiwanese",
]


class FontModdingTool:
    def __init__(self, root):
        self.root = root
        root.title("Lost Ark Font Modding Tool")
        root.geometry("900x780")
        root.minsize(760, 640)

        self.quickbms_path = tk.StringVar()
        self.source_path = tk.StringVar()
        self.output_path = tk.StringVar()
        self.profile = tk.StringVar(value=lpk.DEFAULT_PROFILE)
        self.language = tk.StringVar(value="English")
        self.font_entry = tk.StringVar()
        self.ttf_path = tk.StringVar()
        self.replace_font = tk.BooleanVar(value=True)
        self.update_fontmap = tk.BooleanVar(value=True)
        self.apply_all = tk.BooleanVar(value=True)
        self.extra_entry = tk.StringVar()
        self.extra_file = tk.StringVar()

        self.entries: list[lpk.Entry] = []
        self.language_paths: dict[
            str, str
        ] = {}  # language label -> FontMap.xml path in archive
        self.last_mod: str | None = None
        self.busy = False
        self.events: queue.Queue = queue.Queue()

        self.ui = ui.AppUI(root, self)
        self.ui.set_languages(DEFAULT_LANGUAGES)
        self.legacy_defaults(log=False)
        self._apply_settings(config.load())
        root.protocol("WM_DELETE_WINDOW", self.on_close)
        root.after(100, self._poll)

    # infrastructure
    def log(self, msg):
        self.ui.log(msg)

    def _poll(self):
        try:
            while True:
                self.events.get_nowait()()
        except queue.Empty:
            pass
        self.root.after(100, self._poll)

    def _threadsafe_log(self, msg):
        self.events.put(lambda: self.log(msg))

    def run_bg(self, work, done=None):
        if self.busy:
            return
        self.busy = True
        self.ui.set_busy(True)

        def target():
            try:
                result, err = work(), None
            except Exception as e:  # noqa: BLE001
                result, err = None, e
            self.events.put(lambda: self._finish(done, result, err))

        threading.Thread(target=target, daemon=True).start()

    def _finish(self, done, result, err):
        self.busy = False
        self.ui.set_busy(False)
        if err is not None:
            self.log(f"ERROR: {err}")
            if isinstance(err, PermissionError):
                msg = (
                    "Permission denied. Restart the tool as administrator."
                    if not gameinstall.is_admin()
                    else f"Permission denied: {err}"
                )
                messagebox.showerror("Permission error", msg)
            else:
                messagebox.showerror("Error", str(err))
            return
        if done:
            done(result)

    # validation
    def _quickbms(self) -> lpk.QuickBMS:
        exe = self.quickbms_path.get().strip()
        if not exe or not Path(exe).is_file():
            raise ValueError("Select the QuickBMS 4GB executable first.")
        return lpk.QuickBMS(exe, self.profile.get(), self._threadsafe_log)

    @staticmethod
    def _require_file(path: str, label: str) -> Path:
        p = Path(path.strip()) if path.strip() else None
        if not p or not p.is_file():
            raise ValueError(f"{label} not found: {path or '(empty)'}")
        return p

    # browsing
    def _browse_open(self, var, title, types):
        f = filedialog.askopenfilename(title=title, filetypes=types)
        if f:
            var.set(f)

    def browse_quickbms(self):
        self._browse_open(
            self.quickbms_path,
            "Select QuickBMS executable",
            [("Executable", "*.exe"), ("All", "*.*")],
        )

    def browse_source(self):
        self._browse_open(
            self.source_path,
            "Select source archive",
            [("LPK archives", "*.lpk *.bak"), ("All", "*.*")],
        )

    def browse_ttf(self):
        self._browse_open(
            self.ttf_path,
            "Select font",
            [("Fonts", "*.ttf *.otf *.ttc"), ("All", "*.*")],
        )

    def browse_extra(self):
        self._browse_open(self.extra_file, "Select replacement file", [("All", "*.*")])

    def browse_output(self):
        f = filedialog.asksaveasfilename(
            title="Save modded LPK",
            defaultextension=".lpk",
            initialfile="font.lpk",
            filetypes=[("LPK archives", "*.lpk"), ("All", "*.*")],
        )
        if f:
            self.output_path.set(f)

    def detect_game(self):
        d = gameinstall.find_game_dir()
        if not d:
            d = filedialog.askdirectory(
                title="Select Lost Ark EFGame folder (containing font.lpk)"
            )
            d = Path(d) if d else None
        if not d or not (d / "font.lpk").exists():
            self.log("Game folder not found.")
            return
        bak = d / "font.lpk.bak"
        src = bak if bak.exists() else d / "font.lpk"
        self.source_path.set(str(src))
        self.log(f"Game folder: {d}")
        self.log(
            f"Source archive set to {src.name}"
            + (" (backup of the original)" if src == bak else "")
        )

    # archive scanning
    def scan_archive(self):
        try:
            qb = self._quickbms()
            archive = self._require_file(self.source_path.get(), "Source archive")
        except ValueError as e:
            messagebox.showerror("Error", str(e))
            return
        self.ui.clear_log()
        self.log("Scanning archive...")
        self.run_bg(lambda: qb.list_entries(archive), self._scan_done)

    def _scan_done(self, entries):
        self.entries = entries
        self.log(f"Found {len(entries)} entries.")
        if lpk.is_modded(entries):
            self.log(
                "WARNING: this archive was already modded. Prefer the original (font.lpk.bak or a "
                "Steam-verified file) as source."
            )
        self.language_paths = {}
        for e in entries:
            if e.basename.lower() == "fontmap.xml":
                label = (
                    ROOT_LABEL
                    if lpk.norm(e.folder) == lpk.norm(FONTS_DIR)
                    else e.folder.rsplit("\\", 1)[-1]
                )
                self.language_paths[label] = e.name
        labels = sorted(self.language_paths) or DEFAULT_LANGUAGES
        self.ui.set_languages(labels)
        if self.language.get() not in labels:
            self.language.set("English" if "English" in labels else labels[0])
        self.ui.set_all_entries(entries)
        self.on_language_changed()

    def _fontmap_entry_name(self) -> str:
        label = self.language.get()
        if label in self.language_paths:
            return self.language_paths[label]
        if label == ROOT_LABEL:
            return FONTS_DIR + "\\FontMap.xml"
        return f"{FONTS_DIR}\\{label}\\FontMap.xml"

    def on_language_changed(self):
        folder = self._fontmap_entry_name().rsplit("\\", 1)[0]
        names = [
            e.name
            for e in self.entries
            if lpk.norm(e.folder) == lpk.norm(folder)
            and e.basename.lower().endswith(FONT_EXT)
            and not e.basename.startswith(lpk.REPLACED_PREFIX)
        ]
        self.ui.set_font_entries(names)
        if names and lpk.norm(self.font_entry.get()) not in {
            lpk.norm(n) for n in names
        }:
            pick = next((n for n in names if "exuberance" in n.lower()), names[0])
            self.font_entry.set(pick)
        if self.entries:
            self.reload_fontmap(auto=True)

    # fontmap rows
    @staticmethod
    def _item_to_row(it: fontmap.FontItem) -> dict:
        return {
            "key": it.key,
            "file": it.file,
            "size": it.size_correction,
            "leading": it.leading_correction,
            "extra": it.extra,
        }

    @staticmethod
    def _row_to_item(r: dict) -> fontmap.FontItem:
        return fontmap.FontItem(
            r["key"], r["file"], r["size"], r["leading"], dict(r.get("extra", {}))
        )

    def legacy_defaults(self, log=True):
        font = (
            Path(self.font_entry.get()).name
            if hasattr(self, "font_entry") and self.font_entry.get()
            else None
        )
        items = [
            fontmap.FontItem(
                i.key, font or i.file, i.size_correction, i.leading_correction
            )
            for i in fontmap.LEGACY_DEFAULTS
        ]
        self.ui.set_fontmap_rows([self._item_to_row(i) for i in items])
        if log:
            self.log("Loaded legacy default FontMap rows.")

    def reload_fontmap(self, auto=False):
        try:
            qb = self._quickbms()
            archive = self._require_file(self.source_path.get(), "Source archive")
        except ValueError as e:
            if not auto:
                messagebox.showerror("Error", str(e))
            return
        path = self._fontmap_entry_name()

        def work():
            with tempfile.TemporaryDirectory(prefix="loa_fm_") as td:
                try:
                    files = qb.extract(archive, "*FontMap.xml", Path(td))
                    wanted = lpk.norm(path)
                    for f in files:
                        rel = lpk.norm(str(f.relative_to(td)))
                        if rel == wanted:
                            return fontmap.parse(f.read_bytes())
                except Exception as e:  # noqa: BLE001
                    self._threadsafe_log(f"Could not read FontMap from archive: {e}")
            return None

        def done(items):
            if items is None:
                self.log(f"Could not load {path}; keeping the current rows.")
                return
            self.ui.set_fontmap_rows([self._item_to_row(i) for i in items])
            self.log(f"Loaded {len(items)} FontMap rows from {path}")

        self.run_bg(work, done)

    # extras
    def add_extra(self):
        entry, f = self.extra_entry.get().strip(), self.extra_file.get().strip()
        if not entry or not Path(f).is_file():
            messagebox.showerror(
                "Error", "Pick an archive entry and an existing local file."
            )
            return
        extras = [
            e for e in self.ui.get_extras() if lpk.norm(e["entry"]) != lpk.norm(entry)
        ]
        extras.append({"entry": entry, "file": f})
        self.ui.set_extras(extras)

    # building
    def build_modded_lpk(self):
        try:
            job = self._make_job()
        except ValueError as e:
            messagebox.showerror("Error", str(e))
            return
        qb, source, output, replacements = job
        self.ui.clear_log()
        self.log(f"Building {output.name} ({len(replacements)} replacement(s))...")

        def work():
            qb.replace(source, replacements, output)
            return output

        def done(out):
            self.last_mod = str(out)
            self.log(f"Saved: {out}")
            messagebox.showinfo("Success", f"Modded archive created:\n{out}")

        self.run_bg(work, done)

    def _make_job(self):
        qb = self._quickbms()
        source = self._require_file(self.source_path.get(), "Source archive")
        replacements: list[tuple[str, lpk.Source]] = []

        if self.replace_font.get():
            ttf = self._require_file(self.ttf_path.get(), "Font file")
            if ttf.read_bytes()[:4] not in FONT_MAGIC:
                raise ValueError(
                    f"{ttf.name} does not look like a TrueType/OpenType font."
                )
            font_entry = self.font_entry.get().strip()
            if not font_entry:
                raise ValueError(
                    "Choose which font file inside the archive to replace."
                )
        else:
            ttf, font_entry = None, ""

        if self.update_fontmap.get():
            items = [self._row_to_item(r) for r in self.ui.get_fontmap_rows()]
            if self.apply_all.get() and font_entry:
                for it in items:
                    it.file = font_entry.replace("/", "\\").rsplit("\\", 1)[-1]
            try:
                fontmap.validate(items)
            except ValueError as e:
                raise ValueError(f"FontMap: {e}")
            folder = self._fontmap_entry_name().rsplit("\\", 1)[0]
            if self.entries:
                present = {
                    e.basename.lower()
                    for e in self.entries
                    if lpk.norm(e.folder) == lpk.norm(folder)
                }
                if ttf is not None:
                    present.add(Path(font_entry).name.lower())
                for it in items:
                    if it.file.lower() not in present:
                        self.log(
                            f"WARNING: FontMap row {it.key} references '{it.file}', which is not in {folder}."
                        )
            replacements.append(
                (self._fontmap_entry_name(), fontmap.build(items).encode("utf-8"))
            )

        if ttf is not None:
            replacements.append((font_entry, ttf))

        for e in self.ui.get_extras():
            replacements.append(
                (
                    e["entry"],
                    self._require_file(e["file"], f"Replacement file for {e['entry']}"),
                )
            )

        if not replacements:
            raise ValueError(
                "Nothing to do: enable a font replacement, FontMap, or add an extra replacement."
            )
        targets = [lpk.norm(t) for t, _ in replacements]
        if len(set(targets)) != len(targets):
            raise ValueError(
                "The same archive entry is replaced more than once. Remove the duplicate."
            )

        out = self.output_path.get().strip()
        if not out:
            out = filedialog.asksaveasfilename(
                title="Save modded LPK",
                defaultextension=".lpk",
                initialfile="font.lpk",
                filetypes=[("LPK archives", "*.lpk")],
            )
            if not out:
                raise ValueError("No output file chosen.")
            self.output_path.set(out)
        output = Path(out)
        if output.resolve() == source.resolve():
            raise ValueError(
                "Output must differ from the source archive (the source is never overwritten)."
            )
        return qb, source, output, replacements

    # install / revert
    def _scan_modded(self, qb, font: Path):
        if qb is None:
            return None
        try:
            return lpk.is_modded(qb.list_entries(font))
        except Exception as e:  # noqa: BLE001
            self._threadsafe_log(f"Could not inspect {font.name}: {e}")
            return None

    def _optional_quickbms(self):
        try:
            return self._quickbms()
        except ValueError:
            return None

    def _game_dir(self):
        d = gameinstall.find_game_dir()
        if d:
            return d
        messagebox.showinfo(
            "Game folder",
            "Lost Ark 'EFGame' folder not found automatically. Please select it.",
        )
        sel = filedialog.askdirectory(
            title="Select Lost Ark EFGame folder (containing font.lpk)"
        )
        if sel and (Path(sel) / "font.lpk").exists():
            return Path(sel)
        if sel:
            messagebox.showerror("Error", "Selected folder does not contain font.lpk")
        return None

    def insert_to_game(self):
        mod = (
            Path(self.last_mod)
            if self.last_mod and Path(self.last_mod).exists()
            else None
        )
        if (
            mod is None
            and self.output_path.get().strip()
            and Path(self.output_path.get()).is_file()
        ):
            mod = Path(self.output_path.get())
        if mod is None:
            f = filedialog.askopenfilename(
                title="Select modded font.lpk to install",
                filetypes=[("LPK archives", "*.lpk"), ("All", "*.*")],
            )
            if not f:
                return
            mod = Path(f)
        game_dir = self._game_dir()
        if not game_dir:
            return
        qb = self._optional_quickbms()
        self.ui.clear_log()
        self.log(f"Installing {mod.name} into {game_dir}")

        def work():
            if qb is not None:
                entries = qb.list_entries(mod)  # sanity check: the mod must be readable
                if not lpk.is_modded(entries):
                    raise RuntimeError(
                        "The selected file has no replaced entries - it looks like an unmodified archive."
                    )
            modded = self._scan_modded(qb, game_dir / "font.lpk")
            gameinstall.install(mod, game_dir, modded, self._threadsafe_log)

        self.run_bg(
            work, lambda _: messagebox.showinfo("Success", "Modded font installed!")
        )

    def revert_to_original(self):
        game_dir = self._game_dir()
        if not game_dir:
            return
        qb = self._optional_quickbms()
        self.ui.clear_log()

        def work():
            modded = gameinstall.current_is_modded(
                game_dir, self._scan_modded(qb, game_dir / "font.lpk")
            )
            if modded is False:
                self._threadsafe_log(
                    "font.lpk is already original - nothing to revert "
                    "(a game update may have replaced the modded file)."
                )
                return False
            gameinstall.revert(game_dir, self._threadsafe_log)
            return True

        def done(reverted):
            if reverted:
                messagebox.showinfo("Success", "Reverted to the original font!")
            else:
                messagebox.showinfo(
                    "Nothing to do", "The game's font.lpk is already unmodified."
                )

        self.run_bg(work, done)

    # settings/presets
    def _snapshot(self) -> dict:
        return {
            "quickbms_path": self.quickbms_path.get(),
            "profile": self.profile.get(),
            "source": self.source_path.get(),
            "output": self.output_path.get(),
            "language": self.language.get(),
            "font_entry": self.font_entry.get(),
            "ttf": self.ttf_path.get(),
            "replace_font": self.replace_font.get(),
            "update_fontmap": self.update_fontmap.get(),
            "apply_all": self.apply_all.get(),
            "fontmap_rows": self.ui.get_fontmap_rows(),
            "extras": self.ui.get_extras(),
        }

    def _apply_settings(self, d: dict):
        for var, key in (
            (self.quickbms_path, "quickbms_path"),
            (self.source_path, "source"),
            (self.output_path, "output"),
            (self.language, "language"),
            (self.font_entry, "font_entry"),
            (self.ttf_path, "ttf"),
        ):
            if key in d:
                var.set(d[key])
        if d.get("profile") in lpk.PROFILES:
            self.profile.set(d["profile"])
        for var, key in (
            (self.replace_font, "replace_font"),
            (self.update_fontmap, "update_fontmap"),
            (self.apply_all, "apply_all"),
        ):
            if key in d:
                var.set(bool(d[key]))
        if d.get("fontmap_rows"):
            self.ui.set_fontmap_rows(d["fontmap_rows"])
        if "extras" in d:
            self.ui.set_extras(d["extras"])

    def save_preset(self):
        f = filedialog.asksaveasfilename(
            title="Save preset",
            defaultextension=".json",
            filetypes=[("Preset", "*.json")],
            initialfile="font_preset.json",
        )
        if f:
            config.save(self._snapshot(), f)
            self.log(f"Preset saved: {f}")

    def load_preset(self):
        f = filedialog.askopenfilename(
            title="Load preset", filetypes=[("Preset", "*.json")]
        )
        if f:
            data = config.load(f)
            if not data:
                messagebox.showerror("Error", "Could not read preset.")
                return
            self._apply_settings(data)
            self.log(f"Preset loaded: {f}")

    def on_close(self):
        try:
            config.save(self._snapshot())
        except Exception:
            pass
        self.root.destroy()
