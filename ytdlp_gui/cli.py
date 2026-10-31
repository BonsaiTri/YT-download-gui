"""Entry point: DPI setup, the --selftest smoke test, and main().

``selftest()`` is used by the build scripts and by ``python -m ytdlp_gui
--selftest``: it prints the engine/ffmpeg/JS-runtime status plus a sample
argument line, writes ``selftest_result.txt`` and exits non-zero if the engine
cannot run.
"""

import os
import subprocess
import sys
from shutil import which

import tkinter as tk

from .app import App
from .engine import _engine_env, _shell_quote, js_runtime_args, resolve_yt_dlp
from .paths import APP_DIR, FROZEN
from .settings import DEFAULTS, build_args


def selftest():
    lines = ["frozen: " + str(FROZEN), "app_dir: " + APP_DIR]
    prefix, engine_root, label = resolve_yt_dlp()
    lines.append("engine: " + (label or "NOT FOUND"))
    ok = bool(prefix)
    if prefix:
        try:
            proc = subprocess.run(prefix + ["--version"], capture_output=True, text=True,
                                  cwd=engine_root, timeout=60, env=_engine_env(engine_root))
            out = (proc.stdout or proc.stderr).strip().splitlines()
            lines.append("yt-dlp: " + (out[0] if out else "unknown") +
                         " (exit %d)" % proc.returncode)
            ok = ok and proc.returncode == 0
        except Exception as exc:  # noqa: BLE001 — selftest reports, never crashes
            lines.append("yt-dlp: FAILED " + str(exc))
            ok = False
    args = build_args(DEFAULTS, ["https://example.com/v"])
    lines.append("args: " + " ".join(_shell_quote(a) for a in args))
    lines.append("ffmpeg: " + (which("ffmpeg") or "NOT FOUND"))
    js = js_runtime_args()
    lines.append("js runtime: " + (" ".join(js) if js else "none (needed for YouTube)"))
    text = "\n".join(lines) + "\n"
    try:
        with open(os.path.join(APP_DIR, "selftest_result.txt"), "w", encoding="utf-8") as fh:
            fh.write(text)
    except OSError:
        pass
    _write_stdout(text)
    return 0 if ok else 1


def _write_stdout(text):
    """Write to stdout when one exists.

    Windowed builds (PyInstaller ``--noconsole``) have ``sys.stdout is None``,
    so ``--selftest`` must not depend on a console being attached; the report
    also lands in ``selftest_result.txt`` next to the app.
    """
    stream = sys.stdout
    if stream is None:
        return
    try:
        stream.write(text)
        stream.flush()
    except (OSError, ValueError, AttributeError):
        pass


def main():
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:  # noqa: BLE001 — best effort DPI fix
            pass
    root = tk.Tk()
    App(root)
    root.mainloop()
    return 0
