"""
Pytest configuration and shared fixtures.

This file contains reusable test fixtures and pytest configuration
that is shared across all test modules.
"""

from unittest.mock import Mock

import pytest
from sphinx.util import texescape

# ---------------------------------------------------------------------------
# One-time initialisation
# ---------------------------------------------------------------------------

# sphinx.util.texescape.escape() is a no-op until init() populates the
# replacement table.  Sphinx normally calls this during app startup; we
# must do it explicitly so unit tests that call latex_escape() directly
# (without booting a full Sphinx application) get correct escaping.
texescape.init()


# ---------------------------------------------------------------------------
# Core fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_builder():
    """
    Mock Sphinx builder with minimal required attributes.

    Provides just enough to test LaTeX visitor functions without
    running a full Sphinx build.
    """
    builder = Mock()
    builder.name = "latex"
    builder.images = {}  # URI → output filename mapping

    translator = Mock()
    translator.body = []          # Collects LaTeX output fragments
    translator.builder = builder

    builder.translator = translator

    return builder


@pytest.fixture
def sphinx_env():
    """
    Mock Sphinx environment with minimal required attributes.

    Provides docname, srcdir, and an images collection without
    needing a full Sphinx application instance.
    """
    env = Mock()
    env.docname = "test"
    env.srcdir = "/tmp/test-sphinx"

    env.images = Mock()
    env.images.add_file = Mock()

    _serial_counters: dict = {}

    def new_serialno(category: str) -> int:
        _serial_counters.setdefault(category, 0)
        _serial_counters[category] += 1
        return _serial_counters[category]

    env.new_serialno = new_serialno

    return env


@pytest.fixture
def tmp_sphinx_project(tmp_path):
    """
    Minimal Sphinx project in a temporary directory.

    Use when you need real file I/O; prefer mock_builder / sphinx_env
    for most tests.
    """
    project_dir = tmp_path / "sphinx-project"
    project_dir.mkdir()

    (project_dir / "conf.py").write_text(
        "extensions = ['lightbox']\nproject = 'Test Project'\n"
    )
    (project_dir / "index.rst").write_text(
        "Test Project\n============\n\n.. toctree::\n\n   test_page\n"
    )
    (project_dir / "test_page.rst").write_text(
        "Test Page\n=========\n\n.. lightbox:: /images/test.png\n   :alt: Test image\n"
    )

    images_dir = project_dir / "images"
    images_dir.mkdir()
    (images_dir / "test.png").write_bytes(b"PNG_PLACEHOLDER")

    return project_dir


@pytest.fixture
def minimal_rst_doc():
    """Common RST snippets for directive tests."""
    return {
        "basic": ".. lightbox:: /images/test.png\n   :alt: Test image\n",
        "with_caption": (
            ".. lightbox:: /images/test.png\n"
            "   :alt: Test image\n"
            "   :caption: This is a caption\n"
        ),
        "with_percentage": (
            ".. lightbox:: /images/test.png\n"
            "   :alt: Test image\n"
            "   :percentage: 50 90\n"
        ),
        "with_class": (
            ".. lightbox:: /images/test.png\n"
            "   :alt: Test image\n"
            "   :class: with-border\n"
        ),
        "full_options": (
            ".. lightbox:: /images/test.png\n"
            "   :alt: Test image\n"
            "   :caption: Full example with 40% width\n"
            "   :percentage: 40 85\n"
            "   :class: custom-style\n"
        ),
        "missing_arg": ".. lightbox::\n   :alt: Oops no image\n",
        "invalid_percentage": ".. lightbox:: /images/test.png\n   :percentage: -50\n",
    }


@pytest.fixture
def latex_patterns():
    """Regex patterns for validating LaTeX output structure."""
    import re
    return {
        "figure": re.compile(
            r"\\begin\{figure\}\[htbp\].*?\\end\{figure\}", re.DOTALL
        ),
        "adjustbox": re.compile(r"\\adjustbox\{max width=[\d.]+\\linewidth\}"),
        "includegraphics": re.compile(r"\\includegraphics\{[^}]+\}"),
        "caption": re.compile(r"\\caption\{[^}]*\}"),
    }


@pytest.fixture
def html_patterns():
    """Regex patterns for validating HTML output structure."""
    import re
    return {
        "container": re.compile(
            r'<div class="lightbox-container">.*?</div>', re.DOTALL
        ),
        "checkbox": re.compile(
            r'<input type="checkbox"[^>]*class="lightbox-toggle"'
        ),
        "overlay": re.compile(r'<div class="lightbox-overlay"[^>]*>'),
        "trigger": re.compile(r'<label[^>]*class="[^"]*lightbox-trigger[^"]*"'),
    }


# ---------------------------------------------------------------------------
# Helper functions (exposed on pytest namespace for convenience)
# ---------------------------------------------------------------------------

def extract_checkbox_ids(html_output: str) -> list:
    import re
    return re.compile(r'id="(lightbox-\d+)"').findall(html_output)


def extract_caption_text(latex_output: str):
    import re
    m = re.search(r'\\caption\{([^}]+)\}', latex_output)
    return m.group(1) if m else None


pytest.extract_checkbox_ids = extract_checkbox_ids  # type: ignore[attr-defined]
pytest.extract_caption_text = extract_caption_text  # type: ignore[attr-defined]
