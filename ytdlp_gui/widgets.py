"""A small dark-themed widget toolkit drawn on Tkinter Canvas.

Stock ttk widgets cannot render rounded cards, pill chips or hover/press
states under the 'clam' theme, so the interactive pieces are hand-drawn on
Canvas while text input still uses real tk.Entry/tk.Text for IME and
clipboard support.

Public widgets: RoundedButton, ChoiceGroup, Check, EntryField, TextField,
Card, ScrollArea, NavButton, ProgressBar, Toast, Logo, Pill.
"""

import tkinter as tk
from tkinter import font as tkfont, ttk

from .theme import (BG, BORDER, BORDER_2, GREEN, RED, RED_DARK, RED_HOVER,
                    SURFACE, SURFACE_2, SURFACE_3, SURFACE_4, TEXT, TEXT_DIM,
                    TEXT_FAINT, mix, mono_font, parent_bg, round_rect, ui_font)


# ---------------------------------------------------------------------------
# Widgets — a small dark-themed toolkit built on Canvas
# ---------------------------------------------------------------------------

class RoundedButton(tk.Canvas):
    """A rounded, hover-aware button. kinds: primary, secondary, ghost, danger."""

    def __init__(self, parent, text="", command=None, kind="secondary", glyph=None,
                 width=None, height=38, radius=10, font_size=10, bold=True,
                 bg=None, padx=18, min_width=34):
        self._base_bg = bg if bg is not None else parent_bg(parent)
        super().__init__(parent, bg=self._base_bg, highlightthickness=0, bd=0,
                         height=height, takefocus=1)
        self._text = text
        self._glyph = glyph
        self._command = command
        self._kind = kind
        self._radius = radius
        self._padx = padx
        self._font = ui_font(font_size, "bold" if bold else "normal")
        self._state = "normal"
        self._hover = False
        self._pressed = False
        self._enabled = True
        self._auto_width = width is None
        self._min_width = min_width if width is None else int(width)
        if self._auto_width:
            width = self._measure_width()
        self._width = int(width)
        self.configure(width=self._width)
        self.bind("<Configure>", lambda e: self._draw())
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<Button-1>", self._on_press)
        self.bind("<ButtonRelease-1>", self._on_release)
        self.bind("<Key-Return>", lambda e: self._click())
        self.bind("<Key-space>", lambda e: self._click())
        self._draw()

    def _measure_width(self):
        fnt = tkfont.Font(root=self, font=self._font)
        tw = fnt.measure(self._text) if self._text else 0
        gw = fnt.measure(self._glyph) + 8 if self._glyph else 0
        return max(tw + gw + self._padx * 2, self._min_width)

    # -- appearance -----------------------------------------------------
    def _colors(self):
        if not self._enabled:
            if self._kind == "primary":
                return "#4a1c24", "#a06872", ""
            return SURFACE_2, TEXT_FAINT, BORDER
        if self._kind == "primary":
            fill = RED_DARK if (self._pressed and self._hover) else (RED_HOVER if self._hover else RED)
            return fill, "#ffffff", fill
        if self._kind == "danger":
            fill = "#4a1010" if self._hover else SURFACE_2
            return fill, "#ff6b6b", ("#7a2222" if self._hover else BORDER)
        if self._kind == "ghost":
            fill = SURFACE_2 if self._pressed else (SURFACE_2 if self._hover else self._base_bg)
            return fill, TEXT if self._hover else TEXT_DIM, fill
        fill = SURFACE_4 if (self._pressed and self._hover) else (SURFACE_3 if self._hover else SURFACE_2)
        return fill, TEXT, (BORDER_2 if self._hover else BORDER)

    def _draw(self):
        self.delete("all")
        w, h = self.winfo_width(), self.winfo_height()
        if w <= 1:
            w = int(self.cget("width"))
        if h <= 1:
            h = int(self.cget("height"))
        fill, fg, outline = self._colors()
        round_rect(self, 1, 1, w - 1, h - 1, self._radius, fill=fill,
                   outline=outline, width=1)
        label = self._text
        if self._glyph:
            label = f"{self._glyph}  {label}" if label else self._glyph
        if label:
            self.create_text(w / 2, h / 2 + 1, text=label, fill=fg, font=self._font)

    # -- events ---------------------------------------------------------
    def _on_enter(self, _e):
        self._hover = True
        if self._enabled:
            self.configure(cursor="hand2")
        self._draw()

    def _on_leave(self, _e):
        self._hover = self._pressed = False
        self.configure(cursor="")
        self._draw()

    def _on_press(self, _e):
        if not self._enabled:
            return
        self._pressed = True
        self.focus_set()
        self._draw()

    def _on_release(self, e):
        was = self._pressed
        self._pressed = False
        self._draw()
        if was and 0 <= e.x <= self.winfo_width() and 0 <= e.y <= self.winfo_height():
            self._click()

    def _click(self):
        if self._enabled and self._command:
            self._command()

    # -- API ------------------------------------------------------------
    def set_enabled(self, enabled):
        self._enabled = bool(enabled)
        self.configure(cursor="hand2" if enabled and self._hover else "")
        self._draw()

    def set_text(self, text):
        if text == self._text:
            return
        self._text = text
        if self._auto_width:
            need = self._measure_width()
            if need != self._width:
                self._width = need
                self.configure(width=need)
        self._draw()

    def set_active(self, active):
        self._kind = "primary" if active else "secondary"
        self._draw()

    def configure_state(self, state):
        self.set_enabled(state != "disabled")


