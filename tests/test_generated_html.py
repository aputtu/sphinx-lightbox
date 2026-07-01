from __future__ import annotations

import subprocess
import sys
import textwrap
from pathlib import Path

import pytest
from bs4 import BeautifulSoup
from sphinx.testing.util import SphinxTestApp

from tests.helpers import build_index, html_soup, html_text, write_image

_PNG_BYTES = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
    b"\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
    b"\x00\x00\x00\nIDATx\x9cc\xf8\x0f\x00\x01\x01\x01\x00"
    b"\x18\xdd\x8d\xb0\x00\x00\x00\x00IEND\xaeB`\x82"
)


@pytest.mark.sphinx("html")
def test_standard_image_generates_lightbox_markup(app: SphinxTestApp) -> None:
    write_image(app)
    build_index(
        app,
        """
Generated HTML
==============

.. image:: images/example.png
   :alt: Example image.
   :class: lightbox
""",
    )

    soup = html_soup(app)
    container = soup.select_one(".lightbox-container")
    assert container is not None

    checkbox = container.select_one('input[type="checkbox"].lightbox-toggle')
    trigger = container.select_one(".lightbox-trigger-label")
    overlay = container.select_one('.lightbox-overlay[role="dialog"][aria-modal="true"]')
    assert checkbox is not None
    assert trigger is not None
    assert overlay is not None
    assert trigger["for"] == checkbox["id"]
    assert overlay["aria-label"] == "Example image."
    assert container.select_one("img.lightbox-trigger")["src"].startswith("_images/")


@pytest.mark.sphinx("html")
def test_generated_html_escapes_alt_and_caption(app: SphinxTestApp) -> None:
    write_image(app)
    alt_payload = '<script>alert("alt")</script>'
    caption_payload = "<script>alert(caption)</script>"
    build_index(
        app,
        f"""
Generated HTML
==============

.. figure:: images/example.png
   :alt: {alt_payload}

   {caption_payload}
""",
    )

    html = html_text(app)
    assert alt_payload not in html
    assert caption_payload not in html

    soup = BeautifulSoup(html, "html.parser")
    trigger_image = soup.select_one("img.lightbox-trigger")
    overlay = soup.select_one(".lightbox-overlay")
    text_panel = soup.select_one(".lightbox-text")
    caption = soup.select_one(".lightbox-caption")
    assert trigger_image is not None
    assert overlay is not None
    assert text_panel is not None
    assert caption is not None
    assert caption.parent == text_panel
    assert trigger_image["alt"] == alt_payload
    assert overlay["aria-label"] == alt_payload
    assert caption.get_text(strip=True) == caption_payload


@pytest.mark.sphinx("html")
def test_remote_and_data_images_are_not_transformed(app: SphinxTestApp) -> None:
    build_index(
        app,
        """
Generated HTML
==============

.. image:: https://example.invalid/remote.png
   :alt: Remote image.
   :class: lightbox

.. image:: data:image/png;base64,AAAA
   :alt: Data image.
   :class: lightbox
""",
    )

    soup = html_soup(app)
    assert soup.select_one(".lightbox-container") is None
    image_sources = {image["src"] for image in soup.select("img")}
    assert "https://example.invalid/remote.png" in image_sources
    assert "data:image/png;base64,AAAA" in image_sources


@pytest.mark.sphinx("html")
def test_gallery_controls_reference_existing_lightbox_ids(app: SphinxTestApp) -> None:
    write_image(app, "images/first.png")
    write_image(app, "images/second.png")
    build_index(
        app,
        """
Generated HTML
==============

.. image:: images/first.png
   :alt: First image.
   :class: lightbox

.. image:: images/second.png
   :alt: Second image.
   :class: lightbox
""",
    )

    soup = html_soup(app)
    controls = soup.select(".lightbox-gallery-control")
    assert controls
    for control in controls:
        target_id = control["data-lightbox-target"]
        assert soup.find(id=target_id) is not None


def test_generated_ids_are_sanitized_for_unusual_docnames(tmp_path: Path) -> None:
    docname = 'bad" onclick="alert(1)'
    srcdir = tmp_path / "src"
    outdir = tmp_path / "out"
    image_dir = srcdir / "images"
    image_dir.mkdir(parents=True)
    image_dir.joinpath("example.png").write_bytes(_PNG_BYTES)
    srcdir.joinpath("conf.py").write_text(
        textwrap.dedent(
            f"""
            import sys

            sys.path.insert(0, {str(Path.cwd())!r})

            extensions = ["lightbox"]
            project = "Security test"
            root_doc = {docname!r}
            html_static_path = []
            """
        ),
        encoding="utf-8",
    )
    srcdir.joinpath(f"{docname}.rst").write_text(
        textwrap.dedent(
            """
            Generated HTML
            ==============

            .. image:: images/example.png
               :alt: Example image.
               :class: lightbox
            """
        ),
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "sphinx.cmd.build",
            "-q",
            "-b",
            "html",
            str(srcdir),
            str(outdir),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"

    html = outdir.joinpath(f"{docname}.html").read_text(encoding="utf-8")
    assert "onclick" not in html.split("lightbox-bad", 1)[0]

    soup = BeautifulSoup(html, "html.parser")
    checkbox = soup.select_one(".lightbox-toggle")
    trigger = soup.select_one(".lightbox-trigger-label")
    assert checkbox is not None
    assert trigger is not None
    assert checkbox["id"].startswith("lightbox-bad-onclick-alert-1-")
    assert '"' not in checkbox["id"]
    assert trigger["for"] == checkbox["id"]
