"""The application window: layout, pages, download lifecycle, persistence."""

import json
import os
import queue
import subprocess
import sys
import threading
import tkinter as tk
from shutil import which
from tkinter import filedialog, ttk

from .engine import (_engine_env, _engine_python, _shell_quote, js_runtime_args,
                     resolve_yt_dlp)
from .icon import apply_window_icon
from .parsing import (DEST_RE, ITEM_RE, PROG_RE, STATUS_TAGS, TAG_RE)
from .paths import CONFIG_PATH, DEFAULT_OUTDIR
from .settings import (AUDIO_QUALITIES, BROWSERS, CONTAINERS, DEFAULTS,
                       DEFAULT_SPONSOR_CATS, PLAYLIST_MODES, QUALITY_CHIPS,
                       REMUX_TARGETS, SPONSOR_ACTIONS, SUB_FORMATS, build_args)
from .theme import (BG, BG_SOFT, BLUE, BORDER, GREEN, RED, SURFACE, TEXT,
                    TEXT_DIM, TEXT_FAINT, YELLOW, mono_font, setup_theme,
                    ui_font)
from .widgets import (Card, Check, ChoiceGroup, EntryField, Logo, NavButton,
                      Pill, ProgressBar, RoundedButton, ScrollArea, TextField,
                      Toast, parent_bg)


