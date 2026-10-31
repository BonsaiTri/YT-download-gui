"""Settings model: every UI option, its CLI flag, and validation.

build_args() is the single source of truth for what gets executed. It is a
pure function of (settings dict, urls) - no Tkinter, no I/O - so it can be
unit-tested on its own and is reused by the live command preview, the
download action and the --selftest smoke test.

Validation raises ValueError with a human-readable message; the UI shows that
message verbatim and disables the download buttons until it is fixed.
"""

import os
import re
import shlex

from .engine import js_runtime_args
from .paths import DEFAULT_OUTDIR


# ---------------------------------------------------------------------------
# Argument building (pure functions — unit-testable without the GUI)
# ---------------------------------------------------------------------------

QUALITY_FORMATS = {
    "Best (original)": "bestvideo*+bestaudio/best",
    "8K (4320p)":      "bestvideo[height<=4320]+bestaudio/best[height<=4320]",
    "4K (2160p)":      "bestvideo[height<=2160]+bestaudio/best[height<=2160]",
    "1440p":           "bestvideo[height<=1440]+bestaudio/best[height<=1440]",
    "1080p":           "bestvideo[height<=1080]+bestaudio/best[height<=1080]",
    "720p":            "bestvideo[height<=720]+bestaudio/best[height<=720]",
    "480p":            "bestvideo[height<=480]+bestaudio/best[height<=480]",
    "360p":            "bestvideo[height<=360]+bestaudio/best[height<=360]",
}

AUDIO_QUALITIES = ("Audio only (MP3)", "Audio only (M4A)")

# Short labels used by the segmented quality picker on the Download page
QUALITY_CHIPS = [
    ("Best", "Best (original)"),
    ("8K", "8K (4320p)"),
    ("4K", "4K (2160p)"),
    ("1440p", "1440p"),
    ("1080p", "1080p"),
    ("720p", "720p"),
    ("480p", "480p"),
    ("360p", "360p"),
    ("MP3", "Audio only (MP3)"),
    ("M4A", "Audio only (M4A)"),
]

CONTAINERS = ("mkv", "mp4", "webm", "m4a")
REMUX_TARGETS = ("Off", "mp4", "mkv", "webm")
PLAYLIST_MODES = ("Single video only", "Full playlist",
                  "Custom range (1-10, 13, 20-25)")
SUB_FORMATS = ("srt", "vtt", "best")
BROWSERS = ("Off", "chrome", "firefox", "edge", "brave", "opera", "vivaldi",
            "chromium", "safari", "whale")
SPONSOR_ACTIONS = ("Off", "Mark chapters", "Remove segments")
DEFAULT_SPONSOR_CATS = "sponsor,selfpromo,interaction,intro,outro,preview,filler"

DEFAULTS = {
    "quality": "Best (original)",
    "merge_format": "mkv",
    "remux": "Off",
    "playlist_mode": "Single video only",
    "playlist_items": "",
    "outdir": DEFAULT_OUTDIR,
    "template": "%(title)s [%(id)s].%(ext)s",
    "restrict_filenames": False,
    "embed_metadata": False,
    "embed_thumbnail": False,
    "embed_chapters": False,
    "write_thumbnail": False,
    "no_mtime": False,
    "write_subs": False,
    "write_auto_subs": False,
    "sub_langs": "en.*",
    "subs_srt": True,
    "sub_format": "srt",
    "embed_subs": False,
    "cookies": "",
    "cookies_from_browser": "Off",
    "proxy": "",
    "start_time": "",
    "end_time": "",
    "rate_limit": "",
    "concurrent_fragments": "",
    "retries": "",
    "fragment_retries": "",
    "sleep_interval": "",
    "sponsor_action": "Off",
    "sponsor_cats": DEFAULT_SPONSOR_CATS,
    "skip_archived": False,
    "archive": "",
    "extra_args": "",
    "urls": "",
}

_TIME_RE = re.compile(r"^\d+(?::\d{1,2}){0,2}(?:\.\d+)?$")


def _int_field(cfg, key, lo, hi, label):
    """Read an optional integer setting, validating range. Returns int|None."""
    raw = str(cfg.get(key) or "").strip()
    if not raw:
        return None
    try:
        value = int(raw)
    except ValueError:
        raise ValueError(f"{label} must be a whole number (current value: “{raw}”).")
    if not lo <= value <= hi:
        raise ValueError(f"{label} must be between {lo} and {hi} (current value: {value}).")
    return value


def _time_field(cfg, key, label):
    raw = str(cfg.get(key) or "").strip()
    if not raw:
        return ""
    if not _TIME_RE.match(raw):
        raise ValueError(f"{label} must look like 12, 1:30 or 00:01:30 (current value: “{raw}”).")
    return raw