class ChoiceGroup(tk.Canvas):
    """Segmented chip selector (YouTube-style: selected chip is light, rest dark)."""

    def __init__(self, parent, options, value=None, command=None, height=34,
                 radius=9, font_size=9, bg=None, stretch=True, gap=6, padx=12):
        self._base_bg = bg if bg is not None else parent_bg(parent)
        super().__init__(parent, bg=self._base_bg, highlightthickness=0, bd=0,
                         height=height)
        self._items = list(options)
        self._labels = [o[0] if isinstance(o, (tuple, list)) else str(o) for o in self._items]
        self._values = [o[1] if isinstance(o, (tuple, list)) else str(o) for o in self._items]
        if value is None and self._values:
            value = self._values[0]
        self._value = value
        self._command = command
        self._radius = radius
        self._stretch = stretch
        self._gap = gap
        self._padx = padx
        self._font = ui_font(font_size, "bold")
        self._hover = -1
        self._rects = []
        self._enabled = True
        self.bind("<Configure>", lambda e: self._draw())
        self.bind("<Motion>", self._on_motion)
        self.bind("<Leave>", self._on_leave)
        self.bind("<Button-1>", self._on_click)
        self._draw()

    def _layout(self):
        w = max(self.winfo_width(), 40)
        n = len(self._items) or 1
        if self._stretch:
            seg = (w - self._gap * (n - 1)) / n
            return [(i * (seg + self._gap), seg) for i in range(n)]
        fnt = tkfont.Font(root=self, font=self._font)
        out, x = [], 0
        for lab in self._labels:
            seg = fnt.measure(lab) + self._padx * 2
            out.append((x, seg))
            x += seg + self._gap
        return out

    def _draw(self):
        self.delete("all")
        self._rects = []
        h = self.winfo_height()
        if h <= 1:
            h = int(self.cget("height"))
        for (x, seg), label, value in zip(self._layout(), self._labels, self._values):
            selected = value == self._value
            hovered = (not selected) and self._hover == len(self._rects)
            if not self._enabled:
                fill, fg, outline = SURFACE_2, "#5a5a5a", SURFACE_2
            elif selected:
                fill, fg, outline = TEXT, "#0f0f0f", TEXT
            else:
                fill = SURFACE_3 if hovered else SURFACE_2
                fg = TEXT if hovered else TEXT_DIM
                outline = SURFACE_3 if hovered else SURFACE_2
            round_rect(self, x, 1, x + seg, h - 1, self._radius, fill=fill,
                       outline=outline, width=1)
            self.create_text(x + seg / 2, h / 2, text=label, fill=fg, font=self._font)
            self._rects.append((x, seg))

    def _index_at(self, x):
        for i, (rx, rw) in enumerate(self._rects):
            if rx <= x <= rx + rw:
                return i
        return -1

    def _on_motion(self, e):
        if not self._enabled:
            return
        idx = self._index_at(e.x)
        if idx != self._hover:
            self._hover = idx
            self.configure(cursor="hand2" if idx >= 0 else "")
            self._draw()

    def _on_leave(self, _e):
        self._hover = -1
        self.configure(cursor="")
        self._draw()

    def _on_click(self, e):
        if not self._enabled:
            return
        idx = self._index_at(e.x)
        if idx < 0:
            return
        value = self._values[idx]
        if value == self._value:
            return
        self._value = value
        self._draw()
        if self._command:
            self._command(value)

    def get(self):
        return self._value

    def set(self, value):
        if value in self._values:
            self._value = value
        elif value is not None:
            self._value = self._values[0] if self._values else None
        self._draw()

    def set_enabled(self, enabled):
        self._enabled = bool(enabled)
        self._hover = -1
        self.configure(cursor="")
        self._draw()


