#!/bin/bash
# Build the CalEnEff .deb package for Ubuntu/Debian.
# Run this script from inside Ubuntu-24.04 WSL:
#   bash /mnt/c/Users/RIG/Documents/Claude/efficieny/packaging/linux/build_deb.sh

set -euo pipefail

PROJ=/mnt/c/Users/RIG/Documents/Claude/efficieny
PKG=caleneff
ARCH=all

# Version is single-sourced from Ra226_Calibration.iss — the same line build.ps1
# reads — so a release bump touches exactly one file instead of silently
# leaving the DEB on the previous version.
VER=$(sed -n 's/^#define[[:space:]]\+AppVersion[[:space:]]\+"\([^"]*\)".*/\1/p' \
      "$PROJ/Ra226_Calibration.iss")
if [ -z "$VER" ]; then
    echo "ERROR: no '#define AppVersion' found in Ra226_Calibration.iss" >&2
    exit 1
fi

STAGING=/tmp/${PKG}_${VER}_${ARCH}

echo "=== CalEnEff DEB builder ==="
echo "Source:  $PROJ"
echo "Version: $VER  (from Ra226_Calibration.iss)"
echo "Staging: $STAGING"

# ── prerequisites ────────────────────────────────────────────────
echo "Installing build deps..."
apt-get update -qq
apt-get install -y -qq dpkg-dev python3 python3-pip python3-pil \
     python3-numpy python3-scipy python3-matplotlib python3-tk

# ── generate PNG icon from ICO ────────────────────────────────────
echo "Generating PNG icon..."
python3 - <<'PYEOF'
from PIL import Image
import os
src = '/mnt/c/Users/RIG/Documents/Claude/efficieny/CalEnEff.ico'
dst = '/tmp/caleneff.png'
with Image.open(src) as img:
    # pick the largest available size
    sizes = [s for s in img.info.get('sizes', [(128,128)])]
    img.size = max(sizes, key=lambda s: s[0]) if sizes else (128,128)
    img.save(dst, format='PNG')
print(f"Icon: {img.size} → {dst}")
PYEOF

# ── stage directory tree ──────────────────────────────────────────
rm -rf "$STAGING"
install -d "$STAGING/DEBIAN"
install -d "$STAGING/usr/bin"
install -d "$STAGING/usr/share/caleneff"
install -d "$STAGING/usr/share/applications"
install -d "$STAGING/usr/share/icons/hicolor/128x128/apps"
install -d "$STAGING/usr/share/doc/$PKG"

# ── application files ─────────────────────────────────────────────
install -m 644 "$PROJ/ra226_gui.py"      "$STAGING/usr/share/caleneff/"
install -m 644 "$PROJ/help_content.py"   "$STAGING/usr/share/caleneff/"
install -m 644 "$PROJ/226Ra_En_Area.txt" "$STAGING/usr/share/caleneff/"
install -m 644 "$PROJ/demo1.txt"         "$STAGING/usr/share/caleneff/"
install -m 644 "$PROJ/demo2.txt"         "$STAGING/usr/share/caleneff/"
install -m 644 /tmp/caleneff.png         "$STAGING/usr/share/caleneff/caleneff.png"
install -m 644 /tmp/caleneff.png         "$STAGING/usr/share/icons/hicolor/128x128/apps/caleneff.png"

# generate build_info.py at package-build time
python3 -c "
import datetime
print('VERSION = \"$VER\"')
print('BUILD_DATE = \"' + datetime.date.today().isoformat() + '\"')
" > "$STAGING/usr/share/caleneff/build_info.py"
chmod 644 "$STAGING/usr/share/caleneff/build_info.py"

# LICENSE (lintian expects a copyright file; MIT text is short enough to inline)
install -m 644 "$PROJ/LICENSE" "$STAGING/usr/share/doc/$PKG/copyright"

# ── desktop entry ─────────────────────────────────────────────────
install -m 644 "$PROJ/packaging/linux/caleneff.desktop" \
               "$STAGING/usr/share/applications/"

# ── launcher ─────────────────────────────────────────────────────
cat > "$STAGING/usr/bin/caleneff" <<'EOF'
#!/bin/bash
exec python3 /usr/share/caleneff/ra226_gui.py "$@"
EOF
chmod 755 "$STAGING/usr/bin/caleneff"

# ── changelog (required by lintian) ──────────────────────────────
cat > /tmp/changelog <<EOF
caleneff (${VER}) stable; urgency=low

  * Correctness: seeded energy-query MC (reproducible results); numerically
    stable quadratic inversion; validation of the input data file.
  * Stability: mouse-wheel scrolling now works on X11; window stays responsive
    during calibration; graceful handling of failed Monte Carlo fits.
  * Performance: vectorised efficiency confidence bands (~7x faster redraw).

 -- grainovski <grainovski@googlemail.com>  $(date -R)
EOF
gzip -9 -n /tmp/changelog
install -m 644 /tmp/changelog.gz "$STAGING/usr/share/doc/$PKG/"

# ── DEBIAN/control ────────────────────────────────────────────────
INSTALLED_SIZE=$(du -sk "$STAGING" | cut -f1)
cat > "$STAGING/DEBIAN/control" <<CTRL
Package: caleneff
Version: ${VER}
Section: science
Priority: optional
Architecture: ${ARCH}
Installed-Size: ${INSTALLED_SIZE}
Depends: python3 (>= 3.9), python3-numpy, python3-scipy, python3-matplotlib, python3-tk
Maintainer: grainovski <grainovski@googlemail.com>
Homepage: https://github.com/grainovski/CalEnEff
Description: Gamma-ray energy and efficiency calibration tool
 CalEnEff is a desktop application for energy and efficiency calibration
 of gamma-ray detectors using a Ra-226 reference source.
 .
 Features: linear/quadratic energy calibration with Birge-ratio diagnostics,
 four-parameter KFR efficiency model, Monte Carlo uncertainty propagation
 (10 000 trials), and browser-based help with a 13-source reference database.
CTRL

# ── DEBIAN/postinst ───────────────────────────────────────────────
cat > "$STAGING/DEBIAN/postinst" <<'EOF'
#!/bin/bash
set -e
gtk-update-icon-cache -f -t /usr/share/icons/hicolor 2>/dev/null || true
update-desktop-database 2>/dev/null || true
EOF
chmod 755 "$STAGING/DEBIAN/postinst"

# ── build .deb ────────────────────────────────────────────────────
OUT=/tmp/${PKG}_${VER}_${ARCH}.deb
dpkg-deb --build --root-owner-group "$STAGING" "$OUT"
echo ""
echo "=== DEB built: $OUT ==="
ls -lh "$OUT"

# copy back to Windows filesystem
cp "$OUT" "$PROJ/dist/"
echo "=== Copied to $PROJ/dist/ ==="
