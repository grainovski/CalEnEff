# Ra226_Calibration.spec
# PyInstaller spec for Ra226 Energy & Efficiency Calibration GUI
# Build: pyinstaller Ra226_Calibration.spec

import os
import re

from PyInstaller.utils.win32.versioninfo import (
    FixedFileInfo, StringFileInfo, StringStruct, StringTable, VarFileInfo,
    VarStruct, VSVersionInfo,
)

MC_BIN = r"C:\Users\RIG\miniconda3\Library\bin"

# DLLs that Miniconda keeps in Library\bin (not on PATH by default)
# Includes PIL/_imaging deps (libjpeg, lcms2, openjp2, webp, …) which
# matplotlib pulls in transitively via colors.py → PIL.Image
_extra_dlls = [
    # Python / Tcl/Tk runtime
    "ffi.dll",
    "libmpdec-4.dll",
    "liblzma.dll",
    "libbz2.dll",
    "libexpat.dll",
    "expat.dll",
    "tk86t.dll",
    "tcl86t.dll",
    # Image codecs required by PIL/_imaging.pyd
    "libjpeg.dll",
    "openjp2.dll",
    "lcms2.dll",
    "libwebp.dll",
    "libwebpdecoder.dll",
    "libwebpdemux.dll",
    "libwebpmux.dll",
    "libtiff.dll",
    "tiff.dll",
    "libpng16.dll",
    "zlib.dll",
    "libzstd.dll",
    # Font rendering (matplotlib ft2font.pyd)
    "freetype.dll",
]
extra_binaries = [
    (os.path.join(MC_BIN, dll), ".")
    for dll in _extra_dlls
    if os.path.exists(os.path.join(MC_BIN, dll))
]

# ---------------------------------------------------------------------------
# Windows version resource
#
# Without this the built CalEnEff.exe has a blank Details tab in Explorer -- no
# version, no publisher, no copyright -- even though the INSTALLER carries all
# three.  Nothing is hardcoded here: the version comes from build_info.py,
# which build.ps1 stamps from Ra226_Calibration.iss immediately before calling
# PyInstaller, and the publisher and copyright come from that .iss directly.
# AppVersion therefore remains the one line to bump.
#
# If either file is missing or unreadable -- a bare `pyinstaller
# Ra226_Calibration.spec` with no build.ps1 run first -- the resource is simply
# omitted rather than failing the build or, worse, stamping a wrong version.
# ---------------------------------------------------------------------------

def _read_text(path):
    try:
        with open(path, encoding="utf-8") as fh:
            return fh.read()
    except OSError:
        return ""


def _iss_field(text, name, default):
    m = re.search(r"^%s=(.+)$" % re.escape(name), text, re.MULTILINE)
    return m.group(1).strip() if m else default


def _version_quad(version):
    """'4.7' -> (4, 7, 0, 0).  A version resource needs exactly four ints."""
    parts = []
    for piece in str(version).split(".")[:4]:
        m = re.match(r"\d+", piece)
        parts.append(int(m.group()) if m else 0)
    return tuple((parts + [0, 0, 0, 0])[:4])


_build_info = _read_text("build_info.py")
_m = re.search(r'VERSION\s*=\s*"([^"]+)"', _build_info)
_version = _m.group(1) if _m else ""