class Check(tk.Canvas):
    """Checkbox with label text, drawn on a single canvas."""

    def __init__(self, parent, text="", value=False, command=None, font_size=10,
                 bg=None, box=18):
        self._base_bg = bg if bg is not None else parent_bg(parent)
        self._font = ui_font(font_size)
        fnt = tkfont.Font(root=parent, font=self._font)
        width = box + 10 + fnt.measure(text) + 4
        super().__init__(parent, bg=self._base_bg, highlightthickness=0, bd=0,
                         height=box + 8, width=width, takefocus=1)
        self._text = text
        self._value = bool(value)
        self._command = command
        self._box = box
        self._hover = False
        self._width = int(width)
        self._in_draw = False
        self.bind("<Configure>", lambda e: self._draw())
        self.bind("<Enter>", lambda e: self._hover_event(True))
        self.bind("<Leave>", lambda e: self._hover_event(False))
        self.bind("<Button-1>", lambda e: self.toggle())
        self.bind("<Key-space>", lambda e: self.toggle())
        self.bind("<Key-Return>", lambda e: self.toggle())
        self._draw()

    def _hover_event(self, state):
        self._hover = state
        self.configure(cursor="hand2" if state else "")
        self._draw()

    def _draw(self):
        if self._in_draw:
            return
        self._in_draw = True
        try:
            self._paint()
        finally:
            self._in_draw = False

    def _paint(self):
        self.delete("all")
        h = self.winfo_height() or (self._box + 8)
        y = h / 2
        x1 = 2
        y1 = y - self._box / 2
        x2 = x1 + self._box
        y2 = y + self._box / 2
        if self._value:
            fill = RED_HOVER if self._hover else RED
            round_rect(self, x1, y1, x2, y2, 5, fill=fill, outline=fill)
            self.create_line(x1 + 4.5, y, x1 + 7.5, y + 3.5, x1 + 13.5, y - 3.5,
                             fill="#ffffff", width=2, capstyle="round", joinstyle="round")
        else:
            outline = BORDER_2 if self._hover else SURFACE_4
            round_rect(self, x1, y1, x2, y2, 5, fill=SURFACE_2, outline=outline, width=1.5)
        self.create_text(x2 + 10, y, text=self._text, anchor="w", font=self._font,
                         fill=TEXT if self._hover or self._value else TEXT_DIM)
        need = int(x2 + 10 + tkfont.Font(root=self, font=self._font).measure(self._text) + 4)
        if need != self._width:
            self._width = need
            self.configure(width=need)

    def get(self):
        return self._value

    def set(self, value):
        self._value = bool(value)
        self._draw()

    def toggle(self):
        self._value = not self._value
        self._draw()
        if self._command:
            self._command(self._value)

    # compatibility with the ttk.Checkbutton "command=" usage
    def config_command(self, command):
        self._command = command


