"""ModDiver Laboratory - desktop mod toolkit for Helldivers 2 data mods.

Deploy / purge / merge data mods and export a YAO DATA LOADER pack.
"""
import ctypes
import os
import queue
import subprocess
import sys
import threading
import time
import tkinter as tk
from tkinter import colorchooser, filedialog, messagebox, simpledialog, ttk
from pathlib import Path

import core
import actions
import editor_names
import editor_weapons
import editor_fields

try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass
try:
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("YAO.ModForge.1")
except Exception:
    pass

APP_NAME = "ModDiver Laboratory"
VERSION = "1.8.3"

THEMES = {
    "Helldiver": {"bg": "#080808", "panel": "#141414", "panel2": "#222222", "accent": "#ffd400",
                  "accent_text": "#080808", "text": "#ffffff", "muted": "#c4c4c4"},
    "Midnight": {"bg": "#0b1020", "panel": "#121a2e", "panel2": "#1a2440", "accent": "#4f8cff",
                 "accent_text": "#0b1020", "text": "#e6ecff", "muted": "#8a93b0"},
    "Light": {"bg": "#eef0f3", "panel": "#ffffff", "panel2": "#e2e6ec", "accent": "#c8102e",
              "accent_text": "#ffffff", "text": "#1b1b1b", "muted": "#5f6672"},
    "High Contrast": {"bg": "#000000", "panel": "#0a0a0a", "panel2": "#161616", "accent": "#ffd400",
                      "accent_text": "#000000", "text": "#ffffff", "muted": "#a0a0a0"},
    "Ember": {"bg": "#140d0a", "panel": "#1e1310", "panel2": "#2a1a15", "accent": "#ff6b35",
              "accent_text": "#140d0a", "text": "#f2e6dd", "muted": "#a08a7c"},
}
SWATCHES = ["#f4c542", "#ff6b35", "#ff4d4d", "#4f8cff", "#38d996", "#b06bff", "#ffffff", "#c8102e"]

