#!/usr/bin/env bash
# ============================================================
#  yt-dlp GUI — macOS .app builder (run this ON a Mac)
#  Produces <outdir>/yt-dlp-gui-macos.zip containing yt-dlp-gui.app
#
#  The output folder is chosen in a menu first (default: dist/).
#  Non-interactive/CI: YTDLP_GUI_BUILD_OUT=/some/folder ./macos-build.sh
# ============================================================
set -euo pipefail
cd "$(dirname "$0")/.."

command -v python3 >/dev/null || { echo "Install Python 3 first:  brew install python3"; exit 1; }
command -v git >/dev/null     || { echo "Install Git first (Xcode command-line tools or brew)."; exit 1; }

# ---- pick where the build lands ------------------------------
# choose_output.py prints only the chosen path (the menu goes to stderr) and
# also creates + write-tests the folder. No TTY => it just uses the default.
export YTDLP_GUI_BUILD_APP="yt-dlp GUI (macOS build)"
export YTDLP_GUI_BUILD_ROOT="$PWD"
: "${YTDLP_GUI_BUILD_DEFAULT:=$PWD/dist}"
if ! DIST=$(python3 build/choose_output.py); then
  echo "Build cancelled."
  exit 1
fi
unset YTDLP_GUI_BUILD_APP YTDLP_GUI_BUILD_DEFAULT YTDLP_GUI_BUILD_ROOT
mkdir -p "$DIST"
APP="$DIST/yt-dlp-gui.app"
echo "Building into: $DIST"

echo "[1/7] Installing PyInstaller..."
python3 -m pip install --quiet pyinstaller 2>/dev/null \
  || python3 -m pip install --quiet --user pyinstaller

echo "[2/7] Checking yt-dlp engine..."
if [ ! -f ../yt-dlp/yt_dlp/__init__.py ] && [ ! -d ../yt-dlp ]; then
  git clone --depth 1 https://github.com/yt-dlp/yt-dlp ../yt-dlp
fi
[ -f ../yt-dlp/yt_dlp/__init__.py ] || { echo "yt-dlp engine missing at ../yt-dlp"; exit 1; }

echo "[3/7] Building with PyInstaller..."
python3 -m PyInstaller --noconfirm --clean --windowed --name "yt-dlp GUI" \
  --paths . --distpath "$DIST" --workpath build/pyi --specpath build yt_dlp_gui.py

echo "[4/7] Assembling .app bundle..."
rm -rf "$APP"
mkdir -p "$APP/Contents/MacOS" "$APP/Contents/Resources"
cp -R "$DIST/yt-dlp GUI/"* "$APP/Contents/MacOS/"
cp -R ../yt-dlp "$APP/Contents/Resources/yt-dlp"
rm -rf "$APP/Contents/Resources/yt-dlp/.git"
cat > "$APP/Contents/Info.plist" <<'PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>CFBundleName</key><string>yt-dlp GUI</string>
  <key>CFBundleDisplayName</key><string>yt-dlp GUI</string>
  <key>CFBundleIdentifier</key><string>local.ytdlp.gui</string>
  <key>CFBundleExecutable</key><string>yt-dlp GUI</string>
  <key>CFBundlePackageType</key><string>APPL</string>
  <key>CFBundleShortVersionString</key><string>1.0.0</string>
  <key>CFBundleVersion</key><string>1</string>
  <key>NSHighResolutionCapable</key><true/>
</dict>
</plist>
PLIST
cat > "$APP/Contents/Resources/UPDATE.txt" <<'TXT'
To update the yt-dlp engine inside this app:
  cd "yt-dlp-gui.app/Contents/Resources/yt-dlp"
  git pull --ff-only
(Or run the builder again.)
TXT

echo "[5/7] Selftest..."
"$APP/Contents/MacOS/yt-dlp GUI" --selftest \
  || { echo "SELFTEST FAILED"; cat "$APP/Contents/Resources/selftest_result.txt" 2>/dev/null; exit 1; }

echo "[6/7] Zipping..."
(cd "$DIST" && rm -f yt-dlp-gui-macos.zip && zip -qr yt-dlp-gui-macos.zip yt-dlp-gui.app)

echo "[7/7] Done..."
echo
echo "DONE: $DIST/yt-dlp-gui-macos.zip"
echo "First launch: right-click the app -> Open (Gatekeeper, unsigned build)."
open "$DIST" >/dev/null 2>&1 || true
