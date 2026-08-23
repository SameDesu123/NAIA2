#!/usr/bin/env python3
"""Reject non-system absolute dylib dependencies in a bundled macOS Python."""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import json
from pathlib import Path
import subprocess


ALLOWED_ABSOLUTE_PREFIXES = ("/System/Library/", "/usr/lib/")
MACHO_MAGICS = frozenset(
    {
        b"\xfe\xed\xfa\xce",
        b"\xce\xfa\xed\xfe",
        b"\xfe\xed\xfa\xcf",
        b"\xcf\xfa\xed\xfe",
        b"\xca\xfe\xba\xbe",
        b"\xbe\xba\xfe\xca",
        b"\xca\xfe\xba\xbf",
        b"\xbf\xba\xfe\xca",
    }
)


@dataclass(frozen=True)
class DependencyViolation:
    binary: str
    dependency: str


@dataclass(frozen=True)
class AuditResult:
    runtime_root: str
    macho_files: int
    violations: tuple[DependencyViolation, ...]

    @property
    def ok(self) -> bool:
        return not self.violations


def parse_otool_paths(output: str) -> tuple[str, ...]:
    paths: list[str] = []
    for line in output.splitlines():
        if not line[:1].isspace():
            continue
        stripped = line.strip()
        if not stripped:
            continue
        paths.append(stripped.split(" (", 1)[0])
    return tuple(paths)


def parse_otool_install_ids(output: str) -> set[str]:
    return {
        line.strip()
        for line in output.splitlines()
        if line.strip() and not line.rstrip().endswith(":")
    }


def is_allowed_dependency(dependency: str, install_ids: set[str]) -> bool:
    if dependency in install_ids:
        return True
    if dependency.startswith("@"):
        return True
    return dependency.startswith(ALLOWED_ABSOLUTE_PREFIXES)


def _run_tool(*command: str) -> str:
    completed = subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if completed.returncode != 0:
        raise RuntimeError(
            f"{' '.join(command)} failed: {completed.stderr.strip() or completed.stdout.strip()}"
        )
    return completed.stdout


def _is_macho(path: Path) -> bool:
    try:
        with path.open("rb") as binary:
            return binary.read(4) in MACHO_MAGICS
    except OSError:
        return False


def audit_runtime(runtime_root: str | Path) -> AuditResult:
    root = Path(runtime_root).resolve()
    if not root.is_dir():
        raise RuntimeError(f"Python runtime root is not a directory: {root}")

    violations: list[DependencyViolation] = []
    macho_files = 0
    for path in sorted(
        candidate
        for candidate in root.rglob("*")
        if candidate.is_file() and not candidate.is_symlink()
    ):
        if not _is_macho(path):
            continue
        macho_files += 1
        dependencies = parse_otool_paths(_run_tool("otool", "-L", str(path)))
        install_id_result = subprocess.run(
            ["otool", "-D", str(path)],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        install_ids = (
            parse_otool_install_ids(install_id_result.stdout)
            if install_id_result.returncode == 0
            else set()
        )
        for dependency in dependencies:
            if is_allowed_dependency(dependency, install_ids):
                continue
            violations.append(
                DependencyViolation(
                    binary=str(path.relative_to(root)),
                    dependency=dependency,
                )
            )

    return AuditResult(
        runtime_root=str(root),
        macho_files=macho_files,
        violations=tuple(violations),
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Audit bundled macOS Python binaries for host-specific dylib dependencies."
    )
    parser.add_argument("runtime_root", help="The bundled Python runtime directory.")
    args = parser.parse_args(argv)

    result = audit_runtime(args.runtime_root)
    payload = asdict(result)
    payload["ok"] = result.ok
    print(json.dumps(payload, indent=2))
    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