ABOUT_BLOCKS = [
    ("MODDIVER LABORATORY", "h1"),
    (f"Version {VERSION}   /   HELLDIVERS 2 DATA MOD TOOLKIT\n", "sub"),
    ("Build and manage data-file mods with one focused desktop toolkit. The app works offline and "
     "writes game data files; it does not inject code into the running game or bypass anti-cheat.\n", "body"),

    ("THE ENGINE\n", "h2"),
    ("Data engine: HD2 data files are sealed LDLD blocks. The app opens them, merges byte ranges in mod priority "
     "order, corrects the content hash in the reserved header bytes, re-seals with libsodium and verifies the "
     "result before writing. Stock snapshots and backups make every deploy reversible.\n", "body"),
    ("Editor engine: the native Editor and the bundled SHODAN editor both run on that data engine. The Editor "
     "bridge loads Lua 5.1 modules headlessly through the vendored LuaJIT (gamedata.lua) to read and write "
     "weapon, armour-passive and damage tables.\n", "body"),
    ("Loader engine: boot-script loaders are packaged, not reimplemented. The app bundles Chef Shared Loader and "
     "Boot Mod Loader, deploys one at a time, and refuses to let two boot replacements coexist.\n", "body"),

    ("GET STARTED\n", "h2"),
    ("1.  Import mods from the Mods tab with Add ZIP or Add Folder. Use Switch Category when a mod needs to move "
     "between gameplay and visual/audio groups. Higher entries win when mods change the same value.\n", "num"),
    ("2.  Install All in Deploy merges enabled mods against the Stock snapshot and backs up game files before writing.\n", "num"),
    ("3.  Use Purge (restore) to return files changed by ModDiver Laboratory to their backed-up state.\n", "num"),

    ("SHODAN EDITOR WORKFLOW\n", "h2"),
    ("Use SHODAN Stat Editor Offline v4.1.0 for stats and armour passives, or Combined Community Mods v2.0.13 "
     "for the combined SHODAN, Armory Forge, Vanilla+ and Hellpod tools. Press Install in the editor to write changes.\n", "body"),
    ("To make those edits a reusable library mod, first purge any active ModDiver Laboratory deployment and confirm a clean Stock snapshot exists. "
     "Then choose Capture Game as Mod. Capture creates a Mods entry, a portable data/game ZIP, and an Arsenal data pack that bundles the YAO loader. "
     "Arsenal, HD2 Mod Manager and DDMM can deploy the data pack as patch files; launch, exit normally, then launch again.\n", "body"),

    ("MOD CREATOR & RECOVERY\n", "h2"),
    ("NoMoFOMO is a built-in unlock payload included by Install All when enabled in Mod Creator. Capture Stock records the clean baseline "
     "used for comparisons. After a game update, purge, verify files through Steam, launch once, then capture a fresh Stock snapshot.\n", "body"),
    ("Export Mod saves deployed files as a ZIP that can be imported back into the library. Verify Steam Files asks Steam to restore "
     "the game and may also remove changes made by other tools. Import Edit Presets copies SHODAN .txt presets into its persistent preset folder.\n", "body"),

    ("SUPPORTED CONTENT\n", "h2"),
    ("Data mods - merged and deployed by the app, no loader needed: plain .dl_bin files, YAO/QET-signed .stream "
     "descriptors (e.g. DP100), Arsenal .patch_0/.patch_N containers, manifests and options, generic data trees.\n", "body"),
    ("Lua mods - need a boot-script loader: Chef Shared Loader runs Lua 5.1 mods side by side with a crash guard, "
     "sandbox and F9 menu; Boot Mod Loader starts \"-- HD2-Addon:\" mods on the game's own boot script. Deploy only "
     "one loader at a time.\n", "body"),
    ("Runtime scripts and injectors can be listed in the library, but are not deployed by the app itself. The YAO "
     "Data Loader is not needed: the app already merges and deploys YAO/QET-signed data packs natively.\n", "body"),

    ("RUNTIME MODS & LOADERS\n", "h2"),
    ("Chef Shared Loader is the primary runtime path: import Chef-compatible Lua mods as usual, add Chef from Mod Creator, and "
     "deploy. Lua files deploy under mod/, which is where Chef looks; Chef runs each mod in its own space with a crash "
     "guard, sandbox and F9 menu.\n", "body"),
    ("Chef and Boot Mod Loader both replace the game's boot script, so only one can be active: the app refuses to deploy "
     "both and orders Chef last so it owns boot. Boot is for simple \"-- HD2-Addon:\" mods or as a fallback only.\n", "body"),
    ("Dependencies and order: data mods merge independently of loaders; a Lua mod depends on its loader being present. "
     "Library order sets merge priority (top wins), and the loader is always deployed last.\n", "body"),

    ("LIMITS\n", "h2"),
    ("Supported runtime mods are Chef-compatible Lua packages. Native injectors (DLL/ASI/EXE) are detected, listed and "
     "reported as unsupported, never deployed. Chef has its own per-mod compatibility limits; some Lua mods still fail "
     "inside Chef.\n", "body"),
    ("EAC matters: runtime loaders change game behaviour and may not survive protected sessions. If a launch fails, "
     "remove mod files and verify the game. The app never bypasses anti-cheat and only writes data files; runtime "
     "behaviour belongs to the game and the loader.\n", "body"),
    ("Editor output folders are available from buttons in Mod Creator: captured mods, SHODAN presets, and Armory Forge presets.\n", "body"),

    ("PROJECT & CREDITS\n", "h2"),
    ("Free, open-source, and community-built. No account or telemetry is required.\n", "body"),
    ("SHODAN", "name"), ("    Stat Editor\n", "tool"),
    ("Chef chfb", "name"), ("    Chef Shared Loader\n", "tool"),
    ("VeganSquid", "name"), ("    Boot Mod Loader\n", "tool"),
    ("Medic 3048", "name"), ("    File Mod Merger\n", "tool"),
    ("Cowboy Bingus", "name"), ("    Bingus Shared Loader and Vanilla+ Megapack\n", "tool"),
    ("huffdesigns", "name"), ("    NoMoFOMO\n", "tool"),
    ("\n", "body"),
    ("Yao", "name"), ("    ModDiver Laboratory and Merge Engine\n", "tool"),
    ("\nThanks to the Helldivers 2 modding community for sharing tools and work openly.\n", "body"),
]


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.cfg = core.load_config()
        core.clean_builtins(self.cfg)
        self.theme = dict(self.cfg.get("theme") or core.DEFAULT_THEME)
        legacy_helldiver = (
            {"bg": "#0d0f0c", "panel": "#151a12", "panel2": "#1c2318", "accent": "#f4c542",
             "accent_text": "#151a12", "text": "#e8e6d9", "muted": "#8a8f7a"},
            {"bg": "#11140f", "panel": "#1a2018", "panel2": "#252d21", "accent": "#d6b84b",
             "accent_text": "#171a12", "text": "#ecebdc", "muted": "#a2a58f"},
        )
        if self.theme.get("preset") == "Helldiver" and any(
                all(self.theme.get(k) == v for k, v in old.items()) for old in legacy_helldiver):
            font_size = self.theme.get("font", core.DEFAULT_THEME["font"])
            self.theme = {**core.DEFAULT_THEME, "font": font_size}
            self.cfg["theme"] = dict(self.theme)
        self.title(APP_NAME)
        dpi = self.winfo_fpixels("1i")
        self.tk.call("tk", "scaling", max(1.0, dpi / 72.0))
        scale = max(1.0, dpi / 96.0)
        self.geometry(f"{int(1180 * scale)}x{int(760 * scale)}")
        self.minsize(int(980 * scale), int(640 * scale))
        self.configure(bg=self.theme["bg"])
        try:
            icon = Path(__file__).resolve().parent / "icon_yellow.png"
            if icon.exists():
                self._icon = tk.PhotoImage(file=str(icon))
                self.iconphoto(True, self._icon)
        except Exception:
            pass
        self.style = ttk.Style(self)
        self.style.theme_use("clam")
        self.log_queue = queue.Queue()
        self.texts = []
        self.nav_buttons = {}
        self.current = "mods"
        self.busy = False
        self.editor_proc = None
        self._build()
        self.apply_theme()
        self.refresh_mods()
        self.refresh_status()
        self.after(100, self._drain)
        self.after(200, self._dark_titlebar)
        self.after(800, self._ensure_shortcut)
        self.protocol("WM_DELETE_WINDOW", self._close)

    # ---------------------------------------------------------------- layout
    def _build(self):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self._sidebar()
        main = ttk.Frame(self, style="TFrame")
        main.grid(row=0, column=1, sticky="nsew")
        main.grid_columnconfigure(0, weight=1)
        main.grid_rowconfigure(1, weight=1)
        self._header(main)
        self.content = ttk.Frame(main, style="TFrame")
        self.content.grid(row=1, column=0, sticky="nsew", padx=18, pady=(0, 10))
        self.content.grid_columnconfigure(0, weight=1)
        self.content.grid_rowconfigure(0, weight=1)
        self.pages = {}
        for name, builder in (("mods", self._page_mods), ("deploy", self._page_deploy),
                              ("editor", self._page_editor), ("tools", self._page_tools),
                              ("themes", self._page_themes),
                              ("log", self._page_log), ("about", self._page_about)):
            page = builder(self.content)
            page.grid(row=0, column=0, sticky="nsew")
            self.pages[name] = page
        self.status = ttk.Label(main, text="ready", style="Muted.TLabel", anchor="w")
        self.status.grid(row=2, column=0, sticky="ew", padx=18, pady=(0, 8))
        self._show("mods")

    def _sidebar(self):
        self.sidebar = tk.Frame(self, width=212, bd=0, highlightthickness=0)
        self.sidebar.grid(row=0, column=0, sticky="ns")
        self.sidebar.grid_propagate(False)
        self.brand = tk.Frame(self.sidebar, bd=0, highlightthickness=0)
        self.brand.pack(fill="x", padx=20, pady=(24, 0))
        tk.Label(self.brand, text="MODDIVER", font=("Segoe UI Semibold", 19), anchor="w").pack(side="left")
        tk.Label(self.sidebar, text="LABORATORY", font=("Segoe UI", 10), anchor="w", fg="#9a9a9a").pack(fill="x", padx=20, pady=(0, 2))
        self.brand_sub = tk.Label(self.sidebar, text=f"v{VERSION}", font=("Segoe UI", 9), anchor="w")
        self.brand_sub.pack(fill="x", padx=20, pady=(2, 22))
        for name, label in (("mods", "MODS"), ("deploy", "DEPLOY"), ("editor", "EDITOR*"), ("tools", "MOD CREATOR"),
                            ("themes", "THEMES"), ("log", "LOG"), ("about", "ABOUT")):
            b = tk.Button(self.sidebar, text=label, anchor="w", bd=0, relief="flat",
                          font=("Segoe UI Semibold", 11), padx=20, pady=10, cursor="hand2",
                          command=lambda n=name: self._show(n))
            b.pack(fill="x")
            self.nav_buttons[name] = b
        self.sidebar_footer = tk.Label(self.sidebar, text="data mods only\nno runtime hooks",
                                       font=("Segoe UI", 8), anchor="w", justify="left")
        self.sidebar_footer.pack(side="bottom", fill="x", padx=20, pady=14)
        self.start_btn = tk.Button(self.sidebar, text="\u25b6  START GAME", bd=0, relief="flat",
                                   font=("Segoe UI Semibold", 11), pady=10, cursor="hand2",
                                   command=self.launch_game)
        self.start_btn.pack(side="bottom", fill="x", padx=14, pady=(0, 10))

    def _header(self, parent):
        head = ttk.Frame(parent, style="TFrame")
        head.grid(row=0, column=0, sticky="ew", padx=18, pady=(16, 8))
        head.grid_columnconfigure(0, weight=1)
        self.title_label = ttk.Label(head, text="Mod Library", style="Title.TLabel")
        self.title_label.grid(row=0, column=0, sticky="w")
        self.subtitle_label = ttk.Label(head, text="Add data mods, merge and deploy them with one click.",
                                        style="Muted.TLabel")
        self.subtitle_label.grid(row=1, column=0, sticky="w")
        self.chip = ttk.Label(head, text="STOCK: ?", style="Chip.TLabel")
        self.chip.grid(row=0, column=1, rowspan=2, sticky="e")

    def _show(self, name):
        self.current = name
        self.pages[name].tkraise()
        titles = {"mods": ("Mod Library", "Add data mods, merge and deploy them with one click."),
                  "deploy": ("Deploy & Purge", "Write the merged pack to the game, or restore stock."),
                  "editor": ("Editor", "Edit SHODAN stats and capture changes into your mod library."),
                  "tools": ("Mod Creator", "Loaders, editors and unlocks for your mod setup."),
                  "themes": ("Themes", "Change the look of the Laboratory. Presets or your own colors."),
                  "log": ("Log", "Everything the Laboratory did this session."),
                  "about": ("About", "ModDiver Laboratory.")}
        t, s = titles[name]
        self.title_label.configure(text=t)
        self.subtitle_label.configure(text=s)
        for n, b in self.nav_buttons.items():
            b.configure(bg=self.theme["panel2"] if n == name else self.theme["panel"],
                        fg=self.theme["accent"] if n == name else self.theme["muted"])
        if name == "editor":
            self.title_label.grid_remove()
            self.subtitle_label.grid_remove()
        else:
            self.title_label.grid()
            self.subtitle_label.grid()

    # ---------------------------------------------------------------- theme
    def apply_theme(self):
        t = self.theme
        s = self.style
        f = int(t.get("font", 10))
        body = ("Segoe UI", f)
        small = ("Segoe UI", max(8, f - 1))
        s.configure("TFrame", background=t["bg"])
        s.configure("Panel.TFrame", background=t["panel"])
        s.configure("TLabel", background=t["bg"], foreground=t["text"], font=body)
        s.configure("Muted.TLabel", background=t["bg"], foreground=t["muted"], font=small)
        s.configure("Panel.TLabel", background=t["panel"], foreground=t["text"], font=body)
        s.configure("PanelMuted.TLabel", background=t["panel"], foreground=t["muted"], font=small)
        s.configure("Title.TLabel", background=t["bg"], foreground=t["accent"], font=("Segoe UI Semibold", f + 8))
        s.configure("Chip.TLabel", background=t["panel2"], foreground=t["accent"], font=("Segoe UI Semibold", f - 1),
                    padding=(10, 4))
        s.configure("TButton", background=t["panel2"], foreground=t["text"], font=body, padding=(10, 6),
                    borderwidth=0, focusthickness=0)
        s.map("TButton", background=[("active", t["accent"]), ("pressed", t["accent"])],
              foreground=[("active", t["accent_text"]), ("pressed", t["accent_text"])])
        s.configure("Accent.TButton", background=t["accent"], foreground=t["accent_text"],
                    font=("Segoe UI Semibold", f))
        s.map("Accent.TButton", background=[("pressed", t["accent"]), ("active", t["panel2"])],
              foreground=[("pressed", t["accent_text"]), ("active", t["accent"])])
        s.configure("Danger.TButton", background=t["bad"], foreground="#ffffff")
        s.map("Danger.TButton", background=[("pressed", "#ad2521"), ("active", "#f04b45")],
              foreground=[("active", "#ffffff"), ("pressed", "#ffffff")])
        s.configure("Treeview", background=t["panel"], fieldbackground=t["panel"], foreground=t["text"],
                    font=body, rowheight=max(24, f * 2 + 6), borderwidth=0)
        s.configure("Treeview.Heading", background=t["panel2"], foreground=t["muted"],
                    font=("Segoe UI Semibold", f - 1), relief="flat", padding=(8, 6))
        s.map("Treeview", background=[("selected", t["accent"])], foreground=[("selected", t["accent_text"])])
        s.map("Treeview.Heading", background=[("active", t["panel2"])])
        s.configure("TNotebook", background=t["bg"], borderwidth=0, tabmargins=(0, 0, 4, 0))
        s.configure("TNotebook.Tab", background=t["panel"], foreground=t["muted"], padding=(14, 6),
                    font=("Segoe UI Semibold", f - 1), borderwidth=0)
        s.map("TNotebook.Tab", background=[("selected", t["panel2"]), ("active", t["panel2"])],
              foreground=[("selected", t["accent"]), ("active", t["text"])])
        s.configure("TEntry", fieldbackground=t["panel"], foreground=t["text"], insertcolor=t["text"],
                    bordercolor=t["panel2"], lightcolor=t["panel2"], darkcolor=t["panel2"])
        s.configure("TCheckbutton", background=t["bg"], foreground=t["text"], font=body)
        s.map("TCheckbutton", background=[("active", t["bg"])], foreground=[("active", t["accent"])])
        s.configure("TCombobox", fieldbackground=t["panel"], background=t["panel2"], foreground=t["text"])
        s.configure("Horizontal.TScale", background=t["bg"], troughcolor=t["panel2"])
        self.configure(bg=t["bg"])
        self.sidebar.configure(bg=t["panel"])
        if hasattr(self, "editor_host"):
            self.editor_host.configure(bg=t["bg"])
        for parent in (self.sidebar, getattr(self, "brand", None)):
            if parent is None:
                continue
            for w in parent.winfo_children():
                if isinstance(w, tk.Label):
                    w.configure(bg=t["panel"], fg=t["muted"])
        for w in self.brand.winfo_children():
            if isinstance(w, tk.Label):
                w.configure(fg=t["accent"] if w.cget("text") == "MODDIVER" else t["text"])
        self.sidebar_footer.configure(bg=t["panel"], fg=t["muted"])
        for name, b in self.nav_buttons.items():
            b.configure(bg=t["panel2"] if name == self.current else t["panel"],
                        fg=t["accent"] if name == self.current else t["muted"],
                        activebackground=t["panel2"], activeforeground=t["accent"])
        self.start_btn.configure(bg=t["accent"], fg=t["accent_text"],
                                 activebackground=t["accent"], activeforeground=t["accent_text"])
        for w in self.texts:
            try:
                w.configure(bg=t["panel"], fg=t["text"], insertbackground=t["text"],
                            selectbackground=t["accent"], selectforeground=t["accent_text"])
            except tk.TclError:
                pass
        about = getattr(self, "about_text", None)
        if about is not None:
            try:
                about.tag_configure("h1", foreground=t["text"])
                about.tag_configure("sub", foreground=t["muted"])
                about.tag_configure("h2", foreground=t["accent"])
                about.tag_configure("body", foreground=t["text"])
                about.tag_configure("name", foreground=t["text"])
                about.tag_configure("tool", foreground=t["muted"])
                about.tag_configure("num", foreground=t["text"])
                about.tag_configure("bullet", foreground=t["text"])
            except tk.TclError:
                pass
        if hasattr(self, "font_scale"):
            self.font_scale.configure(bg=t["bg"], fg=t["text"], troughcolor=t["panel2"],
                                      highlightthickness=0, bd=0, activebackground=t["panel2"])
        try:
            self.tree.tag_configure("cat", font=("Segoe UI Semibold", f))
        except tk.TclError:
            pass
        try:
            self._dark_titlebar()
        except Exception:
            pass
        self.cfg["theme"] = dict(self.theme)
        core.save_config(self.cfg)

    def _set_theme(self, **kw):
        self.theme.update(kw)
        self.apply_theme()

    def _bgr(self, color):
        h = color.lstrip("#")
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        return (b << 16) | (g << 8) | r

    def _dark_titlebar(self):
        try:
            hwnd = int(self.wm_frame(), 16)
            if not hwnd:
                return
            dwm = ctypes.windll.dwmapi
            one = ctypes.c_int(1)
            dwm.DwmSetWindowAttribute(hwnd, 20, ctypes.byref(one), 4)
            for attr, color in ((35, self.theme["panel"]), (34, self.theme["bg"]),
                                (36, self.theme["text"])):
                c = ctypes.c_int(self._bgr(color))
                dwm.DwmSetWindowAttribute(hwnd, attr, ctypes.byref(c), 4)
        except Exception:
            pass

    # ---------------------------------------------------------------- mods page
    def _page_mods(self, parent):
        page = ttk.Frame(parent, style="TFrame")
        page.grid_columnconfigure(0, weight=1)
        page.grid_rowconfigure(2, weight=1)
        bar = ttk.Frame(page, style="TFrame")
        bar.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        for label, cmd in (("+ Add ZIP", self.add_zip), ("+ Add Folder", self.add_folder),
                           ("Remove", self.remove_mod), ("Enable / Disable", self.toggle_mod),
                           ("Up", lambda: self.move_mod(-1)), ("Down", lambda: self.move_mod(1)),
                           ("Options", self.configure_mod), ("Switch Category", self.toggle_category),
                           ("Purge (restore)", self.do_purge)):
            style = "Danger.TButton" if label.startswith("Purge") else "TButton"
            ttk.Button(bar, text=label, style=style, command=cmd).pack(side="left", padx=(0, 6))
        self.mod_count = ttk.Label(bar, text="0 mods", style="Muted.TLabel")
        self.mod_count.pack(side="right")
        ttk.Label(
            page,
            text=("You can put mods into either the gameplay or visual/audio category. "
                  "It is only for your organization and has no effect on how the mods deploy. "
                  "Gameplay mods deploy first, then visual/audio, in top-to-bottom order."),
            style="Muted.TLabel", wraplength=760, justify="left").grid(
            row=1, column=0, sticky="w", pady=(0, 10))
        wrap = ttk.Frame(page, style="Panel.TFrame")
        wrap.grid(row=2, column=0, sticky="nsew")
        wrap.grid_columnconfigure(0, weight=1)
        wrap.grid_rowconfigure(0, weight=1)
        self.tree = ttk.Treeview(wrap, columns=("name", "type", "targets", "on"),
                                 show="tree headings", selectmode="browse")
        self.tree.heading("#0", text="CATEGORY")
        self.tree.column("#0", width=150, anchor="w")
        for col, text, width in (("name", "MOD", 360), ("type", "TYPE", 100), ("targets", "TARGETS", 80),
                                 ("on", "ON", 50)):
            self.tree.heading(col, text=text)
            self.tree.column(col, width=width, anchor="w" if col == "name" else "center")
        self.tree.grid(row=0, column=0, sticky="nsew")
        sb = ttk.Scrollbar(wrap, orient="vertical", command=self.tree.yview)
        sb.grid(row=0, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.bind("<<TreeviewSelect>>", self._mod_selected)
        self.mod_detail = ttk.Label(page, text="Priority: the top mod wins where two change the same value.",
                                    style="Muted.TLabel")
        self.mod_detail.grid(row=3, column=0, sticky="w", pady=(8, 0))
        return page

    def _mod_selected(self, _event=None):
        sel = self.tree.selection()
        if not sel:
            return
        if sel[0].startswith("cat:"):
            self.mod_detail.configure(text="Group: " + sel[0].split(":", 1)[1])
            return
        m = self.cfg["mods"][int(sel[0])]
        targets = ", ".join(m.get("targets", [])) or "no data targets"
        opts = ", ".join(m.get("options") or []) or "none"
        self.mod_detail.configure(text=f"{m['name']}  |  {m['type']}  |  {targets}  |  options: {opts}")

    def _add_paths(self, paths):
        if self.busy:
            return
        self.busy = True
        self.log(f"reading {len(paths)} mod(s)...")

        def work():
            for p in paths:
                try:
                    m = core.parse_mod(p)
                except Exception as exc:
                    self.log(f"  {p}: {exc}")
                    continue
                opts = [o["name"] for o in m.get("options", [])]
                defaults = {o["name"]: bool(o.get("default", True)) for o in m.get("options", [])}
                self.cfg["mods"].append({"path": m["path"], "name": m["name"], "type": m["type"],
                                         "targets": m["targets"], "options": opts,
                                         "selected": defaults, "enabled": True,
                                         "runtime": bool(m.get("runtime"))})
                self.log(f"  added {m['name']} ({m['type']}, {len(m['targets'])} targets)"
                         + ("  [runtime - needs a loader, will be skipped]" if m.get("runtime") else ""))
            core.save_config(self.cfg)
            self.after(0, self._added)

        threading.Thread(target=work, daemon=True).start()

    def _added(self):
        self.busy = False
        self.refresh_mods()
        self.refresh_status()

    def add_zip(self):
        paths = filedialog.askopenfilenames(title="Add data mods", filetypes=[("Mods", "*.zip")])
        if paths:
            self._add_paths(paths)

    def add_folder(self):
        path = filedialog.askdirectory(title="Add a mod folder")
        if path:
            self._add_paths([path])

    def _selected_index(self):
        sel = self.tree.selection()
        if not sel or sel[0].startswith("cat:"):
            return None
        return int(sel[0])

    def remove_mod(self):
        i = self._selected_index()
        if i is None:
            return
        actions.remove_mod(self.cfg, i, self.log)
        self.refresh_mods()

    def toggle_mod(self):
        i = self._selected_index()
        if i is None:
            return
        actions.toggle_mod(self.cfg, i)
        self.refresh_mods()

    def move_mod(self, delta):
        i = self._selected_index()
        if i is None:
            return
        j = actions.move_mod(self.cfg, i, delta)
        self.refresh_mods()
        self.tree.selection_set(str(j))

    def configure_mod(self):
        i = self._selected_index()
        if i is None:
            return
        m = self.cfg["mods"][i]
        opts = m.get("options") or []
        if not opts:
            self.log("this mod has no options")
            return
        win = tk.Toplevel(self)
        win.title("Options - " + m["name"])
        win.configure(bg=self.theme["bg"])
        win.geometry("420x" + str(120 + 28 * len(opts)))
        win.transient(self)
        win.grab_set()
        ttk.Label(win, text="Enable the parts of this mod to deploy:",
                  style="TLabel").pack(anchor="w", padx=16, pady=(14, 6))
        vars_ = {}
        for o in opts:
            var = tk.BooleanVar(value=(m.get("selected") or {}).get(o, True))
            vars_[o] = var
            ttk.Checkbutton(win, text=o, variable=var).pack(anchor="w", padx=20, pady=3)

        def save():
            m["selected"] = {o: bool(v.get()) for o, v in vars_.items()}
            core.save_config(self.cfg)
            self.log("options saved for " + m["name"])
            win.destroy()

        ttk.Button(win, text="Save", style="Accent.TButton", command=save).pack(pady=14)

    def toggle_category(self):
        i = self._selected_index()
        if i is None:
            return
        m = self.cfg["mods"][i]
        cur = m.get("category") or core.mod_category(m.get("targets", []))
        m["category"] = "visual" if cur == "gameplay" else "gameplay"
        core.save_config(self.cfg)
        self.refresh_mods()
        self.log(f"{m['name']} -> {m['category']}")

    def refresh_mods(self):
        if not hasattr(self, "tree"):
            return
        self.tree.delete(*self.tree.get_children())
        groups = {"gameplay": [], "visual": []}
        for i, m in enumerate(self.cfg["mods"]):
            cat = m.get("category") or core.mod_category(m.get("targets", []))
            groups["visual" if cat == "visual" else "gameplay"].append((i, m))
        for key, label in (("gameplay", "GAMEPLAY"), ("visual", "VISUAL & AUDIO")):
            parent = self.tree.insert("", "end", iid=f"cat:{key}",
                                      text=f"{label}  ({len(groups[key])})", open=True,
                                      values=("", "", "", ""), tags=("cat",))
            for i, m in groups[key]:
                self.tree.insert(parent, "end", iid=str(i), text="",
                                 values=(m["name"] + ("   [runtime]" if m.get("runtime") else ""),
                                         m["type"], len(m.get("targets", [])),
                                         "yes" if m.get("enabled", True) else "no"))
        self.mod_count.configure(text=f"{len(self.cfg['mods'])} mods")

    # ---------------------------------------------------------------- deploy page
    def _page_deploy(self, parent):
        page = ttk.Frame(parent, style="TFrame")
        page.grid_columnconfigure(0, weight=1)
        row = ttk.Frame(page, style="TFrame")
        row.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        ttk.Label(row, text="Game folder").pack(side="left")
        self.game_var = tk.StringVar(value=self.cfg["game"])
        entry = ttk.Entry(row, textvariable=self.game_var, width=70)
        entry.pack(side="left", padx=8, fill="x", expand=True)
        entry.bind("<FocusOut>", lambda e: self._save_game())
        ttk.Button(row, text="Browse", command=self._browse_game).pack(side="left")
        stat = ttk.Frame(page, style="TFrame")
        stat.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        self.stock_label = ttk.Label(stat, text="Stock: not captured", style="Muted.TLabel")
        self.stock_label.pack(side="left")
        self.deployed_label = ttk.Label(stat, text="   Deployed: 0", style="Muted.TLabel")
        self.deployed_label.pack(side="left")
        bar = ttk.Frame(page, style="TFrame")
        bar.grid(row=2, column=0, sticky="ew", pady=(0, 10))
        self.btn_install = ttk.Button(bar, text="Install All (one click)", style="Accent.TButton", command=self.install_all)
        self.btn_install.pack(side="left", padx=(0, 6))
        self.btn_capture = ttk.Button(bar, text="Capture Stock", command=self.capture_stock)
        self.btn_capture.pack(side="left", padx=(0, 6))
        self.btn_purge = ttk.Button(bar, text="Purge (restore)", style="Danger.TButton", command=self.do_purge)
        self.btn_purge.pack(side="left", padx=(0, 6))
        self.btn_export = ttk.Button(bar, text="Export Mod (library)", command=self.do_export)
        self.btn_export.pack(side="left")
        self.btn_verify = ttk.Button(bar, text="Verify Steam Files", command=self.steam_verify)
        self.btn_verify.pack(side="left", padx=(6, 0))
        self.deploy_log = tk.Text(page, height=16, wrap="word", bd=0, highlightthickness=0, font=("Consolas", 9))
        self.deploy_log.grid(row=3, column=0, sticky="nsew")
        page.grid_rowconfigure(3, weight=1)
        self.texts.append(self.deploy_log)
        self.deploy_log.configure(state="disabled")
        return page

    def _save_game(self):
        self.cfg["game"] = self.game_var.get().strip()
        core.save_config(self.cfg)
        self.refresh_status()

    def _browse_game(self):
        path = filedialog.askdirectory(title="Helldivers 2 folder")
        if path:
            self.game_var.set(path)
            self._save_game()

    def capture_stock(self):
        try:
            n = core.capture_stock(self.cfg, self.log)
            self.log(f"stock snapshot ready ({n} files)")
        except Exception as exc:
            self.log(f"ERROR: {exc}")
            messagebox.showerror(APP_NAME, str(exc))
        self.refresh_status()

    def _task(self, fn, done):
        if self.busy:
            return
        self.busy = True
        self._task_result = None
        self._set_buttons(False)

        def work():
            try:
                self._task_result = fn()
            except Exception as exc:
                import traceback
                self.log(f"ERROR: {exc}")
                self.log(traceback.format_exc())
            finally:
                self.after(0, lambda: (self._set_buttons(True), done()))

        threading.Thread(target=work, daemon=True).start()

    def _set_buttons(self, on):
        self.busy = not on
        state = "normal" if on else "disabled"
        for b in (self.btn_install, self.btn_capture, self.btn_purge, self.btn_export, self.btn_verify):
            b.configure(state=state)

    def install_all(self, dry_run=False):
        self._task(lambda: actions.install_all(self.cfg, self.log, dry_run=dry_run), self.refresh_status)

    def do_purge(self):
        self._task(lambda: actions.purge(self.cfg, self.log), self.refresh_status)

    def do_export(self):
        path = filedialog.asksaveasfilename(defaultextension=".zip", initialfile="ModDiver Laboratory Mod.zip",
                                            filetypes=[("ZIP", "*.zip")])
        if not path:
            return
        self._task(lambda: core.export_mod(self.cfg, path, self.log), self.refresh_status)

    def launch_game(self):
        try:
            core.launch_game()
            self.log("launching Helldivers 2")
        except Exception as exc:
            self.log("launch: " + str(exc))

    def steam_verify(self):
        if not messagebox.askyesno(
                "Verify Steam Files",
                "Steam will re-download every changed game file, reverting ALL mods and tools "
                "(not just the ones from the Laboratory).\n\nContinue?"):
            return
        try:
            core.steam_verify()
            self.log("Steam verify requested")
        except Exception as exc:
            self.log("steam: " + str(exc))
    def _page_editor(self, parent):
        page = ttk.Frame(parent, style="TFrame")
        page.grid_columnconfigure(0, weight=1)
        page.grid_rowconfigure(1, weight=1)
        head = ttk.Frame(page, style="TFrame")
        head.grid(row=0, column=0, sticky="ew", padx=24, pady=(20, 8))
        ttk.Label(head, text="EDITOR", style="Title.TLabel").pack(side="left")
        ttk.Label(head, text="UNDER CONSTRUCTION", style="Muted.TLabel").pack(side="left", padx=(12, 0))
        ttk.Label(head, text="Mod Creator > Open SHODAN Stat Editor has the full editor today.",
                  style="Muted.TLabel").pack(side="right")
        nb = ttk.Notebook(page)
        nb.grid(row=1, column=0, sticky="nsew", padx=24, pady=(0, 20))
        self._editor_passives_tab(nb)
        self._editor_weapons_tab(nb)
        self._editor_damage_tab(nb)
        return page

    def _editor_passives_tab(self, nb):
        page = ttk.Frame(nb, style="TFrame")
        nb.add(page, text="Armour passives")
        page.grid_columnconfigure(0, weight=1)
        page.grid_columnconfigure(1, weight=2)
        page.grid_rowconfigure(1, weight=1)
        head = ttk.Frame(page, style="TFrame")
        head.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(8, 8))
        ttk.Button(head, text="RELOAD", command=self._scan_editor).pack(side="right")
        ttk.Label(head, text="Double-click a value, then SAVE PASSIVES.", style="Muted.TLabel").pack(side="left")
        self.editor_tree = ttk.Treeview(page, columns=("n",), show="tree headings")
        self.editor_tree.heading("#0", text="Passive")
        self.editor_tree.heading("n", text="Fields")
        self.editor_tree.column("#0", width=280)
        self.editor_tree.column("n", width=70, anchor="e")
        self.editor_tree.grid(row=1, column=0, sticky="nsew", padx=(0, 12))
        self.editor_tree.bind("<<TreeviewSelect>>", self._editor_select)
        right = ttk.Frame(page, style="TFrame")
        right.grid(row=1, column=1, sticky="nsew")
        right.grid_columnconfigure(0, weight=1)
        right.grid_rowconfigure(0, weight=1)
        self.editor_mods = ttk.Treeview(right, columns=("name", "value"), show="headings")
        for c, t, w, a in (("name", "Value", 320, "w"), ("value", "Current", 110, "e")):
            self.editor_mods.heading(c, text=t)
            self.editor_mods.column(c, width=w, anchor=a)
        self.editor_mods.grid(row=0, column=0, sticky="nsew")
        sb = ttk.Scrollbar(right, orient="vertical", command=self.editor_mods.yview)
        sb.grid(row=0, column=1, sticky="ns")
        self.editor_mods.configure(yscrollcommand=sb.set)
        self.editor_mods.bind("<Double-1>", self._editor_edit)
        ttk.Button(page, text="SAVE PASSIVES", command=self._save_editor).grid(row=2, column=0, columnspan=2, sticky="e", pady=(8, 0))
        self.after_idle(self._scan_editor)

    def _scan_editor(self):
        if not hasattr(self, "editor_tree"):
            return
        self.editor_tree.delete(*self.editor_tree.get_children())
        self.editor_mods.delete(*self.editor_mods.get_children())
        self._editor_rows = []
        self._editor_changes = {}
        try:
            self._editor_rows = core.dump_passives(core.game_dir(self.cfg))
        except Exception as exc:
            self.log(f"editor: {exc}")
            return
        ids = sorted({r[1] for r in self._editor_rows})
        for pid in ids:
            n = sum(1 for r in self._editor_rows if r[1] == pid)
            name = editor_names.PASSIVE_NAMES.get(pid, f"Passive {pid}")
            self.editor_tree.insert("", "end", iid=str(pid), text=name, values=(n,))
        self.log(f"editor: {len(ids)} armour passives loaded")

    def _editor_select(self, event=None):
        sel = self.editor_tree.selection()
        if not sel:
            return
        pid = int(sel[0])
        self.editor_mods.delete(*self.editor_mods.get_children())
        for kind, p, mid, val in self._editor_rows:
            if p == pid:
                name = editor_names.MOD_NAMES.get(mid, f"Modifier {mid:#010x}")
                self.editor_mods.insert("", "end", iid=f"{kind}:{mid}", values=(name, f"{val:.4g}"))

    def _editor_edit(self, event=None):
        sel = self.editor_mods.selection()
        if not sel or not self.editor_tree.selection():
            return
        kind, mid = sel[0].split(":")
        mid, pid = int(mid), int(self.editor_tree.selection()[0])
        cur = next((v for k, p, m, v in self._editor_rows if p == pid and k == kind and m == mid), None)
        if cur is None:
            return
        name = editor_names.MOD_NAMES.get(mid, f"Modifier {mid:#010x}")
        val = simpledialog.askfloat("Edit value", f"{name}:", initialvalue=cur,
                                    minvalue=-1e9, maxvalue=1e9, parent=self)
        if val is None:
            return
        self._editor_changes[(kind, pid, mid)] = val
        self.editor_mods.item(sel[0], values=(name, f"{val:.4g}"))

    def _save_editor(self):
        if not getattr(self, "_editor_changes", None):
            messagebox.showinfo(APP_NAME, "No edits yet. Double-click a value first.")
            return
        edits = [(k, p, m, v) for (k, p, m), v in self._editor_changes.items()]
        try:
            core.apply_passives(core.game_dir(self.cfg), edits)
            self.log(f"editor: saved {len(edits)} passive value(s)")
            self._editor_changes = {}
        except Exception as exc:
            messagebox.showerror(APP_NAME, str(exc))

    WEAPON_FIELDS = tuple((f[1], f[2]) for f in editor_fields.WEAPON_FIELDS if f[4] is not None)

    def _editor_weapons_tab(self, nb):
        page = ttk.Frame(nb, style="TFrame")
        nb.add(page, text="Weapons")
        page.grid_columnconfigure(0, weight=1)
        page.grid_columnconfigure(1, weight=2)
        page.grid_rowconfigure(1, weight=1)
        head = ttk.Frame(page, style="TFrame")
        head.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(8, 8))
        ttk.Button(head, text="RELOAD", command=self._scan_weapons).pack(side="right")
        ttk.Label(head, text="Double-click a value, then SAVE WEAPONS.", style="Muted.TLabel").pack(side="left")
        self.weapon_tree = ttk.Treeview(page, columns=("slot",), show="tree headings")
        self.weapon_tree.heading("#0", text="Weapon")
        self.weapon_tree.heading("slot", text="Slot")
        self.weapon_tree.column("#0", width=280)
        self.weapon_tree.column("slot", width=90)
        self.weapon_tree.grid(row=1, column=0, sticky="nsew", padx=(0, 12))
        self.weapon_tree.bind("<<TreeviewSelect>>", self._weapon_select)
        right = ttk.Frame(page, style="TFrame")
        right.grid(row=1, column=1, sticky="nsew")
        right.grid_columnconfigure(0, weight=1)
        right.grid_rowconfigure(0, weight=1)
        self.weapon_mods = ttk.Treeview(right, columns=("name", "value"), show="headings")
        for c, t, w, a in (("name", "Value", 320, "w"), ("value", "Current", 110, "e")):
            self.weapon_mods.heading(c, text=t)
            self.weapon_mods.column(c, width=w, anchor=a)
        self.weapon_mods.grid(row=0, column=0, sticky="nsew")
        sb = ttk.Scrollbar(right, orient="vertical", command=self.weapon_mods.yview)
        sb.grid(row=0, column=1, sticky="ns")
        self.weapon_mods.configure(yscrollcommand=sb.set)
        self.weapon_mods.bind("<Double-1>", self._weapon_edit)
        ttk.Button(page, text="SAVE WEAPONS", command=self._save_weapons).grid(row=2, column=0, columnspan=2, sticky="e", pady=(8, 0))
        self.after_idle(self._scan_weapons)

    def _scan_weapons(self):
        if not hasattr(self, "weapon_tree"):
            return
        self.weapon_tree.delete(*self.weapon_tree.get_children())
        self.weapon_mods.delete(*self.weapon_mods.get_children())
        self._weapon_rows = []
        self._weapon_changes = {}
        try:
            self._weapon_rows = core.dump_weapons(core.game_dir(self.cfg))
        except Exception as exc:
            self.log(f"weapons: {exc}")
            return
        by_key = {}
        for kind, key, field, val in self._weapon_rows:
            if kind == "W":
                by_key.setdefault(key, {})[field] = val
        n = 0
        for key in sorted(by_key):
            if key == "0" * 16:
                continue
            name, slot = editor_weapons.WEAPONS.get(key, (key, ""))
            self.weapon_tree.insert("", "end", iid=key, text=name, values=(slot,))
            n += 1
        self.log(f"weapons: {n} loaded")
        self._scan_damage()

    def _weapon_select(self, event=None):
        sel = self.weapon_tree.selection()
        if not sel:
            return
        key = sel[0]
        self.weapon_mods.delete(*self.weapon_mods.get_children())
        vals = {f: v for kind, k, f, v in self._weapon_rows if kind == "W" and k == key}
        for field, label in self.WEAPON_FIELDS:
            self.weapon_mods.insert("", "end", iid=field, values=(label, f"{vals.get(field, 0):.4g}"))

    def _weapon_edit(self, event=None):
        sel = self.weapon_mods.selection()
        if not sel or not self.weapon_tree.selection():
            return
        field = sel[0]
        key = self.weapon_tree.selection()[0]
        cur = next((v for k, f, v in self._weapon_rows if k == key and f == field), 0.0)
        label = dict(self.WEAPON_FIELDS).get(field, field)
        val = simpledialog.askfloat("Edit value", f"{label}:", initialvalue=cur,
                                    minvalue=-1e9, maxvalue=1e9, parent=self)
        if val is None:
            return
        self._weapon_changes[(key, field)] = val
        self.weapon_mods.item(sel[0], values=(label, f"{val:.4g}"))

    def _save_weapons(self):
        if not getattr(self, "_weapon_changes", None):
            messagebox.showinfo(APP_NAME, "No edits yet. Double-click a value first.")
            return
        edits = [("W", k, f, v) for (k, f), v in self._weapon_changes.items()]
        try:
            core.apply_weapons(core.game_dir(self.cfg), edits)
            self.log(f"weapons: saved {len(edits)} value(s)")
            self._weapon_changes = {}
        except Exception as exc:
            messagebox.showerror(APP_NAME, str(exc))

    DAMAGE_LABELS = {
        "damage": "Damage", "durable": "Durable damage", "ap_direct": "Armor pen. (direct)",
        "ap_slight": "Armor pen. (slight angle)", "ap_large": "Armor pen. (large angle)",
        "ap_extreme": "Armor pen. (extreme angle)", "demolition": "Demolition force",
        "stagger": "Stagger force", "push": "Push force",
    }

    def _editor_damage_tab(self, nb):
        page = ttk.Frame(nb, style="TFrame")
        nb.add(page, text="Damage")
        page.grid_columnconfigure(0, weight=1)
        page.grid_columnconfigure(1, weight=2)
        page.grid_rowconfigure(1, weight=1)
        head = ttk.Frame(page, style="TFrame")
        head.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(8, 8))
        ttk.Button(head, text="RELOAD", command=self._scan_damage).pack(side="right")
        ttk.Label(head, text="Double-click a value, then SAVE DAMAGE.", style="Muted.TLabel").pack(side="left")
        self.damage_tree = ttk.Treeview(page, columns=("n",), show="tree headings")
        self.damage_tree.heading("#0", text="Damage id")
        self.damage_tree.heading("n", text="Values")
        self.damage_tree.column("#0", width=280)
        self.damage_tree.column("n", width=70, anchor="e")
        self.damage_tree.grid(row=1, column=0, sticky="nsew", padx=(0, 12))
        self.damage_tree.bind("<<TreeviewSelect>>", self._damage_select)
        right = ttk.Frame(page, style="TFrame")
        right.grid(row=1, column=1, sticky="nsew")
        right.grid_columnconfigure(0, weight=1)
        right.grid_rowconfigure(0, weight=1)
        self.damage_mods = ttk.Treeview(right, columns=("name", "value"), show="headings")
        for c, t, w, a in (("name", "Value", 320, "w"), ("value", "Current", 110, "e")):
            self.damage_mods.heading(c, text=t)
            self.damage_mods.column(c, width=w, anchor=a)
        self.damage_mods.grid(row=0, column=0, sticky="nsew")
        sb = ttk.Scrollbar(right, orient="vertical", command=self.damage_mods.yview)
        sb.grid(row=0, column=1, sticky="ns")
        self.damage_mods.configure(yscrollcommand=sb.set)
        self.damage_mods.bind("<Double-1>", self._damage_edit)
        ttk.Button(page, text="SAVE DAMAGE", command=self._save_damage).grid(row=2, column=0, columnspan=2, sticky="e", pady=(8, 0))
        self.after_idle(self._scan_damage)

    def _scan_damage(self):
        if not hasattr(self, "damage_tree"):
            return
        self.damage_tree.delete(*self.damage_tree.get_children())
        self.damage_mods.delete(*self.damage_mods.get_children())
        self._damage_rows = []
        self._damage_changes = {}
        try:
            self._damage_rows = core.dump_damage(core.game_dir(self.cfg))
        except Exception as exc:
            self.log(f"damage: {exc}")
            return
        ids = sorted({r[0] for r in self._damage_rows}, key=lambda x: int(x))
        for did in ids:
            n = sum(1 for r in self._damage_rows if r[0] == did)
            self.damage_tree.insert("", "end", iid=did, text=did, values=(n,))
        self.log(f"damage: {len(ids)} rows")

    def _damage_select(self, event=None):
        sel = self.damage_tree.selection()
        if not sel:
            return
        did = sel[0]
        self.damage_mods.delete(*self.damage_mods.get_children())
        values = {f: v for k, f, v in self._damage_rows if k == did}
        for field, label in self.DAMAGE_LABELS.items():
            self.damage_mods.insert("", "end", iid=field, values=(label, f"{values.get(field, 0):.4g}"))

    def _damage_edit(self, event=None):
        sel = self.damage_mods.selection()
        if not sel or not self.damage_tree.selection():
            return
        field = sel[0]
        did = self.damage_tree.selection()[0]
        cur = next((v for kind, k, f, v in self._damage_rows if k == did and f == field), 0.0)
        label = self.DAMAGE_LABELS.get(field, field)
        val = simpledialog.askfloat("Edit value", f"{label}:", initialvalue=cur,
                                    minvalue=-1e9, maxvalue=1e9, parent=self)
        if val is None:
            return
        self._damage_changes[(did, field)] = val
        self.damage_mods.item(sel[0], values=(label, f"{val:.4g}"))

    def _save_damage(self):
        if not getattr(self, "_damage_changes", None):
            messagebox.showinfo(APP_NAME, "No edits yet. Double-click a value first.")
            return
        edits = [(k, f, v) for (k, f), v in self._damage_changes.items()]
        try:
            core.apply_damage(core.game_dir(self.cfg), edits)
            self.log(f"damage: saved {len(edits)} value(s)")
            self._damage_changes = {}
        except Exception as exc:
            messagebox.showerror(APP_NAME, str(exc))


    def _page_tools(self, parent):
        page = ttk.Frame(parent, style="TFrame")
        page.grid_columnconfigure(0, weight=1)
        ttk.Label(
            page,
            text=("Capture Game as Mod writes two ZIPs: a portable file mod for file-based "
                  "managers, and an Arsenal data pack that bundles the YAO loader so Arsenal, "
                  "HD2 Mod Manager and DDMM can deploy it as patch files. The Arsenal pack needs "
                  "launch, exit and launch again to apply."),
            style="Muted.TLabel", wraplength=760, justify="left").grid(
            row=0, column=0, sticky="w", pady=(0, 12))

        loaders = ttk.Frame(page, style="Panel.TFrame", padding=16)
        loaders.grid(row=2, column=0, sticky="ew", pady=(0, 12))
        ttk.Label(loaders, text="GAME LOADERS", style="Panel.TLabel",
                  font=("Segoe UI Semibold", 11)).pack(anchor="w")
        ttk.Label(loaders, text="Runtime Lua loaders. Add one to the library, then Deploy to install it.",
                  style="PanelMuted.TLabel", wraplength=760).pack(anchor="w", pady=(5, 8))
        ttk.Label(loaders, text="Chef Shared Loader 1.1.0 - full Lua 5.1 runtime: side-by-side mods, crash guard, "
                                "sandbox, F9 menu. Deploy it last. Use when your mods need Chef's runtime.",
                  style="PanelMuted.TLabel", wraplength=760).pack(anchor="w")
        ttk.Label(loaders, text="Boot Mod Loader 0.7.0 - minimal: starts -- HD2-Addon: mods on the game's own boot "
                                "script. Use for simple add-on mods. Never enable both loaders at once.",
                  style="PanelMuted.TLabel", wraplength=760).pack(anchor="w", pady=(0, 8))
        row = ttk.Frame(loaders, style="TFrame")
        row.pack(anchor="w")
        ttk.Button(row, text="ADD CHEF SHARED LOADER 1.1.0",
                   command=lambda: self.install_loader("chef_loader")).pack(side="left")
        ttk.Button(row, text="ADD BOOT MOD LOADER 0.7.0",
                   command=lambda: self.install_loader("boot_loader")).pack(side="left", padx=(8, 0))

        feature = ttk.Frame(page, style="Panel.TFrame", padding=16)
        feature.grid(row=3, column=0, sticky="ew", pady=(0, 12))
        ttk.Label(feature, text="SHODAN  /  STAT EDITOR", style="Panel.TLabel",
                  font=("Segoe UI Semibold", 11)).pack(anchor="w")
        ttk.Label(feature, text="SHODAN Stat Editor Offline v4.1.0 for weapons, vehicles, stratagems and armour passives. "
                                "It opens in its own window; press Install there to write, then capture the result as a mod here.",
                  style="PanelMuted.TLabel", wraplength=760).pack(anchor="w", pady=(5, 8))
        row = ttk.Frame(feature, style="TFrame")
        row.pack(anchor="w")
        ttk.Button(row, text="OPEN SHODAN STAT EDITOR", style="Accent.TButton",
                   command=self.open_editor).pack(side="left")
        ttk.Button(row, text="CAPTURE GAME AS MOD",
                   command=self.capture_game_mod).pack(side="left", padx=(8, 0))
        ttk.Button(row, text="IMPORT EDIT PRESETS",
                   command=self.import_presets).pack(side="left", padx=(8, 0))
        outputs = ttk.Frame(feature, style="TFrame")
        outputs.pack(anchor="w", pady=(8, 0))
        ttk.Button(outputs, text="OPEN CAPTURE FOLDER",
                   command=lambda: self.open_output_folder(core.APP_DATA / "mods")).pack(side="left")
        ttk.Button(outputs, text="OPEN SHODAN PRESETS",
                   command=lambda: self.open_output_folder(core.EDITOR_CFG)).pack(side="left", padx=(8, 0))

        ccm = ttk.Frame(page, style="Panel.TFrame", padding=16)
        ccm.grid(row=4, column=0, sticky="ew", pady=(0, 12))
        ttk.Label(ccm, text="COMBINED COMMUNITY MODS  /  v2.0.13", style="Panel.TLabel",
                  font=("Segoe UI Semibold", 11)).pack(anchor="w")
        ttk.Label(ccm, text="Combined offline editor with Armory Forge, Vanilla+ and Hellpod Control.",
                  style="PanelMuted.TLabel", wraplength=760).pack(anchor="w", pady=(5, 8))
        row2 = ttk.Frame(ccm, style="TFrame")
        row2.pack(anchor="w")
        ttk.Button(row2, text="OPEN COMBINED COMMUNITY MODS", style="Accent.TButton",
                   command=self.open_editor_ccm).pack(side="left")
        ttk.Button(row2, text="CAPTURE GAME AS MOD",
                   command=self.capture_game_mod).pack(side="left", padx=(8, 0))
        ttk.Button(row2, text="IMPORT PRESETS",
                   command=self.import_presets_ccm).pack(side="left", padx=(8, 0))
        outputs2 = ttk.Frame(ccm, style="TFrame")
        outputs2.pack(anchor="w", pady=(8, 0))
        ttk.Button(outputs2, text="OPEN CAPTURE FOLDER",
                   command=lambda: self.open_output_folder(core.APP_DATA / "mods")).pack(side="left")
        ttk.Button(outputs2, text="OPEN SAVED PRESETS",
                   command=lambda: self.open_output_folder(core.EDITOR_CFG)).pack(side="left", padx=(8, 0))
        ttk.Button(outputs2, text="OPEN ARMORY PRESETS",
                   command=lambda: self.open_output_folder(core.EDITOR_CCM_PRESETS)).pack(side="left", padx=(8, 0))

        feature2 = ttk.Frame(page, style="Panel.TFrame", padding=16)
        feature2.grid(row=5, column=0, sticky="ew")
        ttk.Label(feature2, text="NoMoFOMO  /  HIDDEN CONTENT UNLOCKER", style="Panel.TLabel",
                  font=("Segoe UI Semibold", 11)).pack(anchor="w")
        ttk.Label(feature2, text="Built-in armour unlock payload. It is included with Install All; turning it off restores stock armour.",
                  style="PanelMuted.TLabel", wraplength=760).pack(anchor="w", pady=(5, 8))
        self.nomofomo_var = tk.BooleanVar(value=bool(self.cfg.get("nomofomo", True)))
        ttk.Checkbutton(feature2, text="Include with Install All", variable=self.nomofomo_var,
                        command=self.toggle_nomofomo).pack(anchor="w")
        return page

    def import_presets(self):
        paths = filedialog.askopenfilenames(
            title="Import SHODAN presets", parent=self,
            filetypes=[("SHODAN preset", "*.txt"), ("All files", "*.*")])
        if not paths:
            return
        dest = core.EDITOR_CFG
        dest.mkdir(parents=True, exist_ok=True)
        n = 0
        for p in paths:
            try:
                shutil.copy2(p, dest / Path(p).name)
                n += 1
            except Exception as exc:
                self.log(f"preset {p}: {exc}")
        self.log(f"imported {n} SHODAN preset(s) to {dest}")
        messagebox.showinfo(APP_NAME, f"Imported {n} preset(s) into the SHODAN preset folder:\n\n{dest}")

    def open_output_folder(self, folder):
        try:
            folder = Path(folder)
            folder.mkdir(parents=True, exist_ok=True)
            os.startfile(str(folder))
        except Exception as exc:
            messagebox.showerror(APP_NAME, f"Could not open folder:\n{folder}\n\n{exc}")

    def install_loader(self, name):
        label = {"chef_loader": "Chef's Loader added", "boot_loader": "Boot Loader added"}.get(name, "Loader added")
        try:
            core.install_builtin(self.cfg, name, self.log)
            self.refresh_mods()
            messagebox.showinfo(APP_NAME, label)
        except Exception as exc:
            messagebox.showerror(APP_NAME, str(exc))

    def open_editor_ccm(self):
        exe = core.EDITOR_CCM / "Combined Community Mods.exe"
        if not exe.exists():
            messagebox.showerror(APP_NAME, "Combined Community Mods not found.")
            return
        try:
            preset_source = core.EDITOR_CCM_PRESETS
            preset_dest = core.EDITOR_CCM / "Armory Forge Settings" / "forge_presets"
            preset_dest.mkdir(parents=True, exist_ok=True)
            if preset_source.is_dir():
                for preset in preset_source.glob("*.ini"):
                    shutil.copy2(preset, preset_dest / preset.name)
            subprocess.Popen([str(exe)], cwd=str(core.EDITOR_CCM))
            self.log("launched Combined Community Mods")
        except Exception as exc:
            self.log(f"editor: {exc}")

    def import_presets_ccm(self):
        paths = filedialog.askopenfilenames(
            title="Import Combined Community Mods presets", parent=self,
            filetypes=[("Preset", "*.ini"), ("All files", "*.*")])
        if not paths:
            return
        dest = core.EDITOR_CCM_PRESETS
        dest.mkdir(parents=True, exist_ok=True)
        runtime_dest = core.EDITOR_CCM / "Armory Forge Settings" / "forge_presets"
        runtime_dest.mkdir(parents=True, exist_ok=True)
        n = 0
        for p in paths:
            try:
                name = Path(p).name
                shutil.copy2(p, dest / name)
                shutil.copy2(p, runtime_dest / name)
                n += 1
            except Exception as exc:
                self.log(f"preset {p}: {exc}")
        self.log(f"imported {n} Combined Community Mods preset(s)")
        messagebox.showinfo(APP_NAME, f"Imported {n} preset(s) into Combined Community Mods.\n\nSaved copies:\n{dest}")

    def open_editor(self):
        exe = core.EDITOR / "SHODAN Stat Editor Offline.exe"
        if not exe.exists():
            messagebox.showerror(APP_NAME, f"Editor not found:\n{exe}")
            return
        try:
            subprocess.Popen([str(exe)], cwd=str(core.EDITOR))
            self.log("launched SHODAN stat editor")
        except Exception as exc:
            self.log(f"editor: {exc}")

    def toggle_nomofomo(self):
        self.cfg["nomofomo"] = bool(self.nomofomo_var.get())
        core.save_config(self.cfg)
        self.log(f"NoMoFOMO {'enabled' if self.cfg['nomofomo'] else 'disabled'}")

    def capture_game_mod(self):
        name = simpledialog.askstring("Capture", "Name for the captured editor changes:",
                                      initialvalue="Stat Editor changes", parent=self)
        if not name:
            return

        def done():
            self.refresh_mods()
            self.refresh_status()
            m = self._task_result
            if not m:
                return
            lines = ["Captured as a library mod.", "", "Library folder:", str(m.get("path", ""))]
            if m.get("package"):
                lines += ["", "Portable file mod:", m["package"]]
            if m.get("arsenal_package"):
                lines += ["", "Arsenal data pack:", m["arsenal_package"],
                          "", "Arsenal: import the *-Arsenal.zip, enable it, Deploy, "
                          "launch, exit normally, then launch again."]
            if m.get("arsenal_package"):
                lines += ["", "The pack includes the YAO loader; do not enable another "
                          "boot replacement with it."]
            messagebox.showinfo(APP_NAME, "\n".join(lines))

        self._task(lambda: core.capture_game_mod(self.cfg, self.log, name), done)

    # ---------------------------------------------------------------- themes page
    def _page_themes(self, parent):
        page = ttk.Frame(parent, style="TFrame")
        page.grid_columnconfigure(0, weight=1)
        ttk.Label(page, text="Presets", style="Title.TLabel").grid(row=0, column=0, sticky="w")
        presets = ttk.Frame(page, style="TFrame")
        presets.grid(row=1, column=0, sticky="w", pady=(6, 16))
        for i, (name, t) in enumerate(THEMES.items()):
            b = tk.Button(presets, text=name, width=14, height=3, bd=0, relief="flat", cursor="hand2",
                          bg=t["panel"], fg=t["accent"], activebackground=t["panel2"],
                          activeforeground=t["accent"], font=("Segoe UI Semibold", 10),
                          command=lambda n=name: self.apply_preset(n))
            b.grid(row=0, column=i, padx=(0, 8))
            tk.Label(presets, text="Aa", bg=t["panel"], fg=t["text"], font=("Segoe UI", 9)).grid(row=1, column=i)
        ttk.Label(page, text="Accent", style="Title.TLabel").grid(row=2, column=0, sticky="w")
        sw = ttk.Frame(page, style="TFrame")
        sw.grid(row=3, column=0, sticky="w", pady=(6, 16))
        for c in SWATCHES:
            b = tk.Button(sw, bg=c, width=3, height=1, bd=0, relief="flat", cursor="hand2",
                          command=lambda col=c: self._set_theme(accent=col,
                                                                accent_text="#151a12" if col in ("#f4c542", "#ffffff", "#38d996") else "#ffffff"))
            b.pack(side="left", padx=(0, 6))
        ttk.Label(page, text="Custom colors", style="Title.TLabel").grid(row=4, column=0, sticky="w")
        custom = ttk.Frame(page, style="TFrame")
        custom.grid(row=5, column=0, sticky="w", pady=(6, 10))
        for key, label in (("bg", "Background"), ("panel", "Panel"), ("text", "Text"), ("accent", "Accent")):
            ttk.Button(custom, text=label, command=lambda k=key: self.pick_color(k)).pack(side="left", padx=(0, 8))
        ttk.Label(page, text="Font size", style="Title.TLabel").grid(row=6, column=0, sticky="w", pady=(8, 0))
        self.font_scale = tk.Scale(page, from_=8, to=16, orient="horizontal", length=260,
                                   showvalue=True, command=lambda v: self._set_theme(font=int(float(v))))
        self.font_scale.set(self.theme.get("font", 10))
        self.font_scale.grid(row=7, column=0, sticky="w")
        bar = ttk.Frame(page, style="TFrame")
        bar.grid(row=8, column=0, sticky="w", pady=(14, 0))
        ttk.Button(bar, text="Save theme", style="Accent.TButton", command=self.save_theme).pack(side="left", padx=(0, 8))
        ttk.Button(bar, text="Reset", command=self.apply_reset).pack(side="left")
        return page

    def apply_preset(self, name):
        base = dict(core.DEFAULT_THEME)
        base.update(THEMES[name])
        base["preset"] = name
        self.theme = base
        self.apply_theme()

    def pick_color(self, key):
        color = colorchooser.askcolor(color=self.theme.get(key), title=f"Pick {key}")[1]
        if color:
            self._set_theme(**{key: color})

    def save_theme(self):
        self.cfg["theme"] = dict(self.theme)
        core.save_config(self.cfg)
        self.log("theme saved")

    def apply_reset(self):
        self.theme = dict(core.DEFAULT_THEME)
        self.apply_theme()

    # ---------------------------------------------------------------- log / about
    def _page_log(self, parent):
        page = ttk.Frame(parent, style="TFrame")
        page.grid_columnconfigure(0, weight=1)
        page.grid_rowconfigure(1, weight=1)
        bar = ttk.Frame(page, style="TFrame")
        bar.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        ttk.Button(bar, text="Clear Log", command=self.clear_log).pack(side="left")
        self.log_text = tk.Text(page, wrap="word", bd=0, highlightthickness=0, font=("Consolas", 9))
        self.log_text.grid(row=1, column=0, sticky="nsew")
        sb = ttk.Scrollbar(page, orient="vertical", command=self.log_text.yview)
        sb.grid(row=1, column=1, sticky="ns")
        self.log_text.configure(yscrollcommand=sb.set, state="disabled")
        self.texts.append(self.log_text)
        return page

    def _page_about(self, parent):
        page = ttk.Frame(parent, style="TFrame")
        page.grid_columnconfigure(0, weight=1)
        page.grid_rowconfigure(0, weight=1)
        text = tk.Text(page, wrap="word", bd=0, highlightthickness=0, font=("Segoe UI", 10),
                       padx=14, pady=12, cursor="arrow", spacing1=2, spacing3=3)
        text.grid(row=0, column=0, sticky="nsew")
        sb = ttk.Scrollbar(page, orient="vertical", command=text.yview)
        sb.grid(row=0, column=1, sticky="ns")
        text.configure(yscrollcommand=sb.set)
        text.tag_configure("h1", font=("Segoe UI Black", 26), spacing1=0, spacing3=4)
        text.tag_configure("sub", font=("Segoe UI Semibold", 11), spacing3=16)
        text.tag_configure("h2", font=("Segoe UI Semibold", 13), spacing1=18, spacing3=7)
        text.tag_configure("name", font=("Segoe UI Semibold", 10))
        text.tag_configure("tool", font=("Segoe UI", 10))
        text.tag_configure("body", font=("Segoe UI", 10), spacing1=2, spacing3=5)
        text.tag_configure("num", font=("Segoe UI", 10), spacing1=5, lmargin1=14, lmargin2=30)
        text.tag_configure("bullet", font=("Segoe UI", 10), spacing1=5, lmargin1=14, lmargin2=30)
        for chunk, tag in ABOUT_BLOCKS:
            text.insert("end", chunk, tag)
        text.configure(state="disabled")
        self.about_text = text
        self.texts.append(text)
        return page

    # ---------------------------------------------------------------- log plumbing
    def log(self, msg):
        self.log_queue.put(str(msg))

    def _drain(self):
        while True:
            try:
                msg = self.log_queue.get_nowait()
            except queue.Empty:
                break
            line = f"[{time.strftime('%H:%M:%S')}] {msg}"
            for w in (getattr(self, "deploy_log", None), getattr(self, "log_text", None)):
                if w is not None:
                    try:
                        w.configure(state="normal")
                        w.insert("end", line + "\n")
                        w.see("end")
                        w.configure(state="disabled")
                    except tk.TclError:
                        pass
            try:
                self.status.configure(text=msg[:140])
            except tk.TclError:
                pass
        self.after(120, self._drain)

    def refresh_status(self):
        stock = len(list(core.STOCK.glob("*.dl_bin"))) if core.STOCK.exists() else 0
        deployed = len(core.load_deployed())
        self.stock_label.configure(text=f"Stock: {stock} files" if stock else "Stock: not captured")
        self.deployed_label.configure(text=f"   Deployed: {deployed}")
        self.chip.configure(text=f"STOCK {stock}  DEPLOYED {deployed}")

    def _close(self):
        try:
            core.save_config(self.cfg)
        finally:
            if self.editor_proc is not None and self.editor_proc.poll() is None:
                self.editor_proc.terminate()
                try:
                    self.editor_proc.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    self.editor_proc.kill()
            self.destroy()

    def _ensure_shortcut(self):
        if self.cfg.get("shortcut_v2"):
            return
        exe = os.environ.get("YAO_FORGE_EXE")
        if not exe or not Path(exe).exists():
            return
        try:
            ps = ("$ws=New-Object -ComObject WScript.Shell; "
                  "$s=$ws.CreateShortcut((Join-Path ([Environment]::GetFolderPath('Desktop')) 'ModDiver Laboratory.lnk')); "
                  "$s.TargetPath='" + exe + "'; "
                  "$s.WorkingDirectory='" + str(Path(exe).parent) + "'; "
                  "$s.IconLocation='" + exe + "'; "
                  "$s.Save()")
            subprocess.run(["powershell", "-NoProfile", "-Command", ps],
                           creationflags=0x08000000, timeout=30)
            self.cfg["shortcut_v2"] = True
            core.save_config(self.cfg)
            self.log("desktop shortcut created")
        except Exception as exc:
            self.log("shortcut: " + str(exc))

    def clear_log(self):
        for w in (getattr(self, "deploy_log", None), getattr(self, "log_text", None)):
            if w is not None:
                w.configure(state="normal")
                w.delete("1.0", "end")
                w.configure(state="disabled")


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--lua-runner":
        import lua_runner
        sys.argv = [sys.argv[0]] + sys.argv[2:]
        raise SystemExit(lua_runner.main())
    App().mainloop()


if __name__ == "__main__":
    main()
