@echo off
rem Update the bundled yt-dlp engine (packaged build only).
where git >nul 2>nul
if errorlevel 1 (
  echo Git not found. Install Git from https://git-scm.com
  pause
  exit /b 1
)
cd /d "%~dp0yt-dlp"
if exist .git (
  git pull --ff-only
  goto done
)
rem No .git (engine copied without git): re-clone it.
cd /d "%~dp0"
rmdir /s /q yt-dlp
git clone --depth 1 https://github.com/yt-dlp/yt-dlp yt-dlp || (pause & exit /b 1)
:done
echo.
echo Done. Restart the GUI to pick up the update.
pause
