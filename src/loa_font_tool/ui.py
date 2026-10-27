import json
import tkinter as tk
import webbrowser
from tkinter import ttk
from typing import Any, cast

from . import lpk

VERSION = "v2.0"
GITHUB = "https://github.com/TanByv/loa-font-tool"

HELP = (
    "Size correction: 120 = x1.2 size, 80 = x0.8.   Leading correction: 200 = more line spacing, -200 = less.\n"
    "Leave a cell empty to omit that attribute.  Double-click a cell to edit it."
)


class EditableTree(ttk.Treeview):
    """Treeview whose cells can be edited by double-clicking."""

    def __init__(self, master, columns, headings, widths, display=None, height=8):
        super().__init__(
            master,
            columns=columns,
            show="headings",
            selectmode="browse",
            height=height,
            displaycolumns=display or columns,
        )
        for c, h, w in zip(columns, headings, widths):
            self.heading(c, text=h)
            self.column(c, width=w, anchor="w")
        self.bind("<Double-1>", self._edit)

    def _edit(self, event):
        if self.identify("region", event.x, event.y) != "cell":
            return
        row, col = self.identify_row(event.y), self.identify_column(event.x)
        name = self["displaycolumns"][int(col[1:]) - 1]
        x, y, w, h = self.bbox(row, col)
        ent = ttk.Entry(self)
        ent.place(x=x, y=y, width=w, height=h)
        ent.insert(0, self.set(row, name))
        ent.select_range(0, "end")
        ent.focus_set()
        done = []

        def commit(_=None):
            if not done:
                done.append(1)
                self.set(row, name, ent.get())
                ent.destroy()

        def cancel(_=None):
            if not done:
                done.append(1)
                ent.destroy()

        ent.bind("<Return>", commit)
        ent.bind("<FocusOut>", commit)
        ent.bind("<Escape>", cancel)


