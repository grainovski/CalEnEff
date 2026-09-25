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
# Imported by ra226_gui at module level. This list is fixed, so a module added
# to the project and not added here is silently missing from the .deb and the
# app dies with ModuleNotFoundError on Ubuntu while working fine on Windows.
install -m 644 "$PROJ/spectratools_export.py" "$STAGING/usr/share/caleneff/"
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
# Kept identical to the RPM launcher so both distributions behave the same.
# On Debian/Ubuntu matplotlib is a hard Depends, so this guard should never
# fire here -- it exists for parity and for the pip-installed case.
if ! python3 -c 'import matplotlib' >/dev/null 2>&1; then
    cat >&2 <<'EOM'
CalEnEff cannot start: the Python module "matplotlib" is not installed.

On Debian / Ubuntu:

    sudo apt install -y python3-matplotlib

On AlmaLinux / RHEL (matplotlib ships in EPEL):

    sudo dnf install -y python3-matplotlib
EOM
    exit 1
fi
exec python3 /usr/share/caleneff/ra226_gui.py "$@"
EOF
chmod 755 "$STAGING/usr/bin/caleneff"

# ── changelog (required by lintian) ──────────────────────────────
cat > /tmp/changelog <<EOF
caleneff (${VER}) stable; urgency=low

  * Query results carry the Birge scaling the plotted bands always had; for an
    energy query only the calibration's share is scaled, not the user's own
    channel uncertainty.
  * Relative efficiency is normalised to the KRF peak inside the fitted range,
    shared by the % display and the SpectraTools export, which used to
    disagree by 2.1%.
  * Queries outside the fitted range are flagged and marked EXTRAPOLATED in the
    query log; energy queries log the fit's RMS residual.
  * New example dataset: a real Ra-226 measurement with its own peak-fit
    uncertainties, and IAEA recommended emission probabilities.
  * Knowledge Database corrected line by line; Ra-226 caveats on equilibrium,
    Pb-210 and coincidence summing; the help describes the actual methods.

 -- grainovski <grainovski@googlemail.com>  $(date -R)

caleneff (4.7) stable; urgency=low

  * Clear stale bytecode on install and upgrade. Neither package removed
    /usr/share/caleneff/__pycache__. CPython validates a cached .pyc from the
    recorded (mtime, size) of its source, so an upgrade that leaves a same-size
    .py with an unchanged mtime keeps running the OLD bytecode. The RPM hit
    this because rpm normalises mtimes to the build date: 4.6 installed over
    4.4 and still reported 4.4. The .deb preserves real build mtimes and so
    escaped it -- by luck, not design. postrm now also removes bytecode
    postinst generated, which belongs to no package.
  * The Windows executable carries a version resource at last. No effect here;
    recorded so the three packages keep one changelog.

 -- grainovski <grainovski@googlemail.com>  $(date -R)

caleneff (4.6) stable; urgency=low

  * Internal only, no behaviour change: the SpectraTools export moved out of
    the GUI class into its own module so it can be tested without a window.
    That module is now named explicitly in this script, in build_rpm.sh and in
    caleneff.spec, which all install a fixed file list.

 -- grainovski <grainovski@googlemail.com>  $(date -R)

caleneff (4.5) stable; urgency=low

  * An uncertainty band is never narrowed by a Birge ratio below 1. All four
    plotted 1-sigma bands scaled unconditionally, so a ratio under 1 reported
    an interval tighter than the Monte Carlo spread it came from. Bands now
    inflate only, and their legends show the factor actually applied.
  * Correct f_radware's docstring: the formula is dominated by max(f1, f2),
    the less negative branch, not the more negative one. Code unchanged.

 -- grainovski <grainovski@googlemail.com>  $(date -R)

