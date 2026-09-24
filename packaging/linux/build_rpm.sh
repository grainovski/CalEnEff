#!/bin/bash
# Build the CalEnEff .rpm package.
#
# Run this from inside AlmaLinux-10 WSL, as root:
#   wsl -d AlmaLinux-10 -u root bash \
#     /mnt/c/Users/RIG/Documents/Claude/efficieny/packaging/linux/build_rpm.sh
#
# NOT AlmaLinux-8: its python3-matplotlib is unusable there because the
# libqhull.so.7 it links against is missing from the repos.

set -euo pipefail

PROJ=/mnt/c/Users/RIG/Documents/Claude/efficieny
PKG=caleneff

# Version is single-sourced from Ra226_Calibration.iss — the same line build.ps1
# reads — so a release bump touches exactly one file instead of silently
# leaving the RPM on the previous version.
VER=$(sed -n 's/^#define[[:space:]]\+AppVersion[[:space:]]\+"\([^"]*\)".*/\1/p' \
      "$PROJ/Ra226_Calibration.iss")
if [ -z "$VER" ]; then
    echo "ERROR: no '#define AppVersion' found in Ra226_Calibration.iss" >&2
    exit 1
fi

echo "=== CalEnEff RPM builder ==="
echo "Version: $VER  (from Ra226_Calibration.iss)"

# ── prerequisites ────────────────────────────────────────────────
echo "Installing build deps..."
dnf install -y rpm-build python3 python3-pip

# Enable EPEL if not already present.  Only python3-matplotlib actually
# needs it -- numpy, scipy and tkinter are all in AppStream on
# AlmaLinux/RHEL 10.
#
# This enables EPEL on the BUILD host, which is needed to *build* against
# matplotlib.  Note it also means this host can never tell you whether the
# RPM installs on a stock system -- it always succeeds here.  Smoke-test on
# a throwaway instance instead:
#   wsl --install AlmaLinux-10 --name AlmaStock --no-launch
# As of 4.2 the RPM does install on a stock box: matplotlib is a weak
# dependency and epel-release a hard one.  See caleneff.spec for why no
# arrangement of hard Requires can achieve that.
if ! rpm -q epel-release &>/dev/null; then
    dnf install -y epel-release
    dnf makecache --timer
fi
dnf install -y python3-numpy python3-scipy python3-matplotlib python3-tkinter \
     python3-pillow 2>/dev/null || \
pip3 install --quiet Pillow 2>/dev/null || true

# ── generate PNG icon ─────────────────────────────────────────────
echo "Generating PNG icon..."
python3 - <<'PYEOF'
try:
    from PIL import Image
    src = '/mnt/c/Users/RIG/Documents/Claude/efficieny/CalEnEff.ico'
    dst = '/tmp/caleneff.png'
    with Image.open(src) as img:
        sizes = list(img.info.get('sizes', [(128,128)]))
        best = max(sizes, key=lambda s: s[0]) if sizes else (128,128)
        img.size = best
        img.save(dst, format='PNG')
    print(f"Icon: {best} -> {dst}")
except Exception as e:
    print(f"Pillow not available ({e}), using fallback 1x1 PNG")
    import struct, zlib
    def png1x1():
        sig = b'\x89PNG\r\n\x1a\n'
        def chunk(t, d): c=zlib.crc32(t+d)&0xffffffff; return struct.pack('>I',len(d))+t+d+struct.pack('>I',c)
        ihdr=chunk(b'IHDR',struct.pack('>IIBBBBB',1,1,8,2,0,0,0))
        raw=b'\x00\x00\xff\x00'  # blue pixel
        idat=chunk(b'IDAT',zlib.compress(raw))
        iend=chunk(b'IEND',b'')
        return sig+ihdr+idat+iend
    open('/tmp/caleneff.png','wb').write(png1x1())
PYEOF

# ── rpmbuild tree ─────────────────────────────────────────────────
RPMBUILD=$HOME/rpmbuild
mkdir -p "$RPMBUILD"/{BUILD,RPMS,SOURCES,SPECS,SRPMS}

