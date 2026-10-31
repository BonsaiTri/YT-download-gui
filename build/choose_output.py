#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Ask where the finished build should be written.

Every builder (``windows-build.bat``, ``windows-build-onefile.bat``,
``macos-build.sh``, ``linux-build.sh``) calls this first, so all of them ask
the same question and honour the same overrides:

    [1] <default folder>          (default)
    [2] Browse for a folder...    (graphical picker, Tk)
    [3] Type a path...            (console input)
    [4] Cancel the build

Only the chosen directory is printed on stdout (one line, nothing else) so a
builder can capture it::

    for /f "usebackq delims=" %%O in (`python build\\choose_output.py`) do set "OUTDIR=%%O"
    OUTDIR=$(python3 build/choose_output.py)

Environment variables (used instead of command line flags so that callers
never have to quote paths with spaces):

    YTDLP_GUI_BUILD_DEFAULT  default output directory offered by the menu
    YTDLP_GUI_BUILD_APP      app name used in dialog/menu titles
    YTDLP_GUI_BUILD_ROOT     repo root; a folder that contains it is refused
    YTDLP_GUI_BUILD_OUT      the answer: skip the prompt entirely (CI, scripts)

Exit codes: 0 = a directory was chosen, 1 = cancelled or failed, 2 = bad input.
"""

import os
import sys
import tempfile

MENU_DEFAULT = "1"
MENU_BROWSE = "2"
MENU_TYPE = "3"
MENU_CANCEL = "4"


class OutputError(Exception):
    """The chosen location cannot be used as a build output directory."""


def _say(message=""):
    """Human-facing text always goes to stderr, never to the captured stdout."""
    print(message, file=sys.stderr, flush=True)


def app_name():
    return os.environ.get("YTDLP_GUI_BUILD_APP") or "yt-dlp GUI"


def default_dir():
    raw = os.environ.get("YTDLP_GUI_BUILD_DEFAULT") or os.path.join(os.getcwd(), "dist")
    return _expand(raw)


def _expand(raw):
    cleaned = raw.strip().strip('"').strip("'")
    return os.path.abspath(os.path.expanduser(os.path.expandvars(cleaned)))


def prepare(path):
    """Create ``path`` if needed, prove it is writable, return it normalised."""
    if not path or not path.strip():
        raise OutputError("no folder given")
    target = _expand(path)
    if os.path.isfile(target):
        raise OutputError("%s is a file, not a folder" % target)
    try:
        os.makedirs(target, exist_ok=True)
    except OSError as exc:
        raise OutputError("cannot create %s (%s)" % (target, exc))
    try:
        handle, probe = tempfile.mkstemp(prefix=".write-test-", dir=target)
        os.close(handle)
        os.unlink(probe)
    except OSError as exc:
        raise OutputError("no permission to write in %s (%s)" % (target, exc))

    # Writing the archive into the repo root would make the archive contain
    # itself (tar/Compress-Archive), so only subfolders are allowed.
    root = os.environ.get("YTDLP_GUI_BUILD_ROOT", "").strip()
    if root:
        root = os.path.normcase(_expand(root))
        here = os.path.normcase(target)
        if here == root or root.startswith(here + os.sep):
            raise OutputError(
                "%s holds the sources - pick a subfolder such as %s"
                % (target, os.path.join(target, "dist"))
            )
    return os.path.normpath(target)


def browse(initial, title):
    """Open a native folder picker; None if there is no display / no Tk."""
    try:
        import tkinter as tk
        from tkinter import filedialog
    except Exception:
        return None
    try:
        root = tk.Tk()
    except Exception:
        return None
    try:
        root.withdraw()
        try:
            root.attributes("-topmost", True)
        except Exception:
            pass
        start = initial if os.path.isdir(initial) else os.getcwd()
        chosen = filedialog.askdirectory(
            parent=root,
            initialdir=start,
            title=title,
            mustexist=False,
        )
    finally:
        try:
            root.destroy()
        except Exception:
            pass
    return chosen or None


def _looks_like_path(answer):
    return any(token in answer for token in ("/", "\\", ":", "~")) or answer.startswith(".")


def _ask():
    """Read one line of input. Prompts go to stderr: stdout carries the answer."""
    try:
        return input()
    except (EOFError, KeyboardInterrupt):
        _say()
        return ""


def choose_non_interactive():
    """No terminal (CI, piped stdin): just take the default."""
    target = prepare(os.environ.get("YTDLP_GUI_BUILD_OUT") or default_dir())
    return target


def choose_interactive():
    fallback = default_dir()
    _say()
    _say("=" * 62)
    _say(" %s - where should the finished build be written?" % app_name())
    _say("=" * 62)
    _say("   [1] %s   (default)" % fallback)
    _say("   [2] Browse for a folder...")
    _say("   [3] Type a path...")
    _say("   [4] Cancel the build")
    _say()

    while True:
        _say(" Choice [1], or paste a folder path, then press Enter:")
        answer = (_ask() or "").strip()
        if not answer:
            answer = MENU_DEFAULT  # bare Enter takes the default

        if answer == MENU_CANCEL:
            _say("Build cancelled.")
            return None

        if answer == MENU_BROWSE:
            picked = browse(fallback, "%s - choose build output folder" % app_name())
            if not picked:
                _say("No folder picked (no file dialog available?). Choose 1 or 3 instead.")
                continue
            answer = picked
        elif answer == MENU_TYPE:
            _say(" Build output folder:")
            answer = (_ask() or "").strip()
            if not answer:
                _say("Nothing entered.")
                continue
        elif answer == MENU_DEFAULT:
            answer = fallback
        elif not _looks_like_path(answer):
            _say("'%s' is not one of 1-4 and does not look like a folder path." % answer)
            continue

        try:
            target = prepare(answer)
        except OutputError as exc:
            _say("Cannot use that location: %s" % exc)
            continue

        _say("Build output: %s" % target)
        return target


def main(argv):
    if any(arg in ("-h", "--help") for arg in argv[1:]):
        _say(__doc__)
        return 0
    if os.environ.get("YTDLP_GUI_BUILD_OUT", "").strip():
        try:
            print(choose_non_interactive())
        except OutputError as exc:
            _say("Cannot use YTDLP_GUI_BUILD_OUT: %s" % exc)
            return 1
        return 0
    try:
        if not sys.stdin.isatty():
            print(choose_non_interactive())
            return 0
        target = choose_interactive()
    except OutputError as exc:
        _say("Cannot use that location: %s" % exc)
        return 1
    if target is None:
        return 1
    print(target)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