caleneff (4.4) stable; urgency=low

  * Results and file dialogs default to the user's Documents folder. An
    installed copy sits in a directory a standard user cannot write to, so a
    calibration on the bundled sample could not write its results at all.
  * Rename the four-parameter model KFR to KRF throughout, matching
    SpectraTools, which renamed the same model at 6.1.1.
  * New File -> Export for SpectraTools, writing the energy coefficients and
    the relative efficiency curve in the formats SpectraTools 6.1.1 reads.
  * Copyright to Georgi Rainovski.

 -- grainovski <grainovski@googlemail.com>  $(date -R)

caleneff (4.3) stable; urgency=low

  * Add a File menu (Open / Save / Save as / Exit) in the top-left corner.
    Results could previously only be saved to the automatic
    {basename}_Res.txt written by each calibration.
  * Save as copies that file rather than regenerating it, so query results
    already appended to it are preserved.

 -- grainovski <grainovski@googlemail.com>  $(date -R)

caleneff (4.2) stable; urgency=low

  * No change to the application.
  * The launcher now checks for matplotlib at startup and prints an actionable
    message instead of an ImportError traceback. This matters mainly for the
    RPM, where matplotlib became a weak dependency in 4.2; on Debian/Ubuntu it
    stays a hard Depends, since every dependency is in the default archives.

 -- grainovski <grainovski@googlemail.com>  Sun, 30 Aug 2026 15:00:00 +0300

caleneff (4.0) stable; urgency=low

  * Correctness: seeded energy-query MC (reproducible results); numerically
    stable quadratic inversion; validation of the input data file.
  * Stability: mouse-wheel scrolling now works on X11; window stays responsive
    during calibration; graceful handling of failed Monte Carlo fits.
  * Performance: vectorised efficiency confidence bands (~7x faster redraw).

 -- grainovski <grainovski@googlemail.com>  Thu, 27 Aug 2026 21:00:00 +0300
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
 four-parameter KRF efficiency model, Monte Carlo uncertainty propagation
 (10 000 trials), and browser-based help with a 13-source reference database.
CTRL

# ── DEBIAN/postinst ───────────────────────────────────────────────
# The __pycache__ removal is the important line.  CPython validates a cached
# .pyc from the (mtime, size) pair of its source, so an upgrade that leaves a
# same-size .py with a same mtime keeps running the OLD bytecode.  The .deb
# preserves real build mtimes and so has not been bitten in practice, unlike
# the RPM -- but that is luck, not design, and the two packages should not
# diverge on something this quiet.  See the matching block in caleneff.spec.
cat > "$STAGING/DEBIAN/postinst" <<'EOF'
#!/bin/bash
set -e
rm -rf /usr/share/caleneff/__pycache__
python3 -m compileall -q /usr/share/caleneff >/dev/null 2>&1 || true
gtk-update-icon-cache -f -t /usr/share/icons/hicolor 2>/dev/null || true
update-desktop-database 2>/dev/null || true
EOF
chmod 755 "$STAGING/DEBIAN/postinst"

# ── DEBIAN/postrm ─────────────────────────────────────────────────
# dpkg removes only the files it installed; the bytecode postinst generated
# belongs to no package, so without this it is orphaned under /usr/share.
cat > "$STAGING/DEBIAN/postrm" <<'EOF'
#!/bin/bash
set -e
case "$1" in
    remove|purge)
        rm -rf /usr/share/caleneff/__pycache__
        rmdir /usr/share/caleneff 2>/dev/null || true
        ;;
esac
EOF
chmod 755 "$STAGING/DEBIAN/postrm"

# ── build .deb ────────────────────────────────────────────────────
OUT=/tmp/${PKG}_${VER}_${ARCH}.deb
dpkg-deb --build --root-owner-group "$STAGING" "$OUT"
echo ""
echo "=== DEB built: $OUT ==="
ls -lh "$OUT"

# copy back to Windows filesystem
cp "$OUT" "$PROJ/dist/"
echo "=== Copied to $PROJ/dist/ ==="
