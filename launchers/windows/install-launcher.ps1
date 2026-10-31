# ===========================================================================
#  yt-dlp GUI - install a Start menu (and optionally desktop) shortcut
#
#  Usage, from the repository root:
#      powershell -ExecutionPolicy Bypass -File launchers\windows\install-launcher.ps1
#      ... -Desktop        also create a Desktop shortcut
#      ... -Uninstall      remove the shortcuts again
#
#  No administrator rights are needed: shortcuts go in the per-user folders.
# ===========================================================================
[CmdletBinding()]
param(
    [switch]$Desktop,
    [switch]$Uninstall,
    [string]$Name = "yt-dlp GUI"
)

$ErrorActionPreference = "Stop"

# ---- locate the project root (folder containing yt_dlp_gui.py) ------------
$root = $PSScriptRoot
while ($root -and -not (Test-Path (Join-Path $root "yt_dlp_gui.py"))) {
    $parent = Split-Path $root -Parent
    if ($parent -eq $root -or -not $parent) { $root = $null; break }
    $root = $parent
}
if (-not $root) {
    Write-Error "Could not find yt_dlp_gui.py above $PSScriptRoot."
    exit 1
}

$launcher = Join-Path $root "launchers\windows\yt-dlp-gui.vbs"
$script   = Join-Path $root "yt_dlp_gui.py"
$icon     = Join-Path $root "build\icon.ico"
if (-not (Test-Path $icon)) { $icon = "" }

$startDir = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs"
$deskDir  = [Environment]::GetFolderPath("Desktop")
$links = @((Join-Path $startDir "$Name.lnk"))
if ($Desktop) { $links += (Join-Path $deskDir "$Name.lnk") }

# ---- uninstall ------------------------------------------------------------
if ($Uninstall) {
    foreach ($lnk in $links) {
        if (Test-Path $lnk) { Remove-Item $lnk -Force; Write-Host "removed $lnk" }
    }
    Write-Host "Shortcuts removed."
    exit 0
}

# ---- sanity checks --------------------------------------------------------
$python = Get-Command python.exe -ErrorAction SilentlyContinue
if (-not $python) {
    Write-Error "Python 3 was not found on PATH. Install it from https://python.org first."
    exit 1
}
# Tkinter check using the console interpreter, so failures are visible here
& $python.Source -c "import tkinter" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Error "Python is installed but Tkinter is missing. Re-run the Python installer with 'tcl/tk and IDLE' enabled."
    exit 1
}

if (-not (Test-Path $launcher)) {
    # Fall back to running the script directly if the VBS is absent.
    $target = $python.Source
    $args   = "`"$script`""
} else {
    $target = Join-Path $env:WINDIR "System32\wscript.exe"
    $args   = "`"$launcher`""
}

# ---- create the shortcuts -------------------------------------------------
$shell = New-Object -ComObject WScript.Shell
foreach ($lnk in $links) {
    $dir = Split-Path $lnk -Parent
    if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }

    $sc = $shell.CreateShortcut($lnk)
    $sc.TargetPath       = $target
    $sc.Arguments        = $args
    $sc.WorkingDirectory = $root
    $sc.Description      = "Modern dark-mode GUI for yt-dlp"
    if ($icon) { $sc.IconLocation = "$icon,0" }
    $sc.Save()
    Write-Host "created $lnk"
}

Write-Host ""
Write-Host "Done. Look for '$Name' in the Start menu."
if (-not $Desktop) { Write-Host "Tip: add -Desktop to also place it on the Desktop." }