def build_args(cfg, urls):
    """Translate GUI settings into yt-dlp CLI arguments."""
    a = []
    q = (cfg.get("quality") or "").strip() or DEFAULTS["quality"]
    audio_only = q in AUDIO_QUALITIES

    # --- format / quality --------------------------------------------------
    if audio_only:
        a += ["--extract-audio", "--audio-format", "mp3" if "MP3" in q else "m4a"]
    else:
        a += ["-f", QUALITY_FORMATS.get(q, "bestvideo*+bestaudio/best")]
        mf = (cfg.get("merge_format") or "").strip()
        if mf:
            a += ["--merge-output-format", mf]
        remux = (cfg.get("remux") or "Off").strip()
        if remux and remux != "Off":
            a += ["--remux-video", remux]

    # --- subtitles ----------------------------------------------------------
    if cfg.get("embed_subs"):
        a += ["--embed-subs"]
        if not cfg.get("write_subs") and not cfg.get("write_auto_subs"):
            a += ["--write-subs", "--write-auto-subs"]
    if cfg.get("write_subs"):
        a += ["--write-subs"]
    if cfg.get("write_auto_subs"):
        a += ["--write-auto-subs"]
    wants_sub_output = cfg.get("write_subs") or cfg.get("write_auto_subs") or cfg.get("embed_subs")
    langs = (cfg.get("sub_langs") or "").strip()
    if langs and wants_sub_output:
        a += ["--sub-langs", langs]
    writing_files = cfg.get("write_subs") or cfg.get("write_auto_subs")
    sub_fmt = (cfg.get("sub_format") or "").strip()
    if writing_files and (sub_fmt or cfg.get("subs_srt")):
        if not sub_fmt:
            sub_fmt = "srt" if cfg.get("subs_srt") else ""
        if sub_fmt:
            a += ["--sub-format", sub_fmt]

    # --- output ---------------------------------------------------------------
    outdir = (cfg.get("outdir") or "").strip() or DEFAULT_OUTDIR
    a += ["--paths", f"home:{outdir}"]  # yt-dlp 2025.12+: --output-dir removed, use -P/--paths
    tmpl = (cfg.get("template") or "").strip() or "%(title)s [%(id)s].%(ext)s"
    a += ["-o", tmpl]
    if cfg.get("restrict_filenames"):
        a += ["--restrict-filenames"]
    if cfg.get("embed_metadata"):
        a += ["--embed-metadata"]
    if cfg.get("embed_chapters"):
        a += ["--embed-chapters"]
    if cfg.get("embed_thumbnail") and not audio_only:
        a += ["--embed-thumbnail"]
    if cfg.get("write_thumbnail"):
        a += ["--write-thumbnail"]
    if cfg.get("no_mtime"):
        a += ["--no-mtime"]

    # --- playlist handling -----------------------------------------------------
    mode = (cfg.get("playlist_mode") or "Single video only").strip()
    if mode == "Full playlist":
        a += ["--yes-playlist"]
    elif mode.startswith("Custom range"):
        items = (cfg.get("playlist_items") or "").strip()
        if items:
            a += ["--playlist-items", items]
        else:
            a += ["--yes-playlist"]
    else:
        a += ["--no-playlist"]

    # --- authentication ---------------------------------------------------------
    # A cookies file wins over browser extraction: passing both makes yt-dlp
    # try the browser too, which on Windows spews DPAPI decryption errors.
    cookies = (cfg.get("cookies") or "").strip()
    browser = (cfg.get("cookies_from_browser") or "Off").strip()
    if cookies:
        a += ["--cookies", cookies]
    elif browser and browser != "Off":
        a += ["--cookies-from-browser", browser]

    # --- network / performance ---------------------------------------------------
    proxy = (cfg.get("proxy") or "").strip()
    if proxy:
        a += ["--proxy", proxy]
    rate = (cfg.get("rate_limit") or "").strip()
    if rate:
        a += ["--limit-rate", rate]
    cf = _int_field(cfg, "concurrent_fragments", 1, 64, "Concurrent fragments")
    if cf is not None:
        a += ["--concurrent-fragments", str(cf)]
    retries = _int_field(cfg, "retries", 0, 1000, "Retries")
    if retries is not None:
        a += ["--retries", str(retries)]
    frag_retries = _int_field(cfg, "fragment_retries", 0, 1000, "Fragment retries")
    if frag_retries is not None:
        a += ["--fragment-retries", str(frag_retries)]
    sleep = (cfg.get("sleep_interval") or "").strip()
    if sleep:
        try:
            float(sleep)
        except ValueError:
            raise ValueError(f"Sleep between requests must be a number of seconds (current value: “{sleep}”).")
        a += ["--sleep-requests", sleep]

    # --- clipping ------------------------------------------------------------------
    start_t = _time_field(cfg, "start_time", "Start time")
    end_t = _time_field(cfg, "end_time", "End time")
    if start_t or end_t:
        # yt-dlp 2025.12+: --start-time/--end-time removed; --download-sections needs ffmpeg
        a += ["--download-sections", f"*{start_t or '0'}-{end_t or 'inf'}"]

    # --- SponsorBlock ----------------------------------------------------------------
    sponsor = (cfg.get("sponsor_action") or "Off").strip()
    cats = (cfg.get("sponsor_cats") or "").strip() or DEFAULT_SPONSOR_CATS
    if sponsor == "Mark chapters":
        a += ["--sponsorblock-mark", cats]
    elif sponsor == "Remove segments":
        a += ["--sponsorblock-remove", cats]

    # --- archive -----------------------------------------------------------------------
    if cfg.get("skip_archived"):
        arch = (cfg.get("archive") or "").strip()
        a += ["--download-archive", arch or os.path.join(outdir, "archive.txt")]

    # --- passthrough ---------------------------------------------------------------------
    extra = (cfg.get("extra_args") or "").strip()
    if extra:
        try:
            a += shlex.split(extra)
        except ValueError as exc:
            raise ValueError(f"Could not parse the extra CLI arguments: {exc}")

    a += ["--newline"]
    a += js_runtime_args()
    a += [u for u in urls if u]
    return a
