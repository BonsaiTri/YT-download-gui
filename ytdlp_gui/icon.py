"""Locating the app icon for windows, taskbars and launchers.

The icon lives in build/ (icon.ico for Windows, icon.png elsewhere) and is
generated from source by ``python build/make_icon.py``. A packaged build ships
it next to the executable instead, so every sensible location is probed.
"""

import os
import sys

from .paths import APP_DIR

_PACKAGE_DIR = os.path.dirname(os.path.abspath(__file__))

#: Candidate directories, in priority order.
_SEARCH_DIRS = (APP_DIR, os.path.join(APP_DIR, "build"), os.path.join(_PACKAGE_DIR, os.pardir, "build"))


def find_icon(names=("icon.png", "icon.ico")):
    """Return the first existing icon path, or None."""
    for directory in _SEARCH_DIRS:
        for name in names:
            path = os.path.normpath(os.path.join(directory, name))
            if os.path.isfile(path):
                return path
    return None


def apply_window_icon(root):
    """Set the window/taskbar icon, ignoring failures.

    Windows accepts .ico via ``iconbitmap``; everywhere else Tk wants a
    ``PhotoImage`` (PNG on 8.6+). Both are best-effort: a missing or
    unreadable icon must never stop the app from starting.
    """
    try:
        import tkinter as tk
    except ImportError:  # pragma: no cover - tkinter is a hard requirement
        return

    ico = find_icon(("icon.ico",))
    png = find_icon(("icon.png",))

    if sys.platform == "win32" and ico:
        try:
            root.iconbitmap(ico)
        except tk.TclError:
            pass

    if png:
        try:
            # Keep a reference: Tk drops the image if it is garbage collected.
            root._app_icon = tk.PhotoImage(master=root, file=png)  # noqa: SLF001
            root.iconphoto(True, root._app_icon)  # noqa: SLF001
        except tk.TclError:
            pass
