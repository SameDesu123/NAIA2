# -*- mode: python ; coding: utf-8 -*-

from __future__ import annotations

import os
import subprocess
from pathlib import Path


PROJECT_ROOT = Path(SPECPATH).resolve().parent
if PROJECT_ROOT.name == "packaging":
    PROJECT_ROOT = PROJECT_ROOT.parent

RUNTIME_DIRECTORIES = {"core", "data", "interfaces", "modules", "tabs", "ui", "utils", "workflows"}
RUNTIME_ROOT_FILES = {
    "NAIA_cold_v4.py",
    "Pretendard-Bold.otf",
    "Pretendard-Regular.otf",
    "__init__.py",
    "artist_dictionary.py",
    "danbooru_character.py",
    "result_dict_copyright.py",
    "result_dupl.py",
}


def tracked_runtime_files() -> list[Path]:
    tracked = subprocess.check_output(
        ["git", "ls-files", "-z"],
        cwd=PROJECT_ROOT,
    ).decode("utf-8").split("\0")

    selected: list[Path] = []
    for relative_name in tracked:
        if not relative_name:
            continue
        relative_path = Path(relative_name)
        if relative_path.name == "CLAUDE.md" or ".claude" in relative_path.parts:
            continue
        if relative_path.as_posix() in RUNTIME_ROOT_FILES or relative_path.parts[0] in RUNTIME_DIRECTORIES:
            selected.append(relative_path)
    return selected


runtime_files = tracked_runtime_files()
datas = [
    (str(PROJECT_ROOT / relative_path), str(Path("runtime") / relative_path.parent))
    for relative_path in runtime_files
]

build_version = os.environ.get("NAIA_BUILD_VERSION")
if not build_version:
    build_version = subprocess.check_output(
        ["git", "rev-parse", "HEAD"],
        cwd=PROJECT_ROOT,
        text=True,
    ).strip()

generated_dir = PROJECT_ROOT / "build" / "packaging"
generated_dir.mkdir(parents=True, exist_ok=True)
bundle_version_path = generated_dir / ".bundle-version"
bundle_version_path.write_text(build_version + "\n", encoding="utf-8")
datas.append((str(bundle_version_path), "runtime"))

hiddenimports = sorted(
    {
        ".".join(relative_path.with_suffix("").parts)
        for relative_path in runtime_files
        if relative_path.suffix == ".py" and relative_path.name != "__init__.py"
    }
)

target_arch = os.environ.get("NAIA_TARGET_ARCH") or None
build_number = os.environ.get("NAIA_BUILD_NUMBER", "1")

a = Analysis(
    [str(PROJECT_ROOT / "packaging" / "macos_launcher.py")],
    pathex=[str(PROJECT_ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["PySide6", "tkinter"],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="NAIA2",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    target_arch=target_arch,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="NAIA2",
)

app = BUNDLE(
    coll,
    name="NAIA2.app",
    icon=None,
    bundle_identifier="com.samedesu.naia2",
    version=build_number,
    info_plist={
        "CFBundleDisplayName": "NAIA2",
        "CFBundleShortVersionString": "2.0",
        "LSMinimumSystemVersion": "12.0",
        "NSHighResolutionCapable": True,
        "NSPrincipalClass": "NSApplication",
    },
)
