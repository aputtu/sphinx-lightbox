#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from collections import Counter
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit

IDREF_ATTRS = (
    "aria-controls",
    "aria-describedby",
    "aria-details",
    "aria-errormessage",
    "aria-labelledby",
    "aria-owns",
)
_SOURCE_BUILD_ASSETS = (
    ("lightbox/static/lightbox.css", "_static/lightbox.css"),
    ("lightbox/static/lightbox.js", "_static/lightbox.js"),
    ("docs/_static/favicon.png", "_static/favicon.png"),
)
_RASTER_IMAGE_SUFFIXES = {".avif", ".gif", ".jpeg", ".jpg", ".png", ".webp"}
_VOID_ELEMENTS = {
    "area",
    "base",
    "br",
    "col",
    "embed",
    "hr",
    "img",
    "input",
    "link",
    "meta",
    "param",
    "source",
    "track",
    "wbr",
}
_BLOCK_ELEMENTS = {
    "address",
    "article",
    "aside",
    "blockquote",
    "div",
    "dl",
    "fieldset",
    "figcaption",
    "figure",
    "footer",
    "form",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "header",
    "hgroup",
    "hr",
    "main",
    "menu",
    "nav",
    "ol",
    "p",
    "pre",
    "section",
    "table",
    "ul",
}


@dataclass
class ParsedTag:
    tag: str
    attrs: dict[str, str]
    line: int
    ancestors: tuple[str, ...] = ()
    text_parts: list[str] = field(default_factory=list)

    @property
    def text(self) -> str:
        return "".join(self.text_parts).strip()


class DocumentParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.tags: list[ParsedTag] = []
        self._open_tags: list[int] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        parsed = ParsedTag(
            tag,
            {key: value or "" for key, value in attrs},
            self.getpos()[0],
            tuple(self.tags[index].tag for index in self._open_tags),
        )
        self.tags.append(parsed)
        if (
            tag == "img"
            and parsed.attrs.get("aria-hidden") != "true"
            and parsed.attrs.get("alt", "").strip()
            and not any(
                self.tags[index].attrs.get("aria-hidden") == "true" for index in self._open_tags
            )
        ):
            for index in self._open_tags:
                self.tags[index].text_parts.append(parsed.attrs["alt"])
        if tag not in _VOID_ELEMENTS:
            self._open_tags.append(len(self.tags) - 1)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.tags.append(
            ParsedTag(
                tag,
                {key: value or "" for key, value in attrs},
                self.getpos()[0],
                tuple(self.tags[index].tag for index in self._open_tags),
            )
        )

    def handle_endtag(self, tag: str) -> None:
        for position in range(len(self._open_tags) - 1, -1, -1):
            if self.tags[self._open_tags[position]].tag == tag:
                del self._open_tags[position:]
                return

    def handle_data(self, data: str) -> None:
        if any(self.tags[index].attrs.get("aria-hidden") == "true" for index in self._open_tags):
            return
        for index in self._open_tags:
            self.tags[index].text_parts.append(data)


def _has_accessible_name(element: ParsedTag) -> bool:
    attrs = element.attrs
    return bool(
        attrs.get("aria-label", "").strip()
        or attrs.get("aria-labelledby", "").strip()
        or attrs.get("title", "").strip()
        or (element.tag == "input" and attrs.get("value", "").strip())
        or element.text
    )


