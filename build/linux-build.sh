#!/usr/bin/env bash
# ============================================================
#  yt-dlp GUI — Linux app builder (run on the target distro)
#  Produces <outdir>/yt-dlp-gui-linux.tar.gz containing yt-dlp-gui/
#    yt-dlp-gui   the app binary (or run ./run.sh)
#    yt-dlp/      bundled engine
#
#  The output folder is chosen in a menu first (default: dist/).
#  Non-interactive/CI: YTDLP_GUI_BUILD_OUT=/some/folder ./linux-build.sh
# ============================================================
set -euo pipefail
cd "$(dirname "$0")/.."

command -v python3 >/dev/null || { echo "Install python3 + tkinter first, e.g.: sudo apt install python3 python3-tk"; exit 1; }
command -v git >/dev/null     || { echo "Install git first."; exit 1; }

# ---- pick where the build lands ------------------------------
# choose_output.py prints only the chosen path (the menu goes to stderr) and
# also creates + write-tests the folder. No TTY => it just uses the default.
export YTDLP_GUI_BUILD_APP="yt-dlp GUI (Linux build on $OSTYPE)"
export YTDLP_GUI_BUILD_ROOT="$PWD"
: "${YTDLP_GUI_BUILD_DEFAULT:=$PWD/dist}"
if ! DIST=$(python3 build/choose_output.py); then
  echo "Build cancelled."
  exit 1
fi
unset YTDLP_GUI_BUILD_APP YTDLP_GUI_BUILD_DEFAULT YTDLP_GUI_BUILD_ROOT
mkdir -p "$DIST"
APP="$DIST/yt-dlp-gui"
echo "Building into: $DIST"

echo "[1/6] Installing PyInstaller..."
python3 -m pip install --quiet pyinstaller 2>/dev/null \
  || python3 -m pip install --quiet --user pyinstaller

echo "[2/6] Checking yt-dlp engine..."
if [ ! -f ../yt-dlp/yt_dlp/__init__.py ] && [ ! -d ../yt-dlp ]; then
  git clone --depth 1 https://github.com/yt-dlp/yt-dlp ../yt-dlp
fi
[ -f ../yt-dlp/yt_dlp/__init__.py ] || { echo "yt-dlp engine missing at ../yt-dlp"; exit 1; }

echo "[3/6] Building app dir..."
python3 -m PyInstaller --noconfirm --clean --windowed --name yt-dlp-gui \
  --icon build/icon.png --paths . --distpath "$DIST" --workpath build/pyi --specpath build yt_dlp_gui.py
rm -rf "$APP"
mv "$DIST/yt-dlp-gui" "$APP"
cp -R ../yt-dlp "$APP/yt-dlp"
rm -rf "$APP/yt-dlp/.git"
cat > "$APP/run.sh" <<'SH'
#!/usr/bin/env bash
exec "$(cd "$(dirname "$0")" && pwd)/yt-dlp-gui" "$@"
SH
chmod +x "$APP/run.sh" "$APP/yt-dlp-gui"

echo "[4/6] Selftest..."
"$APP/yt-dlp-gui" --selftest \
  || { echo "SELFTEST FAILED"; cat "$APP/selftest_result.txt" 2>/dev/null; exit 1; }

echo "[5/6] Tarring..."
tar -C "$DIST" -czf "$DIST/yt-dlp-gui-linux.tar.gz" yt-dlp-gui

echo "[6/6] Done..."
echo
echo "DONE: $DIST/yt-dlp-gui-linux.tar.gz"
if command -v xdg-open >/dev/null; then xdg-open "$DIST" >/dev/null 2>&1 || true; fi
