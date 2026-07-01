#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path

IDREF_ATTRS = ("aria-controls", "aria-describedby", "aria-labelledby")


class DocumentParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.tags: list[tuple[str, dict[str, str], int]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.tags.append((tag, {key: value or "" for key, value in attrs}, self.getpos()[0]))

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)


def _has_accessible_name(attrs: dict[str, str]) -> bool:
    return bool(attrs.get("aria-label") or attrs.get("aria-labelledby") or attrs.get("title"))


def _validate_html_file(path: Path) -> list[str]:
    parser = DocumentParser()
    try:
        parser.feed(path.read_text(encoding="utf-8"))
    except UnicodeDecodeError as exc:
        return [f"{path}: cannot decode as UTF-8: {exc}"]

    errors: list[str] = []
    ids = [attrs["id"] for _tag, attrs, _line in parser.tags if attrs.get("id")]
    id_counts = Counter(ids)
    id_set = set(ids)

    for element_id, count in id_counts.items():
        if count > 1:
            errors.append(f"{path}: duplicate id {element_id!r} appears {count} times")

    for tag, attrs, line in parser.tags:
        if tag == "html" and not attrs.get("lang"):
            errors.append(f"{path}:{line}: <html> is missing lang")

        if tag == "img":
            is_decorative = (
                attrs.get("role") == "presentation" or attrs.get("aria-hidden") == "true"
            )
            if "alt" not in attrs and not is_decorative:
                errors.append(f"{path}:{line}: <img> is missing alt text")

        if tag == "iframe" and not attrs.get("title"):
            errors.append(f"{path}:{line}: <iframe> is missing title")

        if tag == "button" and not _has_accessible_name(attrs):
            errors.append(f"{path}:{line}: <button> is missing an accessible name")

        if attrs.get("role") == "heading" and not attrs.get("aria-level"):
            errors.append(f"{path}:{line}: role='heading' is missing aria-level")

        if tag == "pre" and "tabindex" not in attrs:
            errors.append(f"{path}:{line}: <pre> is missing tabindex")

        for attr in IDREF_ATTRS:
            for target_id in attrs.get(attr, "").split():
                if target_id and target_id not in id_set:
                    errors.append(f"{path}:{line}: {attr} references missing id {target_id!r}")

    contentinfo_count = sum(
        1
        for tag, attrs, _line in parser.tags
        if tag == "footer" or attrs.get("role") == "contentinfo"
    )
    if contentinfo_count > 1:
        errors.append(
            f"{path}: expected at most one contentinfo landmark, found {contentinfo_count}"
        )

    return errors


def validate_docs(html_dir: Path) -> list[str]:
    if not html_dir.exists():
        return [f"{html_dir}: directory does not exist"]

    html_files = sorted(html_dir.rglob("*.html"))
    if not html_files:
        return [f"{html_dir}: no HTML files found"]

    errors: list[str] = []
    for html_file in html_files:
        errors.extend(_validate_html_file(html_file))

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
