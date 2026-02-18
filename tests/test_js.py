"""
Tests for lightbox.js progressive enhancement.

Verifies that the JavaScript file is registered with Sphinx and contains
the expected accessibility features (focus trap, Escape key, idempotency).
"""

import os

import pytest

# ---------------------------------------------------------------------------
# File existence and content
# ---------------------------------------------------------------------------


class TestLightboxJsContent:
    """Verify lightbox.js exists and contains expected accessibility patterns."""

    @staticmethod
    def _read_js():
        js_path = os.path.join(
            os.path.dirname(__file__), "..", "lightbox", "static", "lightbox.js"
        )
        with open(js_path) as f:
            return f.read()

    @pytest.mark.unit
    def test_js_file_exists(self):
        js_path = os.path.join(
            os.path.dirname(__file__), "..", "lightbox", "static", "lightbox.js"
        )
        assert os.path.isfile(js_path), "lightbox.js not found in static directory"

    @pytest.mark.unit
    def test_js_is_syntactically_valid(self):
        """The file should be parseable (no obvious syntax errors).

        We cannot run a full JS parser in Python, but we verify the IIFE
        structure opens and closes correctly.
        """
        source = self._read_js()
        # Contains an IIFE (may be preceded by a comment block)
        assert "(function" in source, "Expected IIFE wrapper"
        # Ends with the IIFE invocation
        assert source.strip().endswith("})();"), "Expected IIFE closing"

    @pytest.mark.unit
    def test_js_contains_idempotency_guard(self):
        source = self._read_js()
        assert "__sphinxLightboxInit" in source

    @pytest.mark.unit
    def test_js_contains_focus_trap(self):
        source = self._read_js()
        assert "getFocusableElements" in source
        assert "e.shiftKey" in source

    @pytest.mark.unit
    def test_js_contains_escape_key_handler(self):
        source = self._read_js()
        assert "Escape" in source

    @pytest.mark.unit
    def test_js_contains_focus_management(self):
        """Focus should move to close button on open, return to trigger on close."""
        source = self._read_js()
        assert "_lastTrigger" in source
        assert ".focus()" in source

    @pytest.mark.unit
    def test_js_dispatches_change_event(self):
        """Programmatic checkbox toggling must dispatch change for focus management."""
        source = self._read_js()
        assert "dispatchEvent" in source
        assert "new Event('change')" in source or 'new Event("change")' in source


# ---------------------------------------------------------------------------
# Sphinx registration
# ---------------------------------------------------------------------------


class TestJsRegistration:
    """Verify the extension registers lightbox.js with Sphinx."""

    @pytest.mark.unit
    def test_setup_registers_js_file(self):
        """setup() should call app.add_js_file('lightbox.js')."""
        from unittest.mock import Mock

        from lightbox.lightbox import setup

        app = Mock()
        app.config.html_static_path = []

        setup(app)

        # Collect all add_js_file calls
        js_calls = [
            call.args[0] for call in app.add_js_file.call_args_list
        ]
        assert "lightbox.js" in js_calls, (
            "setup() must register lightbox.js via app.add_js_file"
        )

    @pytest.mark.unit
    def test_setup_registers_css_file(self):
        """setup() should call app.add_css_file('lightbox.css')."""
        from unittest.mock import Mock

        from lightbox.lightbox import setup

        app = Mock()
        app.config.html_static_path = []

        setup(app)

        css_calls = [
            call.args[0] for call in app.add_css_file.call_args_list
        ]
        assert "lightbox.css" in css_calls, (
            "setup() must register lightbox.css via app.add_css_file"
        )
