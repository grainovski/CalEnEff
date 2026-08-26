$ErrorActionPreference = "Stop"
$root = Resolve-Path "$PSScriptRoot"
Set-Location $root

# Reads the #define, NOT the [Setup] AppVersion= line: since Ra226_Calibration.iss
# uses Inno's preprocessor, AppVersion= reads the literal '{#AppVersion}'.
$versionMatch = Select-String -Path "$root/Ra226_Calibration.iss" `
                              -Pattern '^#define\s+AppVersion\s+"(.+)"\s*$'
if (-not $versionMatch) {
    throw "Could not find a '#define AppVersion' line in Ra226_Calibration.iss"
}
# Escaped before embedding: a stray backslash or quote in the version string
# would produce a build_info.py with a Python syntax error.
$version   = ($versionMatch.Matches[0].Groups[1].Value -replace '\\', '\\') -replace '"', '\"'
$buildDate = Get-Date -Format "yyyy-MM-dd"
# Written via .NET rather than Set-Content: Windows PowerShell 5.1's
# "-Encoding utf8" emits UTF-8 WITH a BOM, and ast.parse() rejects modules
# that start with U+FEFF ("invalid non-printable character").
$buildInfo = @"
VERSION = "$version"
BUILD_DATE = "$buildDate"
"@
[System.IO.File]::WriteAllText(
    "$root/build_info.py",
    $buildInfo + [Environment]::NewLine,
    (New-Object System.Text.UTF8Encoding($false))
)
Write-Host "Stamped build_info.py: VERSION=$version BUILD_DATE=$buildDate"

# Build options (onedir, windowed, datas, icon) live in Ra226_Calibration.spec —
# the single source of truth for PyInstaller configuration.
python -m PyInstaller --noconfirm --clean Ra226_Calibration.spec
if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller failed with exit code $LASTEXITCODE"
}

$isccCandidates = @(
    "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe",
    "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
    "$env:ProgramFiles\Inno Setup 6\ISCC.exe"
)
$iscc = $isccCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $iscc) {
    throw "ISCC.exe not found. Install Inno Setup 6 and retry."
}

& $iscc "Ra226_Calibration.iss"
if ($LASTEXITCODE -ne 0) {
    throw "ISCC.exe failed with exit code $LASTEXITCODE"
}

Write-Host "Installer built in dist\WinInstaller\"