class EntryField(tk.Frame):
    """Flat dark text entry with placeholder and focus ring."""

    def __init__(self, parent, placeholder="", width=None, font_size=10, mono=False):
        self._base_bg = parent_bg(parent)
        super().__init__(parent, bg=BORDER)
        if width:
            self.configure(width=width)
        self.inner = tk.Frame(self, bg=SURFACE_2)
        self.inner.pack(fill="both", expand=True, padx=1, pady=1)
        self.var = tk.StringVar()
        self.entry = tk.Entry(
            self.inner, textvariable=self.var, relief="flat", bd=0,
            bg=SURFACE_2, fg=TEXT, insertbackground=RED, insertwidth=2,
            highlightthickness=0, font=mono_font(font_size) if mono else ui_font(font_size),
            selectbackground=RED, selectforeground="#ffffff", disabledbackground=SURFACE,
            disabledforeground=TEXT_FAINT)
        self.entry.pack(fill="both", expand=True, padx=11, pady=7)
        self._placeholder = placeholder
        self._ph_on = False
        self.entry.bind("<FocusIn>", self._on_focus_in, add="+")
        self.entry.bind("<FocusOut>", self._on_focus_out, add="+")
        self.entry.bind("<Key>", self._on_key, add="+")
        if placeholder:
            self._show_ph()

    def _show_ph(self):
        if self._ph_on or self.var.get() or not self._placeholder:
            return
        self._ph_on = True
        self.var.set(self._placeholder)
        self.entry.configure(fg="#5c5c5c" if self.entry.cget("state") == "disabled"
                             else TEXT_FAINT)

    def _hide_ph(self, _e=None):
        if self._ph_on:
            self._ph_on = False
            self.var.set("")
            self.entry.configure(fg=TEXT)

    def _on_focus_in(self, _e):
        self.configure(bg=RED)
        self._hide_ph()

    def _on_focus_out(self, _e):
        self.configure(bg=BORDER)
        self._show_ph()

    def _on_key(self, e):
        if self._ph_on and e.keysym not in ("Left", "Right", "Up", "Down", "Tab",
                                            "ISO_Left_Tab", "Shift_L", "Shift_R"):
            self._hide_ph()

    # -- API (mirrors the tk.Entry methods the app uses) ----------------
    def get(self):
        return "" if self._ph_on else self.var.get()

    def set(self, value):
        value = "" if value is None else str(value)
        self._ph_on = False
        self.var.set(value)
        self.entry.configure(fg=TEXT)
        if not value:
            try:
                focused = self.focus_get() is self.entry
            except (KeyError, tk.TclError):
                focused = False
            if not focused:
                self._show_ph()

    def delete(self, *_a):
        self.set("")

    def insert(self, _index, value):
        self.set((self.get() if not self._ph_on else "") + str(value))

    def bind_entry(self, sequence, func):
        self.entry.bind(sequence, func, add="+")

    def focus_entry(self):
        self.entry.focus_set()

    def set_enabled(self, enabled):
        state = "normal" if enabled else "disabled"
        self.entry.configure(state=state)
        self.configure(bg=BORDER if enabled else "#262626")
        self.inner.configure(bg=SURFACE_2 if enabled else SURFACE)
        if self._ph_on:
            # placeholder text is currently shown: just restyle it
            self.entry.configure(fg="#5c5c5c" if not enabled else TEXT_FAINT)
            return
        if self.get():
            return
        try:
            focused = self.focus_get() is self.entry
        except (KeyError, tk.TclError):
            focused = False
        if not focused:
            self._show_ph()


