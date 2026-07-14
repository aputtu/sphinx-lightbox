#!/usr/bin/env python3
"""Validate that distribution archives contain only publishable files."""

from __future__ import annotations

import argparse
import re
import stat
import sys
import tarfile
import zipfile
from collections import Counter
from email.parser import BytesParser
from pathlib import Path, PurePosixPath

_PACKAGE_FILES = {".py", ".typed", ".css", ".js", ".pot", ".po", ".mo"}
_TRANSLATION_FILES = {
    "lightbox/locales/sphinx-lightbox.pot",
    "lightbox/locales/da/LC_MESSAGES/sphinx-lightbox.po",
    "lightbox/locales/da/LC_MESSAGES/sphinx-lightbox.mo",
}
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
    "MANIFEST.in",
    "PKG-INFO",
    "README.md",
    "pyproject.toml",
    "lightbox/__init__.py",
    "lightbox/lightbox.py",
    "lightbox/py.typed",
    "lightbox/static/lightbox.css",
    "lightbox/static/lightbox.js",
} | _TRANSLATION_FILES
_EGG_INFO_FILES = {
    "dependency_links.txt",
    "entry_points.txt",
    "PKG-INFO",
    "requires.txt",
    "SOURCES.txt",
    "top_level.txt",
}
_WHEEL_REQUIRED = {
    "lightbox/__init__.py",
    "lightbox/lightbox.py",
    "lightbox/py.typed",
    "lightbox/static/lightbox.css",
    "lightbox/static/lightbox.js",
} | _TRANSLATION_FILES
_SDIST_SOURCE_FILES = _WHEEL_REQUIRED | {
    "LICENSE",
    "MANIFEST.in",
    "README.md",
    "pyproject.toml",
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
    return {name.rstrip("/") for name in names if name.rstrip("/") and not name.endswith("/")}


def _package_file_allowed(path: str) -> bool:
    return path.startswith("lightbox/") and Path(path).suffix in _PACKAGE_FILES


def _unsafe_archive_path(path: str) -> bool:
    normalized = path.replace("\\", "/")
    archive_path = PurePosixPath(normalized)
    return "\\" in path or archive_path.is_absolute() or ".." in archive_path.parts


def _contains_forbidden_part(path: str) -> bool:
    return bool(set(Path(path).parts) & _FORBIDDEN_PARTS)


def _validate_sdist(path: Path) -> list[str]:
    with tarfile.open(path, "r:gz") as archive:
        members = archive.getmembers()
        names = {member.name.rstrip("/") for member in members if member.isfile()}
        invalid_members = [
            member.name for member in members if not (member.isfile() or member.isdir())
        ]

    errors = [f"{path}: unsupported archive member type: {name}" for name in invalid_members]
    member_counts = Counter(
        member.name.rstrip("/") for member in members if member.name.rstrip("/")
    )
    errors.extend(
        f"{path}: duplicate path in sdist: {name}"
        for name, count in member_counts.items()
        if count > 1
    )
    errors.extend(
        f"{path}: unsafe path in sdist: {member.name}"
        for member in members
        if _unsafe_archive_path(member.name)
    )

    roots = {name.split("/", 1)[0] for name in names}
    if len(roots) != 1:
        errors.append(f"{path}: expected exactly one sdist root directory, found {sorted(roots)}")
        return errors

    root = next(iter(roots))
    relative_names = {
        name.removeprefix(f"{root}/")
        for name in names
        if name != root and name.startswith(f"{root}/")
    }
    errors.extend(_missing_required(path, relative_names, _SDIST_REQUIRED))

    for relative_name in sorted(relative_names):
        if _contains_forbidden_part(relative_name):
            errors.append(f"{path}: forbidden path in sdist: {relative_name}")
            continue
        if relative_name in _SDIST_ROOT_FILES:
            continue
        if _package_file_allowed(relative_name):
            continue
        if relative_name.startswith("sphinx_lightbox.egg-info/") and (
            relative_name.removeprefix("sphinx_lightbox.egg-info/") in _EGG_INFO_FILES
        ):
            continue
        errors.append(f"{path}: unexpected path in sdist: {relative_name}")
    return errors


def _validate_wheel(path: Path) -> list[str]:
    with zipfile.ZipFile(path) as archive:
        infos = archive.infolist()
        names = _normal_files([info.filename for info in infos])

    errors = _missing_required(path, names, _WHEEL_REQUIRED)
    member_counts = Counter(
        info.filename.rstrip("/") for info in infos if info.filename.rstrip("/")
    )
    errors.extend(
        f"{path}: duplicate path in wheel: {name}"
        for name, count in member_counts.items()
        if count > 1
    )
    errors.extend(
        f"{path}: unsafe path in wheel: {info.filename}"
        for info in infos
        if _unsafe_archive_path(info.filename)
    )
    errors.extend(
        f"{path}: unsupported symlink in wheel: {info.filename}"
        for info in infos
        if stat.S_ISLNK(info.external_attr >> 16)
    )
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
        errors.append(f"{path}: unexpected path in wheel: {name}")
    return errors


def _archive_payloads(path: Path) -> dict[str, bytes]:
    """Return archive file payloads keyed by paths relative to the sdist root."""
    if path.suffix == ".whl":
        with zipfile.ZipFile(path) as archive:
            return {
                info.filename: archive.read(info)
                for info in archive.infolist()
                if not info.is_dir()
            }

    if path.name.endswith(".tar.gz"):
        with tarfile.open(path, "r:gz") as archive:
            members = [member for member in archive.getmembers() if member.isfile()]
            roots = {member.name.split("/", 1)[0] for member in members}
            if len(roots) != 1:
                return {}
            root = next(iter(roots))
            payloads: dict[str, bytes] = {}
            for member in members:
                if not member.name.startswith(f"{root}/"):
                    continue
                extracted = archive.extractfile(member)
                if extracted is not None:
                    payloads[member.name.removeprefix(f"{root}/")] = extracted.read()
            return payloads

    return {}


def _source_parity_errors(path: Path, source_root: Path) -> list[str]:
    """Return errors when built source/runtime files differ from the checkout."""
    payloads = _archive_payloads(path)
    expected_files = _WHEEL_REQUIRED if path.suffix == ".whl" else _SDIST_SOURCE_FILES
    errors: list[str] = []
    for name in sorted(expected_files):
        source_path = source_root / name
        if not source_path.is_file():
            errors.append(f"{path}: source file is missing: {name}")
            continue
        archive_payload = payloads.get(name)
        if archive_payload is None:
            continue  # The structural validator reports missing archive files.
        if archive_payload != source_path.read_bytes():
            errors.append(f"{path}: built file differs from source: {name}")
    return errors


def _metadata_version_errors(path: Path, expected_version: str) -> list[str]:
    """Return errors when archive metadata does not match the project version."""
    payloads = _archive_payloads(path)
    metadata_names = [
        name
        for name in payloads
        if (path.suffix == ".whl" and name.endswith(".dist-info/METADATA"))
        or (path.name.endswith(".tar.gz") and name == "PKG-INFO")
    ]
    if len(metadata_names) != 1:
        return [f"{path}: expected exactly one primary metadata file"]

    metadata = BytesParser().parsebytes(payloads[metadata_names[0]])
    built_version = metadata.get("Version", "")
    if built_version != expected_version:
        return [
            f"{path}: metadata version {built_version!r} does not match "
            f"project version {expected_version!r}"
        ]
    return []


def _missing_required(path: Path, names: set[str], required: set[str]) -> list[str]:
    missing = sorted(required - names)
    if not missing:
        return []
    return [f"{path}: missing required file: {name}" for name in missing]


def _archive_errors(
    path: Path,
    *,
    source_root: Path | None = None,
    expected_version: str | None = None,
) -> list[str]:
    if path.suffix == ".whl":
        errors = _validate_wheel(path)
    elif path.name.endswith(".tar.gz"):
        errors = _validate_sdist(path)
    else:
        return [f"{path}: unsupported distribution archive type"]

    if source_root is not None:
        errors.extend(_source_parity_errors(path, source_root))
    if expected_version is not None:
        errors.extend(_metadata_version_errors(path, expected_version))
    return errors


def _project_version(pyproject_path: Path) -> str | None:
    """Read the static ``project.version`` value without adding a TOML dependency."""
    content = pyproject_path.read_text(encoding="utf-8")
    project_match = re.search(r"(?ms)^\[project\]\s*(.*?)(?=^\[|\Z)", content)
    if project_match is None:
        return None
    version_match = re.search(r'^version\s*=\s*"([^"]+)"\s*$', project_match.group(1), re.MULTILINE)
    return version_match.group(1) if version_match is not None else None


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

    source_root = Path(__file__).resolve().parents[1]
    version = _project_version(source_root / "pyproject.toml")
    if version is None:
        print("Could not determine project.version from pyproject.toml", file=sys.stderr)
        return 1

    expected_names = {
        f"sphinx_lightbox-{version}-py3-none-any.whl",
        f"sphinx_lightbox-{version}.tar.gz",
    }
    actual_names = {archive.name for archive in archives}
    errors = [
        f"{args.dist_dir}: missing expected distribution: {name}"
        for name in sorted(expected_names - actual_names)
    ]
    errors.extend(
        f"{args.dist_dir}: unexpected distribution: {name}"
        for name in sorted(actual_names - expected_names)
    )
    for archive in archives:
        errors.extend(
            _archive_errors(
                archive,
                source_root=source_root,
                expected_version=version,
            )
        )

    if errors:
        print("Distribution contents validation failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    print(f"Distribution contents validation passed: {args.dist_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
