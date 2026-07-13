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
    trigger_label = container.select_one("label.lightbox-trigger-label")
    trigger = container.select_one(".lightbox-trigger-control")
    overlay = container.select_one('.lightbox-overlay[role="dialog"][aria-modal="true"]')
    assert checkbox is not None
    assert trigger_label is not None
    assert trigger is not None
    assert overlay is not None
    assert trigger_label["for"] == checkbox["id"]
    assert "role" not in trigger_label.attrs
    assert trigger["role"] == "button"
    assert trigger["data-lightbox-target"] == checkbox["id"]
    assert overlay["aria-label"] == "Example image."
    close_label = overlay.select_one("label.lightbox-close-label")
    close = overlay.select_one(".lightbox-close")
    assert close_label is not None
    assert close is not None
    assert close_label["for"] == checkbox["id"]
    assert "role" not in close_label.attrs
    assert close["role"] == "button"
    assert close["data-lightbox-target"] == checkbox["id"]
    trigger_image = container.select_one("img.lightbox-trigger")
    assert trigger_image is not None
    assert trigger_image["alt"] == ""
    assert trigger_image["src"].startswith("_images/")


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
    assert trigger_image["alt"] == ""
    assert alt_payload in soup.select_one(".lightbox-trigger-control").get_text(" ", strip=True)
    assert overlay["aria-label"] == alt_payload
    assert caption.get_text(strip=True) == caption_payload


@pytest.mark.sphinx("html")
def test_standard_image_preserves_native_options_on_thumbnail(app: SphinxTestApp) -> None:
    write_image(app)
    build_index(
        app,
        """
Native image options
====================

.. image:: images/example.png
   :alt: Native options example.
   :width: 60%
   :height: 200px
   :scale: 50%
   :align: right
   :loading: lazy
   :name: native-options-example
   :class: lightbox custom-thumbnail
""",
    )

    soup = html_soup(app)
    container = soup.select_one(".lightbox-container.align-right")
    assert container is not None
    thumbnail = container.select_one("img.lightbox-trigger.custom-thumbnail")
    assert thumbnail is not None
    assert thumbnail["alt"] == ""
    assert thumbnail["loading"] == "lazy"
    assert thumbnail["id"] == "native-options-example"
    styles = {}
    for declaration in thumbnail["style"].split(";"):
        if ":" in declaration:
            name, value = declaration.split(":", 1)
            styles[name.strip()] = value.strip()
    assert float(styles["width"].removesuffix("%")) == 30
    assert float(styles["height"].removesuffix("px")) == 100


@pytest.mark.sphinx("html")
def test_figure_preserves_native_wrapper_options(app: SphinxTestApp) -> None:
    write_image(app)
    build_index(
        app,
        """
Native figure options
=====================

.. figure:: images/example.png
   :alt: Native figure options example.
   :width: 100%
   :figwidth: 40%
   :align: right
   :figclass: product-figure

   Native figure caption.
""",
    )

    soup = html_soup(app)
    figure = soup.select_one("figure.align-right.product-figure")
    assert figure is not None
    assert "width: 40%" in figure["style"]
    assert figure.select_one(".lightbox-container") is not None
    thumbnail = figure.select_one("img.lightbox-trigger")
    assert thumbnail is not None
    assert "width: 100%" in thumbnail["style"]
    assert (
        figure.select_one("figcaption .caption-text").get_text(" ", strip=True)
        == "Native figure caption."
    )


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
    write_image(app, "images/pdf-only.png")
    build_index(
        app,
        """
Generated HTML
==============

.. only:: html

   .. image:: images/first.png
      :alt: First image.
      :class: lightbox

.. only:: latex

   .. image:: images/pdf-only.png
      :alt: PDF-only image.
      :class: lightbox

.. image:: images/second.png
   :alt: Second image.
   :class: lightbox
""",
    )

    soup = html_soup(app)
    assert len(soup.select(".lightbox-container")) == 2
    controls = soup.select(".lightbox-gallery-control")
    assert controls
    for control in controls:
        target_id = control["data-lightbox-target"]
        assert soup.find(id=target_id) is not None
        assert "of 2" in control["aria-label"]


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


@pytest.mark.sphinx("html")
def test_legacy_checkbox_id_does_not_duplicate_later_named_image(app: SphinxTestApp) -> None:
    write_image(app)
    build_index(
        app,
        """
Unique generated ids
====================

.. lightbox:: images/example.png
   :alt: Compatibility lightbox.

.. image:: images/example.png
   :alt: Named standard image.
   :name: lightbox-index-0
   :class: lightbox
""",
    )

    soup = html_soup(app)
    ids = [element["id"] for element in soup.select("[id]")]
    checkbox_ids = [checkbox["id"] for checkbox in soup.select(".lightbox-toggle")]
    assert len(ids) == len(set(ids))
    assert checkbox_ids == ["lightbox-index-1", "lightbox-index-2"]
    assert soup.select_one("img#lightbox-index-0.lightbox-trigger") is not None
    assert {
        label["for"]
        for label in soup.select("label.lightbox-trigger-label, label.lightbox-close-label")
    } == set(checkbox_ids)


@pytest.mark.sphinx("html", confoverrides={"lightbox_all_images": True})
def test_nested_document_writes_no_images_outside_outdir(app: SphinxTestApp) -> None:
    """A page nested several levels deep must not push images above outdir.

    The build-finished copy step used builder.imgpath, which Sphinx rewrites on
    every write_doc to a URI relative to that document ("../../../_images" here).
    Joined onto outdir, that escaped the build tree entirely.

    Sphinx writes documents in sorted order, so the nested page is deliberately
    named to sort after "index" and thus be written last -- that is what leaves
    the escaping imgpath behind on the builder at build-finished time.
    """
    write_image(app, "topics/deep/nested/images/example.png")
    app.srcdir.joinpath("topics/deep/nested/page.rst").write_text(
        "Nested\n======\n\n.. image:: images/example.png\n   :alt: Nested image\n",
        encoding="utf-8",
    )
    build_index(
        app,
        """
Root
====

.. toctree::

   topics/deep/nested/page
""",
    )

    outdir = Path(app.outdir)
    assert outdir.joinpath("_images").is_dir()
    escaped_image_dir = outdir.parents[2] / "_images"
    assert not escaped_image_dir.exists(), f"images written outside outdir, at {escaped_image_dir}"


@pytest.mark.sphinx("epub")
def test_epub_uses_visible_plain_image_fallbacks(app: SphinxTestApp) -> None:
    write_image(app)
    build_index(
        app,
        """
EPUB fallbacks
==============

.. image:: images/example.png
   :alt: Standard EPUB image.
   :class: lightbox

.. lightbox:: images/example.png
   :alt: Directive EPUB image.
""",
    )

    soup = BeautifulSoup(
        app.outdir.joinpath("index.xhtml").read_text(encoding="utf-8"), "html.parser"
    )
    assert soup.select_one(".lightbox-container") is None
    assert soup.select_one(".lightbox-hidden") is None
    assert {image.get("alt") for image in soup.select("img")} >= {
        "Standard EPUB image.",
        "Directive EPUB image.",
    }
