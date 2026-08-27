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
