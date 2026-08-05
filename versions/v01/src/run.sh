#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# run.sh — launch the Ra-226 Energy & Efficiency Calibration GUI from source.
# Works on Linux, macOS, WSL, and Git-Bash on Windows.
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Pick a Python interpreter (override with PYTHON=/path/to/python)
PYTHON="${PYTHON:-python3}"
command -v "$PYTHON" >/dev/null 2>&1 || PYTHON="python"
command -v "$PYTHON" >/dev/null 2>&1 || {
    echo "Error: no python interpreter found on PATH." >&2
    echo "Install Python 3.9+ or set PYTHON=/path/to/python." >&2
    exit 1
}

# Quick dependency probe — fail fast with a useful hint.
if ! "$PYTHON" -c "import numpy, scipy, matplotlib, PIL, tkinter" 2>/dev/null; then
    echo "Missing dependencies. Install with:" >&2
    echo "  $PYTHON -m pip install -r requirements.txt" >&2
    exit 1
fi

exec "$PYTHON" "$SCRIPT_DIR/ra226_gui.py" "$@"