class TextField(tk.Frame):
    """Bordered multi-line text box with placeholder."""

    def __init__(self, parent, height=5, placeholder="", font_size=10, mono=False,
                 wrap="word"):
        self._base_bg = parent_bg(parent)
        super().__init__(parent, bg=BORDER)
        self.text = tk.Text(
            self, height=height, wrap=wrap, relief="flat", bd=0, bg=SURFACE_2,
            fg=TEXT, insertbackground=RED, insertwidth=2, highlightthickness=0,
            selectbackground=RED, selectforeground="#ffffff",
            font=mono_font(font_size) if mono else ui_font(font_size),
            padx=10, pady=8, spacing1=1, spacing3=1, undo=True)
        self.text.pack(fill="both", expand=True, padx=1, pady=1)
        self._placeholder = placeholder
        self._ph_on = False
        self.text.bind("<FocusIn>", self._on_focus_in, add="+")
        self.text.bind("<FocusOut>", self._on_focus_out, add="+")
        self.text.bind("<Key>", self._on_key, add="+")
        if placeholder:
            self._show_ph()

    def _show_ph(self):
        if self._ph_on or self.text.get("1.0", "end-1c") or not self._placeholder:
            return
        self._ph_on = True
        self.text.insert("1.0", self._placeholder)
        self.text.configure(fg=TEXT_FAINT)

    def _hide_ph(self, _e=None):
        if self._ph_on:
            self._ph_on = False
            self.text.delete("1.0", "end")
            self.text.configure(fg=TEXT)

    def _on_focus_in(self, _e):
        self.configure(bg=RED)
        self._hide_ph()

    def _on_focus_out(self, _e):
        self.configure(bg=BORDER)
        self._show_ph()

    def _on_key(self, e):
        if self._ph_on:
            self._hide_ph()
            if e.keysym in ("BackSpace", "Delete"):
                return "break"

    def get(self):
        return "" if self._ph_on else self.text.get("1.0", "end-1c")

    def set(self, value):
        value = "" if value is None else str(value)
        prev_state = self.text.cget("state")
        if prev_state == "disabled":
            self.text.configure(state="normal")
        self._ph_on = False
        self.text.configure(fg=TEXT)
        self.text.delete("1.0", "end")
        if value:
            self.text.insert("1.0", value)
        else:
            try:
                focused = self.focus_get() is self.text
            except (KeyError, tk.TclError):
                focused = False
            if not focused:
                self._show_ph()
        if prev_state == "disabled":
            self.text.configure(state="disabled")

    def clear(self):
        self.set("")


class Card(tk.Canvas):
    """Rounded surface card: padded header (title / subtitle / right slot)
    plus a content frame for arbitrary widgets."""

    def __init__(self, parent, title=None, subtitle=None, radius=16, pad=20,
                 gap=12):
        self._base_bg = parent_bg(parent)
        super().__init__(parent, bg=self._base_bg, highlightthickness=0, bd=0,
                         height=80)
        self._pad = pad
        self._radius = radius
        self._gap = gap
        self._height = 80
        self._draw_job = None

        self.body = tk.Frame(self, bg=SURFACE)
        self._win = self.create_window(pad, pad, window=self.body, anchor="nw")

        self.header = tk.Frame(self.body, bg=SURFACE)
        self._title_label = None
        if title:
            self.header.pack(fill="x")
            self.header_right = tk.Frame(self.header, bg=SURFACE)
            self.header_right.pack(side="right", anchor="n")
            self._title_label = tk.Label(self.header, text=title, bg=SURFACE, fg=TEXT,
                                         font=ui_font(12, "bold"), anchor="w")
            self._title_label.pack(side="left", anchor="n")
        else:
            self.header_right = tk.Frame(self.body, bg=SURFACE)
        self._subtitle_label = None
        if subtitle:
            self._subtitle_label = tk.Label(self.body, text=subtitle, bg=SURFACE,
                                            fg=TEXT_FAINT, font=ui_font(9), anchor="w",
                                            justify="left")
            self._subtitle_label.pack(fill="x", pady=(6, 0))
        self.content = tk.Frame(self.body, bg=SURFACE)
        self.content.pack(fill="x", pady=((gap, 0) if (title or subtitle) else (0, 0)))
        self.body.bind("<Configure>", self._queue_draw)
        self.bind("<Configure>", self._queue_draw)

    def _queue_draw(self, _e=None):
        if self._draw_job is None:
            self._draw_job = self.after_idle(self._redraw)

    def _redraw(self):
        self._draw_job = None
        if not self.winfo_exists():
            return
        w = self.winfo_width()
        if w <= 1:
            self.after(40, self._redraw)
            return
        pad = self._pad
        need = self.body.winfo_reqheight() + pad * 2
        if need != self._height:
            self._height = need
            self.configure(height=need)
        inner = max(w - pad * 2, 40)
        try:
            self.coords(self._win, pad, pad)
            self.itemconfigure(self._win, width=inner)
        except tk.TclError:
            pass
        if self._subtitle_label is not None:
            self._subtitle_label.configure(wraplength=inner - 4)
        self.delete("cardbg")
        round_rect(self, 0.5, 0.5, w - 0.5, self._height - 0.5, self._radius,
                   fill=SURFACE, outline=BORDER, width=1, tags="cardbg")
        self.tag_lower("cardbg")


