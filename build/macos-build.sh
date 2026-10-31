#!/usr/bin/env bash
# ============================================================
#  yt-dlp GUI — macOS .app builder (run this ON a Mac)
#  Produces dist/yt-dlp-gui-macos.zip containing yt-dlp-gui.app
# ============================================================
set -euo pipefail
cd "$(dirname "$0")/.."

APP=dist/yt-dlp-gui.app

command -v python3 >/dev/null || { echo "Install Python 3 first:  brew install python3"; exit 1; }
command -v git >/dev/null     || { echo "Install Git first (Xcode command-line tools or brew)."; exit 1; }

echo "[1/6] Installing PyInstaller..."
python3 -m pip install --quiet pyinstaller 2>/dev/null \
  || python3 -m pip install --quiet --user pyinstaller

echo "[2/6] Checking yt-dlp engine..."
if [ ! -f ../yt-dlp/yt_dlp/__init__.py ] && [ ! -d ../yt-dlp ]; then
  git clone --depth 1 https://github.com/yt-dlp/yt-dlp ../yt-dlp
fi
[ -f ../yt-dlp/yt_dlp/__init__.py ] || { echo "yt-dlp engine missing at ../yt-dlp"; exit 1; }

echo "[3/6] Building with PyInstaller..."
python3 -m PyInstaller --noconfirm --clean --windowed --name "yt-dlp GUI" \
  --paths . --distpath dist --workpath build/pyi --specpath build yt_dlp_gui.py

echo "[4/6] Assembling .app bundle..."
rm -rf "$APP"
mkdir -p "$APP/Contents/MacOS" "$APP/Contents/Resources"
cp -R "dist/yt-dlp GUI/"* "$APP/Contents/MacOS/"
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

echo "[5/6] Selftest..."
"$APP/Contents/MacOS/yt-dlp GUI" --selftest \
  || { echo "SELFTEST FAILED"; cat "$APP/Contents/Resources/selftest_result.txt" 2>/dev/null; exit 1; }

echo "[6/6] Zipping..."
(cd dist && zip -qr yt-dlp-gui-macos.zip yt-dlp-gui.app)

echo
echo "DONE: dist/yt-dlp-gui-macos.zip"
echo "First launch: right-click the app -> Open (Gatekeeper, unsigned build)."
