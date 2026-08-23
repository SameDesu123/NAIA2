"""Bootstrap the frozen macOS app from a writable application directory.

NAIA historically stores settings and downloaded assets relative to the current
working directory. A normal macOS application bundle is not a suitable writable
location, so the packaged source tree is synchronized to Application Support and
executed from there.
"""

from __future__ import annotations

import json
import os
import runpy
import shutil
import sys
from pathlib import Path


APP_SUPPORT_DIRNAME = "NAIA2"
PACKAGED_FILES_MANIFEST = ".naia-packaged-files.json"
BUNDLE_VERSION_FILE = ".bundle-version"


def _pyinstaller_dependency_anchor() -> None:
    """Make the regular entry point visible to PyInstaller's static analysis."""
    import NAIA_cold_v4  # noqa: F401


def _atomic_write_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_name(f"{path.name}.tmp")
    temporary_path.write_text(value, encoding="utf-8")
    temporary_path.replace(path)


def _packaged_files(source_root: Path) -> list[str]:
    return sorted(
        path.relative_to(source_root).as_posix()
        for path in source_root.rglob("*")
        if path.is_file() and path.name != BUNDLE_VERSION_FILE
    )


def _load_previous_manifest(destination_root: Path) -> set[str]:
    manifest_path = destination_root / PACKAGED_FILES_MANIFEST
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return set()

    if not isinstance(manifest, list):
        return set()
    return {value for value in manifest if isinstance(value, str)}


def _safe_destination(root: Path, relative_path: str) -> Path:
    candidate = (root / relative_path).resolve()
    resolved_root = root.resolve()
    if candidate != resolved_root and resolved_root not in candidate.parents:
        raise ValueError(f"Unsafe packaged path: {relative_path}")
    return candidate


def _sync_runtime(source_root: Path, destination_root: Path) -> None:
    """Overlay packaged files while preserving files created by the user."""
    version = (source_root / BUNDLE_VERSION_FILE).read_text(encoding="utf-8").strip()
    destination_version_path = destination_root / BUNDLE_VERSION_FILE
    try:
        installed_version = destination_version_path.read_text(encoding="utf-8").strip()
    except OSError:
        installed_version = ""

    if version and installed_version == version:
        return

    destination_root.mkdir(parents=True, exist_ok=True)
    packaged_files = _packaged_files(source_root)
    packaged_file_set = set(packaged_files)

    # Remove only files that belonged to the previous bundle. User-created files
    # in save/, wildcards/, data/, and other legacy writable paths are retained.
    for relative_path in _load_previous_manifest(destination_root) - packaged_file_set:
        stale_path = _safe_destination(destination_root, relative_path)
        if stale_path.is_file() or stale_path.is_symlink():
            stale_path.unlink()

    for relative_path in packaged_files:
        source_path = source_root / relative_path
        destination_path = _safe_destination(destination_root, relative_path)
        destination_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, destination_path)

    _atomic_write_text(
        destination_root / PACKAGED_FILES_MANIFEST,
        json.dumps(packaged_files, ensure_ascii=False, indent=2) + "\n",
    )
    _atomic_write_text(destination_version_path, version + "\n")


def _application_support_root() -> Path:
    override = os.environ.get("NAIA_APP_SUPPORT_DIR")
    if override:
        return Path(override).expanduser()
    return Path.home() / "Library" / "Application Support" / APP_SUPPORT_DIRNAME


def main() -> None:
    if getattr(sys, "frozen", False):
        bundle_root = Path(sys._MEIPASS)
        runtime_source = bundle_root / "runtime"
        runtime_root = _application_support_root()
        _sync_runtime(runtime_source, runtime_root)
    else:
        runtime_root = Path(__file__).resolve().parents[1]

    os.chdir(runtime_root)
    sys.path.insert(0, str(runtime_root))
    runpy.run_path(str(runtime_root / "NAIA_cold_v4.py"), run_name="__main__")


if __name__ == "__main__":
    main()
