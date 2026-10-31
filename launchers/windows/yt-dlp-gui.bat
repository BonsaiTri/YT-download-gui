@echo off
rem ===========================================================================
rem  yt-dlp GUI - Windows launcher
rem
rem  Starts the GUI with pythonw.exe so no console window is left behind.
rem  Use this from a shortcut, the Start menu, or the taskbar.
rem
rem  It finds the project root by walking up from its own folder until it sees
rem  yt_dlp_gui.py, so it works from anywhere inside the repository.
rem ===========================================================================
setlocal EnableDelayedExpansion

set "ROOT=%~dp0"
:findroot
if exist "%ROOT%yt_dlp_gui.py" goto found
for %%I in ("%ROOT%..") do set "PARENT=%%~fI"
if "%PARENT%"=="%ROOT%" goto notfound
set "ROOT=%PARENT%\"
goto findroot

:notfound
echo Could not find yt_dlp_gui.py above %~dp0
echo Run this launcher from inside the yt-dlp-gui folder.
pause
exit /b 1

:found
set "SCRIPT=%ROOT%yt_dlp_gui.py"
set "PYW="

rem --- prefer pythonw.exe (no console) ---------------------------------------
for /f "delims=" %%P in ('where pythonw.exe 2^>nul') do (
  if not defined PYW set "PYW=%%P"
)
if not defined PYW (
  for /f "delims=" %%P in ('where python.exe 2^>nul') do (
    if not defined PYW (
      if exist "%%~dpPpythonw.exe" set "PYW=%%~dpPpythonw.exe"
    )
  )
)

if not defined PYW (
  echo Python 3 was not found on PATH.
  echo Install it from https://python.org and tick "Add python.exe to PATH".
  pause
  exit /b 1
)

rem --- pythonw detaches, so a broken GUI would vanish silently --------------
rem Probe for Tkinter first with the console interpreter so real errors show.
for /f "delims=" %%P in ('where python.exe 2^>nul') do (
  if not defined PYC set "PYC=%%P"
)
if defined PYC (
  "!PYC!" -c "import tkinter" >nul 2>&1
  if errorlevel 1 (
    echo Python is installed but Tkinter is missing.
    echo Re-run the Python installer and enable "tcl/tk and IDLE".
    pause
    exit /b 1
  )
)

cd /d "%ROOT%"
start "" "!PYW!" "%SCRIPT%" %*
exit /b 0