class App:
    PAGES = (
        ("download", "Download", "download"),
        ("output", "Output", "folder"),
        ("subs", "Subtitles", "cc"),
        ("advanced", "Advanced", "sliders"),
        ("command", "Command", "terminal"),
    )

    def __init__(self, root: tk.Tk):
        self.root = root
        self._proc = None
        self._q = None
        self._running = False
        self._user_stopped = False
        self._save_job = None
        self._tracked = []
        self._log_visible = False
        self._page_key = "download"
        self._item_index = 0
        self._item_total = 0
        self._engine_state = (None, None, None)

        self._engine_state = resolve_yt_dlp()
        self._setup_window()
        setup_theme(root)
        self._build_shell()
        self._build_pages()
        self._apply_defaults()
        self._load_config()
        self._bind_changes()
        self._sync_states()
        self.update_preview()
        self._refresh_engine()
        self._log_append("Engine: " + self._engine_label() + "\n", "dim")
        root.protocol("WM_DELETE_WINDOW", self._on_close)

    # ================= window & shell =================

    def _setup_window(self):
        self.root.title("yt-dlp GUI — modern downloader")
        self.root.configure(bg=BG)
        self.root.minsize(1000, 640)
        sw, sh = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
        w, h = min(1180, sw - 80), min(860, sh - 120)
        x, y = max((sw - w) // 2, 0), max((sh - h) // 3, 0)
        self.root.geometry(f"{w}x{h}+{x}+{y}")
        apply_window_icon(self.root)

    def _build_shell(self):
        root = self.root

        # ---- header ---------------------------------------------------
        header = tk.Frame(root, bg=BG_SOFT, height=64)
        header.pack(fill="x")
        header.pack_propagate(False)
        hin = tk.Frame(header, bg=BG_SOFT)
        hin.pack(fill="both", expand=True, padx=20)
        Logo(hin).pack(side="left", pady=15)
        tk.Frame(hin, bg=BG_SOFT, width=14).pack(side="left")

        self.btn_start = RoundedButton(hin, "Download", self.start, kind="primary",
                                       glyph="⬇", height=38, bg=BG_SOFT,
                                       font_size=10, min_width=142)
        self.btn_start.pack(side="right", pady=13)
        self.btn_stop = RoundedButton(hin, "Stop", self.stop, kind="danger",
                                      glyph="■", height=38, bg=BG_SOFT,
                                      font_size=10, min_width=96)
        self.btn_stop.pack(side="right", padx=(0, 8), pady=13)
        self.btn_stop.set_enabled(False)
        RoundedButton(hin, "Open folder", self.open_folder, kind="ghost",
                      height=38, bg=BG_SOFT, padx=14).pack(side="right", padx=(0, 6), pady=13)
        self.pill = Pill(hin, "Checking engine…", bg=BG_SOFT, color=TEXT_FAINT,
                         command=lambda: self.show_page("command"))
        self.pill.pack(side="right", padx=(0, 16), pady=18)
        tk.Frame(root, bg=BORDER, height=1).pack(fill="x")

        # ---- body ------------------------------------------------------
        body = tk.Frame(root, bg=BG)
        body.pack(fill="both", expand=True)

        sidebar = tk.Frame(body, bg=BG_SOFT, width=200)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)
        self.sidebar = sidebar

        tk.Label(sidebar, text="  MENU", bg=BG_SOFT, fg=TEXT_FAINT,
                 font=ui_font(8, "bold"), anchor="w").pack(fill="x", pady=(18, 8), padx=12)
        self.nav = {}
        for key, label, icon in self.PAGES:
            btn = NavButton(sidebar, key, label, icon, self.show_page)
            btn.pack(fill="x", padx=10, pady=1)
            self.nav[key] = btn

        foot = tk.Frame(sidebar, bg=BG_SOFT)
        foot.pack(side="bottom", fill="x", padx=14, pady=14)
        tk.Frame(foot, bg=BORDER, height=1).pack(fill="x", pady=(0, 10))
        self.sidebar_engine = tk.StringVar(value="")
        tk.Label(foot, textvariable=self.sidebar_engine, bg=BG_SOFT, fg=TEXT_FAINT,
                 font=ui_font(8), anchor="w", justify="left", wraplength=170).pack(fill="x")
        tk.Label(foot, text="Dark theme · YouTube palette", bg=BG_SOFT, fg=TEXT_FAINT,
                 font=ui_font(8), anchor="w").pack(fill="x", pady=(5, 0))

        right = tk.Frame(body, bg=BG)
        right.pack(side="left", fill="both", expand=True)
        self.pages_holder = tk.Frame(right, bg=BG)
        self.pages_holder.pack(fill="both", expand=True)
        self._build_status(right)

    def _build_status(self, parent):
        wrap = tk.Frame(parent, bg=BG)
        wrap.pack(side="bottom", fill="x")
        tk.Frame(wrap, bg=BORDER, height=1).pack(fill="x")
        pad = tk.Frame(wrap, bg=BG)
        pad.pack(fill="x", padx=20, pady=(11, 12))

        self.progress = ProgressBar(pad, height=7, bg=BG)
        self.progress.pack(fill="x", pady=(0, 8))

        row = tk.Frame(pad, bg=BG)
        row.pack(fill="x")
        self.state_var = tk.StringVar(value="Ready")
        self.speed_var = tk.StringVar(value="")
        self.eta_var = tk.StringVar(value="")
        self.state_label = tk.Label(row, textvariable=self.state_var, bg=BG, fg=TEXT_DIM,
                                    font=ui_font(9, "bold"), anchor="w")
        self.state_label.pack(side="left")
        tk.Label(row, textvariable=self.eta_var, bg=BG, fg=TEXT_FAINT,
                 font=ui_font(9), anchor="e").pack(side="right")
        tk.Label(row, textvariable=self.speed_var, bg=BG, fg=TEXT_FAINT,
                 font=ui_font(9), anchor="e").pack(side="right", padx=(0, 18))

        for text, cmd in (("Clear", self.clear_log), ("Copy", self.copy_log)):
            btn = tk.Label(row, text=text, bg=BG, fg=TEXT_FAINT, font=ui_font(9),
                           cursor="hand2")
            btn.pack(side="right", padx=(14, 0))
            btn.bind("<Button-1>", lambda e, c=cmd: c())
            btn.bind("<Enter>", lambda e, b=btn: b.configure(fg=TEXT))
            btn.bind("<Leave>", lambda e, b=btn: b.configure(fg=TEXT_FAINT))
        self.log_toggle = tk.Label(row, text="▸  Activity log", bg=BG, fg=TEXT_FAINT,
                                   font=ui_font(9, "bold"), cursor="hand2")
        self.log_toggle.pack(side="right", padx=(0, 18))
        self.log_toggle.bind("<Button-1>", lambda e: self.toggle_log())

        self.logbox = tk.Frame(pad, bg=BORDER)
        self.log = tk.Text(self.logbox, height=8, wrap="none", state="disabled",
                           relief="flat", bd=0, bg="#0b0b0b", fg="#c9c9c9",
                           insertbackground=TEXT, highlightthickness=0,
                           font=mono_font(9), padx=12, pady=8)
        vsb = ttk.Scrollbar(self.logbox, orient="vertical", command=self.log.yview,
                            style="Dark.Vertical.TScrollbar")
        self.log.configure(yscrollcommand=vsb.set)
        self.log.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        self.logbox.grid_rowconfigure(0, weight=1)
        self.logbox.grid_columnconfigure(0, weight=1)
        self.log.tag_configure("err", foreground="#ff7b8a")
        self.log.tag_configure("warn", foreground=YELLOW)
        self.log.tag_configure("ok", foreground="#7ee29a")
        self.log.tag_configure("dim", foreground=TEXT_FAINT)
        self.log.tag_configure("cmd", foreground=BLUE)
        self.log.configure(state="disabled")
        self.log.bind("<MouseWheel>", lambda e: self._log_wheel(e))
        self.log.bind("<Button-4>", lambda e: self._log_wheel(e, -1))
        self.log.bind("<Button-5>", lambda e: self._log_wheel(e, 1))

    def _log_wheel(self, event, direction=None):
        step = direction if direction is not None else (-1 if event.delta > 0 else 1)
        self.log.yview_scroll(step * 3, "units")
        return "break"

    def toggle_log(self):
        self._log_visible = not self._log_visible
        if self._log_visible:
            self.logbox.pack(fill="x", pady=(9, 0))
            self.log_toggle.configure(text="▾  Activity log", fg=TEXT_DIM)
        else:
            self.logbox.pack_forget()
            self.log_toggle.configure(text="▸  Activity log", fg=TEXT_FAINT)

    def copy_log(self):
        text = self.log.get("1.0", "end-1c")
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        self._toast("Log copied to clipboard", "ok")

    def clear_log(self):
        self.log.configure(state="normal")
        self.log.delete("1.0", "end")
        self.log.configure(state="disabled")

    def _toast(self, text, kind="info"):
        Toast(self.pages_holder, text, kind)

    # ================= pages =================

    def _build_pages(self):
        self.pages = {}
        builders = {
            "download": self._page_download,
            "output": self._page_output,
            "subs": self._page_subs,
            "advanced": self._page_advanced,
            "command": self._page_command,
        }
        for key, _label, _icon in self.PAGES:
            frame = tk.Frame(self.pages_holder, bg=BG)
            scroll, inner = self._scroll_page(frame)
            builders[key](inner)
            self.pages[key] = (frame, scroll)
        self.show_page("download")

    def _scroll_page(self, frame):
        scroll = ScrollArea(frame, bg=BG)
        scroll.pack(fill="both", expand=True)
        inner = scroll.inner
        tk.Frame(inner, bg=BG, height=18).pack(fill="x")
        holder = tk.Frame(inner, bg=BG)
        holder.pack(fill="both", expand=True, padx=20)
        tk.Frame(inner, bg=BG, height=26).pack(fill="x")
        return scroll, holder

    def show_page(self, key):
        if key not in self.pages:
            return
        frame, scroll = self.pages[key]
        for other, (f, _s) in self.pages.items():
            if other != key:
                f.pack_forget()
        frame.pack(fill="both", expand=True)
        scroll.to_top()
        for nav_key, btn in self.nav.items():
            btn.set_active(nav_key == key)
        self._page_key = key

    # ---- small helpers -------------------------------------------------

    def _lbl(self, parent, text, size=9, weight="bold", color=None, **kw):
        return tk.Label(parent, text=text, bg=parent_bg(parent),
                        fg=color or TEXT_DIM, font=ui_font(size, weight),
                        anchor="w", **kw)

    def _hint(self, parent, text, size=9, **kw):
        return tk.Label(parent, text=text, bg=parent_bg(parent), fg=TEXT_FAINT,
                        font=ui_font(size), anchor="w", justify="left", **kw)

    def _sep(self, parent, pady=(12, 12)):
        f = tk.Frame(parent, bg=BORDER, height=1)
        f.pack(fill="x", pady=pady)
        return f

    def _combo(self, parent, values, width=None):
        cb = ttk.Combobox(parent, values=list(values), state="readonly",
                          style="Dark.TCombobox")
        if width:
            cb.configure(width=width)
        return cb

    # ---- Download page -------------------------------------------------

    def _page_download(self, holder):
        # Links ---------------------------------------------------------
        card = Card(holder, title="Links",
                    subtitle="One URL per line — single videos, playlists, channels, or a list of links.")
        card.pack(fill="x", pady=(0, 14))
        RoundedButton(card.header_right, "Paste", self.paste_urls, kind="ghost",
                      height=28, font_size=9, padx=12, bg=SURFACE).pack(side="left")
        RoundedButton(card.header_right, "Clear", lambda: self._clear(self.urls), kind="ghost",
                      height=28, font_size=9, padx=12, bg=SURFACE).pack(side="left", padx=(6, 0))
        self.urls = TextField(card.content, height=5,
                              placeholder="https://www.youtube.com/watch?v=…")
        self.urls.pack(fill="x")

        # Quality -------------------------------------------------------
        card = Card(holder, title="Quality & format")
        card.pack(fill="x", pady=(0, 14))
        self.quality = ChoiceGroup(card.content, QUALITY_CHIPS, value=DEFAULTS["quality"],
                                   command=lambda v: self._on_change(), bg=SURFACE)
        self.quality.pack(fill="x")

        self._sep(card.content, pady=(14, 12))
        row = tk.Frame(card.content, bg=SURFACE)
        row.pack(fill="x")
        self._lbl(row, "CONTAINER", size=8).grid(row=0, column=0, sticky="w", pady=(0, 4))
        self._lbl(row, "RE-ENCODE TO", size=8).grid(row=0, column=1, sticky="w",
                                                    padx=(24, 0), pady=(0, 4))
        self._lbl(row, "AUDIO QUALITY", size=8).grid(row=0, column=2, sticky="w",
                                                     padx=(24, 0), pady=(0, 4))
        self.merge_fmt = ChoiceGroup(row, [(c.upper(), c) for c in CONTAINERS],
                                     value=DEFAULTS["merge_format"],
                                     command=lambda v: self._on_change(), bg=SURFACE,
                                     stretch=False, height=34)
        self.merge_fmt.grid(row=1, column=0, sticky="w")
        self.remux = self._combo(row, REMUX_TARGETS, width=8)
        self.remux.grid(row=1, column=1, sticky="w", padx=(24, 0))
        self.audio_note = self._hint(row, "")
        self.audio_note.grid(row=1, column=2, sticky="w", padx=(24, 0))
        self._hint(card.content,
                   "MKV keeps every stream lossless · MP4 is the most compatible · "
                   "audio-only entries extract MP3/M4A with ffmpeg.",
                   pady=10).pack(fill="x", pady=(12, 0))

        # Playlist ------------------------------------------------------
        card = Card(holder, title="Playlist")
        card.pack(fill="x", pady=(0, 14))
        self.playlist_mode = ChoiceGroup(
            card.content,
            [("Single video", "Single video only"),
             ("Full playlist", "Full playlist"),
             ("Custom range", "Custom range (1-10, 13, 20-25)")],
            value=DEFAULTS["playlist_mode"], command=lambda v: self._on_playlist_change(),
            bg=SURFACE)
        self.playlist_mode.pack(fill="x", pady=(0, 12))
        sub = tk.Frame(card.content, bg=SURFACE)
        sub.pack(fill="x")
        self._lbl(sub, "ITEM RANGE", size=8).pack(side="left", padx=(0, 10))
        self.playlist_items = EntryField(sub, placeholder="1-10, 13, 20-25", width=26)
        self.playlist_items.pack(side="left")
        self.playlist_hint = self._hint(sub, "   used with “Custom range”")
        self.playlist_hint.pack(side="left", padx=(8, 0))

        # Actions -------------------------------------------------------
        actions = tk.Frame(holder, bg=BG)
        actions.pack(fill="x", pady=(2, 10))
        self.btn_start2 = RoundedButton(actions, "Start download", self.start,
                                        kind="primary", glyph="⬇", height=46,
                                        width=210, font_size=11, bg=BG)
        self.btn_start2.pack(side="left")
        RoundedButton(actions, "Open downloads folder", self.open_folder, kind="secondary",
                      height=46, bg=BG).pack(side="left", padx=(10, 0))
        tk.Label(actions, text="Ctrl+Enter to start  ·  Esc to stop", bg=BG,
                 fg=TEXT_FAINT, font=ui_font(9)).pack(side="right")

    def _page_output(self, holder):
        card = Card(holder, title="Destination",
                    subtitle="Where finished files land, and how they are named.")
        card.pack(fill="x", pady=(0, 14))
        row = tk.Frame(card.content, bg=SURFACE)
        row.pack(fill="x")
        self._lbl(row, "OUTPUT FOLDER", size=8).grid(row=0, column=0, sticky="w", pady=(0, 4))
        self.outdir = EntryField(row)
        self.outdir.grid(row=1, column=0, sticky="ew")
        RoundedButton(row, "Browse", self.browse_outdir, kind="secondary", height=34,
                      font_size=9, bg=SURFACE, width=90).grid(row=1, column=1, padx=(8, 0))
        row.grid_columnconfigure(0, weight=1)

        tplrow = tk.Frame(card.content, bg=SURFACE)
        tplrow.pack(fill="x", pady=(14, 0))
        self._lbl(tplrow, "FILENAME TEMPLATE", size=8).grid(row=0, column=0, sticky="w", pady=(0, 4))
        self.template = EntryField(tplrow, mono=True)
        self.template.grid(row=1, column=0, sticky="ew")
        RoundedButton(tplrow, "Reset", self.reset_template, kind="ghost", height=34,
                      font_size=9, bg=SURFACE, padx=12).grid(row=1, column=1, padx=(8, 0))
        tplrow.grid_columnconfigure(0, weight=1)
        self._hint(card.content,
                   "%(title)s  ·  %(id)s  ·  %(ext)s  ·  %(uploader)s  ·  %(upload_date)s  ·  "
                   "%(playlist_title)s  ·  %(resolution)s").pack(fill="x", pady=(9, 0))

        # File handling ------------------------------------------------
        card = Card(holder, title="File handling")
        card.pack(fill="x", pady=(0, 14))
        grid = tk.Frame(card.content, bg=SURFACE)
        grid.pack(fill="x")
        self.restrict_filenames = self._add_check(grid, "Safe ASCII-only filenames", "restrict_filenames", 0, 0)
        self.embed_metadata = self._add_check(grid, "Embed metadata", "embed_metadata", 0, 1)
        self.embed_thumbnail = self._add_check(grid, "Embed thumbnail", "embed_thumbnail", 1, 0)
        self.write_thumbnail = self._add_check(grid, "Save thumbnail separately", "write_thumbnail", 1, 1)
        self.embed_chapters = self._add_check(grid, "Embed chapters", "embed_chapters", 2, 0)
        self.no_mtime = self._add_check(grid, "Keep file date = download date", "no_mtime", 2, 1)
        grid.grid_columnconfigure(0, weight=1, uniform="fh")
        grid.grid_columnconfigure(1, weight=1, uniform="fh")

        # Archive ------------------------------------------------------
        card = Card(holder, title="Skip already downloaded",
                    subtitle="Record finished items in an archive file and never fetch them again.")
        card.pack(fill="x", pady=(0, 18))
        chk = tk.Frame(card.content, bg=SURFACE)
        chk.pack(fill="x")
        self.skip_archived = self._add_check(chk, "Use a download archive",
                                             "skip_archived", 0, 0)
        arow = tk.Frame(card.content, bg=SURFACE)
        arow.pack(fill="x", pady=(10, 0))
        self._lbl(arow, "ARCHIVE FILE", size=8).pack(side="left", padx=(0, 10))
        self.archive = EntryField(arow, placeholder="empty = archive.txt inside the output folder")
        self.archive.pack(side="left", fill="x", expand=True)
        RoundedButton(arow, "Browse", self.browse_archive, kind="secondary", height=34,
                      font_size=9, bg=SURFACE, width=90).pack(side="left", padx=(8, 0))

    def _page_subs(self, holder):
        card = Card(holder, title="Subtitles",
                    subtitle="Download caption tracks, convert them, or burn them into the file.")
        card.pack(fill="x", pady=(0, 14))
        grid = tk.Frame(card.content, bg=SURFACE)
        grid.pack(fill="x")
        self.write_subs = self._add_check(grid, "Write original subtitles", "write_subs", 0, 0)
        self.write_auto_subs = self._add_check(grid, "Write auto-generated subtitles", "write_auto_subs", 0, 1)
        self.embed_subs = self._add_check(grid, "Embed subtitles into the media file", "embed_subs", 1, 0)
        grid.grid_columnconfigure(0, weight=1, uniform="sub")
        grid.grid_columnconfigure(1, weight=1, uniform="sub")

        self._sep(card.content, pady=(14, 12))
        row = tk.Frame(card.content, bg=SURFACE)
        row.pack(fill="x")
        self._lbl(row, "LANGUAGES", size=8).grid(row=0, column=0, sticky="w", pady=(0, 4))
        self._lbl(row, "FORMAT", size=8).grid(row=0, column=1, sticky="w", padx=(24, 0), pady=(0, 4))
        self.sub_langs = EntryField(row)
        self.sub_langs.grid(row=1, column=0, sticky="ew")
        self.sub_format = self._combo(row, SUB_FORMATS, width=8)
        self.sub_format.grid(row=1, column=1, sticky="w", padx=(24, 0))
        row.grid_columnconfigure(0, weight=1)
        self._hint(card.content,
                   "Language codes: en, zh, ja, de, es, fr …   wildcards: en.*   "
                   "“all” grabs every track. Embedding needs a video container and ffmpeg."
                   ).pack(fill="x", pady=(12, 0))

        card = Card(holder, title="Good to know")
        card.pack(fill="x", pady=(0, 18))
        for text in ("Embedding subtitles forces MP4/MKV output — it is skipped for audio-only picks.",
                     "Auto-generated captions are the ones marked “auto” on the site; they can be out of sync.",
                     "“srt” is the most compatible format for players; “best” keeps the site's own format."):
            line = tk.Frame(card.content, bg=SURFACE)
            line.pack(fill="x", pady=2)
            tk.Label(line, text="•", bg=SURFACE, fg=RED, font=ui_font(10, "bold")).pack(side="left")
            tk.Label(line, text=text, bg=SURFACE, fg=TEXT_DIM, font=ui_font(9),
                     anchor="w", justify="left").pack(side="left", padx=(8, 0))

    def _page_advanced(self, holder):
        # Authentication ----------------------------------------------
        card = Card(holder, title="Authentication",
                    subtitle="Required for age-restricted, private or member-only videos.")
        card.pack(fill="x", pady=(0, 14))
        row = tk.Frame(card.content, bg=SURFACE)
        row.pack(fill="x")
        self._lbl(row, "COOKIES FILE (NETSCAPE .TXT)", size=8).grid(row=0, column=0, sticky="w", pady=(0, 4))
        self._lbl(row, "OR READ FROM BROWSER", size=8).grid(row=0, column=1, sticky="w",
                                                            padx=(24, 0), pady=(0, 4))
        self.cookies = EntryField(row, placeholder="C:\\path\\to\\cookies.txt")
        self.cookies.grid(row=1, column=0, sticky="ew")
        RoundedButton(row, "Browse", self.browse_cookies, kind="secondary", height=34,
                      font_size=9, bg=SURFACE, width=84).grid(row=1, column=1, padx=(8, 0))
        self.cookies_from_browser = self._combo(row, BROWSERS, width=12)
        self.cookies_from_browser.grid(row=1, column=2, sticky="w", padx=(16, 0))
        row.grid_columnconfigure(0, weight=1)
        self._hint(card.content,
                   "Reading from a browser must be done with the browser closed on some systems, "
                   "and the cookie file wins if both are set.").pack(fill="x", pady=(10, 0))

        # Network ------------------------------------------------------
        card = Card(holder, title="Network & performance")
        card.pack(fill="x", pady=(0, 14))
        grid = tk.Frame(card.content, bg=SURFACE)
        grid.pack(fill="x")
        specs = [
            ("PROXY", "proxy", "http://host:port or socks5://host:port"),
            ("RATE LIMIT", "rate_limit", "e.g. 2M (empty = unlimited)"),
            ("CONCURRENT FRAGMENTS", "concurrent_fragments", "1–64, empty = default"),
            ("RETRIES", "retries", "whole download retries"),
            ("FRAGMENT RETRIES", "fragment_retries", "per-fragment retries"),
            ("SLEEP BETWEEN REQUESTS", "sleep_interval", "seconds, e.g. 1.5"),
        ]
        for i, (label, attr, ph) in enumerate(specs):
            r, c = divmod(i, 2)
            box = tk.Frame(grid, bg=SURFACE)
            box.grid(row=r, column=c, sticky="ew", padx=(0, 18) if c == 0 else (0, 0), pady=(0, 12))
            self._lbl(box, label, size=8).pack(fill="x", pady=(0, 4))
            field = EntryField(box, placeholder=ph)
            field.pack(fill="x")
            setattr(self, attr, field)
        grid.grid_columnconfigure(0, weight=1, uniform="net")
        grid.grid_columnconfigure(1, weight=1, uniform="net")

        # Clip ---------------------------------------------------------
        card = Card(holder, title="Clip a section")
        card.pack(fill="x", pady=(0, 14))
        row = tk.Frame(card.content, bg=SURFACE)
        row.pack(fill="x")
        box = tk.Frame(row, bg=SURFACE)
        box.pack(side="left", fill="x", expand=True)
        self._lbl(box, "START TIME", size=8).pack(fill="x", pady=(0, 4))
        self.start_time = EntryField(box, placeholder="0 or 00:01:30")
        self.start_time.pack(fill="x")
        box = tk.Frame(row, bg=SURFACE)
        box.pack(side="left", fill="x", expand=True, padx=(18, 0))
        self._lbl(box, "END TIME", size=8).pack(fill="x", pady=(0, 4))
        self.end_time = EntryField(box, placeholder="empty = until the end")
        self.end_time.pack(fill="x")
        self._hint(card.content,
                   "Uses ffmpeg to cut the section — the download itself still covers the parts needed."
                   ).pack(fill="x", pady=(10, 0))

        # SponsorBlock -------------------------------------------------
        card = Card(holder, title="SponsorBlock",
                    subtitle="Uses community-marked segments (sponsors, intros, self-promos…).")
        card.pack(fill="x", pady=(0, 14))
        row = tk.Frame(card.content, bg=SURFACE)
        row.pack(fill="x")
        self._lbl(row, "ACTION", size=8).grid(row=0, column=0, sticky="w", pady=(0, 4))
        self._lbl(row, "CATEGORIES", size=8).grid(row=0, column=1, sticky="w",
                                                  padx=(24, 0), pady=(0, 4))
        self.sponsor_action = self._combo(row, SPONSOR_ACTIONS, width=14)
        self.sponsor_action.grid(row=1, column=0, sticky="w")
        self.sponsor_cats = EntryField(row, mono=True)
        self.sponsor_cats.grid(row=1, column=1, sticky="ew", padx=(24, 0))
        row.grid_columnconfigure(1, weight=1)
        self._hint(card.content,
                   "Defaults: sponsor, selfpromo, interaction, intro, outro, preview, filler."
                   ).pack(fill="x", pady=(10, 0))

        # Extra args ---------------------------------------------------
        card = Card(holder, title="Extra CLI arguments",
                    subtitle="Raw passthrough — any yt-dlp flag works here.")
        card.pack(fill="x", pady=(0, 18))
        self.extra_args = EntryField(card.content, mono=True,
                                     placeholder="--no-part --windows-filenames --sleep-requests 1")
        self.extra_args.pack(fill="x")

    def _page_command(self, holder):
        card = Card(holder, title="Exact command",
                    subtitle="Live preview of what will be executed. Copy it to run in a terminal anywhere.")
        card.pack(fill="x", pady=(0, 14))
        self.cmd_preview = tk.Text(card.content, height=9, wrap="word", relief="flat",
                                   bd=0, bg="#0b0b0b", fg="#c9c9c9", state="disabled",
                                   highlightthickness=0, font=mono_font(10),
                                   padx=12, pady=10)
        self.cmd_preview.pack(fill="x")
        self.cmd_preview.tag_configure("err", foreground="#ff7b8a")
        row = tk.Frame(card.content, bg=SURFACE)
        row.pack(fill="x", pady=(10, 0))
        RoundedButton(row, "Copy command", self.copy_command, kind="primary", height=36,
                      font_size=9, bg=SURFACE, padx=16).pack(side="left")
        RoundedButton(row, "Open manual", self.open_manual, kind="ghost", height=36,
                      font_size=9, bg=SURFACE).pack(side="left", padx=(8, 0))

        # Environment ---------------------------------------------------
        card = Card(holder, title="Environment",
                    subtitle="Everything the downloader needs, detected on this machine.")
        card.pack(fill="x", pady=(0, 18))
        RoundedButton(card.header_right, "Re-check", self.recheck_engine, kind="ghost",
                      height=28, font_size=9, padx=12, bg=SURFACE).pack(side="left")
        self.env_rows = tk.Frame(card.content, bg=SURFACE)
        self.env_rows.pack(fill="x")

    def _env_row(self, parent, label, value, ok):
        row = tk.Frame(parent, bg=SURFACE)
        row.pack(fill="x", pady=3)
        dot = tk.Canvas(row, width=12, height=12, bg=SURFACE, highlightthickness=0, bd=0)
        dot.pack(side="left")
        dot.create_oval(2, 2, 10, 10, fill=GREEN if ok else RED,
                        outline=GREEN if ok else RED)
        tk.Label(row, text=label, bg=SURFACE, fg=TEXT, font=ui_font(9, "bold"),
                 width=12, anchor="w").pack(side="left", padx=(8, 0))
        tk.Label(row, text=value, bg=SURFACE, fg=TEXT_DIM if ok else "#ff8ba0",
                 font=ui_font(9), anchor="w", justify="left").pack(side="left")

    def recheck_engine(self):
        global _JS_RUNTIME_ARGS
        _JS_RUNTIME_ARGS = None  # re-scan PATH for deno/node
        self._refresh_engine()
        self._engine_state = resolve_yt_dlp()
        self._refresh_engine()
        prefix, _root, _label = self._engine_state
        self._toast("Engine ready" if prefix else "Engine still missing", "ok" if prefix else "error")

    def _refresh_engine(self):
        prefix, engine_root, label = resolve_yt_dlp()
        self._engine_state = (prefix, engine_root, label)
        if prefix is None:
            self.pill.set_text("Engine missing", RED)
            self.sidebar_engine.set("yt-dlp not found — check the Command tab")
        else:
            if label.startswith("checkout:"):
                self.pill.set_text("Engine ready", GREEN)
                self.sidebar_engine.set("Engine: local checkout")
            else:
                self.pill.set_text("System yt-dlp", GREEN)
                self.sidebar_engine.set("Engine: yt-dlp on PATH")
        self.update_preview()
        if hasattr(self, "env_rows"):
            for child in self.env_rows.winfo_children():
                child.destroy()
            self._env_row(self.env_rows, "yt-dlp",
                          label or "not found — clone it next to this app, or pip install yt-dlp",
                          prefix is not None)
            ff = which("ffmpeg") or which("ffmpeg.exe")
            self._env_row(self.env_rows, "ffmpeg",
                          ff or "not found — needed for merges, audio, thumbnails, clipping",
                          bool(ff))
            js = js_runtime_args()
            self._env_row(self.env_rows, "JS runtime",
                          " ".join(js) if js else "none — YouTube needs Node.js or Deno",
                          bool(js))
            self._env_row(self.env_rows, "Python",
                          _engine_python() or "not found", bool(_engine_python()))
            self._env_row(self.env_rows, "Config",
                          CONFIG_PATH, os.path.isfile(CONFIG_PATH))

    # ---- checkbox factory ----------------------------------------------

    def _add_check(self, parent, text, attr, row, col):
        widget = Check(parent, text=text, value=bool(DEFAULTS.get(attr)),
                       command=lambda v=None: self._on_change())
        widget.grid(row=row, column=col, sticky="w", pady=3,
                    padx=(0, 18) if col == 0 else (0, 0))
        setattr(self, attr, widget)
        return widget


    # ================= settings persistence =================

    def _apply_defaults(self):
        self.quality.set(DEFAULTS["quality"])
        self.merge_fmt.set(DEFAULTS["merge_format"])
        self.remux.set(DEFAULTS["remux"])
        self.playlist_mode.set(DEFAULTS["playlist_mode"])
        self.outdir.set(DEFAULT_OUTDIR)
        self.template.set(DEFAULTS["template"])
        self.sub_langs.set(DEFAULTS["sub_langs"])
        self.sub_format.set(DEFAULTS["sub_format"])
        self.cookies_from_browser.set(DEFAULTS["cookies_from_browser"])
        self.sponsor_action.set(DEFAULTS["sponsor_action"])
        self.sponsor_cats.set(DEFAULTS["sponsor_cats"])
        self.extra_args.set("")
        self.urls.set("")

    def collect(self):
        cfg = {
            "quality": self.quality.get(),
            "merge_format": self.merge_fmt.get(),
            "remux": self.remux.get(),
            "playlist_mode": self.playlist_mode.get(),
            "playlist_items": self.playlist_items.get().strip(),
            "outdir": self.outdir.get().strip(),
            "template": self.template.get().strip(),
            "sub_langs": self.sub_langs.get().strip(),
            "sub_format": self.sub_format.get(),
            "cookies": self.cookies.get().strip(),
            "cookies_from_browser": self.cookies_from_browser.get(),
            "proxy": self.proxy.get().strip(),
            "start_time": self.start_time.get().strip(),
            "end_time": self.end_time.get().strip(),
            "rate_limit": self.rate_limit.get().strip(),
            "concurrent_fragments": self.concurrent_fragments.get().strip(),
            "retries": self.retries.get().strip(),
            "fragment_retries": self.fragment_retries.get().strip(),
            "sleep_interval": self.sleep_interval.get().strip(),
            "sponsor_action": self.sponsor_action.get(),
            "sponsor_cats": self.sponsor_cats.get().strip(),
            "archive": self.archive.get().strip(),
            "extra_args": self.extra_args.get().strip(),
            "urls": self.urls.get(),
        }
        for key in ("restrict_filenames", "embed_metadata", "embed_thumbnail",
                    "embed_chapters", "write_thumbnail", "no_mtime", "write_subs",
                    "write_auto_subs", "embed_subs", "skip_archived"):
            cfg[key] = bool(getattr(self, key).get())
        cfg["subs_srt"] = cfg.get("sub_format") == "srt"
        return cfg

    def save_config(self):
        self._save_job = None
        try:
            with open(CONFIG_PATH, "w", encoding="utf-8") as fh:
                json.dump(self.collect(), fh, indent=2, ensure_ascii=False)
        except OSError as exc:
            self._log_append(f"[config save failed: {exc}]\n", "warn")

    def _schedule_save(self):
        if self._save_job is not None:
            try:
                self.root.after_cancel(self._save_job)
            except (tk.TclError, ValueError):
                pass
        self._save_job = self.root.after(600, self.save_config)

    def _load_config(self):
        if not os.path.isfile(CONFIG_PATH):
            return
        try:
            with open(CONFIG_PATH, encoding="utf-8") as fh:
                cfg = json.load(fh)
        except (OSError, ValueError):
            return
        if not isinstance(cfg, dict):
            return
        get = lambda key: cfg.get(key, DEFAULTS.get(key, ""))
        try:
            self.quality.set(str(get("quality")))
            self.merge_fmt.set(str(get("merge_format")))
            self.remux.set(str(get("remux")) if cfg.get("remux") in REMUX_TARGETS else "Off")
            mode = str(get("playlist_mode"))
            if mode not in PLAYLIST_MODES:
                mode = DEFAULTS["playlist_mode"]
            self.playlist_mode.set(mode)
            self.playlist_items.set(get("playlist_items"))
            self.outdir.set(get("outdir") or DEFAULT_OUTDIR)
            self.template.set(get("template") or DEFAULTS["template"])
            self.sub_langs.set(get("sub_langs"))
            fmt = str(get("sub_format") or "")
            if fmt not in SUB_FORMATS:
                fmt = "srt" if cfg.get("subs_srt", True) else "best"
            self.sub_format.set(fmt)
            browser = str(get("cookies_from_browser") or "Off")
            self.cookies_from_browser.set(browser if browser in BROWSERS else "Off")
            self.cookies.set(get("cookies"))
            self.proxy.set(get("proxy"))
            self.start_time.set(get("start_time"))
            self.end_time.set(get("end_time"))
            self.rate_limit.set(get("rate_limit"))
            self.concurrent_fragments.set(get("concurrent_fragments"))
            self.retries.set(get("retries"))
            self.fragment_retries.set(get("fragment_retries"))
            self.sleep_interval.set(get("sleep_interval"))
            sponsor = str(get("sponsor_action") or "Off")
            self.sponsor_action.set(sponsor if sponsor in SPONSOR_ACTIONS else "Off")
            self.sponsor_cats.set(get("sponsor_cats") or DEFAULT_SPONSOR_CATS)
            self.archive.set(get("archive"))
            self.extra_args.set(get("extra_args"))
            for key in ("restrict_filenames", "embed_metadata", "embed_thumbnail",
                        "embed_chapters", "write_thumbnail", "no_mtime", "write_subs",
                        "write_auto_subs", "embed_subs", "skip_archived"):
                getattr(self, key).set(bool(cfg.get(key, DEFAULTS.get(key, False))))
            self.urls.set(get("urls"))
        except (tk.TclError, KeyError, ValueError, TypeError) as exc:
            self._log_append(f"[config load skipped: {exc}]\n", "warn")

    def _bind_changes(self):
        for combo in (self.remux, self.sub_format, self.cookies_from_browser,
                      self.sponsor_action):
            combo.bind("<<ComboboxSelected>>", self._on_change)
        for field in (self.playlist_items, self.outdir, self.template, self.sub_langs,
                      self.cookies, self.proxy, self.start_time, self.end_time,
                      self.rate_limit, self.concurrent_fragments, self.retries,
                      self.fragment_retries, self.sleep_interval, self.sponsor_cats,
                      self.archive, self.extra_args):
            field.bind_entry("<FocusOut>", self._on_change)
            field.bind_entry("<Return>", self._on_change)
            field.bind_entry("<KeyRelease>", self._on_typing)
        self.urls.text.bind("<KeyRelease>", self._on_typing)
        self.urls.text.bind("<FocusOut>", self._on_change)

        # global shortcuts
        self.root.bind("<Control-Return>", self.start)
        self.root.bind("<Control-KP_Enter>", self.start)
        self.root.bind("<Escape>", lambda e: self.stop())
        for i, (key, _label, _icon) in enumerate(self.PAGES, start=1):
            self.root.bind(f"<Control-Key-{i}>", lambda e, k=key: self.show_page(k))
        self.root.bind("<Control-l>", lambda e: self.toggle_log())

    def _on_typing(self, event=None):
        self.update_preview()
        self._schedule_save()
        if event is not None and event.keysym in ("Up", "Down", "Left", "Right",
                                                  "Tab", "Shift_L", "Shift_R"):
            return
        self._sync_states()

    def _on_change(self, event=None):
        self.update_preview()
        self._sync_states()
        self._schedule_save()

    def _on_playlist_change(self):
        self._sync_states()
        self._on_change()

    def _sync_states(self):
        """Enable/disable dependent widgets and refresh hints."""
        mode = self.playlist_mode.get()
        custom = bool(mode) and mode.startswith("Custom range")
        self.playlist_items.set_enabled(custom)
        if hasattr(self, "playlist_hint"):
            self.playlist_hint.configure(
                fg=TEXT_FAINT if custom else "#4d4d4d")
        audio = self.quality.get() in AUDIO_QUALITIES
        if hasattr(self, "audio_note"):
            self.audio_note.configure(text="audio codec is chosen above" if audio
                                      else "Video quality applies")
        if hasattr(self, "archive"):
            self.archive.set_enabled(bool(self.skip_archived.get()))

    # ================= command preview =================

    def _preview_cmd(self):
        """Return the full command list for the current settings (or None)."""
        prefix = self._engine_state[0]
        if prefix is None:
            return None
        cfg = self.collect()
        urls = [line.strip() for line in cfg["urls"].splitlines() if line.strip()]
        try:
            return prefix + build_args(cfg, urls if urls else ["<PASTE_A_URL>"])
        except ValueError:
            return None

    def update_preview(self):
        if not hasattr(self, "cmd_preview"):
            return
        self.cmd_preview.configure(state="normal")
        self.cmd_preview.delete("1.0", "end")
        cmd = self._preview_cmd()
        prefix, engine_root, label = self._engine_state
        if cmd is None:
            if prefix is None:
                self.cmd_preview.insert(
                    "1.0",
                    "yt-dlp not found.\n\n"
                    "Fix: clone https://github.com/yt-dlp/yt-dlp into the folder next to this app,\n"
                    "set the YTDLP_HOME environment variable, or install yt-dlp on PATH (pip install yt-dlp).")
            else:
                try:
                    build_args(self.collect(), ["<PASTE_A_URL>"])
                    text = "The command could not be built — check the Advanced tab."
                except ValueError as exc:
                    text = "Invalid setting\n\n" + str(exc)
                self.cmd_preview.insert("1.0", text, "err")
            self.cmd_preview.configure(state="disabled")
            self.btn_start.set_enabled(False)
            self.btn_start2.set_enabled(False)
            return
        text = ""
        if engine_root:
            text += f"# working directory: {engine_root}\n"
        text += " ".join(_shell_quote(x) for x in cmd)
        self.cmd_preview.insert("1.0", text)
        self.cmd_preview.configure(state="disabled")
        if not self._running:
            self.btn_start.set_enabled(True)
            self.btn_start2.set_enabled(True)

    # ================= helper actions =================

    def paste_urls(self):
        try:
            clip = self.root.clipboard_get()
        except tk.TclError:
            self._toast("Clipboard is empty", "error")
            return
        if not clip.strip():
            self._toast("Clipboard is empty", "error")
            return
        current = self.urls.get().strip()
        if current:
            self.urls.set(current.rstrip() + "\n" + clip.strip())
        else:
            self.urls.set(clip.strip())
        self._on_change()
        self._toast("Pasted from clipboard", "ok")

    def _clear(self, field):
        field.set("")
        self._on_change()

    def reset_template(self):
        self.template.set(DEFAULTS["template"])
        self._on_change()

    def browse_outdir(self):
        start = self.outdir.get() or os.path.expanduser("~")
        folder = filedialog.askdirectory(initialdir=start, title="Choose the output folder")
        if folder:
            self.outdir.set(folder)
            self._on_change()

    def browse_cookies(self):
        path = filedialog.askopenfilename(
            title="Select cookies file (Netscape .txt)",
            initialdir=os.path.expanduser("~"),
            filetypes=[("Cookies (Netscape format)", "*.txt"), ("All files", "*")])
        if path:
            self.cookies.set(path)
            self._on_change()

    def browse_archive(self):
        path = filedialog.asksaveasfilename(
            title="Download archive file", defaultextension=".txt",
            initialdir=self.outdir.get() or os.path.expanduser("~"),
            filetypes=[("Text file", "*.txt"), ("All files", "*")])
        if path:
            self.archive.set(path)
            self._on_change()

    def open_folder(self):
        folder = self.outdir.get().strip() or DEFAULT_OUTDIR
        try:
            os.makedirs(folder, exist_ok=True)
        except OSError as exc:
            self.error_dialog("Output folder", str(exc))
            return
        try:
            if sys.platform == "win32":
                os.startfile(folder)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", folder])
            else:
                subprocess.Popen(["xdg-open", folder])
        except (OSError, AttributeError) as exc:
            self.error_dialog("Output folder", f"{folder}\n\n{exc}")

    def open_manual(self):
        import webbrowser
        webbrowser.open("https://github.com/yt-dlp/yt-dlp/wiki/FAQ")

    def copy_command(self):
        cmd = self._preview_cmd()
        if cmd is None:
            self._toast("No command to copy yet", "error")
            return
        self.root.clipboard_clear()
        self.root.clipboard_append(" ".join(_shell_quote(x) for x in cmd))
        self._toast("Command copied to clipboard", "ok")

    # ================= dialogs (dark) =================

    def _center_over_parent(self, win, width, height):
        self.root.update_idletasks()
        px, py = self.root.winfo_rootx(), self.root.winfo_rooty()
        pw, ph = self.root.winfo_width(), self.root.winfo_height()
        x = px + max((pw - width) // 2, 0)
        y = py + max((ph - height) // 3, 0)
        win.geometry(f"{width}x{height}+{x}+{y}")

    def _dialog(self, title, message, kind="info", buttons=(("OK", True),)):
        win = tk.Toplevel(self.root)
        win.withdraw()
        win.title(title)
        win.configure(bg=SURFACE)
        win.transient(self.root)
        win.resizable(False, False)
        accent = {"info": BLUE, "error": RED, "warn": YELLOW, "ok": GREEN}.get(kind, BLUE)
        tk.Frame(win, bg=accent, height=3).pack(fill="x")
        pad = tk.Frame(win, bg=SURFACE)
        pad.pack(fill="both", expand=True, padx=22, pady=18)
        tk.Label(pad, text=title, bg=SURFACE, fg=TEXT, font=ui_font(12, "bold"),
                 anchor="w", justify="left").pack(fill="x")
        tk.Label(pad, text=message, bg=SURFACE, fg=TEXT_DIM, font=ui_font(10),
                 anchor="w", justify="left", wraplength=430).pack(fill="x", pady=(8, 18))
        row = tk.Frame(pad, bg=SURFACE)
        row.pack(fill="x")
        result = {"value": None}
        for label, value in reversed(buttons):
            kind_btn = "primary" if value is True else ("danger" if value is False else "secondary")
            btn = RoundedButton(row, label, lambda v=value: (result.__setitem__("value", v),
                                                            win.destroy()),
                                kind=kind_btn, height=36, bg=SURFACE, padx=18)
            btn.pack(side="right", padx=(8, 0))
        win.update_idletasks()
        self._center_over_parent(win, min(max(win.winfo_reqwidth(), 380), 520),
                                 win.winfo_reqheight())
        win.deiconify()
        win.grab_set()
        win.focus_force()
        win.bind("<Escape>", lambda e: (result.__setitem__("value", None), win.destroy()))
        primary = next((v for _l, v in reversed(buttons) if v is True),
                       buttons[0][1] if buttons else None)
        win.bind("<Return>", lambda e: (result.__setitem__("value", primary), win.destroy()))
        self.root.wait_window(win)
        return result["value"]

    def error_dialog(self, title, message):
        self._dialog(title, message, "error")

    def info_dialog(self, title, message):
        self._dialog(title, message, "info")

    def ask_dialog(self, title, message):
        return self._dialog(title, message, "warn",
                            (("Cancel", False), ("Continue", True))) is True

    # ================= download lifecycle =================

    def start(self, event=None):
        if self._proc is not None and self._proc.poll() is None:
            self._toast("A download is already running", "error")
            return
        urls = [line.strip() for line in self.urls.get().splitlines() if line.strip()]
        if not urls:
            self.show_page("download")
            self.error_dialog("No links yet",
                              "Paste at least one URL first — one per line.")
            return
        cmd = self._preview_cmd()
        prefix, engine_root, label = self._engine_state if self._engine_state[0] else resolve_yt_dlp()
        if prefix is None:
            self.show_page("command")
            self.error_dialog(
                "yt-dlp not found",
                "No yt-dlp checkout was found next to this folder, and no yt-dlp on PATH.\n\n"
                "Fix:\n  git clone --depth 1 https://github.com/yt-dlp/yt-dlp   "
                "(parent folder of yt-dlp-gui)\n  or:\n  pip install yt-dlp")
            return
        if cmd is None:
            try:
                build_args(self.collect(), ["<url>"])
            except ValueError as exc:
                self.show_page("advanced")
                self.error_dialog("Invalid setting", str(exc))
                return
            self.error_dialog("Cannot start", "The command could not be built. Check the Command tab.")
            return
        cmd = list(cmd)
        if cmd and cmd[-1] == "<PASTE_A_URL>":
            cmd[-1] = urls[0]
            cmd.extend(urls[1:])
        outdir = self.outdir.get().strip() or DEFAULT_OUTDIR
        try:
            os.makedirs(outdir, exist_ok=True)
        except OSError as exc:
            self.error_dialog("Invalid output folder", str(exc))
            return

        self._item_index = 0
        self._item_total = 0
        self._log_append("$ " + " ".join(_shell_quote(x) for x in cmd) + "\n", "cmd")
        self._user_stopped = False
        if not self._log_visible:
            self.toggle_log()
        try:
            creationflags = 0x08000000 if sys.platform == "win32" else 0  # CREATE_NO_WINDOW
            self._proc = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL, cwd=engine_root,
                env=_engine_env(engine_root), creationflags=creationflags)
        except OSError as exc:
            self.error_dialog("Launch failed", str(exc))
            return
        self._q = queue.Queue()
        self._running = True
        threading.Thread(target=self._pump, args=(self._proc,), daemon=True).start()
        self._set_running_ui(True)
        self.state_var.set("Starting…")
        self.state_label.configure(fg=TEXT)
        self.speed_var.set("")
        self.eta_var.set("")
        self.progress.set(0)
        self.progress.start_indeterminate()
        self.root.after(80, self._poll)

    def stop(self, event=None):
        proc = self._proc
        if proc is None or proc.poll() is not None:
            return
        self._user_stopped = True
        self._log_append("\n[stopping…]\n", "warn")
        self.state_var.set("Stopping…")
        try:
            proc.kill()
        except OSError:
            pass

    def _pump(self, proc):
        for raw in proc.stdout:
            line = raw.decode("utf-8", errors="replace").rstrip("\r\n")
            if line:
                self._q.put(line)
        rc = proc.wait()
        self._q.put(("__exit__", rc))

    def _poll(self):
        if not self._running:
            return
        try:
            while True:
                item = self._q.get_nowait()
                if isinstance(item, tuple):
                    self._finish(item[1])
                    return
                self._handle_line(item)
        except queue.Empty:
            pass
        self.root.after(80, self._poll)

    def _handle_line(self, line):
        tag = None
        low = line.lower()
        if "[error]" in low or low.startswith("error") or "unable to download" in low:
            tag = "err"
        elif "[warning]" in low or low.startswith("warning"):
            tag = "warn"
        self._log_append(line + "\n", tag)

        m = PROG_RE.search(line)
        if m:
            pct = min(float(m.group(1)), 100.0)
            self.progress.set(pct)
            if self._item_total > 1:
                self.state_var.set(f"Item {max(self._item_index, 1)}/{self._item_total} — downloading")
            else:
                self.state_var.set("Downloading")
            self.speed_var.set(m.group(2) or "")
            self.eta_var.set(("ETA " + m.group(3)) if m.group(3) else "")
            self.state_label.configure(fg=TEXT)
            return
        m = ITEM_RE.search(line)
        if m:
            self._item_index, self._item_total = int(m.group(1)), int(m.group(2))
            self.progress.set(0)
            self.state_var.set(f"Item {self._item_index}/{self._item_total} — fetching info…")
            return
        m = DEST_RE.search(line)
        if m:
            self.state_var.set("Saving → " + os.path.basename(m.group(1)))
            self.progress.set(0)
            return
        if "Downloading format" in line:
            self.state_var.set(line.split("]", 1)[-1].strip()[:90])
            return
        m2 = TAG_RE.match(line)
        if m2 and m2.group(1) in STATUS_TAGS:
            self.state_var.set(f"{m2.group(1)}: {m2.group(2)[:80]}")

    def _finish(self, code):
        self._running = False
        self.progress.stop()
        self._set_running_ui(False)
        self.speed_var.set("")
        self.eta_var.set("")
        if self._user_stopped:
            self.state_var.set("Stopped by user")
            self.state_label.configure(fg=YELLOW)
            self._log_append("[stopped by user]\n", "warn")
            self.progress.set(0)
        elif code == 0:
            self.state_var.set("Finished")
            self.state_label.configure(fg=GREEN)
            self.progress.set(100)
            self._log_append("✓ Finished successfully.\n", "ok")
            self._toast("Download finished", "ok")
        else:
            self.state_var.set(f"Failed (exit code {code})")
            self.state_label.configure(fg="#ff7b8a")
            self.progress.set(0)
            self._log_append(f"✗ yt-dlp exited with code {code}.\n", "err")
            self._toast("Download failed — see the activity log", "error")

    def _set_running_ui(self, running):
        self.btn_start.set_enabled(not running)
        self.btn_start2.set_enabled(not running)
        self.btn_stop.set_enabled(running)
        self.btn_start.set_text("Downloading…" if running else "Download")
        self.btn_start2.set_text("Downloading…" if running else "Start download")

    def _log_append(self, text, tag=None):
        self.log.configure(state="normal")
        self.log.insert("end", text, (tag,) if tag else ())
        lines = int(self.log.index("end-1c").split(".")[0])
        if lines > 3000:
            self.log.delete("1.0", f"{lines - 2200}.0")
        self.log.see("end")
        self.log.configure(state="disabled")

    def _engine_label(self):
        prefix, _root, label = self._engine_state
        if prefix is None:
            return label or "yt-dlp NOT FOUND — see the Command tab"
        return label

    def _on_close(self):
        proc = self._proc
        if proc is not None and proc.poll() is None:
            if not self.ask_dialog("Quit while downloading?",
                                   "A download is still running. Stop it and quit?"):
                return
            try:
                proc.kill()
            except OSError:
                pass
        self.save_config()
        self.root.destroy()