class ScrollArea(tk.Frame):
    """Vertically scrollable container; children go into ``.inner``."""

    def __init__(self, parent, bg=BG):
        super().__init__(parent, bg=bg)
        self._bg = bg
        self.canvas = tk.Canvas(self, bg=bg, highlightthickness=0, bd=0)
        self.vsb = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview,
                                 style="Dark.Vertical.TScrollbar")
        self.canvas.configure(yscrollcommand=self._on_scroll_set)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.inner = tk.Frame(self.canvas, bg=bg)
        self._win = self.canvas.create_window(0, 0, window=self.inner, anchor="nw")
        self.inner.bind("<Configure>", self._on_inner)
        self.canvas.bind("<Configure>", self._on_canvas)
        self.bind_all("<MouseWheel>", self._on_wheel, add="+")
        self.bind_all("<Button-4>", lambda e: self._wheel_linux(e, -1), add="+")
        self.bind_all("<Button-5>", lambda e: self._wheel_linux(e, 1), add="+")

    def _on_inner(self, _e=None):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        self._update_scrollbar()

    def _on_canvas(self, e):
        self.canvas.itemconfigure(self._win, width=e.width)

    def _on_scroll_set(self, first, last):
        self.vsb.set(first, last)
        self._update_scrollbar(float(first), float(last))

    def _update_scrollbar(self, first=None, last=None):
        if first is None or last is None:
            first, last = self.canvas.yview()
        if last - first >= 0.999:
            self.vsb.pack_forget()
        elif not self.vsb.winfo_ismapped():
            self.vsb.pack(side="right", fill="y")

    def _mine(self, widget):
        while widget is not None:
            if widget is self:
                return True
            widget = getattr(widget, "master", None)
        return False

    def _on_wheel(self, e):
        w = self.winfo_containing(e.x_root, e.y_root)
        if not self._mine(w):
            return
        if self.canvas.yview() == (0.0, 1.0):
            return
        self.canvas.yview_scroll(int(-e.delta / 40), "units")

    def _wheel_linux(self, e, direction):
        w = self.winfo_containing(e.x_root, e.y_root)
        if not self._mine(w):
            return
        self.canvas.yview_scroll(direction, "units")

    def to_top(self):
        self.canvas.yview_moveto(0)


