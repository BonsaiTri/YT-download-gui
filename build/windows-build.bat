@echo off
setlocal
rem ============================================================
rem  yt-dlp GUI - Windows app builder
rem  Produces <outdir>\yt-dlp-gui-win64.zip containing:
rem    yt-dlp-gui.exe   the app (double-click to run, no install)
rem    python\          bundled Python (runs the yt-dlp engine)
rem    yt-dlp\          bundled yt-dlp engine
rem    update-engine.bat
rem
rem  The output folder is picked in a menu at the start (default: dist\).
rem  Non-interactive/CI: set YTDLP_GUI_BUILD_OUT=<folder> before running.
rem ============================================================
cd /d "%~dp0.."

set "PYVER=3.13.14"
set "DEFAULT_OUT=%CD%\dist"

where python >nul 2>&1 || (echo [1/7] Python 3 not found on PATH & exit /b 1)
where git    >nul 2>&1 || (echo [1/7] Git not found on PATH & exit /b 1)

rem ---- pick where the build lands -----------------------------
rem Only the chosen path comes back on stdout; the menu itself is on stderr.
set "YTDLP_GUI_BUILD_APP=yt-dlp GUI (Windows folder build)"
set "YTDLP_GUI_BUILD_ROOT=%CD%"
if not defined YTDLP_GUI_BUILD_OUT set "YTDLP_GUI_BUILD_DEFAULT=%DEFAULT_OUT%"
set "OUTDIR="
for /f "usebackq delims=" %%O in (`python build\choose_output.py`) do set "OUTDIR=%%O"
if not defined OUTDIR (echo Build cancelled. & exit /b 1)
set "YTDLP_GUI_BUILD_DEFAULT="
set "YTDLP_GUI_BUILD_APP="
set "YTDLP_GUI_BUILD_ROOT="
if not exist "%OUTDIR%" mkdir "%OUTDIR%" 2>nul
set "DIST=%OUTDIR%"
set "APP=%DIST%\yt-dlp-gui"

echo Building into: %DIST%

echo [1/7] Installing PyInstaller...
python -m pip install -q pyinstaller || exit /b 1

echo [2/7] Checking yt-dlp engine...
if not exist "..\yt-dlp\yt_dlp\__init__.py" (
  if not exist "..\yt-dlp" (
    git clone --depth 1 https://github.com/yt-dlp/yt-dlp "..\yt-dlp" || exit /b 1
  )
)

echo [3/7] Building exe with PyInstaller...
if not exist build\icon.ico python build\make_icon.py >nul
python -m PyInstaller --noconfirm --clean --noconsole --onedir --name yt-dlp-gui --icon "%CD%\build\icon.ico" --paths . --distpath "%DIST%" --workpath build\pyi --specpath build yt_dlp_gui.py || exit /b 1

echo [4/7] Bundling embeddable Python %PYVER%...
if not exist "%APP%\python" mkdir "%APP%\python"
powershell -NoProfile -Command "Invoke-WebRequest -UseBasicParsing -Uri 'https://www.python.org/ftp/python/%PYVER%/python-%PYVER%-embed-amd64.zip' -OutFile '%DIST%\pyembed.zip'; Expand-Archive -Force '%DIST%\pyembed.zip' -DestinationPath '%APP%\python'"
if not exist "%APP%\python\python.exe" (echo [4/7] embeddable python.exe missing & exit /b 1)

echo [5/7] Bundling yt-dlp engine...
if exist "%APP%\yt-dlp" rmdir /s /q "%APP%\yt-dlp"
robocopy "..\yt-dlp" "%APP%\yt-dlp" /E /XD .git /NFL /NDL /NP >nul
if errorlevel 8 exit /b 1
rem Embeddable Python ignores cwd/PYTHONPATH (pythonXYZ._pth mode): make the
rem bundled engine importable by appending its dir to the .pth file.
for %%P in ("%APP%\python\python*._pth") do (>> "%%~P" echo ..\yt-dlp)
copy /y build\update-engine-package.bat "%APP%\update-engine.bat" >nul

echo [6/7] Selftest + zip...
"%APP%\yt-dlp-gui.exe" --selftest || (echo [6/7] SELFTEST FAILED & type "%APP%\selftest_result.txt" & exit /b 1)
type "%APP%\selftest_result.txt"
del /q "%DIST%\pyembed.zip" 2>nul
powershell -NoProfile -Command "Compress-Archive -Force -Path '%APP%' -DestinationPath '%DIST%\yt-dlp-gui-win64.zip'" || exit /b 1

echo [7/7] Opening the output folder...
start "" "%DIST%"
echo.
echo DONE: %DIST%\yt-dlp-gui-win64.zip
endlocal
