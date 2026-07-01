"""Tests for lightbox.css accessibility styling."""

from pathlib import Path

CSS_PATH = Path(__file__).resolve().parents[1] / "lightbox" / "static" / "lightbox.css"


def test_caption_and_legend_use_one_dark_background_panel() -> None:
    source = CSS_PATH.read_text(encoding="utf-8")

    assert ".lightbox-text {" in source
    assert "background: rgba(0, 0, 0, 0.92);" in source
    assert "border-radius: 4px;" in source
    assert "padding: 0.5rem 0.875rem;" in source
    assert ".lightbox-caption + .lightbox-legend" in source


def test_high_contrast_caption_panel_is_solid() -> None:
    source = CSS_PATH.read_text(encoding="utf-8")
    high_contrast = source.split("@media (prefers-contrast: more)", 1)[1]

    assert ".lightbox-text" in high_contrast
    assert "background: #000;" in high_contrast
    assert "border: 2px solid #fff;" in high_contrast
