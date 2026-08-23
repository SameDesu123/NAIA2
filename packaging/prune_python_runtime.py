#!/usr/bin/env python3
"""Remove development-only files rejected by NAIA's release audit."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
import os
from pathlib import Path
import shutil


DEVELOPMENT_DIRECTORIES = frozenset({".pytest_cache", "__pycache__", "docs", "tests"})


@dataclass(frozen=True)
class PruneResult:
    runtime_root: str
    removed_directories: int
    removed_markdown_files: int


def _validated_runtime_root(runtime_root: str | Path) -> Path:
    root = Path(runtime_root).resolve()
    if not root.is_dir():
        raise RuntimeError(f"Python runtime root is not a directory: {root}")
    if root.name != "python" or root.parent.name != "resources":
        raise RuntimeError(
            "Refusing to prune a path other than a staged resources/python directory: "
            f"{root}"
        )
    return root


def prune_python_runtime(runtime_root: str | Path) -> PruneResult:
    root = _validated_runtime_root(runtime_root)
    removed_directories = 0
    removed_markdown_files = 0

    for directory, child_directories, filenames in os.walk(root, topdown=False, followlinks=False):
        current = Path(directory)
        for filename in filenames:
            path = current / filename
            if path.suffix == ".md":
                path.unlink()
                removed_markdown_files += 1

        for child_name in child_directories:
            if child_name not in DEVELOPMENT_DIRECTORIES:
                continue
            path = current / child_name
            if path.is_symlink():
                path.unlink()
            else:
                shutil.rmtree(path)
            removed_directories += 1

    return PruneResult(
        runtime_root=str(root),
        removed_directories=removed_directories,
        removed_markdown_files=removed_markdown_files,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Prune development-only content from a staged Python runtime."
    )
    parser.add_argument("runtime_root", help="The staged resources/python directory.")
    args = parser.parse_args(argv)

    result = prune_python_runtime(args.runtime_root)
    print(json.dumps(result.__dict__, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
