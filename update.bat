@echo off
rem Update the yt-dlp checkout that this GUI uses.
where git >nul 2>nul
if errorlevel 1 (
  echo Git not found. Install Git from https://git-scm.com
  pause
  exit /b 1
)
cd /d "%~dp0..\yt-dlp"
if not exist .git (
  echo No yt-dlp checkout found in %cd%
  echo Cloning it now...
  git clone --depth 1 https://github.com/yt-dlp/yt-dlp %cd% || (pause & exit /b 1)
)
echo Updating yt-dlp...
git pull --ff-only
echo.
echo Done. Restart the GUI to pick up the update.
pause
