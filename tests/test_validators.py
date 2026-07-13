from __future__ import annotations

import base64
import io
import stat
import tarfile
import zipfile
from pathlib import Path

import pytest
from scripts.validate_dist import (
    _SDIST_REQUIRED,
    _SDIST_SOURCE_FILES,
    _WHEEL_REQUIRED,
    _archive_errors,
    _project_version,
)
from scripts.validate_docs import _validate_html_file, validate_docs


def test_generated_docs_patch_normalizes_third_party_markup(tmp_path: Path) -> None:
    from docs._ext.validation_fixes import _patch_generated_html

    html_path = tmp_path / "index.html"
    html_path.write_text(
        '<!DOCTYPE html><html lang="en"><head><meta charset="utf-8" />'
        '<meta name="viewport" content="width=device-width, initial-scale=1.0">'
        '<meta content="width=device-width, initial-scale=1" name="viewport"></head>'
        '<body><pre><div class="viewcode-block" id="example">code</div></pre>'
        '<span class="sig-return-icon">&#x2192;</span>'
        '<img src="photo.png" alt="Photo" /><input type="search" /></body></html>',
        encoding="utf-8",
    )
    tmp_path.joinpath("photo.png").write_bytes(
        base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUB"
            "AScY42YAAAAASUVORK5CYII="
        )
    )

    _patch_generated_html(tmp_path)

    patched = html_path.read_text(encoding="utf-8")
    assert '<meta charset="utf-8">' in patched
    assert (
        '<img src="photo.png" alt="Photo" width="1" height="1" data-docs-intrinsic-size="true">'
    ) in patched
    assert '<input type="search">' in patched
    assert '<span class="viewcode-block" id="example">code</span>' in patched
    assert '<span class="sig-return-icon">returns</span>' in patched
    assert patched.count('name="viewport"') == 1
    assert 'content="width=device-width, initial-scale=1.0"' in patched
    assert " />" not in patched


def test_docs_validator_rejects_stale_source_assets(tmp_path: Path) -> None:
    source_root = tmp_path / "source"
    html_dir = tmp_path / "html"
    source_static = source_root / "lightbox/static"
    source_docs_static = source_root / "docs/_static"
    built_static = html_dir / "_static"
    source_static.mkdir(parents=True)
    source_docs_static.mkdir(parents=True)
    built_static.mkdir(parents=True)
    html_dir.joinpath("index.html").write_text(
        '<!DOCTYPE html><html lang="en"><head><title>Test</title>'
        '<link rel="icon" href="_static/favicon.png"></head><body></body></html>',
        encoding="utf-8",
    )
    source_static.joinpath("lightbox.css").write_text("source css", encoding="utf-8")
    source_static.joinpath("lightbox.js").write_text("source js", encoding="utf-8")
    source_docs_static.joinpath("favicon.png").write_bytes(b"source favicon")
    built_static.joinpath("lightbox.css").write_text("stale css", encoding="utf-8")
    built_static.joinpath("lightbox.js").write_text("source js", encoding="utf-8")
    built_static.joinpath("favicon.png").write_bytes(b"source favicon")

    errors = validate_docs(html_dir, source_root)

    assert any("generated asset differs" in error for error in errors)
    assert not any("lightbox.js" in error for error in errors)
    assert not any("favicon.png" in error for error in errors)


def test_docs_validator_rejects_missing_favicon_link(tmp_path: Path) -> None:
    html_dir = tmp_path / "html"
    html_dir.mkdir()
    html_dir.joinpath("index.html").write_text(
        '<!DOCTYPE html><html lang="en"><head><title>Test</title></head><body></body></html>',
        encoding="utf-8",
    )

    errors = validate_docs(html_dir, tmp_path / "source")

    assert any("expected exactly one favicon link, found 0" in error for error in errors)


def test_docs_validator_rejects_public_doctrees(tmp_path: Path) -> None:
    html_dir = tmp_path / "html"
    doctree_dir = html_dir / ".doctrees"
    doctree_dir.mkdir(parents=True)
    doctree_dir.joinpath("environment.pickle").write_bytes(b"private build state")
    html_dir.joinpath("index.html").write_text(
        '<!DOCTYPE html><html lang="en"><head><title>Test</title>'
        '<link rel="icon" href="_static/favicon.png"></head><body></body></html>',
        encoding="utf-8",
    )

    errors = validate_docs(html_dir, tmp_path / "source")

    assert any("public Sphinx build state under .doctrees" in error for error in errors)


def test_docs_validator_rejects_duplicate_viewport_metadata(tmp_path: Path) -> None:
    html = tmp_path / "index.html"
    html.write_text(
        '<html lang="en"><head><meta name="viewport" content="width=device-width">'
        '<meta content="width=device-width, initial-scale=1" name="viewport"></head>'
        "<body></body></html>",
        encoding="utf-8",
    )

    assert any(
        "expected at most one viewport meta element, found 2" in error
        for error in _validate_html_file(html)
    )


