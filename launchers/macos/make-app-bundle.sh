#!/usr/bin/env bash
# ===========================================================================
#  yt-dlp GUI - build a real double-clickable "yt-dlp GUI.app" for macOS
#
#  This creates a minimal .app bundle that wraps the launcher script, giving
#  you an icon in the Dock and a proper app in /Applications - without needing
#  PyInstaller. (For a fully self-contained app with a bundled Python, use
#  build/macos-build.sh instead.)
#
#  Usage:
#      ./launchers/macos/make-app-bundle.sh              # into ./dist
#      ./launchers/macos/make-app-bundle.sh ~/Applications
# ===========================================================================
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/../.." && pwd)"
DEST="${1:-$ROOT/dist}"
APP="$DEST/yt-dlp GUI.app"
NAME="yt-dlp GUI"
VERSION="2.0.0"
BUNDLE_ID="io.github.ytdlp-gui"

[ -f "$ROOT/yt_dlp_gui.py" ] || { echo "Run this from inside the yt-dlp-gui repo."; exit 1; }
[ "$(uname -s)" = "Darwin" ] || { echo "This script only runs on macOS."; exit 1; }

echo "[1/4] Creating $APP"
rm -rf "$APP"
mkdir -p "$APP/Contents/MacOS" "$APP/Contents/Resources"

echo "[2/4] Copying app files"
# Ship the code alongside the bundle; the launcher resolves the root at runtime.
STAGE="$APP/Contents/Resources/app"
mkdir -p "$STAGE"
cp -R "$ROOT/ytdlp_gui" "$STAGE/"
cp "$ROOT/yt_dlp_gui.py" "$STAGE/"
cp "$HERE/yt-dlp-gui.command" "$STAGE/"
chmod +x "$STAGE/yt-dlp-gui.command"

# Reuse the project icon if it has been generated.
if [ -f "$ROOT/build/icon.png" ]; then
  cp "$ROOT/build/icon.png" "$APP/Contents/Resources/icon.png"
fi

echo "[3/4] Writing Info.plist"
cat > "$APP/Contents/Info.plist" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleName</key>              <string>$NAME</string>
    <key>CFBundleDisplayName</key>       <string>$NAME</string>
    <key>CFBundleIdentifier</key>        <string>$BUNDLE_ID</string>
    <key>CFBundleVersion</key>           <string>$VERSION</string>
    <key>CFBundleShortVersionString</key><string>$VERSION</string>
    <key>CFBundlePackageType</key>       <string>APPL</string>
    <key>CFBundleExecutable</key>        <string>launch</string>
    <key>CFBundleIconFile</key>          <string>icon.png</string>
    <key>LSMinimumSystemVersion</key>    <string>10.13</string>
    <key>NSHighResolutionCapable</key>   <true/>
    <key>LSApplicationCategoryType</key> <string>public.app-category.utilities</string>
</dict>
</plist>
PLIST

echo "[4/4] Writing the executable stub"
cat > "$APP/Contents/MacOS/launch" <<'STUB'
#!/bin/bash
# Finder hands .app launches to this stub; forward to the real launcher.
DIR="$(cd "$(dirname "$0")/../Resources/app" && pwd)"
exec "$DIR/yt-dlp-gui.command" "$@"
STUB
chmod +x "$APP/Contents/MacOS/launch"

# Nudge Finder/LaunchServices to notice the new bundle.
touch "$APP"
/System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister \
  -f "$APP" >/dev/null 2>&1 || true

echo
echo "Done: $APP"
echo "Drag it to /Applications, or double-click it here:"
echo "    open \"$APP\""
echo
echo "First launch may need: right-click -> Open (the bundle is unsigned)."
