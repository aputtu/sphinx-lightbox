"""Docs-only validation fixes for third-party generated output."""

from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import unquote, urlsplit

from sphinx.application import Sphinx
from sphinx.util.images import get_image_size
from sphinx.util.typing import ExtensionMetadata

_HEADING_WITHOUT_LEVEL_RE = re.compile(r'<p\b(?=[^>]*\brole="heading")[^>]*>')
_PRE_WITHOUT_TABINDEX_RE = re.compile(r"<pre(?![^>]*\btabindex=)([^>]*)>")
_VIEWCODE_BLOCK_RE = re.compile(
    r'<div class="viewcode-block"(?P<attrs>[^>]*)>(?P<body>.*?)</div>',
    re.DOTALL,
)
_SELF_CLOSING_HTML_VOID_RE = re.compile(
    r"(<(?:area|base|br|col|embed|hr|img|input|link|meta|source|track|wbr)\b[^<>]*?)\s*/>",
    re.IGNORECASE,
)
_VIEWPORT_META_RE = re.compile(
    r'<meta\b(?=[^>]*\bname\s*=\s*["\']viewport["\'])[^>]*>',
    re.IGNORECASE,
)
_IMAGE_TAG_RE = re.compile(r"<img\b[^<>]*>", re.IGNORECASE)
_IMAGE_SRC_RE = re.compile(r'\bsrc\s*=\s*(["\'])(?P<src>.*?)\1', re.IGNORECASE)
_WIDTH_OR_HEIGHT_RE = re.compile(r"\b(?:width|height)\s*=", re.IGNORECASE)
_SIG_RETURN_ICON_RE = re.compile(
    r'<span class="sig-return-icon"(?![^>]*\baria-hidden=)(?P<attrs>[^>]*)>'
    r".*?</span>"
)
_SIDEBAR_NAV_HEADING = "<h3>Navigation</h3>"
_SEARCH_FORM_WITH_EMPTY_ACTION = '<form action="" method="get">'
_FOOTER_WITHOUT_LANDMARK = '<div class="footer">'


def _deduplicate_viewport_metadata(content: str) -> str:
    found = False

    def keep_first(match: re.Match[str]) -> str:
        nonlocal found
        if found:
            return ""
        found = True
        return match.group(0)

    return _VIEWPORT_META_RE.sub(keep_first, content)


def _add_intrinsic_image_dimensions(content: str, html_file: Path, outdir: Path) -> str:
    """Add true dimensions and mark local images for responsive docs CSS."""
    output_root = outdir.resolve()

    def add_dimensions(match: re.Match[str]) -> str:
        tag = match.group(0)
        if _WIDTH_OR_HEIGHT_RE.search(tag):
            return tag

        src_match = _IMAGE_SRC_RE.search(tag)
        if src_match is None:
            return tag
        parsed_src = urlsplit(src_match.group("src"))
        if parsed_src.scheme or parsed_src.netloc or not parsed_src.path:
            return tag

        image_path = Path(unquote(parsed_src.path))
        if image_path.is_absolute():
            candidate = output_root / image_path.relative_to("/")
        else:
            candidate = html_file.parent / image_path
        candidate = candidate.resolve()
        if not candidate.is_relative_to(output_root) or not candidate.is_file():
            return tag

        size = get_image_size(candidate)
        if size is None:
            return tag
        width, height = size
        return f'{tag[:-1]} width="{width}" height="{height}" data-docs-intrinsic-size="true">'

    return _IMAGE_TAG_RE.sub(add_dimensions, content)


def _add_missing_heading_level(match: re.Match[str]) -> str:
    tag = match.group(0)
    if "aria-level" in tag:
        return tag
    return f'{tag[:-1]} aria-level="2">'


def _replace_viewcode_block(match: re.Match[str]) -> str:
    return f'<span class="viewcode-block"{match.group("attrs")}>{match.group("body")}</span>'


def _replace_signature_return_icon(match: re.Match[str]) -> str:
    """Replace an ambiguous arrow glyph with explicit readable text."""
    return f'<span class="sig-return-icon"{match.group("attrs")}>returns</span>'


def _patch_generated_html(outdir: Path) -> None:
    for html_file in outdir.rglob("*.html"):
        content = html_file.read_text(encoding="utf-8")
        patched = _deduplicate_viewport_metadata(content)
        patched = _HEADING_WITHOUT_LEVEL_RE.sub(_add_missing_heading_level, patched)
        patched = _PRE_WITHOUT_TABINDEX_RE.sub(r'<pre tabindex="0"\1>', patched)
        patched = _VIEWCODE_BLOCK_RE.sub(_replace_viewcode_block, patched)
        patched = _SELF_CLOSING_HTML_VOID_RE.sub(r"\1>", patched)
        patched = _add_intrinsic_image_dimensions(patched, html_file, outdir)
        patched = _SIG_RETURN_ICON_RE.sub(_replace_signature_return_icon, patched)
        patched = patched.replace(
            _SIDEBAR_NAV_HEADING,
            '<h2 class="sphinxsidebar-title">Navigation</h2>',
        )
        patched = patched.replace(
            _SEARCH_FORM_WITH_EMPTY_ACTION,
            '<form action="search.html" method="get">',
        )
        patched = patched.replace(
            _FOOTER_WITHOUT_LANDMARK,
            '<div class="footer" role="contentinfo">',
        )
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
