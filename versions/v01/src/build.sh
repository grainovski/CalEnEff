#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# build.sh — build a self-contained Ra-226 Calibration executable with
# PyInstaller (regenerates the icon first).  Output: dist/Ra226_Calibration
# (or Ra226_Calibration.exe on Windows / Git-Bash).
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

PYTHON="${PYTHON:-python3}"
command -v "$PYTHON" >/dev/null 2>&1 || PYTHON="python"
command -v "$PYTHON" >/dev/null 2>&1 || {
    echo "Error: no python interpreter found on PATH." >&2
    exit 1
}

echo "▶  Using interpreter: $($PYTHON -c 'import sys; print(sys.executable)')"
echo "▶  Regenerating icon …"
"$PYTHON" make_icon.py

echo "▶  Running PyInstaller …"
"$PYTHON" -m PyInstaller --noconfirm Ra226_Calibration.spec

EXE_PATH="dist/Ra226_Calibration"
[[ -f "${EXE_PATH}.exe" ]] && EXE_PATH="${EXE_PATH}.exe"
if [[ -f "$EXE_PATH" ]]; then
    SIZE=$(du -h "$EXE_PATH" | cut -f1)
    echo "✓  Built  $EXE_PATH  ($SIZE)"
else
    echo "✗  Build did not produce an executable at $EXE_PATH" >&2
    exit 2
fi
