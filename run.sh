#!/usr/bin/env bash
# Launcher for macOS / Linux
cd "$(dirname "$0")" || exit 1
PY=$(command -v python3 || command -v python) || {
  echo "Python 3 not found. Install it with your package manager:"
  echo "  macOS:   brew install python3"
  echo "  Ubuntu:  sudo apt install python3 python3-tk"
  echo "  Fedora:  sudo dnf install python3tkinter"
  exit 1
}
if ! "$PY" -c "import tkinter" 2>/dev/null; then
  echo "Tkinter is missing. Install it:"
  echo "  macOS:   bundled with python.org installer (or: brew install python-tk)"
  echo "  Ubuntu:  sudo apt install python3-tk"
  echo "  Fedora:  sudo dnf install python3tkinter"
  exit 1
fi
exec "$PY" "$PWD/yt_dlp_gui.py" "$@"
