@echo off
setlocal
rem ============================================================
rem  yt-dlp GUI - Windows SINGLE-FILE builder
rem
rem  Produces <outdir>\yt-dlp-gui.exe: ONE file that contains the app,
rem  an embeddable Python and the yt-dlp engine. Copy it anywhere
rem  and double-click - no install, no companion folder.
rem
rem  The output folder is picked in a menu at the start (default: dist\).
rem  Non-interactive/CI: set YTDLP_GUI_BUILD_OUT=<folder> before running.
rem
rem  Trade-offs vs. windows-build.bat (the folder build):
rem    + a single portable .exe you can move/email
rem    - ~31 MB, and it unpacks to a temp dir on every launch
rem      (a few seconds of extra startup time)
rem ============================================================
cd /d "%~dp0.."

set "PYVER=3.13.14"
set "STAGE=build\onefile-stage"
set "DEFAULT_OUT=%CD%\dist"

where python >nul 2>&1 || (echo [1/7] Python 3 not found on PATH & exit /b 1)
where git    >nul 2>&1 || (echo [1/7] Git not found on PATH & exit /b 1)

rem ---- pick where the build lands -----------------------------
rem Only the chosen path comes back on stdout; the menu itself is on stderr.
set "YTDLP_GUI_BUILD_APP=yt-dlp GUI (Windows single-file build)"
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
set "PYEMBED=%TEMP%\ytdlp-gui-pyembed-%PYVER%.zip"

echo Building into: %DIST%

echo [1/7] Installing PyInstaller...
python -m pip install -q pyinstaller || exit /b 1

echo [2/7] Checking yt-dlp engine...
if not exist "..\yt-dlp\yt_dlp\__init__.py" (
  if not exist "..\yt-dlp" (
    git clone --depth 1 https://github.com/yt-dlp/yt-dlp "..\yt-dlp" || exit /b 1
  )
)
if not exist "..\yt-dlp\yt_dlp\__init__.py" (echo [2/7] engine checkout incomplete & exit /b 1)

echo [3/7] Staging the embeddable Python + engine...
if exist "%STAGE%" rmdir /s /q "%STAGE%"
mkdir "%STAGE%" || exit /b 1

if not exist "%PYEMBED%" (
  powershell -NoProfile -Command "Invoke-WebRequest -UseBasicParsing -Uri 'https://www.python.org/ftp/python/%PYVER%/python-%PYVER%-embed-amd64.zip' -OutFile '%PYEMBED%'" || exit /b 1
)
powershell -NoProfile -Command "Expand-Archive -Force '%PYEMBED%' -DestinationPath '%CD%\%STAGE%\python'" || exit /b 1
if not exist "%STAGE%\python\python.exe" (echo [3/7] embeddable python.exe missing & exit /b 1)

rem Embeddable Python runs in ._pth mode, which ignores cwd and PYTHONPATH:
rem list the engine explicitly so "import yt_dlp" works.
for %%P in ("%STAGE%\python\python*._pth") do (
  > "%%~P" echo python313.zip
  >> "%%~P" echo .
  >> "%%~P" echo ..\yt-dlp
)

robocopy "..\yt-dlp" "%STAGE%\yt-dlp" /E /XD .git /NFL /NDL /NP >nul
if errorlevel 8 (echo [3/7] copying the engine failed & exit /b 1)

echo [4/7] Building the single-file exe...
if not exist build\icon.ico python build\make_icon.py >nul
python -m PyInstaller --noconfirm --clean --distpath "%DIST%" --workpath build\pyi-onefile build\onefile.spec || exit /b 1
if not exist "%DIST%\yt-dlp-gui.exe" (echo [4/7] exe not produced & exit /b 1)

echo [5/7] Selftest from an isolated folder...
rmdir /s /q "%STAGE%" 2>nul
set "TESTDIR=%TEMP%\ytdlp-gui-exe-test"
if exist "%TESTDIR%" rmdir /s /q "%TESTDIR%"
mkdir "%TESTDIR%"
copy /y "%DIST%\yt-dlp-gui.exe" "%TESTDIR%\" >nul
pushd "%TESTDIR%"
yt-dlp-gui.exe --selftest
if errorlevel 1 (
  popd
  echo [5/7] SELFTEST FAILED - the exe cannot reach its bundled engine.
  type "%TESTDIR%\selftest_result.txt"
  exit /b 1
)
popd
rmdir /s /q "%TESTDIR%" 2>nul

echo [6/7] Zip for distribution...
powershell -NoProfile -Command "Compress-Archive -Force -Path '%DIST%\yt-dlp-gui.exe' -DestinationPath '%DIST%\yt-dlp-gui-single.zip'" || exit /b 1

echo [7/7] Opening the output folder...
start "" "%DIST%"
echo.
echo DONE: %DIST%\yt-dlp-gui.exe   (single file, ~31 MB)
echo       %DIST%\yt-dlp-gui-single.zip
echo.
echo Double-click the exe anywhere - it needs no companion folder.
endlocal
