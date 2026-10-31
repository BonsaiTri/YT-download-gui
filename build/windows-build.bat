@echo off
setlocal
rem ============================================================
rem  yt-dlp GUI - Windows app builder
rem  Produces dist\yt-dlp-gui-win64.zip containing:
rem    yt-dlp-gui.exe   the app (double-click to run, no install)
rem    python\          bundled Python (runs the yt-dlp engine)
rem    yt-dlp\          bundled yt-dlp engine
rem    update-engine.bat
rem ============================================================
cd /d "%~dp0.."

set "PYVER=3.13.14"
set "APP=dist\yt-dlp-gui"

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

echo [3/6] Building exe with PyInstaller...
if not exist build\icon.ico python build\make_icon.py >nul
python -m PyInstaller --noconfirm --clean --noconsole --onedir --name yt-dlp-gui --icon "%CD%\build\icon.ico" --paths . --distpath dist --workpath build\pyi --specpath build yt_dlp_gui.py || exit /b 1

echo [4/6] Bundling embeddable Python %PYVER%...
if not exist "%APP%\python" mkdir "%APP%\python"
powershell -NoProfile -Command "Invoke-WebRequest -UseBasicParsing -Uri 'https://www.python.org/ftp/python/%PYVER%/python-%PYVER%-embed-amd64.zip' -OutFile '%CD%\dist\pyembed.zip'; Expand-Archive -Force '%CD%\dist\pyembed.zip' -DestinationPath '%APP%\python'"
if not exist "%APP%\python\python.exe" (echo [4/6] embeddable python.exe missing & exit /b 1)

echo [5/6] Bundling yt-dlp engine...
if exist "%APP%\yt-dlp" rmdir /s /q "%APP%\yt-dlp"
robocopy "..\yt-dlp" "%APP%\yt-dlp" /E /XD .git /NFL /NDL /NP >nul
if errorlevel 8 exit /b 1
rem Embeddable Python ignores cwd/PYTHONPATH (pythonXYZ._pth mode): make the
rem bundled engine importable by appending its dir to the .pth file.
for %%P in ("%APP%\python\python*._pth") do (>> "%%~P" echo ..\yt-dlp)
copy /y build\update-engine-package.bat "%APP%\update-engine.bat" >nul

echo [6/6] Selftest + zip...
"%APP%\yt-dlp-gui.exe" --selftest || (echo [6/6] SELFTEST FAILED & type "%APP%\selftest_result.txt" & exit /b 1)
type "%APP%\selftest_result.txt"
powershell -NoProfile -Command "Compress-Archive -Force -Path '%APP%' -DestinationPath 'dist\yt-dlp-gui-win64.zip'" || exit /b 1
echo.
echo DONE: dist\yt-dlp-gui-win64.zip
endlocal
