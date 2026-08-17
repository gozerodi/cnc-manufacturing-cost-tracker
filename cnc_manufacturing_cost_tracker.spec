# -*- mode: python ; coding: utf-8 -*-
#
# PyInstaller --onedir build spec.
# Build on Windows with:
#   pyinstaller cnc_manufacturing_cost_tracker.spec
# Output: dist/CNCManufacturingCostTracker/ (zip this folder to distribute to other machines)

APP_NAME = "CNCManufacturingCostTracker"

# backend_qtagg and QtPrintSupport are imported directly (see app/ui/pages/*), so PyInstaller's
# static analysis normally finds them on its own; listed explicitly here as a safety net.
hidden_imports = [
    "matplotlib.backends.backend_qtagg",
    "matplotlib.backends.backend_agg",
    "PySide6.QtPrintSupport",
    "psycopg2",
]

# config.ini itself is never bundled (it holds no secrets by default), only the example
# template, so it's easy to copy to config.ini and fill in on the target machine.
datas = [
    ("config.example.ini", "."),
]

a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name=APP_NAME,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # PyInstaller 6+ defaults to putting all support files under an "_internal" subfolder;
    # the classic flat layout is used here instead so config.ini stays in the SAME folder
    # as the exe (get_base_dir() in app/core/config.py resolves relative to the exe's folder).
    contents_directory=".",
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name=APP_NAME,
)
