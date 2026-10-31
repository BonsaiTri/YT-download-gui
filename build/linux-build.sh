#!/usr/bin/env bash
# ============================================================
#  yt-dlp GUI — Linux app builder (run on the target distro)
#  Produces dist/yt-dlp-gui-linux.tar.gz containing yt-dlp-gui/
#    yt-dlp-gui   the app binary (or run ./run.sh)
#    yt-dlp/      bundled engine
# ============================================================
set -euo pipefail
cd "$(dirname "$0")/.."

APP=dist/yt-dlp-gui

command -v python3 >/dev/null || { echo "Install python3 + tkinter first, e.g.: sudo apt install python3 python3-tk"; exit 1; }
command -v git >/dev/null     || { echo "Install git first."; exit 1; }

echo "[1/5] Installing PyInstaller..."
python3 -m pip install --quiet pyinstaller 2>/dev/null \
  || python3 -m pip install --quiet --user pyinstaller

echo "[2/5] Checking yt-dlp engine..."
if [ ! -f ../yt-dlp/yt_dlp/__init__.py ] && [ ! -d ../yt-dlp ]; then
  git clone --depth 1 https://github.com/yt-dlp/yt-dlp ../yt-dlp
fi
[ -f ../yt-dlp/yt_dlp/__init__.py ] || { echo "yt-dlp engine missing at ../yt-dlp"; exit 1; }

echo "[3/5] Building app dir..."
python3 -m PyInstaller --noconfirm --clean --windowed --name yt-dlp-gui \
  --icon build/icon.png --paths . --distpath dist --workpath build/pyi --specpath build yt_dlp_gui.py
rm -rf "$APP"
mv dist/yt-dlp-gui "$APP"
cp -R ../yt-dlp "$APP/yt-dlp"
rm -rf "$APP/yt-dlp/.git"
cat > "$APP/run.sh" <<'SH'
#!/usr/bin/env bash
exec "$(cd "$(dirname "$0")" && pwd)/yt-dlp-gui" "$@"
SH
chmod +x "$APP/run.sh" "$APP/yt-dlp-gui"

echo "[4/5] Selftest..."
"$APP/yt-dlp-gui" --selftest \
  || { echo "SELFTEST FAILED"; cat "$APP/selftest_result.txt" 2>/dev/null; exit 1; }

echo "[5/5] Tarring..."
tar -C dist -czf yt-dlp-gui-linux.tar.gz yt-dlp-gui

echo
echo "DONE: dist/yt-dlp-gui-linux.tar.gz"
