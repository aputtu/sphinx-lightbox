#!/usr/bin/env python3
"""Validate that distribution archives contain only publishable files."""

from __future__ import annotations

import argparse
import sys
import tarfile
import zipfile
from pathlib import Path

_PACKAGE_FILES = {".py", ".typed", ".css", ".js"}
_SDIST_ROOT_FILES = {
    "LICENSE",
    "MANIFEST.in",
    "PKG-INFO",
    "README.md",
    "pyproject.toml",
    "setup.cfg",
}
_SDIST_REQUIRED = {
    "LICENSE",
    "PKG-INFO",
    "README.md",
    "pyproject.toml",
    "lightbox/__init__.py",
    "lightbox/lightbox.py",
    "lightbox/py.typed",
    "lightbox/static/lightbox.css",
    "lightbox/static/lightbox.js",
}
_WHEEL_REQUIRED = {
    "lightbox/__init__.py",
    "lightbox/lightbox.py",
    "lightbox/py.typed",
    "lightbox/static/lightbox.css",
    "lightbox/static/lightbox.js",
}
_FORBIDDEN_PARTS = {
    ".github",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".tox",
    "__pycache__",
    "build",
    "dist",
    "docs",
    "htmlcov",
    "requirements",
    "scripts",
    "test-root",
    "tests",
}


def _normal_files(names: list[str]) -> set[str]:
    return {name.rstrip("/") for name in names if name.rstrip("/")}


def _package_file_allowed(path: str) -> bool:
    return path.startswith("lightbox/") and Path(path).suffix in _PACKAGE_FILES


def _contains_forbidden_part(path: str) -> bool:
    return bool(set(Path(path).parts) & _FORBIDDEN_PARTS)


def _validate_sdist(path: Path) -> list[str]:
    with tarfile.open(path, "r:gz") as archive:
        names = _normal_files(archive.getnames())

    roots = {name.split("/", 1)[0] for name in names}
    if len(roots) != 1:
        return [f"{path}: expected exactly one sdist root directory, found {sorted(roots)}"]

    root = next(iter(roots))
    relative_names = {
        name.removeprefix(f"{root}/")
        for name in names
        if name != root and name.startswith(f"{root}/")
    }
    errors = _missing_required(path, relative_names, _SDIST_REQUIRED)

    for relative_name in sorted(relative_names):
        if _contains_forbidden_part(relative_name):
            errors.append(f"{path}: forbidden path in sdist: {relative_name}")
            continue
        if relative_name in _SDIST_ROOT_FILES:
            continue
        if _package_file_allowed(relative_name):
            continue
        if relative_name == "sphinx_lightbox.egg-info":
            continue
        if relative_name == "sphinx_lightbox.egg-info/SOURCES.txt":
            continue
        if not Path(relative_name).suffix:
            continue
        errors.append(f"{path}: unexpected path in sdist: {relative_name}")
    return errors


def _validate_wheel(path: Path) -> list[str]:
    with zipfile.ZipFile(path) as archive:
        names = _normal_files(archive.namelist())

    errors = _missing_required(path, names, _WHEEL_REQUIRED)
    dist_info_dirs = {
        name.split("/", 1)[0] for name in names if name.split("/", 1)[0].endswith(".dist-info")
    }
    if len(dist_info_dirs) != 1:
        errors.append(f"{path}: expected exactly one .dist-info directory")

    for name in sorted(names):
        if _contains_forbidden_part(name):
            errors.append(f"{path}: forbidden path in wheel: {name}")
            continue
        if _package_file_allowed(name):
            continue
        if any(name.startswith(f"{dist_info_dir}/") for dist_info_dir in dist_info_dirs):
            continue
        if not Path(name).suffix:
            continue
        errors.append(f"{path}: unexpected path in wheel: {name}")
    return errors


def _missing_required(path: Path, names: set[str], required: set[str]) -> list[str]:
    missing = sorted(required - names)
    if not missing:
        return []
    return [f"{path}: missing required file: {name}" for name in missing]


def _archive_errors(path: Path) -> list[str]:
    if path.suffix == ".whl":
        return _validate_wheel(path)
    if path.name.endswith(".tar.gz"):
        return _validate_sdist(path)
    return [f"{path}: unsupported distribution archive type"]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "dist_dir",
        nargs="?",
        default="dist",
        type=Path,
        help="Directory containing built distribution archives.",
    )
    args = parser.parse_args()

    archives = sorted(args.dist_dir.glob("*.whl")) + sorted(args.dist_dir.glob("*.tar.gz"))
    if not archives:
        print(f"No distribution archives found in {args.dist_dir}", file=sys.stderr)
        return 1

    errors: list[str] = []
    for archive in archives:
        errors.extend(_archive_errors(archive))

    if errors:
        print("Distribution contents validation failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    print(f"Distribution contents validation passed: {args.dist_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