# ── generate build_info.py ────────────────────────────────────────
python3 -c "
import datetime
print('VERSION = \"$VER\"')
print('BUILD_DATE = \"' + datetime.date.today().isoformat() + '\"')
" > "$RPMBUILD/SOURCES/build_info.py"

# ── copy sources ──────────────────────────────────────────────────
cp "$PROJ/ra226_gui.py"                   "$RPMBUILD/SOURCES/"
cp "$PROJ/help_content.py"                "$RPMBUILD/SOURCES/"
# See build_deb.sh: a module missing from this list ships a broken RPM.
cp "$PROJ/spectratools_export.py"         "$RPMBUILD/SOURCES/"
cp "$PROJ/226Ra_En_Area.txt"              "$RPMBUILD/SOURCES/"
cp "$PROJ/demo1.txt"                      "$RPMBUILD/SOURCES/"
cp "$PROJ/demo2.txt"                      "$RPMBUILD/SOURCES/"
cp /tmp/caleneff.png                      "$RPMBUILD/SOURCES/"
cp "$PROJ/LICENSE"                        "$RPMBUILD/SOURCES/"
cp "$PROJ/packaging/linux/caleneff.desktop" "$RPMBUILD/SOURCES/"

# ── launcher script ───────────────────────────────────────────────
cat > "$RPMBUILD/SOURCES/caleneff.sh" <<'EOF'
#!/bin/bash
# python3-matplotlib is a weak dependency of this package because on
# AlmaLinux/RHEL 10 it lives only in EPEL, and a hard Requires made the RPM
# uninstallable on a stock system.  It can therefore legitimately be absent.
# Say what to do about it instead of dying with an ImportError traceback.
if ! python3 -c 'import matplotlib' >/dev/null 2>&1; then
    cat >&2 <<'EOM'
CalEnEff cannot start: the Python module "matplotlib" is not installed.

On AlmaLinux / RHEL it ships in EPEL, which this package has already
configured for you.  Run:

    sudo dnf install -y python3-matplotlib

On Debian / Ubuntu:

    sudo apt install -y python3-matplotlib
EOM
    exit 1
fi
exec python3 /usr/share/caleneff/ra226_gui.py "$@"
EOF
chmod 755 "$RPMBUILD/SOURCES/caleneff.sh"

# ── spec file ─────────────────────────────────────────────────────
cp "$PROJ/packaging/linux/caleneff.spec" "$RPMBUILD/SPECS/"

# ── build ─────────────────────────────────────────────────────────
rpmbuild -bb "$RPMBUILD/SPECS/caleneff.spec" \
    --define "_sourcedir $RPMBUILD/SOURCES" \
    --define "_topdir $RPMBUILD" \
    --define "version $VER"

# ── locate the output RPM ─────────────────────────────────────────
# Match the version we just built, not "${PKG}-*.rpm".  The bare glob matches
# every version ever built on this host and `head -1` then takes whichever the
# filesystem happens to return first -- with 4.0, 4.1 and 4.2 all present in
# RPMS/noarch it picked 4.1 and copied that stale package into dist/ as though
# it were the new build.  Fail loudly rather than guess.
RPM_MATCHES=$(find "$RPMBUILD/RPMS" -name "${PKG}-${VER}-*.rpm")
RPM_COUNT=$(printf '%s\n' "$RPM_MATCHES" | grep -c . || true)
if [ "$RPM_COUNT" -ne 1 ]; then
    echo "ERROR: expected exactly one ${PKG}-${VER} RPM, found $RPM_COUNT:" >&2
    printf '  %s\n' $RPM_MATCHES >&2
    exit 1
fi
RPM_FILE=$RPM_MATCHES
echo ""
echo "=== RPM built: $RPM_FILE ==="
ls -lh "$RPM_FILE"

mkdir -p "$PROJ/dist"
cp "$RPM_FILE" "$PROJ/dist/"
echo "=== Copied to $PROJ/dist/ ==="
