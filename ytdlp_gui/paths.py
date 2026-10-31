"""Filesystem locations: app root, config file, default download folder.

APP_DIR is the directory the app "lives in":

* packaged build  -> the executable's folder
                     (macOS .app -> Contents/Resources)
* running from src -> the project root, i.e. the parent of this package

Everything the app writes (config.json, the default downloads/ folder) goes
there, so a packaged copy stays fully self-contained.
"""

import os
import sys

FROZEN = getattr(sys, "frozen", False)  # True when running as a packaged exe/app

_PACKAGE_DIR = os.path.dirname(os.path.abspath(__file__))


def app_dir():
    """Directory the app treats as its home (see module docstring)."""
    if FROZEN:
        exe = os.path.dirname(os.path.abspath(sys.executable))
        if sys.platform == "darwin" and exe.lower().endswith(os.path.join("contents", "macos")):
            return os.path.normpath(os.path.join(os.path.dirname(os.path.dirname(exe)),
                                                 "Contents", "Resources"))
        return exe
    return os.path.dirname(_PACKAGE_DIR)


APP_DIR = app_dir()
CONFIG_PATH = os.path.join(APP_DIR, "config.json")
DEFAULT_OUTDIR = os.path.join(APP_DIR, "downloads")
