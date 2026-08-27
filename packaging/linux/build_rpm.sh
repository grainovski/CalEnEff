#!/bin/bash
# Build the CalEnEff .rpm package for AlmaLinux 8.
# Run this script from inside AlmaLinux-8 WSL:
#   bash /mnt/c/Users/RIG/Documents/Claude/efficieny/packaging/linux/build_rpm.sh

set -euo pipefail

PROJ=/mnt/c/Users/RIG/Documents/Claude/efficieny
PKG=caleneff
VER=3.0

echo "=== CalEnEff RPM builder ==="

# ── prerequisites ────────────────────────────────────────────────
echo "Installing build deps..."
dnf install -y rpm-build python3 python3-pip

# Enable EPEL for scipy / matplotlib if not already present
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
print('VERSION = \"3.0\"')
print('BUILD_DATE = \"' + datetime.date.today().isoformat() + '\"')
" > "$RPMBUILD/SOURCES/build_info.py"

# ── copy sources ──────────────────────────────────────────────────
cp "$PROJ/ra226_gui.py"                   "$RPMBUILD/SOURCES/"
cp "$PROJ/help_content.py"                "$RPMBUILD/SOURCES/"
cp "$PROJ/226Ra_En_Area.txt"              "$RPMBUILD/SOURCES/"
cp "$PROJ/demo1.txt"                      "$RPMBUILD/SOURCES/"
cp "$PROJ/demo2.txt"                      "$RPMBUILD/SOURCES/"
cp /tmp/caleneff.png                      "$RPMBUILD/SOURCES/"
cp "$PROJ/packaging/linux/caleneff.desktop" "$RPMBUILD/SOURCES/"

# ── launcher script ───────────────────────────────────────────────
cat > "$RPMBUILD/SOURCES/caleneff.sh" <<'EOF'
#!/bin/bash
exec python3 /usr/share/caleneff/ra226_gui.py "$@"
EOF
chmod 755 "$RPMBUILD/SOURCES/caleneff.sh"

# ── spec file ─────────────────────────────────────────────────────
cp "$PROJ/packaging/linux/caleneff.spec" "$RPMBUILD/SPECS/"

# ── build ─────────────────────────────────────────────────────────
rpmbuild -bb "$RPMBUILD/SPECS/caleneff.spec" \
    --define "_sourcedir $RPMBUILD/SOURCES" \
    --define "_topdir $RPMBUILD"

# ── locate the output RPM ─────────────────────────────────────────
RPM_FILE=$(find "$RPMBUILD/RPMS" -name "${PKG}-*.rpm" | head -1)
echo ""
echo "=== RPM built: $RPM_FILE ==="
ls -lh "$RPM_FILE"

mkdir -p "$PROJ/dist"
cp "$RPM_FILE" "$PROJ/dist/"
echo "=== Copied to $PROJ/dist/ ==="
