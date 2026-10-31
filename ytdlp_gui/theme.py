"""YouTube-inspired dark palette, fonts, drawing helpers and ttk styling.

Colours follow YouTube's dark theme: near-black page background, slightly
lighter card surfaces, and YouTube red for primary actions.
"""

import tkinter as tk
from tkinter import ttk, font as tkfont


# ---------------------------------------------------------------------------
# Theme — a YouTube-inspired dark palette
# ---------------------------------------------------------------------------

BG         = "#0f0f0f"   # app background (YouTube dark)
BG_SOFT    = "#0a0a0a"   # sidebar
SURFACE    = "#1c1c1c"   # cards
SURFACE_2  = "#242424"   # inputs, chips
SURFACE_3  = "#303030"   # hover / tracks
SURFACE_4  = "#3f3f3f"   # pressed
BORDER     = "#2c2c2c"
BORDER_2   = "#3d3d3d"
TEXT       = "#f1f1f1"
TEXT_DIM   = "#aaaaaa"
TEXT_FAINT = "#717171"
RED        = "#ff0033"   # YouTube red
RED_HOVER  = "#ff3d5e"
RED_DARK   = "#c00028"
RED_TINT   = "#3a1017"   # subtle red wash for selected chips on dark surfaces
BLUE       = "#3ea6ff"
GREEN      = "#2ba640"
YELLOW     = "#f2c94c"
ORANGE     = "#ff8a3d"

_FAMILY = None
_MONO = None


def _ui_family(root=None):
    global _FAMILY
    if _FAMILY is None:
        fams = ()
        try:
            fams = tkfont.families(root)
        except Exception:
            pass
        for cand in ("Segoe UI Variable Text", "Segoe UI", "Inter", "SF Pro Text",
                     "Helvetica Neue", "Ubuntu", "Cantarell", "DejaVu Sans",
                     "Noto Sans", "Arial"):
            if cand in fams:
                _FAMILY = cand
                break
        else:
            _FAMILY = "TkDefaultFont"
    return _FAMILY


def _mono_family(root=None):
    global _MONO
    if _MONO is None:
        fams = ()
        try:
            fams = tkfont.families(root)
        except Exception:
            pass
        for cand in ("Cascadia Mono", "Cascadia Code", "Consolas", "SF Mono",
                     "Menlo", "DejaVu Sans Mono", "Ubuntu Mono", "Liberation Mono",
                     "Courier New"):
            if cand in fams:
                _MONO = cand
                break
        else:
            _MONO = "TkFixedFont"
    return _MONO


def ui_font(size=10, weight="normal", slant="roman"):
    return (_ui_family(), size, weight, slant)


def mono_font(size=9, weight="normal"):
    return (_mono_family(), size, weight)


def parent_bg(widget):
    try:
        return widget.cget("bg")
    except tk.TclError:
        return BG


# ---------------------------------------------------------------------------
# Drawing helpers
# ---------------------------------------------------------------------------

def round_rect(canvas, x1, y1, x2, y2, r, **kw):
    """Draw a rounded rectangle as a smoothed polygon; returns the item id."""
    r = max(0, min(r, (x2 - x1) / 2, (y2 - y1) / 2))
    pts = [
        x1 + r, y1, x2 - r, y1, x2 - r, y1, x2, y1, x2, y1 + r,
        x2, y1 + r, x2, y2 - r, x2, y2 - r, x2, y2, x2 - r, y2,
        x2 - r, y2, x1 + r, y2, x1 + r, y2, x1, y2, x1, y2 - r,
        x1, y2 - r, x1, y1 + r, x1, y1 + r, x1, y1,
    ]
    return canvas.create_polygon(pts, smooth=True, splinesteps=16, **kw)


def hex_to_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def rgb_to_hex(rgb):
    return "#%02x%02x%02x" % tuple(max(0, min(255, int(c))) for c in rgb)


def mix(c1, c2, t):
    """Blend two hex colors; t=0 -> c1, t=1 -> c2."""
    a, b = hex_to_rgb(c1), hex_to_rgb(c2)
    return rgb_to_hex(tuple(a[i] + (b[i] - a[i]) * t for i in range(3)))


# ---------------------------------------------------------------------------
# ttk styling (scrollbars + comboboxes are the only themed ttk widgets)
# ---------------------------------------------------------------------------

def setup_theme(root):
    root.configure(bg=BG)
    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass

    fam = _ui_family(root)
    style.configure(".", background=BG, foreground=TEXT, font=(fam, 10),
                    fieldbackground=SURFACE_2, bordercolor=BORDER, focuscolor=RED,
                    troughcolor=SURFACE, selectbackground=RED, selectforeground="#ffffff")

    # scrollbars -------------------------------------------------------
    for orient in ("Vertical", "Horizontal"):
        name = f"Dark.{orient}.TScrollbar"
        style.layout(name, [
            (f"{orient}.Scrollbar.trough", {"sticky": "ns" if orient == "Vertical" else "ew",
                                            "children": [
                (f"{orient}.Scrollbar.thumb", {"expand": "1", "sticky": "nswe"})]})])
        style.configure(name, troughcolor=BG, background=SURFACE_3, bordercolor=BG,
                        darkcolor=SURFACE_3, lightcolor=SURFACE_3, arrowcolor=TEXT_FAINT,
                        gripcount=0, width=11, arrowsize=11, relief="flat")
        style.map(name, background=[("active", SURFACE_4), ("pressed", SURFACE_4)],
                  arrowcolor=[("active", TEXT_DIM)])

    # combobox ---------------------------------------------------------
    style.configure("Dark.TCombobox",
                    fieldbackground=SURFACE_2, background=SURFACE_2, foreground=TEXT,
                    arrowcolor=TEXT_DIM, bordercolor=BORDER, lightcolor=SURFACE_2,
                    darkcolor=SURFACE_2, selectbackground=SURFACE_2,
                    selectforeground=TEXT, padding=(9, 7), relief="flat",
                    arrowsize=13)
    style.map("Dark.TCombobox",
              fieldbackground=[("readonly", SURFACE_2), ("disabled", SURFACE)],
              foreground=[("disabled", TEXT_FAINT)],
              arrowcolor=[("active", TEXT)],
              bordercolor=[("focus", RED), ("hover", BORDER_2), ("!focus", BORDER)],
              lightcolor=[("focus", RED)], darkcolor=[("focus", RED)],
              background=[("active", SURFACE_3)])
    root.option_add("*TCombobox*Listbox.background", SURFACE_2)
    root.option_add("*TCombobox*Listbox.foreground", TEXT)
    root.option_add("*TCombobox*Listbox.selectBackground", RED)
    root.option_add("*TCombobox*Listbox.selectForeground", "#ffffff")
    root.option_add("*TCombobox*Listbox.borderWidth", 0)
    root.option_add("*TCombobox*Listbox.font", f"{{{fam}}} 10")

    # misc -------------------------------------------------------------
    style.configure("Dark.TSeparator", background=BORDER)
    style.configure("TFrame", background=BG)
    style.configure("TLabel", background=BG, foreground=TEXT, font=(fam, 10))
    style.configure("Dark.TCheckbutton", background=BG, foreground=TEXT, focuscolor=BG)
    return style