def test_docs_validator_rejects_missing_intrinsic_raster_dimensions(tmp_path: Path) -> None:
    html = tmp_path / "index.html"
    html.write_text(
        '<html lang="en"><body><img src="_images/example.png" alt="Example"></body></html>',
        encoding="utf-8",
    )

    assert any(
        "local raster <img> is missing intrinsic dimensions" in error
        for error in _validate_html_file(html)
    )


def _write_sdist(path: Path, extras: dict[str, bytes] | None = None) -> None:
    files = dict.fromkeys(_SDIST_REQUIRED, b"content")
    files["PKG-INFO"] = b"Metadata-Version: 2.4\nVersion: 0.5.0\n"
    files.update(extras or {})
    with tarfile.open(path, "w:gz") as archive:
        for name, content in files.items():
            info = tarfile.TarInfo(f"sphinx_lightbox-0.5.0/{name}")
            info.size = len(content)
            archive.addfile(info, io.BytesIO(content))


def _write_wheel(path: Path, extras: dict[str, bytes] | None = None) -> None:
    files = dict.fromkeys(_WHEEL_REQUIRED, b"content")
    files["sphinx_lightbox-0.5.0.dist-info/METADATA"] = b"Metadata-Version: 2.4\nVersion: 0.5.0\n"
    files.update(extras or {})
    with zipfile.ZipFile(path, "w") as archive:
        for name, content in files.items():
            archive.writestr(name, content)


def test_distribution_validator_accepts_expected_archives(tmp_path: Path) -> None:
    sdist = tmp_path / "sphinx_lightbox-0.5.0.tar.gz"
    wheel = tmp_path / "sphinx_lightbox-0.5.0-py3-none-any.whl"
    _write_sdist(sdist)
    _write_wheel(wheel)

    assert _archive_errors(sdist) == []
    assert _archive_errors(wheel) == []


def test_distribution_validator_confirms_source_and_version_parity(tmp_path: Path) -> None:
    source_root = tmp_path / "source"
    for name in _SDIST_SOURCE_FILES:
        source_path = source_root / name
        source_path.parent.mkdir(parents=True, exist_ok=True)
        source_path.write_bytes(b"content")

    sdist = tmp_path / "sphinx_lightbox-0.5.0.tar.gz"
    wheel = tmp_path / "sphinx_lightbox-0.5.0-py3-none-any.whl"
    _write_sdist(sdist)
    _write_wheel(wheel)

    assert _archive_errors(sdist, source_root=source_root, expected_version="0.5.0") == []
    assert _archive_errors(wheel, source_root=source_root, expected_version="0.5.0") == []


def test_distribution_validator_rejects_source_or_version_mismatch(tmp_path: Path) -> None:
    source_root = tmp_path / "source"
    for name in _SDIST_SOURCE_FILES:
        source_path = source_root / name
        source_path.parent.mkdir(parents=True, exist_ok=True)
        source_path.write_bytes(b"content")
    source_root.joinpath("lightbox/static/lightbox.js").write_bytes(b"new source")

    wheel = tmp_path / "sphinx_lightbox-0.5.0-py3-none-any.whl"
    _write_wheel(wheel)

    errors = _archive_errors(wheel, source_root=source_root, expected_version="0.5.1")
    assert any(
        "built file differs from source: lightbox/static/lightbox.js" in error for error in errors
    )
    assert any(
        "metadata version '0.5.0' does not match project version '0.5.1'" in error
        for error in errors
    )


def test_project_version_reads_only_the_project_table(tmp_path: Path) -> None:
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        '[project]\nname = "example"\nversion = "1.2.3"\n\n[tool.example]\nversion = "9"\n',
        encoding="utf-8",
    )

    assert _project_version(pyproject) == "1.2.3"


def test_distribution_validator_rejects_extensionless_payloads(tmp_path: Path) -> None:
    sdist = tmp_path / "sphinx_lightbox-0.5.0.tar.gz"
    wheel = tmp_path / "sphinx_lightbox-0.5.0-py3-none-any.whl"
    _write_sdist(sdist, {"payload": b"unexpected"})
    _write_wheel(wheel, {"payload": b"unexpected"})

    assert any("unexpected path in sdist: payload" in error for error in _archive_errors(sdist))
    assert any("unexpected path in wheel: payload" in error for error in _archive_errors(wheel))


def test_distribution_validator_rejects_traversal_paths(tmp_path: Path) -> None:
    sdist = tmp_path / "sphinx_lightbox-0.5.0.tar.gz"
    wheel = tmp_path / "sphinx_lightbox-0.5.0-py3-none-any.whl"
    _write_sdist(sdist, {"lightbox/../payload.py": b"unexpected"})
    _write_wheel(wheel, {"lightbox/../payload.py": b"unexpected"})

    assert any("unsafe path in sdist" in error for error in _archive_errors(sdist))
    assert any("unsafe path in wheel" in error for error in _archive_errors(wheel))


