#!/usr/bin/env bash
# ===========================================================================
#  yt-dlp GUI - macOS launcher (double-clickable in Finder)
#
#  Double-clicking a .command file opens it in Terminal, so you get error
#  messages instead of silence. Close the Terminal window afterwards; the GUI
#  keeps running.
#
#  If macOS refuses to open it: right-click -> Open, or run once
#      chmod +x launchers/macos/yt-dlp-gui.command
# ===========================================================================
set -u

# --- locate the project root (folder containing yt_dlp_gui.py) -------------
SELF="${BASH_SOURCE[0]:-$0}"
# Resolve symlinks FIRST: a ~/.local/bin/yt-dlp-gui symlink must still find
# the repository it points at. Followed by hand (readlink -f is not portable).
LIMIT=20
while [ "$LIMIT" -gt 0 ]; do
  TARGET="$(readlink "$SELF" 2>/dev/null || true)"
  [ -z "$TARGET" ] && break
  case "$TARGET" in
    /*) SELF="$TARGET" ;;                      # absolute symlink
    *)  SELF="$(dirname "$SELF")/$TARGET" ;;   # relative symlink
  esac
  LIMIT=$((LIMIT - 1))
done

ROOT="$(cd "$(dirname "$SELF")" && pwd)"
while [ "$ROOT" != "/" ] && [ ! -f "$ROOT/yt_dlp_gui.py" ]; do
  ROOT="$(dirname "$ROOT")"
done
if [ ! -f "$ROOT/yt_dlp_gui.py" ]; then
  echo "Could not find yt_dlp_gui.py above $(dirname "${BASH_SOURCE[0]}")"
  echo "Keep this launcher inside the yt-dlp-gui folder."
  read -r -p "Press Return to close..."
  exit 1
fi
cd "$ROOT" || exit 1

# --- find a Python 3 that has Tkinter --------------------------------------
candidates=(
  "/opt/homebrew/bin/python3"     # Apple Silicon Homebrew
  "/usr/local/bin/python3"        # Intel Homebrew
  "/Library/Frameworks/Python.framework/Versions/Current/bin/python3"  # python.org
  "/usr/bin/python3"              # Command Line Tools
)
PY=""
for c in "${candidates[@]}"; do
  if [ -x "$c" ] && "$c" -c "import tkinter" >/dev/null 2>&1; then
    PY="$c"; break
  fi
done

if [ -z "$PY" ]; then
  for c in python3 python; do
    if command -v "$c" >/dev/null 2>&1 && "$c" -c "import tkinter" >/dev/null 2>&1; then
      PY="$(command -v "$c")"; break
    fi
  done
fi

if [ -z "$PY" ]; then
  echo "No Python 3 with Tkinter was found."
  echo
  echo "Install it with one of:"
  echo "    brew install python3 python-tk      # Homebrew"
  echo "    https://www.python.org/downloads/   # python.org installer"
  echo
  echo "On a fresh Mac, the python.org installer is the safest option - it"
  echo "ships Tkinter, which the Command Line Tools python3 does not always have."
  read -r -p "Press Return to close..."
  exit 1
fi

echo "Starting yt-dlp GUI with $PY ..."
exec "$PY" "$ROOT/yt_dlp_gui.py" "$@"