if _version:
    _iss = _read_text("Ra226_Calibration.iss")
    _publisher = _iss_field(_iss, "AppPublisher", "Georgi Rainovski")
    _copyright = _iss_field(_iss, "AppCopyright",
                            "Copyright (c) 2026 Georgi Rainovski")
    _quad = _version_quad(_version)
    # 040904B0 = US English (0x0409), Unicode charset (0x04B0 = 1200); the
    # VarStruct below must name the same pair or Explorer reads no strings.
    version_resource = VSVersionInfo(
        ffi=FixedFileInfo(
            filevers=_quad,
            prodvers=_quad,
            mask=0x3F,
            flags=0x0,
            OS=0x40004,      # VOS_NT_WINDOWS32
            fileType=0x1,    # VFT_APP
            subtype=0x0,
            date=(0, 0),
        ),
        kids=[
            StringFileInfo([StringTable("040904B0", [
                StringStruct("CompanyName", _publisher),
                StringStruct("FileDescription",
                             "Gamma-ray energy and efficiency calibration"),
                StringStruct("FileVersion", _version),
                StringStruct("InternalName", "CalEnEff"),
                StringStruct("LegalCopyright", _copyright),
                StringStruct("OriginalFilename", "CalEnEff.exe"),
                StringStruct("ProductName", "CalEnEff"),
                StringStruct("ProductVersion", _version),
            ])]),
            VarFileInfo([VarStruct("Translation", [0x0409, 1200])]),
        ],
    )
    print("spec: version resource %s (%s)" % (_version, _publisher))
else:
    version_resource = None
    print("spec: no build_info.py VERSION found -- building WITHOUT a version "
          "resource")


a = Analysis(
    ["ra226_gui.py"],
    pathex=[],
    binaries=extra_binaries,
    datas=[
        ("226Ra_En_Area.txt", "."),
        ("demo1.txt", "."),
        ("demo2.txt", "."),
        ("CalEnEff.ico", "."),
        ("help_content.py", "."),
    ] + ([("build_info.py", ".")] if os.path.exists("build_info.py") else []),
    hiddenimports=[
        "scipy.special._ufuncs",
        "scipy.optimize",
        "scipy.linalg",
        # Matplotlib backends — lazy-imported at savefig() time based on the
        # format string, so PyInstaller's static analysis misses them.  Without
        # these the exe silently fails to save PDF/SVG/EPS/PS while raster
        # formats (which go through the Agg backend already pulled by TkAgg
        # and through PIL) keep working.
        "matplotlib.backends.backend_tkagg",
        "matplotlib.backends.backend_agg",
        "matplotlib.backends.backend_pdf",
        "matplotlib.backends.backend_svg",
        "matplotlib.backends.backend_ps",     # handles both .ps and .eps
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "IPython", "PyQt5", "PyQt6",
        "PySide2", "PySide6", "wx", "gtk", "gi",
        "notebook", "pandas", "sklearn", "cv2",
        "docutils", "sphinx", "pkg_resources._vendor",
        "setuptools",
    ],
    noarchive=False,
)

pyz = PYZ(a.pure)

# onedir mode: exe is a thin launcher; all DLLs and data live beside it
# in the CalEnEff/ folder.  No extraction at startup → fast launch.
exe = EXE(
    pyz,
    a.scripts,
    [],
    [],
    exclude_binaries=True,
    name="CalEnEff",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    # UPX disabled deliberately.  Packing the Miniconda MKL DLLs is the same
    # class of risk as the lzma2 compression that caused an access violation
    # in islzma.dll (hence Compression=zip in the .iss), and UPX-packed
    # binaries are a frequent antivirus false-positive.  PyInstaller also
    # skips UPX silently when upx.exe is absent, so leaving it on makes builds
    # differ between machines.
    upx=False,
    upx_exclude=[],
    console=False,
    windowed=True,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon="CalEnEff.ico",
    # None is the documented way to say "no version resource", and is exactly
    # what this argument defaulted to before.
    version=version_resource,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    # UPX disabled deliberately.  Packing the Miniconda MKL DLLs is the same
    # class of risk as the lzma2 compression that caused an access violation
    # in islzma.dll (hence Compression=zip in the .iss), and UPX-packed
    # binaries are a frequent antivirus false-positive.  PyInstaller also
    # skips UPX silently when upx.exe is absent, so leaving it on makes builds
    # differ between machines.
    upx=False,
    upx_exclude=[],
    name="CalEnEff",
)
