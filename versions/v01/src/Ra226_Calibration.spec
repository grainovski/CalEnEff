# Ra226_Calibration.spec
# PyInstaller spec for Ra226 Energy & Efficiency Calibration GUI
# Build: pyinstaller Ra226_Calibration.spec

import os

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

a = Analysis(
    ["ra226_gui.py"],
    pathex=[],
    binaries=extra_binaries,
    datas=[("226Ra_En_Area.txt", "."), ("Ra226_Calibration.ico", ".")],
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
    ],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="Ra226_Calibration",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,       # no console window
    windowed=True,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon="Ra226_Calibration.ico",
)