class AppUI:
    def __init__(self, root, ctl):
        self.root, self.ctl = root, ctl
        self._buttons = []
        self._build()

    # build
    def _btn(self, parent, text, cmd, **grid):
        b = ttk.Button(parent, text=text, command=cmd)
        if grid:
            b.grid(**grid)
        self._buttons.append(b)
        return b

    def _build(self):
        c = self.ctl
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main = ttk.Frame(self.root, padding=10)
        main.grid(sticky="nsew")
        main.columnconfigure(0, weight=1)
        main.rowconfigure(1, weight=3)
        main.rowconfigure(3, weight=1)

        # etup
        setup = ttk.LabelFrame(main, text="Setup", padding=8)
        setup.grid(row=0, column=0, sticky="we")
        setup.columnconfigure(1, weight=1)

        def path_row(r, label, var, browse):
            ttk.Label(setup, text=label).grid(
                row=r, column=0, sticky="w", padx=(0, 8), pady=2
            )
            ttk.Entry(setup, textvariable=var).grid(
                row=r, column=1, sticky="we", pady=2
            )
            self._btn(setup, "Browse", browse, row=r, column=2, padx=(6, 0))

        path_row(0, "QuickBMS (4GB exe):", c.quickbms_path, c.browse_quickbms)
        path_row(1, "Source archive (font.lpk):", c.source_path, c.browse_source)
        self._btn(
            setup, "Detect game files", c.detect_game, row=1, column=3, padx=(6, 0)
        )
        path_row(2, "Output archive:", c.output_path, c.browse_output)

        ttk.Label(setup, text="Client / key set:").grid(
            row=3, column=0, sticky="w", pady=2
        )
        prof = ttk.Combobox(
            setup,
            textvariable=c.profile,
            values=list(lpk.PROFILES),
            state="readonly",
            width=18,
        )
        prof.grid(row=3, column=1, sticky="w", pady=2)
        self._btn(
            setup,
            "Scan archive",
            c.scan_archive,
            row=3,
            column=2,
            columnspan=2,
            padx=(6, 0),
        )

        # notebook
        nb = ttk.Notebook(main)
        nb.grid(row=1, column=0, sticky="nsew", pady=8)
        self.notebook = nb

        font_tab = ttk.Frame(nb, padding=8)
        extra_tab = ttk.Frame(nb, padding=8)
        contents_tab = ttk.Frame(nb, padding=8)
        nb.add(font_tab, text="Font replacement")
        nb.add(extra_tab, text="Extra replacements")
        nb.add(contents_tab, text="Archive contents")
        self.extra_tab = extra_tab

        # font tab
        font_tab.columnconfigure(1, weight=1)
        ttk.Label(font_tab, text="Language:").grid(row=0, column=0, sticky="w", pady=2)
        row0 = ttk.Frame(font_tab)
        row0.grid(row=0, column=1, columnspan=2, sticky="we")
        row0.columnconfigure(3, weight=1)
        self.lang_box = ttk.Combobox(
            row0, textvariable=c.language, state="readonly", width=16
        )
        self.lang_box.grid(row=0, column=0)
        self.lang_box.bind("<<ComboboxSelected>>", lambda e: c.on_language_changed())
        ttk.Label(row0, text="  Font file inside archive:").grid(row=0, column=1)
        self.font_box = ttk.Combobox(row0, textvariable=c.font_entry)
        self.font_box.grid(row=0, column=3, sticky="we", padx=(6, 0))

        ttk.Label(font_tab, text="New font (TTF/OTF):").grid(
            row=1, column=0, sticky="w", pady=2
        )
        ttk.Entry(font_tab, textvariable=c.ttf_path).grid(
            row=1, column=1, sticky="we", pady=2
        )
        self._btn(font_tab, "Browse", c.browse_ttf, row=1, column=2, padx=(6, 0))

        opts = ttk.Frame(font_tab)
        opts.grid(row=2, column=0, columnspan=3, sticky="w", pady=2)
        ttk.Checkbutton(
            opts, text="Replace the font file", variable=c.replace_font
        ).grid(row=0, column=0, padx=(0, 12))
        ttk.Checkbutton(opts, text="Write FontMap.xml", variable=c.update_fontmap).grid(
            row=0, column=1, padx=(0, 12)
        )
        ttk.Checkbutton(
            opts, text="Point every row at the font file above", variable=c.apply_all
        ).grid(row=0, column=2)

        fm = ttk.LabelFrame(font_tab, text="FontMap rows", padding=6)
        fm.grid(row=3, column=0, columnspan=3, sticky="nsew", pady=(6, 0))
        font_tab.rowconfigure(3, weight=1)
        fm.columnconfigure(0, weight=1)
        fm.rowconfigure(0, weight=1)
        self.fm_tree = EditableTree(
            fm,
            ("key", "file", "size", "leading", "extra"),
            ("Key", "File", "Size correction", "Leading correction", "extra"),
            (170, 220, 110, 130, 0),
            display=("key", "file", "size", "leading"),
            height=6,
        )
        self.fm_tree.grid(row=0, column=0, sticky="nsew")
        sb = ttk.Scrollbar(fm, orient="vertical", command=self.fm_tree.yview)
        sb.grid(row=0, column=1, sticky="ns")
        self.fm_tree.configure(yscrollcommand=sb.set)
        bar = ttk.Frame(fm)
        bar.grid(row=1, column=0, columnspan=2, sticky="w", pady=(6, 0))
        self._btn(
            bar, "Reload from archive", c.reload_fontmap, row=0, column=0, padx=(0, 6)
        )
        self._btn(
            bar, "Legacy defaults", c.legacy_defaults, row=0, column=1, padx=(0, 6)
        )
        self._btn(bar, "Add row", self.add_row, row=0, column=2, padx=(0, 6))
        self._btn(bar, "Remove row", self.remove_row, row=0, column=3)
        ttk.Label(fm, text=HELP, foreground="gray40").grid(
            row=2, column=0, columnspan=2, sticky="w", pady=(6, 0)
        )

        # extra tab
        extra_tab.columnconfigure(1, weight=1)
        extra_tab.rowconfigure(2, weight=1)
        ttk.Label(
            extra_tab,
            text="Replace any other file in the archive with a local file.",
            foreground="gray40",
        ).grid(row=0, column=0, columnspan=4, sticky="w", pady=(0, 6))
        ttk.Label(extra_tab, text="Archive entry:").grid(row=1, column=0, sticky="w")
        self.extra_box = ttk.Combobox(extra_tab, textvariable=c.extra_entry)
        self.extra_box.grid(row=1, column=1, columnspan=3, sticky="we", pady=2)
        ttk.Label(extra_tab, text="Local file:").grid(
            row=2, column=0, sticky="nw", pady=2
        )
        ttk.Entry(extra_tab, textvariable=c.extra_file).grid(
            row=2, column=1, sticky="new", pady=2
        )
        self._btn(
            extra_tab, "Browse", c.browse_extra, row=2, column=2, sticky="n", padx=6
        )
        self._btn(extra_tab, "Add", c.add_extra, row=2, column=3, sticky="n")
        self.extra_tree = ttk.Treeview(
            extra_tab, columns=("entry", "file"), show="headings", height=6
        )
        self.extra_tree.heading("entry", text="Archive entry")
        self.extra_tree.heading("file", text="Local file")
        self.extra_tree.column("entry", width=320)
        self.extra_tree.column("file", width=320)
        self.extra_tree.grid(row=3, column=0, columnspan=4, sticky="nsew", pady=(6, 0))
        extra_tab.rowconfigure(3, weight=1)
        self._btn(
            extra_tab,
            "Remove selected",
            self.remove_extra,
            row=4,
            column=0,
            sticky="w",
            pady=(6, 0),
        )

        # contents tab
        contents_tab.columnconfigure(0, weight=1)
        contents_tab.rowconfigure(0, weight=1)
        self.contents = ttk.Treeview(
            contents_tab, columns=("idx", "size", "name"), show="headings"
        )
        for col, text, w in (
            ("idx", "#", 40),
            ("size", "Size", 100),
            ("name", "Path (double-click to use in Extra replacements)", 560),
        ):
            self.contents.heading(col, text=text)
            self.contents.column(col, width=w, anchor="w")
        self.contents.grid(row=0, column=0, sticky="nsew")
        sb2 = ttk.Scrollbar(
            contents_tab, orient="vertical", command=self.contents.yview
        )
        sb2.grid(row=0, column=1, sticky="ns")
        self.contents.configure(yscrollcommand=sb2.set)
        self.contents.bind("<Double-1>", self._contents_dblclick)

        # actions
        actions = ttk.Frame(main)
        actions.grid(row=2, column=0, sticky="we")
        self._btn(
            actions,
            "Create Modded LPK",
            c.build_modded_lpk,
            row=0,
            column=0,
            padx=(0, 6),
        )
        self._btn(actions, "Insert to Game", c.insert_to_game, row=0, column=1, padx=6)
        self._btn(
            actions, "Revert to Original", c.revert_to_original, row=0, column=2, padx=6
        )
        self._btn(actions, "Save preset", c.save_preset, row=0, column=3, padx=6)
        self._btn(actions, "Load preset", c.load_preset, row=0, column=4, padx=6)
        self.progress = ttk.Progressbar(actions, mode="indeterminate", length=120)
        self.progress.grid(row=0, column=5, padx=(12, 0))

        # log
        logf = ttk.Frame(main)
        logf.grid(row=3, column=0, sticky="nsew", pady=(8, 0))
        logf.columnconfigure(0, weight=1)
        logf.rowconfigure(0, weight=1)
        self.log_text = tk.Text(logf, height=8, wrap=tk.WORD)
        self.log_text.grid(row=0, column=0, sticky="nsew")
        sb3 = ttk.Scrollbar(logf, orient="vertical", command=self.log_text.yview)
        sb3.grid(row=0, column=1, sticky="ns")
        self.log_text.configure(yscrollcommand=sb3.set)

        info = ttk.Frame(main)
        info.grid(row=4, column=0, sticky="we", pady=(6, 0))
        ttk.Label(info, text=f"Version: {VERSION}").pack(side="left")
        link = ttk.Label(
            info, text="GitHub Repository", foreground="blue", cursor="hand2"
        )
        link.pack(side="right")
        link.bind("<Button-1>", lambda e: webbrowser.open_new(GITHUB))

    # helpers
    def log(self, msg):
        self.log_text.insert(tk.END, msg + "\n")
        self.log_text.see(tk.END)

    def clear_log(self):
        self.log_text.delete("1.0", tk.END)

    def set_busy(self, busy):
        for b in self._buttons:
            b.state(["disabled"] if busy else ["!disabled"])
        (self.progress.start if busy else self.progress.stop)(
            *([] if not busy else [12])
        )

    def set_languages(self, labels):
        self.lang_box["values"] = labels

    def set_font_entries(self, names):
        self.font_box["values"] = names

    def set_all_entries(self, entries):
        self.extra_box["values"] = [e.name for e in entries]
        self.contents.delete(*self.contents.get_children())
        for e in entries:
            self.contents.insert("", "end", values=(e.index, f"{e.size:,}", e.name))

    def _contents_dblclick(self, event):
        row = self.contents.identify_row(event.y)
        if row:
            values = cast(tuple[Any, ...], self.contents.item(row, "values"))
            self.ctl.extra_entry.set(values[2])
            self.notebook.select(self.extra_tab)

    # fontmap table
    def set_fontmap_rows(self, rows):
        self.fm_tree.delete(*self.fm_tree.get_children())
        for r in rows:
            self.fm_tree.insert(
                "",
                "end",
                values=(
                    r["key"],
                    r["file"],
                    r["size"],
                    r["leading"],
                    json.dumps(r.get("extra", {})),
                ),
            )

    def get_fontmap_rows(self):
        rows = []
        for iid in self.fm_tree.get_children():
            key, file, size, leading, extra_raw = self.fm_tree.item(iid, "values")
            try:
                extra = json.loads(extra_raw) if extra_raw else {}
            except ValueError:
                extra = {}
            rows.append(
                {
                    "key": str(key),
                    "file": str(file),
                    "size": str(size),
                    "leading": str(leading),
                    "extra": extra,
                }
            )
        return rows

    def add_row(self):
        iid = self.fm_tree.insert("", "end", values=("$NewKey", "", "", "", "{}"))
        self.fm_tree.selection_set(iid)

    def remove_row(self):
        for iid in self.fm_tree.selection():
            self.fm_tree.delete(iid)

    # extras table
    def set_extras(self, extras):
        self.extra_tree.delete(*self.extra_tree.get_children())
        for e in extras:
            self.extra_tree.insert("", "end", values=(e["entry"], e["file"]))

    def get_extras(self):
        return [
            {"entry": str(v[0]), "file": str(v[1])}
            for v in (
                cast(tuple[Any, ...], self.extra_tree.item(i, "values"))
                for i in self.extra_tree.get_children()
            )
        ]

    def remove_extra(self):
        for iid in self.extra_tree.selection():
            self.extra_tree.delete(iid)