class NavButton(tk.Canvas):
    """Sidebar navigation entry with a hand-drawn icon."""

    def __init__(self, parent, key, label, icon, command):
        self._base_bg = parent_bg(parent)
        super().__init__(parent, bg=self._base_bg, highlightthickness=0, bd=0,
                         height=42, width=180)
        self.key = key
        self._label = label
        self._icon = icon
        self._command = command
        self._active = False
        self._hover = False
        self._font = ui_font(10, "bold")
        self.bind("<Configure>", lambda e: self._draw())
        self.bind("<Enter>", lambda e: self._hover_event(True))
        self.bind("<Leave>", lambda e: self._hover_event(False))
        self.bind("<Button-1>", lambda e: self._command(self.key))
        self._draw()

    def _hover_event(self, state):
        self._hover = state
        self.configure(cursor="hand2" if state else "")
        self._draw()

    def set_active(self, active):
        self._active = active
        self._draw()

    def _draw_icon(self, x, cy):
        c = TEXT if self._active else TEXT_FAINT
        if self._hover and not self._active:
            c = TEXT_DIM
        if self._icon == "download":
            self.create_line(x + 8, cy - 6, x + 8, cy + 2, fill=c, width=1.6, capstyle="round")
            self.create_line(x + 3.5, cy - 1.5, x + 8, cy + 3, x + 12.5, cy - 1.5,
                             fill=c, width=1.6, capstyle="round", joinstyle="round")
            self.create_line(x + 2.5, cy + 6.5, x + 13.5, cy + 6.5, fill=c, width=1.6, capstyle="round")
        elif self._icon == "folder":
            self.create_line(x + 2, cy - 4.5, x + 6.5, cy - 4.5, x + 8, cy - 2.5, x + 14, cy - 2.5,
                             fill=c, width=1.5, capstyle="round", joinstyle="round")
            self.create_line(x + 2, cy - 4.5, x + 2, cy + 5.5, x + 14, cy + 5.5, x + 14, cy - 2.5,
                             fill=c, width=1.5, capstyle="round", joinstyle="round")
        elif self._icon == "cc":
            self.create_text(x + 8, cy, text="CC", fill=c, font=ui_font(8, "bold"))
        elif self._icon == "sliders":
            for i, (yy, knob) in enumerate(((cy - 5, 5), (cy, 11), (cy + 5, 6))):
                self.create_line(x + 2, yy, x + 14, yy, fill=c, width=1.4, capstyle="round")
                self.create_oval(x + knob - 2, yy - 2, x + knob + 2, yy + 2,
                                 fill=self._base_bg, outline=c, width=1.4)
        elif self._icon == "terminal":
            self.create_line(x + 3, cy - 4.5, x + 7, cy, x + 3, cy + 4.5, fill=c,
                             width=1.6, capstyle="round", joinstyle="round")
            self.create_line(x + 9, cy + 4.5, x + 14, cy + 4.5, fill=c, width=1.6, capstyle="round")
        else:  # console / lines
            for offset, width in ((-4.5, 13), (0, 9), (4.5, 6.5)):
                self.create_line(x + 2, cy + offset, x + 2 + width, cy + offset,
                                 fill=c, width=1.6, capstyle="round")

    def _draw(self):
        self.delete("all")
        w, h = self.winfo_width(), self.winfo_height()
        if w <= 1:
            w, h = 180, 42
        if self._active:
            round_rect(self, 2, 1, w - 2, h - 1, 10, fill=SURFACE, outline=SURFACE)
            round_rect(self, 2, h / 2 - 9, 5.5, h / 2 + 9, 2, fill=RED, outline=RED)
        elif self._hover:
            round_rect(self, 2, 1, w - 2, h - 1, 10, fill=SURFACE, outline=SURFACE)
        self._draw_icon(16, h / 2)
        self.create_text(40, h / 2, text=self._label, anchor="w",
                         fill=TEXT if self._active else (TEXT if self._hover else TEXT_DIM),
                         font=self._font)


class ProgressBar(tk.Canvas):
    """Rounded progress track with a red fill."""

    def __init__(self, parent, height=8, bg=None, radius=4):
        self._base_bg = bg if bg is not None else parent_bg(parent)
        super().__init__(parent, bg=self._base_bg, highlightthickness=0, bd=0,
                         height=height)
        self._pct = 0.0
        self._radius = radius
        self._indeterminate = False
        self._phase = 0.0
        self.bind("<Configure>", lambda e: self._draw())
        self._draw()

    def _draw(self):
        self.delete("all")
        w, h = self.winfo_width(), self.winfo_height()
        if w <= 1:
            return
        round_rect(self, 0, 0, w, h, self._radius, fill=SURFACE_3, outline=SURFACE_3)
        if self._indeterminate:
            seg = w * 0.28
            x = (w + seg) * self._phase - seg
            x1, x2 = max(0, x), min(w, x + seg)
            if x2 > x1:
                round_rect(self, x1, 0, x2, h, self._radius, fill=RED, outline=RED)
            return
        frac = max(0.0, min(1.0, self._pct / 100.0))
        if frac * w > 2:
            round_rect(self, 0, 0, max(frac * w, h), h, self._radius, fill=RED, outline=RED)

    def set(self, pct):
        self._indeterminate = False
        self._pct = max(0.0, min(100.0, float(pct)))
        self._draw()

    def start_indeterminate(self):
        self._indeterminate = True
        self._pct = 0.0
        self._tick()

    def _tick(self):
        if not self._indeterminate:
            return
        self._phase = (self._phase + 0.02) % 1.35
        self._draw()
        self.after(35, self._tick)

    def stop(self):
        self._indeterminate = False
        self._draw()


