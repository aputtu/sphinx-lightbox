from __future__ import annotations

from pathlib import Path

from bs4 import BeautifulSoup
from sphinx.testing.util import SphinxTestApp

_PNG_BYTES = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
    b"\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
    b"\x00\x00\x00\nIDATx\x9cc\xf8\x0f\x00\x01\x01\x01\x00"
    b"\x18\xdd\x8d\xb0\x00\x00\x00\x00IEND\xaeB`\x82"
)


def write_image(app: SphinxTestApp, relative_path: str = "images/example.png") -> None:
    image_path = Path(app.srcdir).joinpath(relative_path)
    image_path.parent.mkdir(parents=True, exist_ok=True)
    image_path.write_bytes(_PNG_BYTES)


def write_index(app: SphinxTestApp, content: str) -> None:
    Path(app.srcdir).joinpath("index.rst").write_text(content, encoding="utf-8")


def build_index(app: SphinxTestApp, content: str) -> None:
    write_index(app, content)
    app.build()


def html_text(app: SphinxTestApp) -> str:
    return Path(app.outdir).joinpath("index.html").read_text(encoding="utf-8")


def html_soup(app: SphinxTestApp) -> BeautifulSoup:
    return BeautifulSoup(html_text(app), "html.parser")
