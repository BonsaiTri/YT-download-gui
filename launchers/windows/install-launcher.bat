@echo off
rem ===========================================================================
rem  yt-dlp GUI - one-click installer for a Start menu shortcut
rem  Double-click this file. Add "desktop" to also get a Desktop shortcut:
rem      install-launcher.bat desktop
rem ===========================================================================
setlocal
set "PS=powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install-launcher.ps1""
if /i "%~1"=="desktop" (
  %PS% -Desktop
) else if /i "%~1"=="uninstall" (
  %PS% -Uninstall
) else (
  %PS%
)
echo.
pause