def _validate_html_file(path: Path) -> list[str]:
    parser = DocumentParser()
    try:
        parser.feed(path.read_text(encoding="utf-8"))
    except UnicodeDecodeError as exc:
        return [f"{path}: cannot decode as UTF-8: {exc}"]

    errors: list[str] = []
    ids = [element.attrs["id"] for element in parser.tags if element.attrs.get("id")]
    id_counts = Counter(ids)
    id_set = set(ids)
    previous_heading_level = 0

    viewport_count = sum(
        1
        for element in parser.tags
        if element.tag == "meta" and element.attrs.get("name", "").lower() == "viewport"
    )
    if viewport_count > 1:
        errors.append(f"{path}: expected at most one viewport meta element, found {viewport_count}")

    for element_id, count in id_counts.items():
        if count > 1:
            errors.append(f"{path}: duplicate id {element_id!r} appears {count} times")

    for element in parser.tags:
        tag = element.tag
        attrs = element.attrs
        line = element.line
        if tag == "html" and not attrs.get("lang", "").strip():
            errors.append(f"{path}:{line}: <html> is missing lang")

        if "pre" in element.ancestors and tag in _BLOCK_ELEMENTS:
            errors.append(f"{path}:{line}: <{tag}> is not allowed inside <pre>")

        heading_level = 0
        if len(tag) == 2 and tag[0] == "h" and tag[1].isdigit():
            heading_level = int(tag[1])
        elif attrs.get("role") == "heading" and attrs.get("aria-level", "").isdigit():
            heading_level = int(attrs["aria-level"])
        if heading_level:
            if previous_heading_level and heading_level > previous_heading_level + 1:
                errors.append(
                    f"{path}:{line}: heading level {heading_level} follows "
                    f"level {previous_heading_level}"
                )
            previous_heading_level = heading_level

        if tag == "img":
            is_decorative = (
                attrs.get("role") == "presentation" or attrs.get("aria-hidden") == "true"
            )
            if "alt" not in attrs and not is_decorative:
                errors.append(f"{path}:{line}: <img> is missing alt text")
            parsed_src = urlsplit(attrs.get("src", ""))
            is_local_raster = (
                not parsed_src.scheme
                and not parsed_src.netloc
                and Path(parsed_src.path).suffix.lower() in _RASTER_IMAGE_SUFFIXES
            )
            if is_local_raster and "width" not in attrs and "height" not in attrs:
                errors.append(f"{path}:{line}: local raster <img> is missing intrinsic dimensions")

        if tag == "iframe" and not attrs.get("title", "").strip():
            errors.append(f"{path}:{line}: <iframe> is missing title")

        if tag == "form" and "action" in attrs and not attrs["action"].strip():
            errors.append(f"{path}:{line}: <form> has an empty action")

        if (
            "footer" in attrs.get("class", "").split()
            and tag != "footer"
            and attrs.get("role") != "contentinfo"
        ):
            errors.append(f"{path}:{line}: footer container is missing a contentinfo landmark")

        if (tag == "button" or attrs.get("role") == "button") and not _has_accessible_name(element):
            errors.append(f"{path}:{line}: button control is missing an accessible name")

        if attrs.get("role") == "dialog" and not (
            attrs.get("aria-label", "").strip() or attrs.get("aria-labelledby", "").strip()
        ):
            errors.append(f"{path}:{line}: dialog is missing an accessible name")

        if attrs.get("role") == "heading" and not attrs.get("aria-level", "").strip():
            errors.append(f"{path}:{line}: role='heading' is missing aria-level")

        if tag == "pre" and "tabindex" not in attrs:
            errors.append(f"{path}:{line}: <pre> is missing tabindex")

        for attr in IDREF_ATTRS:
            for target_id in attrs.get(attr, "").split():
                if target_id and target_id not in id_set:
                    errors.append(f"{path}:{line}: {attr} references missing id {target_id!r}")

        if tag == "label" and attrs.get("for") and attrs["for"] not in id_set:
            errors.append(f"{path}:{line}: for references missing id {attrs['for']!r}")

    contentinfo_count = sum(
        1
        for element in parser.tags
        if element.tag == "footer" or element.attrs.get("role") == "contentinfo"
    )
    if contentinfo_count > 1:
        errors.append(
            f"{path}: expected at most one contentinfo landmark, found {contentinfo_count}"
        )

    return errors


def _source_build_parity_errors(html_dir: Path, source_root: Path) -> list[str]:
    """Return errors when generated source/download assets are stale."""
    errors: list[str] = []
    for source_name, built_name in _SOURCE_BUILD_ASSETS:
        source_path = source_root / source_name
        built_path = html_dir / built_name
        if not source_path.is_file():
            errors.append(f"{source_path}: source asset is missing")
        elif not built_path.is_file():
            errors.append(f"{built_path}: generated asset is missing")
        elif built_path.read_bytes() != source_path.read_bytes():
            errors.append(f"{built_path}: generated asset differs from {source_path}")

    source_pdf = source_root / "docs/_downloads/sphinx-lightbox.pdf"
    if source_pdf.is_file():
        built_pdfs = sorted(html_dir.glob("_downloads/**/sphinx-lightbox.pdf"))
        if len(built_pdfs) != 1:
            errors.append(
                f"{html_dir}: expected exactly one generated sphinx-lightbox.pdf download"
            )
        elif built_pdfs[0].read_bytes() != source_pdf.read_bytes():
            errors.append(f"{built_pdfs[0]}: generated PDF download differs from {source_pdf}")
    return errors


def validate_docs(html_dir: Path, source_root: Path | None = None) -> list[str]:
    if not html_dir.exists():
        return [f"{html_dir}: directory does not exist"]

    html_files = sorted(html_dir.rglob("*.html"))
    if not html_files:
        return [f"{html_dir}: no HTML files found"]

    errors: list[str] = []
    leaked_doctrees = sorted(
        path for path in html_dir.rglob("*") if ".doctrees" in path.relative_to(html_dir).parts
    )
    if leaked_doctrees:
        errors.append(f"{html_dir}: contains public Sphinx build state under .doctrees")

    for html_file in html_files:
        errors.extend(_validate_html_file(html_file))
        parser = DocumentParser()
        parser.feed(html_file.read_text(encoding="utf-8"))
        favicon_links = [
            element
            for element in parser.tags
            if element.tag == "link" and element.attrs.get("rel") == "icon"
        ]
        if len(favicon_links) != 1:
            errors.append(
                f"{html_file}: expected exactly one favicon link, found {len(favicon_links)}"
            )
    errors.extend(
        _source_build_parity_errors(
            html_dir,
            source_root or Path(__file__).resolve().parents[1],
        )
    )

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate generated Sphinx HTML docs.")
    parser.add_argument("html_dir", nargs="?", default="docs/_build/html")
    args = parser.parse_args()

    errors = validate_docs(Path(args.html_dir))
    if errors:
        print("Documentation validation failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    print(f"Documentation validation passed: {args.html_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
