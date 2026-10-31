#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""yt-dlp GUI - launcher.

This thin wrapper keeps ``python yt_dlp_gui.py`` working (and gives PyInstaller
a single entry point); the application itself lives in the ``ytdlp_gui``
package next to this file:

    ytdlp_gui/paths.py      where the app lives (config, downloads)
    ytdlp_gui/engine.py     finding and invoking the yt-dlp engine
    ytdlp_gui/settings.py   every option, its CLI flag, and validation
    ytdlp_gui/parsing.py    yt-dlp output -> progress/status text
    ytdlp_gui/theme.py      the YouTube-inspired dark palette
    ytdlp_gui/widgets.py    the Canvas-based dark widget toolkit
    ytdlp_gui/app.py        the application window
    ytdlp_gui/cli.py        main() and the --selftest smoke test

Usage::

    python yt_dlp_gui.py              # launch the GUI
    python yt_dlp_gui.py --selftest   # headless environment check
    python -m ytdlp_gui [--selftest]  # same, as a module
"""

import os
import sys

# Make the package importable no matter where this file is called from.
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)


def _run():
    from ytdlp_gui.cli import main, selftest
    return selftest() if "--selftest" in sys.argv[1:] else main()


if __name__ == "__main__":
    sys.exit(_run())
