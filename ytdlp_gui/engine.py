"""Locating and running the yt-dlp engine.

Lookup order, first hit wins:

1. YTDLP_HOME environment variable
2. <app>/yt-dlp      - engine bundled inside a packaged build
3. <app>/../yt-dlp   - sibling checkout when running from source
4. yt-dlp on PATH

The engine is always invoked as ``python -m yt_dlp <args>`` so its interpreter
can be bundled privately (see build/windows-build.bat).
"""

import os
import re
import sys
from shutil import which

from .paths import APP_DIR, FROZEN


# ---------------------------------------------------------------------------
# yt-dlp resolution
# ---------------------------------------------------------------------------

_JS_RUNTIME_ARGS = None


def js_runtime_args():
    """yt-dlp 2025+ needs a JavaScript runtime for YouTube (EJS).
    Returns e.g. ['--js-runtimes', 'node', '--remote-components', 'ejs:github']
    or [] if no runtime (deno/node) is found on PATH."""
    global _JS_RUNTIME_ARGS
    if _JS_RUNTIME_ARGS is None:
        runtime = which("deno") or which("node") or which("nodejs")
        if runtime:
            name = "deno" if os.path.basename(runtime).startswith("deno") else "node"
            _JS_RUNTIME_ARGS = ["--js-runtimes", name, "--remote-components", "ejs:github"]
        else:
            _JS_RUNTIME_ARGS = []
    return _JS_RUNTIME_ARGS


def _bundle_dir():
    """Root of the PyInstaller bundle, or None when running from source.

    A onefile build extracts everything to a temporary folder (``sys._MEIPASS``)
    which is where a bundled interpreter and engine live; an onedir build puts
    them next to the executable instead.
    """
    return getattr(sys, "_MEIPASS", None)


def _engine_python():
    """Interpreter that can run ``python -m yt_dlp``.

    Packaged builds: a bundled embeddable Python (onefile: inside the extracted
    bundle; onedir: ``<app>/python``), else whatever python is on PATH.
    Dev/source mode: the interpreter running this GUI itself.
    """
    if FROZEN:
        for base in (_bundle_dir(), APP_DIR):
            if not base:
                continue
            pdir = os.path.join(base, "python")
            for name in ("python.exe", "python3", "python"):
                cand = os.path.join(pdir, name)
                if os.path.isfile(cand):
                    return cand
        return which("python3") or which("python")
    return sys.executable


def _candidate_repo_roots():
    """Directories that might hold a yt-dlp checkout, best first."""
    roots = []
    env = os.environ.get("YTDLP_HOME")
    if env:
        roots.append(os.path.abspath(env))
    if FROZEN:
        bundle = _bundle_dir()
        if bundle:  # onefile: extracted next to the bundled interpreter
            roots.append(os.path.join(bundle, "yt-dlp"))
        roots.append(os.path.join(APP_DIR, "yt-dlp"))  # onedir: next to the exe
    roots.append(os.path.normpath(os.path.join(APP_DIR, os.pardir, "yt-dlp")))  # dev layout
    return roots


def resolve_yt_dlp():
    """Return (argv_prefix, engine_root_or_None, label) or (None, None, reason)."""
    for engine_root in _candidate_repo_roots():
        if not engine_root or not os.path.isfile(os.path.join(engine_root, "yt_dlp", "__init__.py")):
            continue
        py = _engine_python()
        if not py:
            return None, None, ("engine found at " + engine_root +
                                " but no Python interpreter found — install Python 3")
        if os.path.isfile(os.path.join(engine_root, "yt_dlp", "__main__.py")):
            prefix = [py, "-m", "yt_dlp"]
        else:  # very old checkout: use the dev entry-point script
            prefix = [py, os.path.join(engine_root, "yt_dlp.py")]
        return prefix, engine_root, "checkout: " + engine_root
    exe = which("yt-dlp") or which("yt-dlp.exe")
    if exe:
        return [exe], None, "system yt-dlp on PATH"
    return None, None, None


def _shell_quote(s):
    if s and not re.search(r"""[\s"\'&|<>()^!%]""", s):
        return s
    return '"' + s.replace('"', '\\"') + '"'


def _engine_env(engine_root):
    """Environment for the engine subprocess (embeddable Python needs PYTHONPATH)."""
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    if engine_root:
        env["PYTHONPATH"] = engine_root + os.pathsep + env.get("PYTHONPATH", "")
    return env
