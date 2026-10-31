# Launchers

Start **yt-dlp GUI** the way your OS expects — double-click, application menu,
Dock, or Start menu — instead of typing `python yt_dlp_gui.py` every time.

All launchers are self-locating: they walk up from their own folder until they
find `yt_dlp_gui.py`, so they work from anywhere inside the repository and keep
working if you move the folder (shortcuts made with the installers point at the
launcher, not at a fixed path you have to maintain).

| OS | Launch it | Add to your app menu |
|---|---|---|
| **Windows (no Python needed)** | `dist/yt-dlp-gui.exe` — one self-contained file | create a shortcut to the exe yourself, or run `install-launcher.bat` first |
| **Windows (from source)** | `launchers/windows/yt-dlp-gui.bat` or `.vbs` | `launchers/windows/install-launcher.bat` (add `desktop` for a Desktop icon) |
| **macOS** | `launchers/macos/yt-dlp-gui.command` | `launchers/macos/make-app-bundle.sh` → `yt-dlp GUI.app` |
| **Linux** | `launchers/linux/yt-dlp-gui.sh` | `launchers/linux/install-desktop-entry.sh` |

---

## Windows

### `dist/yt-dlp-gui.exe` — a real single-file executable (recommended)

The only thing you need to double-click. Build it with:

```bat
build\windows-build-onefile.bat
```

It produces **`dist\yt-dlp-gui.exe`** (~31 MB): one file containing the app,
an embeddable Python 3.13 and the yt-dlp engine. Copy it to a USB stick, the
Desktop, anywhere — it needs **no companion folder and no installed Python**,
and downloads land in a `downloads` folder created next to the exe.

Build it this way only if you *want* one file; the trade-off is that PyInstaller
unpacks to a temp folder on each launch (a few seconds of start-up time) and
antivirus scanners sometimes scrutinise fresh one-file binaries.

> Prefer a folder build? `build\windows-build.bat` produces
> `dist\yt-dlp-gui-win64.zip` with `yt-dlp-gui.exe` beside `python\` and
> `yt-dlp\` — faster to start, but the folder must stay together.

Both builders run `yt-dlp-gui.exe --selftest` **from an isolated temp folder**
and fail the build if the bundled engine cannot be reached, so a broken
package never ships.

### `yt-dlp-gui.bat` — from source, visible, self-checking
Runs the GUI with **pythonw.exe** so no console lingers, but first probes
Tkinter with the console interpreter so a broken install reports
`Python is installed but Tkinter is missing` instead of failing silently
(as `pythonw` would). Also verifies `yt_dlp_gui.py` exists, and prints the
python.org install instructions when Python is missing.

The `.bat` and `.vbs` launchers below are for running **from the source repo**,
so they need Python installed. If you built the exe, you do not need them.

### `yt-dlp-gui.vbs` — silent, from source
Pure `WScript` version with no console flash at all, and `MsgBox` errors
instead. Use this for shortcuts to the source checkout.

### `install-launcher.bat` — Start menu shortcut
```bat
launchers\windows\install-launcher.bat            :: Start menu
launchers\windows\install-launcher.bat desktop    :: + Desktop
launchers\windows\install-launcher.bat uninstall  :: remove
```
Creates a per-user shortcut (no admin rights) whose target is
`wscript.exe "…\yt-dlp-gui.vbs"`, with the project folder as working directory
and `build\icon.ico` as the shortcut icon.

> If the shortcut works but the icon looks blank, run
> `python build/make_icon.py` once to generate `build/icon.ico`, then re-run
> the installer.

---

## macOS

### `yt-dlp-gui.command` — double-clickable
Finder opens `.command` files in Terminal, so you see real error messages.
Searches `/opt/homebrew`, `/usr/local`, the python.org framework and
`/usr/bin/python3`, and uses the first one that can `import tkinter`
(the Command Line Tools interpreter often cannot).

If macOS refuses to run it:
```bash
chmod +x launchers/macos/yt-dlp-gui.command
# then right-click -> Open the first time
```

### `make-app-bundle.sh` — a real `.app`
Builds a minimal bundle (no PyInstaller) with an icon, Dock presence and
`LSApplicationCategoryType`:

```bash
./launchers/macos/make-app-bundle.sh              # -> dist/yt-dlp GUI.app
./launchers/macos/make-app-bundle.sh ~/Applications
open "dist/yt-dlp GUI.app"
```

The bundle is unsigned, so the first launch needs **right-click → Open**.
For a fully self-contained app (bundled Python + engine) use
`build/macos-build.sh` instead.

---

## Linux

### `yt-dlp-gui.sh`
Finds a Python 3 with Tkinter and `exec`s the GUI. Follows symlinks, so you can
link it into `~/.local/bin`. Prints the exact install command for Debian,
Fedora, Arch and openSUSE when Tkinter is missing.

### `install-desktop-entry.sh` — application menu (no root)
```bash
./launchers/linux/install-desktop-entry.sh
./launchers/linux/install-desktop-entry.sh --uninstall
```
Installs, under `~/.local`:

| File | Purpose |
|---|---|
| `~/.local/bin/yt-dlp-gui` | terminal command |
| `~/.local/share/applications/yt-dlp-gui.desktop` | menu entry |
| `~/.local/share/icons/hicolor/256x256/apps/yt-dlp-gui.png` | icon |

and refreshes the desktop/icon caches.

### `make-deb.sh` — a `.deb` for Debian/Ubuntu
```bash
./launchers/linux/make-deb.sh        # -> dist/yt-dlp-gui_2.0.0_all.deb
sudo dpkg -i dist/yt-dlp-gui_2.0.0_all.deb
```
Installs to `/usr/share/yt-dlp-gui` with `/usr/bin/yt-dlp-gui`, a menu entry, an
icon, and `Depends: python3, python3-tk` (+ `Recommends: ffmpeg, yt-dlp`).

---

## Notes

- **Nothing here needs administrator rights** except `dpkg -i`.
- Launchers only ever *start* the app — they do not install Python, Tkinter or
  the yt-dlp engine. `python3 -c "import tkinter"` must succeed.
- The GUI still needs the yt-dlp engine (`../yt-dlp`, `YTDLP_HOME`, or on
  `PATH`). The **Command → Environment** panel reports what was found.
- The Shipped `run.bat` / `run.sh` at the repo root are the quickest
  "run it from a terminal" options and stay as they are.
