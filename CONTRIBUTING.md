# Contributing

Thanks for taking a look! This is a small, dependency-free project — the goal is
to stay that way.

## Ground rules

- **Stdlib only.** No third-party runtime dependencies (`pip install` is only used
  for PyInstaller and pyflakes at build/test time).
- **`settings.py` stays Tkinter-free.** It holds the pure
  `build_args(cfg, urls)` mapping; the GUI only collects values and shows the
  resulting command. This is what keeps the important logic testable.
- **Validate, don't crash.** Bad input raises `ValueError` with a full sentence
  naming the field and the value; `App.update_preview()` surfaces it verbatim.
- **Keep the theme in `theme.py`.** No hard-coded hex colours in `app.py` or
  `widgets.py`.

## Setup

```bash
git clone --depth 1 https://github.com/yt-dlp/yt-dlp   # engine, as a sibling
git clone https://github.com/<you>/yt-dlp-gui.git
cd yt-dlp-gui
python -m pip install pyflakes
```

## Before opening a PR

```bash
python -m pyflakes ytdlp_gui tests yt_dlp_gui.py
python -m unittest discover -s tests -t . -v
python yt_dlp_gui.py --selftest
```

All three must be clean. If you add a setting, add a test for the flag it emits in
`tests/test_settings.py`.

## Layout cheat-sheet

| You want to change… | Edit |
|---|---|
| what flags are passed to yt-dlp | `ytdlp_gui/settings.py` |
| how a page looks | `ytdlp_gui/app.py` (`_page_*`) |
| a reusable widget | `ytdlp_gui/widgets.py` |
| colours / fonts | `ytdlp_gui/theme.py` |
| progress/status parsing | `ytdlp_gui/parsing.py` |
| engine lookup, JS runtime | `ytdlp_gui/engine.py` |
| startup, `--selftest` | `ytdlp_gui/cli.py` |

## Commit style

Short imperative subject (`Add SponsorBlock categories field`), then a body that
explains *why* when the change is not obvious.