class Toast(tk.Frame):
    """Small floating notification over the content area."""

    def __init__(self, master, text, kind="info", timeout=2400):
        bgc = {"info": SURFACE_4, "ok": "#12351c", "error": "#3a1017"}.get(kind, SURFACE_4)
        fgc = {"info": TEXT, "ok": "#7ee29a", "error": "#ff8ba0"}.get(kind, TEXT)
        super().__init__(master, bg=bgc, highlightthickness=1,
                         highlightbackground=mix(bgc, "#ffffff", 0.08))
        tk.Label(self, text=text, bg=bgc, fg=fgc, font=ui_font(10, "bold"),
                 padx=16, pady=9).pack()
        self.place(relx=0.5, y=14, anchor="n")
        self.lift()
        self.after(timeout, self._close)

    def _close(self):
        try:
            self.destroy()
        except tk.TclError:
            pass


class Logo(tk.Canvas):
    def __init__(self, parent, height=34):
        super().__init__(parent, width=150, height=height, bg=parent_bg(parent),
                         highlightthickness=0, bd=0)
        self._draw()

    def _draw(self):
        h = int(float(self.cget("height")))
        cy = h / 2
        round_rect(self, 1, cy - 14, 41, cy + 14, 9, fill=RED, outline=RED)
        self.create_polygon(18, cy - 7, 18, cy + 7, 28.5, cy, fill="#ffffff", outline="")
        self.create_text(52, cy, text="yt-dlp", anchor="w", fill=TEXT,
                         font=ui_font(15, "bold"))
        fnt = tkfont.Font(root=self, font=ui_font(15, "bold"))
        x = 52 + fnt.measure("yt-dlp") + 7
        self.create_text(x, cy + 1, text="GUI", anchor="w", fill=TEXT_FAINT,
                         font=ui_font(14, "bold"))


class Pill(tk.Canvas):
    """Rounded status pill (engine indicator)."""

    def __init__(self, parent, text="", color=GREEN, height=28, command=None,
                 bg=None):
        self._text = text
        self._color = color
        self._command = command
        fnt = ui_font(9, "bold")
        w = tkfont.Font(root=parent, font=fnt).measure(text) + 42
        super().__init__(parent, width=w, height=height,
                         bg=bg if bg is not None else parent_bg(parent),
                         highlightthickness=0, bd=0)
        self._font = fnt
        self.bind("<Configure>", lambda e: self._draw())
        if command:
            self.bind("<Button-1>", lambda e: command())
            self.configure(cursor="hand2")
        self._draw()

    def _draw(self):
        self.delete("all")
        w, h = self.winfo_width(), self.winfo_height()
        if w <= 1:
            w, h = int(float(self.cget("width"))), int(float(self.cget("height")))
        round_rect(self, 0.5, 0.5, w - 0.5, h - 0.5, h / 2, fill=SURFACE,
                   outline=BORDER, width=1)
        cy = h / 2
        self.create_oval(13, cy - 3.5, 20, cy + 3.5, fill=self._color, outline=self._color)
        self.create_text(27, cy, text=self._text, anchor="w", fill=TEXT_DIM,
                         font=self._font)
        self.configure(width=int(w))

    def set_text(self, text, color=None):
        self._text = text
        if color:
            self._color = color
        fnt = self._font
        self.configure(width=int(tkfont.Font(root=self, font=fnt).measure(text) + 42))
        self._draw()
