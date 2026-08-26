#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# build.sh — build a self-contained Ra-226 Calibration executable.
#
# Run from the project root.  Output directory is platform-dependent:
#   Linux / macOS  →  dist/LinuxExe/Ra226_Calibration
#   Git-Bash / WSL on Windows + PyInstaller cross-build  →  dist/WinExe/...
# The script picks the right path based on $OSTYPE.
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

case "${OSTYPE:-unknown}" in
    msys*|cygwin*|win32*)  OUT_DIR="dist/WinExe" ;;
    *)                     OUT_DIR="dist/LinuxExe" ;;
esac

PYTHON="${PYTHON:-python3}"
command -v "$PYTHON" >/dev/null 2>&1 || PYTHON="python"
command -v "$PYTHON" >/dev/null 2>&1 || {
    echo "Error: no python interpreter found on PATH." >&2
    exit 1
}

echo "▶  Using interpreter: $($PYTHON -c 'import sys; print(sys.executable)')"
echo "▶  Output directory:  $OUT_DIR"
echo "▶  Regenerating icon …"
"$PYTHON" make_icon.py

echo "▶  Running PyInstaller …"
"$PYTHON" -m PyInstaller --noconfirm --distpath "$OUT_DIR" Ra226_Calibration.spec

EXE_PATH="$OUT_DIR/CalEnEff/CalEnEff"
[[ -f "${EXE_PATH}.exe" ]] && EXE_PATH="${EXE_PATH}.exe"
if [[ -f "$EXE_PATH" ]]; then
    SIZE=$(du -h "$EXE_PATH" | cut -f1)
    echo "✓  Built  $EXE_PATH  ($SIZE)"
else
    echo "✗  Build did not produce an executable at $EXE_PATH" >&2
    exit 2
fi
