"""Docs-only validation fixes for third-party generated output."""

from __future__ import annotations

import re
from pathlib import Path

from sphinx.application import Sphinx
from sphinx.util.typing import ExtensionMetadata

_HEADING_WITHOUT_LEVEL_RE = re.compile(r'<p\b(?=[^>]*\brole="heading")[^>]*>')
_PRE_WITHOUT_TABINDEX_RE = re.compile(r"<pre(?![^>]*\btabindex=)([^>]*)>")


def _add_missing_heading_level(match: re.Match[str]) -> str:
    tag = match.group(0)
    if "aria-level" in tag:
        return tag
    return f'{tag[:-1]} aria-level="2">'


def _patch_generated_html(outdir: Path) -> None:
    for html_file in outdir.rglob("*.html"):
        content = html_file.read_text(encoding="utf-8")
        patched = _HEADING_WITHOUT_LEVEL_RE.sub(_add_missing_heading_level, content)
        patched = _PRE_WITHOUT_TABINDEX_RE.sub(r'<pre tabindex="0"\1>', patched)
        if patched != content:
            html_file.write_text(patched, encoding="utf-8")


def _patch_generated_docs(app: Sphinx, exception: Exception | None) -> None:
    if exception is not None or app.builder.format != "html":
        return

    outdir = Path(app.outdir)
    _patch_generated_html(outdir)


def setup(app: Sphinx) -> ExtensionMetadata:
    app.connect("build-finished", _patch_generated_docs)
    return {
        "version": "1.0",
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
