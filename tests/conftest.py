"""
Pytest configuration and shared fixtures.
This file contains reusable test fixtures and pytest configuration
that is shared across all test modules. [cite: 551]
"""

from unittest.mock import Mock

import pytest
from sphinx.util import texescape

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


@pytest.fixture
def mock_builder():
    """
    Mock Sphinx builder with minimal required attributes.
    Provides just enough to test LaTeX visitor functions without
    running a full Sphinx build. [cite: 553]
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
def sphinx_env():
    """
    Mock Sphinx environment with minimal required attributes.
    Provides docname, srcdir, and an images collection without
    needing a full Sphinx application instance. [cite: 555]
    """
    env = Mock()
    env.docname = "test"
    env.srcdir = "/tmp/test-sphinx"

    env.images = Mock()
    env.images.add_file = Mock()

    _serial_counters: dict = {}

    def new_serialno(category: str) -> int:
        """Generates unique IDs for nodes like checkboxes."""
        _serial_counters.setdefault(category, 0)
        _serial_counters[category] += 1
        return _serial_counters[category]

    env.new_serialno = new_serialno

    return env
