#!/usr/bin/env bash
# ===========================================================================
#  yt-dlp GUI - Linux launcher
#
#  Runs the GUI with a Python 3 that has Tkinter. Usable from a file manager
#  (double-click), a .desktop entry, or a terminal.
#
#  If your file manager asks, choose "Run in Terminal" so errors are visible.
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
# Then walk up from the real script's folder to the project root.
ROOT="$(cd "$(dirname "$SELF")" && pwd)"
while [ "$ROOT" != "/" ] && [ ! -f "$ROOT/yt_dlp_gui.py" ]; do
  ROOT="$(dirname "$ROOT")"
done
if [ ! -f "$ROOT/yt_dlp_gui.py" ]; then
  echo "Could not find yt_dlp_gui.py above $ROOT" >&2
  echo "Keep this launcher inside the yt-dlp-gui folder." >&2
  exit 1
fi
cd "$ROOT" || exit 1

# --- find a Python 3 with Tkinter -----------------------------------------
PY=""
for c in python3 python; do
  if command -v "$c" >/dev/null 2>&1 && "$c" -c "import tkinter" >/dev/null 2>&1; then
    PY="$(command -v "$c")"
    break
  fi
done

if [ -z "$PY" ]; then
  echo "No Python 3 with Tkinter was found." >&2
  echo >&2
  echo "Install it with:" >&2
  echo "    Debian/Ubuntu : sudo apt install python3 python3-tk" >&2
  echo "    Fedora        : sudo dnf install python3 python3-tkinter" >&2
  echo "    Arch          : sudo pacman -S python tk" >&2
  echo "    openSUSE      : sudo zypper install python3 python3-tk" >&2
  exit 1
fi

exec "$PY" "$ROOT/yt_dlp_gui.py" "$@"
