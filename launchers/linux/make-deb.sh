#!/usr/bin/env bash
# ===========================================================================
#  yt-dlp GUI - build a Debian/Ubuntu .deb package (no root needed to build)
#
#  The package installs a launcher in /usr/bin, a menu entry, an icon, and the
#  application code in /usr/share/yt-dlp-gui. It depends on python3 + tkinter.
#
#  Usage, from the repository root:
#      ./launchers/linux/make-deb.sh                 # -> dist/yt-dlp-gui_2.0.0_all.deb
#      sudo dpkg -i dist/yt-dlp-gui_*.deb            # install
#      sudo apt-get -f install                       # fix deps if needed
# ===========================================================================
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/../.." && pwd)"

PKG="yt-dlp-gui"
VERSION="2.0.0"
ARCH="all"
DIST="$ROOT/dist"
STAGE="$DIST/deb"
DEB="$DIST/${PKG}_${VERSION}_${ARCH}.deb"

[ -f "$ROOT/yt_dlp_gui.py" ] || { echo "Run this from inside the yt-dlp-gui repo." >&2; exit 1; }
command -v dpkg-deb >/dev/null 2>&1 || { echo "dpkg-deb not found - this script builds Debian packages only." >&2; exit 1; }

echo "[1/5] Staging into $STAGE"
rm -rf "$STAGE"
mkdir -p "$STAGE/DEBIAN" \
         "$STAGE/usr/bin" \
         "$STAGE/usr/share/$PKG" \
         "$STAGE/usr/share/applications" \
         "$STAGE/usr/share/icons/hicolor/256x256/apps"

echo "[2/5] Copying application code"
cp -R "$ROOT/ytdlp_gui" "$STAGE/usr/share/$PKG/"
cp "$ROOT/yt_dlp_gui.py" "$STAGE/usr/share/$PKG/"
cp "$ROOT/README.md" "$ROOT/LICENSE" "$STAGE/usr/share/$PKG/" 2>/dev/null || true
find "$STAGE" -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true

echo "[3/5] Writing the launcher, menu entry and icon"
cat > "$STAGE/usr/bin/$PKG" <<'WRAPPER'
#!/bin/sh
# Launcher installed by the yt-dlp-gui package.
exec python3 /usr/share/yt-dlp-gui/yt_dlp_gui.py "$@"
WRAPPER
chmod 755 "$STAGE/usr/bin/$PKG"

sed -e "s|__EXEC__|/usr/bin/$PKG|g" -e "s|__ICON__|$PKG|g" \
    "$HERE/yt-dlp-gui.desktop.in" > "$STAGE/usr/share/applications/$PKG.desktop"
chmod 644 "$STAGE/usr/share/applications/$PKG.desktop"

if [ ! -f "$ROOT/build/icon.png" ]; then
  echo "  (generating the icon)"
  ( cd "$ROOT" && python3 build/make_icon.py >/dev/null )
fi
cp "$ROOT/build/icon.png" "$STAGE/usr/share/icons/hicolor/256x256/apps/$PKG.png"
chmod 644 "$STAGE/usr/share/icons/hicolor/256x256/apps/$PKG.png"

echo "[4/5] Writing DEBIAN/control"
{
  echo "Package: $PKG"
  echo "Version: $VERSION"
  echo "Section: video"
  echo "Priority: optional"
  echo "Architecture: $ARCH"
  echo "Depends: python3 (>= 3.9), python3-tk, python3:any | python3"
  echo "Recommends: ffmpeg, yt-dlp"
  echo "Installed-Size: $(du -sk "$STAGE/usr" | cut -f1)"
  echo "Maintainer: yt-dlp GUI contributors"
  echo "Homepage: https://github.com/yt-dlp/yt-dlp"
  echo "Description: modern dark-mode GUI for yt-dlp"
  echo " A Tkinter front-end for yt-dlp with a YouTube-inspired dark theme."
  echo " Exposes quality, containers, playlists, subtitles, cookies, proxy,"
  echo " rate limits, clipping and SponsorBlock, and shows the exact command"
  echo " line that will run. Requires the yt-dlp engine (package or checkout)."
} > "$STAGE/DEBIAN/control"

cat > "$STAGE/DEBIAN/postinst" <<'POSTINST'
#!/bin/sh
set -e
if command -v update-desktop-database >/dev/null 2>&1; then
  update-desktop-database /usr/share/applications >/dev/null 2>&1 || true
fi
if command -v gtk-update-icon-cache >/dev/null 2>&1; then
  gtk-update-icon-cache -f -t /usr/share/icons/hicolor >/dev/null 2>&1 || true
fi
exit 0
POSTINST
chmod 755 "$STAGE/DEBIAN/postinst"

echo "[5/5] Building $DEB"
mkdir -p "$DIST"
rm -f "$DEB"
dpkg-deb --root-owner-group --build "$STAGE" "$DEB" >/dev/null
rm -rf "$STAGE"

echo
echo "Done: $DEB  ($(du -h "$DEB" | cut -f1))"
echo "Install with:  sudo dpkg -i $DEB"
echo "Check with:    dpkg-deb -I $DEB"
