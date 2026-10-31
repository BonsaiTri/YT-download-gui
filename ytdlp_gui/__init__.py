"""A modern, dependency-free desktop GUI for yt-dlp.

The package is split so each concern can be understood and tested alone:

    paths      where the app lives (app dir, config file, downloads)
    engine     finding and invoking the yt-dlp engine
    settings   every option, its CLI flag, and validation (pure functions)
    parsing    regexes that turn yt-dlp output into progress/status text
    theme      the YouTube-inspired dark palette, fonts, ttk styling
    widgets    the Canvas-based dark widget toolkit
    app        the application window and download lifecycle
    cli        entry point (main, --selftest)

Run it with ``python yt_dlp_gui.py`` (or ``python -m ytdlp_gui``).
"""

__version__ = "2.0.0"

__all__ = ["App", "build_args", "resolve_yt_dlp", "__version__"]


def __getattr__(name):
    """Lazily expose the app class without importing Tkinter at package import."""
    if name == "App":
        from .app import App
        return App
    if name == "build_args":
        from .settings import build_args
        return build_args
    if name == "resolve_yt_dlp":
        from .engine import resolve_yt_dlp
        return resolve_yt_dlp
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
