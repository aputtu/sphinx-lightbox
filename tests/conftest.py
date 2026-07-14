"""
Pytest configuration and shared fixtures.
This file contains reusable test fixtures and pytest configuration
that is shared across all test modules.
"""

from pathlib import Path
from unittest.mock import Mock

import pytest
from sphinx.util import texescape

pytest_plugins = "sphinx.testing.fixtures"

# ---------------------------------------------------------------------------
# One-time initialisation
# ---------------------------------------------------------------------------

# sphinx.util.texescape.escape() is a no-op until init() populates the
# replacement table. Sphinx normally calls this during app startup; we
# must do it explicitly so unit tests that call latex_escape() directly
# (without booting a full Sphinx application) get correct escaping.
texescape.init()


# ---------------------------------------------------------------------------
# Core fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def rootdir() -> object:
    root = Path(__file__).parent.parent.absolute()

    # Sphinx 7.0's testing fixtures call ``copytree`` on their legacy path
    # wrapper. Sphinx 7.1 and newer use ``pathlib.Path`` plus ``shutil``.
    try:
        from sphinx.testing.util import path as sphinx_test_path
    except ImportError:
        return root
    return sphinx_test_path(root)


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
    translator.body = []  # Collects LaTeX output fragments
    translator.builder = builder

    builder.translator = translator

    return builder


@pytest.fixture
def sphinx_env(monkeypatch: pytest.MonkeyPatch):
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
    monkeypatch.setattr("sphinx.util.images.get_image_size", lambda _path: (1, 1))

    _serial_counters: dict = {}

    def new_serialno(category: str) -> int:
        """Generates unique IDs for nodes like checkboxes."""
        _serial_counters.setdefault(category, 0)
        _serial_counters[category] += 1
        return _serial_counters[category]

    env.new_serialno = new_serialno

    return env