def test_distribution_validator_rejects_sdist_symlinks(tmp_path: Path) -> None:
    sdist = tmp_path / "sphinx_lightbox-0.5.0.tar.gz"
    with tarfile.open(sdist, "w:gz") as archive:
        for name in _SDIST_REQUIRED:
            content = b"content"
            info = tarfile.TarInfo(f"sphinx_lightbox-0.5.0/{name}")
            info.size = len(content)
            archive.addfile(info, io.BytesIO(content))
        link = tarfile.TarInfo("sphinx_lightbox-0.5.0/link")
        link.type = tarfile.SYMTYPE
        link.linkname = "../../outside"
        archive.addfile(link)

    assert any("unsupported archive member type" in error for error in _archive_errors(sdist))


def test_distribution_validator_rejects_wheel_symlinks(tmp_path: Path) -> None:
    wheel = tmp_path / "sphinx_lightbox-0.5.0-py3-none-any.whl"
    _write_wheel(wheel)
    with zipfile.ZipFile(wheel, "a") as archive:
        link = zipfile.ZipInfo("lightbox/link.py")
        link.create_system = 3
        link.external_attr = (stat.S_IFLNK | 0o777) << 16
        archive.writestr(link, "../outside.py")

    assert any("unsupported symlink in wheel" in error for error in _archive_errors(wheel))


def test_distribution_validator_rejects_duplicate_wheel_members(tmp_path: Path) -> None:
    wheel = tmp_path / "sphinx_lightbox-0.5.0-py3-none-any.whl"
    _write_wheel(wheel)
    with pytest.warns(UserWarning), zipfile.ZipFile(wheel, "a") as archive:
        archive.writestr("lightbox/lightbox.py", b"replacement")

    assert any("duplicate path in wheel" in error for error in _archive_errors(wheel))


def test_docs_validator_accepts_button_text_as_accessible_name(tmp_path: Path) -> None:
    html = tmp_path / "index.html"
    html.write_text('<html lang="en"><body><button>Save</button></body></html>', encoding="utf-8")

    assert _validate_html_file(html) == []


def test_docs_validator_accepts_button_image_alt_as_accessible_name(tmp_path: Path) -> None:
    html = tmp_path / "index.html"
    html.write_text(
        '<html lang="en"><body><button><img src="save.svg" alt="Save"></button></body></html>',
        encoding="utf-8",
    )

    assert _validate_html_file(html) == []


def test_docs_validator_rejects_unnamed_button_roles(tmp_path: Path) -> None:
    html = tmp_path / "index.html"
    html.write_text(
        '<html lang="en"><body><span role="button"><span aria-hidden="true">×</span></span>'
        "</body></html>",
        encoding="utf-8",
    )

    assert any("button control is missing" in error for error in _validate_html_file(html))


def test_docs_validator_rejects_broken_label_targets(tmp_path: Path) -> None:
    html = tmp_path / "index.html"
    html.write_text(
        '<html lang="en"><body><label for="missing">Open</label></body></html>',
        encoding="utf-8",
    )

    assert any(
        "for references missing id 'missing'" in error for error in _validate_html_file(html)
    )


def test_docs_validator_rejects_unnamed_dialogs(tmp_path: Path) -> None:
    html = tmp_path / "index.html"
    html.write_text(
        '<html lang="en"><body><div role="dialog" aria-modal="true"></div></body></html>',
        encoding="utf-8",
    )

    assert any(
        "dialog is missing an accessible name" in error for error in _validate_html_file(html)
    )


def test_docs_validator_rejects_empty_form_actions(tmp_path: Path) -> None:
    html = tmp_path / "index.html"
    html.write_text(
        '<html lang="en"><body><form action=""></form></body></html>',
        encoding="utf-8",
    )

    assert any("<form> has an empty action" in error for error in _validate_html_file(html))


def test_docs_validator_rejects_skipped_heading_levels(tmp_path: Path) -> None:
    html = tmp_path / "index.html"
    html.write_text(
        '<html lang="en"><body><h1>Title</h1><h3>Skipped</h3></body></html>',
        encoding="utf-8",
    )

    assert any("heading level 3 follows level 1" in error for error in _validate_html_file(html))


def test_docs_validator_rejects_footer_without_landmark(tmp_path: Path) -> None:
    html = tmp_path / "index.html"
    html.write_text(
        '<html lang="en"><body><div class="footer">Copyright</div></body></html>',
        encoding="utf-8",
    )

    assert any(
        "footer container is missing a contentinfo landmark" in error
        for error in _validate_html_file(html)
    )


def test_docs_validator_rejects_block_elements_inside_pre(tmp_path: Path) -> None:
    html = tmp_path / "index.html"
    html.write_text(
        '<html lang="en"><body><pre tabindex="0"><div>Invalid</div></pre></body></html>',
        encoding="utf-8",
    )

    assert any("<div> is not allowed inside <pre>" in error for error in _validate_html_file(html))
