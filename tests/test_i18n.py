from __future__ import annotations

import gettext
import subprocess
import sys
import textwrap
from pathlib import Path
from unittest.mock import Mock

from bs4 import BeautifulSoup

from lightbox.lightbox import setup
from tests.helpers import _PNG_BYTES

_CATALOG = "sphinx-lightbox"
_LOCALE_DIR = Path(__file__).resolve().parents[1] / "lightbox" / "locales"


def test_setup_registers_extension_owned_message_catalog() -> None:
    app = Mock()
    app.config.html_static_path = []

    setup(app)

    app.add_message_catalog.assert_called_once_with(_CATALOG, _LOCALE_DIR)


def test_danish_catalog_translates_every_extension_message() -> None:
    translations = gettext.translation(_CATALOG, localedir=_LOCALE_DIR, languages=["da"])
    expected = {
        "Image": "Billede",
        "Invalid lightbox thumbnail width {width!r}; falling back to '100%'.": (
            "Ugyldig bredde {width!r} på lysboksminiaturen; bruger '100%' i stedet."
        ),
        "Invalid lightbox inline style suppressed.": (
            "Ugyldig inline-CSS for lysboksen blev udeladt."
        ),
        "Refusing to copy lightbox images outside the output directory: '{directory}'": (
            "Afviser at kopiere lysboksbilleder uden for outputmappen: '{directory}'"
        ),
        "Could not copy lightbox image '{source}' to '{target}': {error}": (
            "Kunne ikke kopiere lysboksbilledet '{source}' til '{target}': {error}"
        ),
        (
            "Invalid {config_name} value {policy!r}; expected one of 'explicit', 'all', "
            "or 'none'. Falling back to 'explicit'."
        ): (
            "Ugyldig værdi {policy!r} for {config_name}; forventede en af 'explicit', "
            "'all' eller 'none'. Bruger 'explicit' i stedet."
        ),
        (
            "Invalid lightbox_gallery value {mode!r}; expected 'document' or 'none'. "
            "Falling back to 'document'."
        ): (
            "Ugyldig værdi {mode!r} for lightbox_gallery; forventede 'document' eller "
            "'none'. Bruger 'document' i stedet."
        ),
        "Enlarge image: {image}": "Forstør billede: {image}",
        "Previous image in gallery ({index} of {count})": (
            "Forrige billede i galleriet ({index} af {count})"
        ),
        "Next image in gallery ({index} of {count})": (
            "Næste billede i galleriet ({index} af {count})"
        ),
        "Close lightbox": "Luk billedvisning",
        (
            "Could not calculate image dimensions for '{path}': {error}. "
            "Falling back to 1:1 aspect ratio."
        ): (
            "Kunne ikke beregne billeddimensionerne for '{path}': {error}. "
            "Bruger formatforholdet 1:1 i stedet."
        ),
        (
            "Invalid :latex-width: value '{value}'. Expected a float between 0 and 1 "
            "(e.g. 0.8). Falling back to percentage-based width."
        ): (
            "Ugyldig værdi '{value}' for :latex-width:. Forventede et decimaltal mellem "
            "0 og 1 (f.eks. 0.8). Bruger den procentbaserede bredde i stedet."
        ),
        "Lightbox image path traverses outside source directory: {path}": (
            "Stien til lysboksbilledet går uden for kildemappen: {path}"
        ),
        "Lightbox image not found: {path}": "Lysboksbilledet blev ikke fundet: {path}",
    }

    assert {message: translations.gettext(message) for message in expected} == expected


def test_sphinx_danish_build_uses_bundled_catalog(tmp_path: Path) -> None:
    srcdir = tmp_path / "src"
    outdir = tmp_path / "out"
    image_dir = srcdir / "images"
    image_dir.mkdir(parents=True)
    image_dir.joinpath("first.png").write_bytes(_PNG_BYTES)
    image_dir.joinpath("second.png").write_bytes(_PNG_BYTES)
    srcdir.joinpath("conf.py").write_text(
        textwrap.dedent(
            f"""
            import sys

            sys.path.insert(0, {str(Path.cwd())!r})

            extensions = ["lightbox"]
            project = "Danish localization test"
            language = "da"
            html_static_path = []
            lightbox_gallery = "invalid"
            """
        ),
        encoding="utf-8",
    )
    srcdir.joinpath("index.rst").write_text(
        textwrap.dedent(
            """
            Dansk billedvisning
            ==================

            .. image:: images/first.png
               :alt: Første motiv.
               :class: lightbox

            .. image:: images/second.png
               :alt: Andet motiv.
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
    assert "Ugyldig værdi 'invalid' for lightbox_gallery" in result.stderr

    soup = BeautifulSoup(outdir.joinpath("index.html").read_text(encoding="utf-8"), "html.parser")
    trigger_names = [
        trigger.get_text(" ", strip=True) for trigger in soup.select(".lightbox-trigger-control")
    ]
    assert trigger_names == ["Forstør billede: Første motiv.", "Forstør billede: Andet motiv."]
    assert [
        close.get_text(" ", strip=True)
        for close in soup.select(".lightbox-visually-hidden")
        if "Luk" in close.get_text()
    ] == ["Luk billedvisning", "Luk billedvisning"]
    assert soup.select_one(".lightbox-gallery-next")["aria-label"] == (
        "Næste billede i galleriet (1 af 2)"
    )
    assert soup.select_one(".lightbox-gallery-prev")["aria-label"] == (
        "Forrige billede i galleriet (2 af 2)"
    )
    assert [overlay["aria-label"] for overlay in soup.select(".lightbox-overlay")] == [
        "Første motiv.",
        "Andet motiv.",
    ]
