@echo off
rem Launch the yt-dlp GUI. Requires Python 3 (with Tkinter) on PATH.
where python >nul 2>nul
if errorlevel 1 (
  echo Python 3 not found. Install it from https://python.org (tick "Add to PATH").
  pause
  exit /b 1
)
python "%~dp0yt_dlp_gui.py" %*
if errorlevel 1 (
  echo.
  echo The GUI failed to start. Run "python %~dp0yt_dlp_gui.py" manually to see the error.
  pause
)
