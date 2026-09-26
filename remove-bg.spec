# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import (
    collect_data_files,
    collect_dynamic_libs,
    collect_submodules,
    copy_metadata,
)


datas = collect_data_files("rembg") + copy_metadata("rembg")
binaries = collect_dynamic_libs("onnxruntime")
hiddenimports = collect_submodules("rembg.sessions") + [
    "numpy",
    "onnxruntime",
    "PIL",
    "pymatting",
    "pymatting.alpha",
    "pymatting.foreground",
    "pymatting.util",
    "scipy.ndimage",
    "skimage.morphology",
]

a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="remove-bg",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=["icon.ico"],
)
