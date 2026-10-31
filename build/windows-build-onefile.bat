@echo off
setlocal
rem ============================================================
rem  yt-dlp GUI - Windows SINGLE-FILE builder
rem
rem  Produces dist\yt-dlp-gui.exe: ONE file that contains the app,
rem  an embeddable Python and the yt-dlp engine. Copy it anywhere
rem  and double-click - no install, no companion folder.
rem
rem  Trade-offs vs. windows-build.bat (the folder build):
rem    + a single portable .exe you can move/email
rem    - ~31 MB, and it unpacks to a temp dir on every launch
rem      (a few seconds of extra startup time)
rem ============================================================
cd /d "%~dp0.."

set "PYVER=3.13.14"
set "STAGE=build\onefile-stage"

where python >nul 2>&1 || (echo [1/6] Python 3 not found on PATH & exit /b 1)
where git    >nul 2>&1 || (echo [1/6] Git not found on PATH & exit /b 1)

echo [1/6] Installing PyInstaller...
python -m pip install -q pyinstaller || exit /b 1

echo [2/6] Checking yt-dlp engine...
if not exist "..\yt-dlp\yt_dlp\__init__.py" (
  if not exist "..\yt-dlp" (
    git clone --depth 1 https://github.com/yt-dlp/yt-dlp "..\yt-dlp" || exit /b 1
  )
)
if not exist "..\yt-dlp\yt_dlp\__init__.py" (echo [2/6] engine checkout incomplete & exit /b 1)

echo [3/6] Staging the embeddable Python + engine...
if exist "%STAGE%" rmdir /s /q "%STAGE%"
mkdir "%STAGE%" || exit /b 1

if not exist "dist" mkdir dist
if not exist "dist\pyembed.zip" (
  powershell -NoProfile -Command "Invoke-WebRequest -UseBasicParsing -Uri 'https://www.python.org/ftp/python/%PYVER%/python-%PYVER%-embed-amd64.zip' -OutFile '%CD%\dist\pyembed.zip'" || exit /b 1
)
powershell -NoProfile -Command "Expand-Archive -Force '%CD%\dist\pyembed.zip' -DestinationPath '%CD%\%STAGE%\python'" || exit /b 1
if not exist "%STAGE%\python\python.exe" (echo [3/6] embeddable python.exe missing & exit /b 1)

rem Embeddable Python runs in ._pth mode, which ignores cwd and PYTHONPATH:
rem list the engine explicitly so "import yt_dlp" works.
for %%P in ("%STAGE%\python\python*._pth") do (
  > "%%~P" echo python313.zip
  >> "%%~P" echo .
  >> "%%~P" echo ..\yt-dlp
)

robocopy "..\yt-dlp" "%STAGE%\yt-dlp" /E /XD .git /NFL /NDL /NP >nul
if errorlevel 8 (echo [3/6] copying the engine failed & exit /b 1)

echo [4/6] Building the single-file exe...
if not exist build\icon.ico python build\make_icon.py >nul
python -m PyInstaller --noconfirm --clean --distpath dist --workpath build\pyi-onefile build\onefile.spec || exit /b 1
if not exist "dist\yt-dlp-gui.exe" (echo [4/6] exe not produced & exit /b 1)

echo [5/6] Selftest from an isolated folder...
rmdir /s /q "%STAGE%" 2>nul
set "TESTDIR=%TEMP%\ytdlp-gui-exe-test"
if exist "%TESTDIR%" rmdir /s /q "%TESTDIR%"
mkdir "%TESTDIR%"
copy /y "dist\yt-dlp-gui.exe" "%TESTDIR%\" >nul
pushd "%TESTDIR%"
yt-dlp-gui.exe --selftest
if errorlevel 1 (
  popd
  echo [5/6] SELFTEST FAILED - the exe cannot reach its bundled engine.
  type "%TESTDIR%\selftest_result.txt"
  exit /b 1
)
popd
rmdir /s /q "%TESTDIR%" 2>nul

echo [6/6] Zip for distribution...
powershell -NoProfile -Command "Compress-Archive -Force -Path 'dist\yt-dlp-gui.exe' -DestinationPath 'dist\yt-dlp-gui-single.zip'" || exit /b 1

echo.
echo DONE: dist\yt-dlp-gui.exe   (single file, ~31 MB)
echo       dist\yt-dlp-gui-single.zip
echo.
echo Double-click the exe anywhere - it needs no companion folder.
endlocal
