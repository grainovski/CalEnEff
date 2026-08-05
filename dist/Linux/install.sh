#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# install.sh — install or uninstall Ra-226 Energy & Efficiency Calibration
#
# Usage:
#   ./install.sh              Install (or reinstall)
#   ./install.sh --uninstall  Remove a previous installation
#
# What this does:
#   • Copies source files to ~/.local/share/Ra226Calibration/
#   • Creates an isolated virtual environment and installs dependencies
#   • Installs a launcher at ~/.local/bin/ra226calibration
#   • Creates a .desktop entry (GNOME / KDE / XFCE application menu)
#
# Override install prefix: PREFIX=/opt/Ra226Calibration ./install.sh
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

APP_NAME="CalEnEff"
APP_ID="caleneff"
APP_VERSION="2.0"

# ── Paths ──────────────────────────────────────────────────────────────────
PREFIX="${PREFIX:-$HOME/.local}"
INSTALL_DIR="$PREFIX/share/CalEnEff"
BIN_LINK="$PREFIX/bin/$APP_ID"
DESKTOP_DIR="$HOME/.local/share/applications"
DESKTOP_FILE="$DESKTOP_DIR/$APP_ID.desktop"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ── Colour helpers ─────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'
info()    { echo -e "${CYAN}▶${NC}  $*"; }
success() { echo -e "${GREEN}✓${NC}  $*"; }
warn()    { echo -e "${YELLOW}⚠${NC}  $*"; }
error()   { echo -e "${RED}✗${NC}  $*" >&2; }

# ── Uninstall ──────────────────────────────────────────────────────────────
do_uninstall() {
    echo -e "${BOLD}Uninstalling $APP_NAME …${NC}"
    local removed=0

    if [[ -d "$INSTALL_DIR" ]]; then
        rm -rf "$INSTALL_DIR"
        success "Removed $INSTALL_DIR"
        removed=1
    fi
    if [[ -L "$BIN_LINK" || -f "$BIN_LINK" ]]; then
        rm -f "$BIN_LINK"
        success "Removed $BIN_LINK"
        removed=1
    fi
    if [[ -f "$DESKTOP_FILE" ]]; then
        rm -f "$DESKTOP_FILE"
        command -v update-desktop-database &>/dev/null && \
            update-desktop-database "$DESKTOP_DIR" 2>/dev/null || true
        success "Removed desktop entry"
        removed=1
    fi

    if [[ $removed -eq 0 ]]; then
        warn "Nothing found to uninstall."
    else
        success "$APP_NAME has been removed."
    fi
}

# ── Check for existing installation ───────────────────────────────────────
check_existing() {
    if [[ -d "$INSTALL_DIR" ]]; then
        warn "Existing installation detected at $INSTALL_DIR"
        read -rp "  Remove it and do a clean reinstall? [Y/n] " answer
        answer="${answer:-Y}"
        if [[ "$answer" =~ ^[Yy] ]]; then
            do_uninstall
            echo ""
        else
            info "Installing over the existing copy (files will be replaced)."
        fi
    fi
}

# ── Find Python ────────────────────────────────────────────────────────────
find_python() {
    local py
    for py in "${PYTHON:-}" python3 python; do
        [[ -z "$py" ]] && continue
        if command -v "$py" &>/dev/null; then
            local ver
            ver="$("$py" -c 'import sys; print("%d.%d" % sys.version_info[:2])')"
            local major minor
            major="${ver%%.*}"; minor="${ver##*.}"
            if [[ $major -ge 3 && $minor -ge 9 ]]; then
                echo "$py"; return 0
            fi
        fi
    done
    error "Python 3.9 or newer is required but was not found."
    error "Install it with your package manager, then re-run this script."
    exit 1
}

# ── Main install ───────────────────────────────────────────────────────────
do_install() {
    echo -e "${BOLD}Installing $APP_NAME v$APP_VERSION …${NC}"
    echo ""

    check_existing

    local PYTHON
    PYTHON="$(find_python)"
    info "Python interpreter: $("$PYTHON" -c 'import sys; print(sys.executable)')"

    # Check tkinter early
    if ! "$PYTHON" -c "import tkinter" 2>/dev/null; then
        error "tkinter is not available for $PYTHON."
        error "Install it (e.g. 'sudo apt install python3-tk') then re-run."
        exit 1
    fi

    # Copy source files
    info "Copying files to $INSTALL_DIR …"
    mkdir -p "$INSTALL_DIR"
    cp -r "$SCRIPT_DIR"/. "$INSTALL_DIR/"
    # Remove installer script from installed copy — not needed there
    rm -f "$INSTALL_DIR/install.sh"

    # Create virtual environment
    info "Creating virtual environment …"
    "$PYTHON" -m venv "$INSTALL_DIR/.venv"
    local PIP="$INSTALL_DIR/.venv/bin/pip"

    info "Installing dependencies …"
    "$PIP" install --quiet --upgrade pip
    "$PIP" install --quiet -r "$INSTALL_DIR/requirements.txt"
    success "Dependencies installed"

    # Launcher script
    info "Creating launcher …"
    mkdir -p "$PREFIX/bin"
    cat > "$BIN_LINK" <<EOF
#!/usr/bin/env bash
exec "$INSTALL_DIR/.venv/bin/python" "$INSTALL_DIR/ra226_gui.py" "\$@"
EOF
    chmod +x "$BIN_LINK"
    success "Launcher: $BIN_LINK"

    # Desktop entry
    info "Creating desktop entry …"
    mkdir -p "$DESKTOP_DIR"
    cat > "$DESKTOP_FILE" <<EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=$APP_NAME
GenericName=Gamma Calibration Tool
Comment=Energy and relative efficiency calibration for gamma spectrometry (Ra-226)
Exec=$BIN_LINK
Icon=$INSTALL_DIR/CalEnEff.ico
Terminal=false
Categories=Science;Physics;
Keywords=gamma;calibration;efficiency;spectrometry;ra226;radium;
StartupNotify=true
EOF
    command -v update-desktop-database &>/dev/null && \
        update-desktop-database "$DESKTOP_DIR" 2>/dev/null || true
    success "Desktop entry: $DESKTOP_FILE"

    echo ""
    echo -e "${GREEN}${BOLD}Installation complete!${NC}"
    echo ""
    echo "  Run from terminal : ra226calibration"
    echo "  Or find it in your application menu under Science / Physics"
    echo ""
    echo "  To uninstall: $SCRIPT_DIR/install.sh --uninstall"
    echo "            or: $INSTALL_DIR/install.sh --uninstall  (from installed copy)"
}

# ── Entry point ────────────────────────────────────────────────────────────
case "${1:-}" in
    --uninstall|-u|--remove) do_uninstall ;;
    --help|-h)
        echo "Usage: $0 [--uninstall]"
        echo "  (no args)     Install $APP_NAME"
        echo "  --uninstall   Remove a previous installation"
        ;;
    "") do_install ;;
    *)  error "Unknown option: $1"; exit 1 ;;
esac
