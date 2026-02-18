"""
Tests for sphinx-lightbox.

Covers LaTeX and HTML output generation, directive parsing, security,
and CSP-compliant build-time aspect ratio calculations.
"""

from unittest.mock import Mock, patch

import pytest
from docutils import nodes
from lightbox.lightbox import (
    LightboxContainer,
    LightboxDirective,
    LightboxOverlay,
    LightboxTrigger,
    visit_lightbox_container_latex,
)
from sphinx.util.texescape import escape as latex_escape

# ---------------------------------------------------------------------------
# Helper: call the LaTeX visitor and absorb the expected SkipNode signal
# ---------------------------------------------------------------------------


def run_latex_visitor(translator, node):
    with pytest.raises(nodes.SkipNode):
        visit_lightbox_container_latex(translator, node)


# ---------------------------------------------------------------------------
# TestCaptionEscaping (6 tests)
# ---------------------------------------------------------------------------


class TestCaptionEscaping:
    """Test LaTeX special-character escaping in captions."""

    @pytest.mark.unit
    def test_percent_sign_escaped(self):
        assert r"\%" in latex_escape("40% width")

    @pytest.mark.unit
    def test_ampersand_escaped(self):
        assert r"\&" in latex_escape("A & B")

    @pytest.mark.unit
    def test_underscore_escaped(self):
        assert r"\_" in latex_escape("file_name")

    @pytest.mark.unit
    def test_dollar_sign_escaped(self):
        assert r"\$" in latex_escape("Cost: $100")

    @pytest.mark.unit
    def test_hash_escaped(self):
        assert r"\#" in latex_escape("Issue #42")

    @pytest.mark.unit
    def test_multiple_special_chars_escaped(self):
        escaped = latex_escape("40% width & special: $_#")
        assert all(c in escaped for c in [r"\%", r"\&", r"\$", r"\_", r"\#"])


# ---------------------------------------------------------------------------
# TestLatexOutput (6 tests)
# ---------------------------------------------------------------------------

class TestLatexOutput:
    """Test LaTeX code generation via the visitor function."""

    @pytest.mark.integration
    def test_uses_adjustbox_max_width(self, mock_builder):
        node = LightboxContainer()
        node["uri"] = "/images/test.png"
        node["caption"] = ""
        node["latex_width"] = "0.90"
        run_latex_visitor(mock_builder.translator, node)
        assert r"\adjustbox{max width=0.90\linewidth}" in "".join(mock_builder.translator.body)

    @pytest.mark.integration
    def test_includes_figure_environment(self, mock_builder):
        node = LightboxContainer()
        node["uri"] = "/images/test.png"
        node["caption"] = ""
        node["latex_width"] = "0.95"
        run_latex_visitor(mock_builder.translator, node)
        output = "".join(mock_builder.translator.body)
        assert r"\begin{figure}[htbp]" in output
        assert r"\centering" in output
        assert r"\end{figure}" in output

    @pytest.mark.integration
    def test_caption_properly_escaped(self, mock_builder):
        node = LightboxContainer()
        node["uri"] = "/images/test.png"
        node["caption"] = "40% width & more"
        node["latex_width"] = "0.95"
        run_latex_visitor(mock_builder.translator, node)
        assert r"\caption{40\% width \& more}" in "".join(mock_builder.translator.body)

    @pytest.mark.integration
    def test_no_caption_omits_caption_command(self, mock_builder):
        node = LightboxContainer()
        node["uri"] = "/images/test.png"
        node["caption"] = ""
        node["latex_width"] = "0.95"
        run_latex_visitor(mock_builder.translator, node)
        assert r"\caption" not in "".join(mock_builder.translator.body)

    @pytest.mark.integration
    def test_latex_width_percentage_conversion(self, mock_builder):
        node = LightboxContainer()
        node["uri"] = "/images/test.png"
        node["caption"] = ""
        node["latex_width"] = "0.75"
        run_latex_visitor(mock_builder.translator, node)
        assert r"max width=0.75\linewidth" in "".join(mock_builder.translator.body)

    @pytest.mark.integration
    def test_image_file_from_builder(self, mock_builder):
        uri = "/images/test.png"
        mock_builder.images = {uri: "test-abc123.png"}
        node = LightboxContainer()
        node["uri"] = uri
        node["caption"] = ""
        node["latex_width"] = "0.95"
        translator = mock_builder.translator
        translator.builder = mock_builder
        run_latex_visitor(translator, node)
        assert r"\includegraphics{test-abc123.png}" in "".join(translator.body)


# ---------------------------------------------------------------------------
# TestDirectiveIntegration (5 tests)
# ---------------------------------------------------------------------------


class TestDirectiveIntegration:
    """Test the full directive workflow."""

    def _make_directive(self, sphinx_env, arguments, options):
        state = Mock()
        state.document.settings.env = sphinx_env
        state_machine = Mock()
        state_machine.get_source_and_line.return_value = ("test.rst", 10)
        return LightboxDirective("lightbox", arguments, options, [], 1, 0, "", state, state_machine)

    @pytest.mark.integration
    def test_hidden_collector_has_leading_slash(self, sphinx_env):
        directive = self._make_directive(sphinx_env, ["images/test.png"], {})
        with patch("lightbox.lightbox.os.path.isfile", return_value=True):
            result_nodes = directive.run()
        collector = next(
            n for n in result_nodes[0].children if n.__class__.__name__ == "LightboxCollector"
        )
        assert collector.children[0]["uri"] == "/images/test.png"

    @pytest.mark.integration
    def test_percentage_option_converts_to_latex_width(self, sphinx_env):
        directive = self._make_directive(sphinx_env, ["/i.png"], {"percentage": [50, 90]})
        with patch("lightbox.lightbox.os.path.isfile", return_value=True):
            res = directive.run()
        assert res[0]["latex_width"] == "0.90"

    @pytest.mark.integration
    def test_default_percentage_is_95(self, sphinx_env):
        directive = self._make_directive(sphinx_env, ["/i.png"], {})
        with patch("lightbox.lightbox.os.path.isfile", return_value=True):
            res = directive.run()
        assert res[0]["latex_width"] == "0.95"

    @pytest.mark.unit
    def test_external_uri_returns_standard_image(self, sphinx_env):
        directive = self._make_directive(sphinx_env, ["https://ex.com/p.png"], {"alt": "Ext"})
        res = directive.run()
        assert isinstance(res[0], nodes.image)
        assert res[0]["uri"] == "https://ex.com/p.png"

    @pytest.mark.integration
    def test_checkbox_id_includes_docname_for_singlehtml_safety(self, sphinx_env):
        sphinx_env.docname = "nested/page"
        directive = self._make_directive(sphinx_env, ["/i.png"], {})
        with patch("lightbox.lightbox.os.path.isfile", return_value=True):
            res = directive.run()
        trigger = next(n for n in res[0].children if isinstance(n, LightboxTrigger))
        assert trigger["checkbox_id"] == "lightbox-nested-page-1"


# ---------------------------------------------------------------------------
# TestSizeStyleFormula (4 tests)
# ---------------------------------------------------------------------------


class TestSizeStyleFormula:
    """Test build-time CSS sizing logic."""

    def _get_overlay_style(self, sphinx_env, options):
        state = Mock()
        state.document.settings.env = sphinx_env
        state_machine = Mock()
        state_machine.get_source_and_line.return_value = ("test.rst", 1)
        directive = LightboxDirective(
            "lightbox", ["/i.png"], options, [], 1, 0, "", state, state_machine
        )
        with patch("lightbox.lightbox.os.path.isfile", return_value=True):
            res = directive.run()
        overlay = next(n for n in res[0].children if isinstance(n, LightboxOverlay))
        return overlay["size_style"]

    @pytest.mark.unit
    def test_size_style_contains_numeric_ratio(self, sphinx_env):
        style = self._get_overlay_style(sphinx_env, {})
        assert "1.0000" in style
        assert "var(--aspect-ratio)" not in style

    @pytest.mark.unit
    def test_default_size_style_uses_95(self, sphinx_env):
        style = self._get_overlay_style(sphinx_env, {})
        assert "min(95vw," in style

    @pytest.mark.unit
    def test_custom_percentage_used_in_size_style(self, sphinx_env):
        style = self._get_overlay_style(sphinx_env, {"percentage": [50, 80]})
        assert "min(80vw," in style

    @pytest.mark.unit
    def test_first_percentage_does_not_affect_size_style(self, sphinx_env):
        style = self._get_overlay_style(sphinx_env, {"percentage": [30, 70]})
        assert "min(70vw," in style
        assert "30vw" not in style


# ---------------------------------------------------------------------------
# TestMissingImage (4 tests)
# ---------------------------------------------------------------------------


class TestMissingImage:
    """Test behaviour for invalid image paths."""

    @pytest.mark.unit
    def test_missing_image_returns_empty_list(self, sphinx_env):
        state = Mock()
        state.document.settings.env = sphinx_env
        directive = LightboxDirective("lightbox", ["/no.png"], {}, [], 1, 0, "", state, Mock())
        with patch("lightbox.lightbox.os.path.isfile", return_value=False):
            assert directive.run() == []

    @pytest.mark.unit
    def test_missing_image_emits_warning(self, sphinx_env):
        state = Mock()
        state.document.settings.env = sphinx_env
        directive = LightboxDirective("lightbox", ["/no.png"], {}, [], 1, 0, "", state, Mock())
        with (
            patch("lightbox.lightbox.os.path.isfile", return_value=False),
            patch("lightbox.lightbox.logger") as mock_logger,
        ):
            directive.run()
        assert mock_logger.warning.call_args.kwargs.get("subtype") == "image_not_found"

    @pytest.mark.unit
    def test_path_traversal_emits_security_warning(self, sphinx_env):
        state = Mock()
        state.document.settings.env = sphinx_env
        directive = LightboxDirective(
            "lightbox", ["../../etc/passwd"], {}, [], 1, 0, "", state, Mock()
        )
        with (
            patch("lightbox.lightbox.os.path.isfile", return_value=True),
            patch("lightbox.lightbox.logger") as mock_logger,
        ):
            directive.run()
        assert mock_logger.warning.call_args.kwargs.get("subtype") == "path_traversal"

    @pytest.mark.unit
    def test_path_traversal_sibling_directory_bypass(self, sphinx_env):
        """Ensure sibling directories sharing the srcdir prefix are blocked."""
        state = Mock()
        # Set a specific srcdir prefix to test against
        sphinx_env.srcdir = "/var/www/docs"
        state.document.settings.env = sphinx_env

        # Attempt to access a sibling directory that starts with "/var/www/docs"
        directive = LightboxDirective(
            "lightbox", ["../docs-secret/image.png"], {}, [], 1, 0, "", state, Mock()
        )

        with (
            patch("lightbox.lightbox.os.path.isfile", return_value=True),
            patch("lightbox.lightbox.logger") as mock_logger,
        ):
            directive.run()

        # If the bypass works, this assert will fail because the logger was never called
        assert mock_logger.warning.called, "Path traversal bypass succeeded!"
        assert mock_logger.warning.call_args.kwargs.get("subtype") == "path_traversal"


# ---------------------------------------------------------------------------
# TestHtmlOutput (13 tests)
# ---------------------------------------------------------------------------


class TestHtmlOutput:
    """Test HTML visitor functions directly."""

    @staticmethod
    def _make_translator():
        t = Mock()
        t.body = []
        t.builder = Mock(images={})
        return t

    # --- Container ---

    @pytest.mark.unit
    def test_container_opens_and_closes_div(self):
        from lightbox.lightbox import (
            depart_lightbox_container_html,
            visit_lightbox_container_html,
        )

        t = self._make_translator()
        visit_lightbox_container_html(t, LightboxContainer())
        depart_lightbox_container_html(t, LightboxContainer())
        output = "".join(t.body)
        assert '<div class="lightbox-container">' in output
        assert "</div>" in output

    # --- Trigger ---

    @pytest.mark.unit
    def test_trigger_renders_label_and_img(self):
        from lightbox.lightbox import visit_lightbox_trigger_html

        t = self._make_translator()
        node = LightboxTrigger()
        node["uri"] = "i.png"
        node["checkbox_id"] = "l1"
        node.get = lambda k, d: {"alt": "A", "thumbnail_width": "1%", "custom_class": ""}.get(
            k, d
        )
        visit_lightbox_trigger_html(t, node)
        output = "".join(t.body)
        assert "lightbox-trigger-label" in output
        assert "<img" in output

    @pytest.mark.unit
    def test_trigger_thumbnail_width_applied(self):
        from lightbox.lightbox import visit_lightbox_trigger_html

        t = self._make_translator()
        node = LightboxTrigger()
        node["uri"] = "i.png"
        node["checkbox_id"] = "l1"
        node.get = lambda k, d: {"alt": "A", "thumbnail_width": "60%", "custom_class": ""}.get(
            k, d
        )
        visit_lightbox_trigger_html(t, node)
        assert "width: 60%;" in "".join(t.body)

    @pytest.mark.unit
    def test_trigger_aria_label_contains_alt_text(self):
        from lightbox.lightbox import visit_lightbox_trigger_html

        t = self._make_translator()
        node = LightboxTrigger()
        node["uri"] = "i.png"
        node["checkbox_id"] = "l1"
        node.get = lambda k, d: {
            "alt": "Server diagram",
            "thumbnail_width": "100%",
            "custom_class": "",
        }.get(k, d)
        visit_lightbox_trigger_html(t, node)
        assert 'aria-label="Enlarge image: Server diagram"' in "".join(t.body)

    @pytest.mark.unit
    def test_trigger_custom_class_applied(self):
        from lightbox.lightbox import visit_lightbox_trigger_html

        t = self._make_translator()
        node = LightboxTrigger()
        node["uri"] = "i.png"
        node["checkbox_id"] = "l1"
        node.get = lambda k, d: {
            "alt": "A",
            "thumbnail_width": "100%",
            "custom_class": "with-border",
        }.get(k, d)
        visit_lightbox_trigger_html(t, node)
        assert "lightbox-trigger with-border" in "".join(t.body)

    # --- Overlay ---

    @pytest.mark.unit
    def test_overlay_checkbox_input_rendered(self):
        from lightbox.lightbox import visit_lightbox_overlay_html

        t = self._make_translator()
        node = LightboxOverlay()
        node["uri"] = "t.png"
        node["checkbox_id"] = "lb-7"
        node.get = lambda k, d: {
            "alt": "A",
            "caption": "",
            "custom_class": "",
            "size_style": "",
        }.get(k, d)
        visit_lightbox_overlay_html(t, node)
        output = "".join(t.body)
        assert '<input type="checkbox" id="lb-7"' in output
        assert 'class="lightbox-toggle"' in output

    @pytest.mark.unit
    def test_overlay_role_dialog_present(self):
        from lightbox.lightbox import visit_lightbox_overlay_html

        t = self._make_translator()
        node = LightboxOverlay()
        node["uri"] = "t.png"
        node["checkbox_id"] = "l1"
        node.get = lambda k, d: {
            "alt": "A",
            "caption": "",
            "custom_class": "",
            "size_style": "",
        }.get(k, d)
        visit_lightbox_overlay_html(t, node)
        output = "".join(t.body)
        assert 'role="dialog"' in output
        assert 'aria-modal="true"' in output

    @pytest.mark.unit
    def test_overlay_close_button_rendered(self):
        from lightbox.lightbox import visit_lightbox_overlay_html

        t = self._make_translator()
        node = LightboxOverlay()
        node["uri"] = "t.png"
        node["checkbox_id"] = "l1"
        node.get = lambda k, d: {
            "alt": "A",
            "caption": "",
            "custom_class": "",
            "size_style": "",
        }.get(k, d)
        visit_lightbox_overlay_html(t, node)
        output = "".join(t.body)
        assert 'class="lightbox-close"' in output
        assert 'aria-label="Close lightbox"' in output
        assert "&times;" in output

    @pytest.mark.unit
    def test_overlay_renders_with_secure_style(self):
        from lightbox.lightbox import visit_lightbox_overlay_html

        t = self._make_translator()
        node = LightboxOverlay()
        node["uri"] = "t.png"
        node["checkbox_id"] = "l1"
        node.get = lambda k, d: {
            "alt": "A",
            "caption": "Cap",
            "custom_class": "",
            "size_style": "width: min(95vw, calc(95vh * 1.5));",
        }.get(k, d)
        visit_lightbox_overlay_html(t, node)
        output = "".join(t.body)
        assert 'style="width: min(95vw, calc(95vh * 1.5));"' in output
        assert "onload=" not in output

    @pytest.mark.unit
    def test_overlay_caption_rendered_when_present(self):
        from lightbox.lightbox import visit_lightbox_overlay_html

        t = self._make_translator()
        node = LightboxOverlay()
        node["uri"] = "t.png"
        node["checkbox_id"] = "l1"
        node.get = lambda k, d: {
            "alt": "A",
            "caption": "Figure 1",
            "custom_class": "",
            "size_style": "",
        }.get(k, d)
        visit_lightbox_overlay_html(t, node)
        assert '<p class="lightbox-caption">Figure 1</p>' in "".join(t.body)

    @pytest.mark.unit
    def test_overlay_caption_omitted_when_empty(self):
        from lightbox.lightbox import visit_lightbox_overlay_html

        t = self._make_translator()
        node = LightboxOverlay()
        node["uri"] = "t.png"
        node["checkbox_id"] = "l1"
        node.get = lambda k, d: {
            "alt": "A",
            "caption": "",
            "custom_class": "",
            "size_style": "",
        }.get(k, d)
        visit_lightbox_overlay_html(t, node)
        assert "lightbox-caption" not in "".join(t.body)

    @pytest.mark.unit
    def test_overlay_backdrop_close_rendered(self):
        from lightbox.lightbox import visit_lightbox_overlay_html

        t = self._make_translator()
        node = LightboxOverlay()
        node["uri"] = "t.png"
        node["checkbox_id"] = "l1"
        node.get = lambda k, d: {
            "alt": "A",
            "caption": "",
            "custom_class": "",
            "size_style": "",
        }.get(k, d)
        visit_lightbox_overlay_html(t, node)
        assert 'class="lightbox-backdrop-close"' in "".join(t.body)

    @pytest.mark.unit
    def test_overlay_img_custom_class_applied(self):
        from lightbox.lightbox import visit_lightbox_overlay_html

        t = self._make_translator()
        node = LightboxOverlay()
        node["uri"] = "t.png"
        node["checkbox_id"] = "l1"
        node.get = lambda k, d: {
            "alt": "A",
            "caption": "",
            "custom_class": "with-border",
            "size_style": "",
        }.get(k, d)
        visit_lightbox_overlay_html(t, node)
        assert 'class="with-border"' in "".join(t.body)


# ---------------------------------------------------------------------------
# TestHtmlEscaping (8 tests)
# ---------------------------------------------------------------------------


class TestHtmlEscaping:
    """Test that all user-supplied fields are properly HTML escaped."""

    @staticmethod
    def _make_translator():
        t = Mock()
        t.body = []
        t.builder = Mock(images={})
        return t

    @pytest.mark.unit
    def test_trigger_alt_script_injection_escaped(self):
        from lightbox.lightbox import visit_lightbox_trigger_html

        t = self._make_translator()
        node = LightboxTrigger()
        node["uri"] = "i.png"
        node["checkbox_id"] = "l1"
        node.get = lambda k, d: {
            "alt": '<script>alert(1)</script>',
            "thumbnail_width": "1%",
            "custom_class": "",
        }.get(k, d)
        visit_lightbox_trigger_html(t, node)
        output = "".join(t.body)
        assert "<script>" not in output
        assert "&lt;script&gt;" in output

    @pytest.mark.unit
    def test_trigger_alt_double_quote_escaped(self):
        from lightbox.lightbox import visit_lightbox_trigger_html

        t = self._make_translator()
        node = LightboxTrigger()
        node["uri"] = "i.png"
        node["checkbox_id"] = "l1"
        node.get = lambda k, d: {
            "alt": 'Say "hello"',
            "thumbnail_width": "1%",
            "custom_class": "",
        }.get(k, d)
        visit_lightbox_trigger_html(t, node)
        assert "&quot;hello&quot;" in "".join(t.body)

    @pytest.mark.unit
    def test_caption_escaping(self):
        from lightbox.lightbox import visit_lightbox_overlay_html

        t = self._make_translator()
        node = LightboxOverlay()
        node["uri"] = "i.png"
        node["checkbox_id"] = "l1"
        node.get = lambda k, d: {
            "alt": "A",
            "caption": "<b>Bold</b>",
            "custom_class": "",
            "size_style": "",
        }.get(k, d)
        visit_lightbox_overlay_html(t, node)
        output = "".join(t.body)
        assert "<b>" not in output
        assert "&lt;b&gt;Bold&lt;/b&gt;" in output

    @pytest.mark.unit
    def test_overlay_alt_text_escaped(self):
        from lightbox.lightbox import visit_lightbox_overlay_html

        t = self._make_translator()
        node = LightboxOverlay()
        node["uri"] = "i.png"
        node["checkbox_id"] = "l1"
        node.get = lambda k, d: {
            "alt": '"onmouseover="alert(1)',
            "caption": "",
            "custom_class": "",
            "size_style": "",
        }.get(k, d)
        visit_lightbox_overlay_html(t, node)
        output = "".join(t.body)
        assert "onmouseover" not in output.split("&quot;onmouseover")[0] if "&quot;onmouseover" in output else True
        assert "&quot;" in output

    @pytest.mark.unit
    def test_uri_special_chars_escaped(self):
        from lightbox.lightbox import visit_lightbox_trigger_html

        t = self._make_translator()
        node = LightboxTrigger()
        node["uri"] = 'img "name".png'
        node["checkbox_id"] = "l1"
        node.get = lambda k, d: {"alt": "A", "thumbnail_width": "1%", "custom_class": ""}.get(
            k, d
        )
        visit_lightbox_trigger_html(t, node)
        output = "".join(t.body)
        # Double quotes inside the src attribute must be escaped
        assert '&quot;name&quot;' in output

    @pytest.mark.unit
    def test_custom_class_escaped(self):
        from lightbox.lightbox import visit_lightbox_trigger_html

        t = self._make_translator()
        node = LightboxTrigger()
        node["uri"] = "i.png"
        node["checkbox_id"] = "l1"
        node.get = lambda k, d: {
            "alt": "A",
            "thumbnail_width": "1%",
            "custom_class": '"><script>',
        }.get(k, d)
        visit_lightbox_trigger_html(t, node)
        output = "".join(t.body)
        assert "<script>" not in output
        assert "&lt;script&gt;" in output

    @pytest.mark.unit
    def test_caption_with_ampersand_escaped(self):
        from lightbox.lightbox import visit_lightbox_overlay_html

        t = self._make_translator()
        node = LightboxOverlay()
        node["uri"] = "i.png"
        node["checkbox_id"] = "l1"
        node.get = lambda k, d: {
            "alt": "A",
            "caption": "Tom & Jerry",
            "custom_class": "",
            "size_style": "",
        }.get(k, d)
        visit_lightbox_overlay_html(t, node)
        output = "".join(t.body)
        assert "Tom &amp; Jerry" in output

    @pytest.mark.unit
    def test_overlay_caption_with_quotes_escaped(self):
        from lightbox.lightbox import visit_lightbox_overlay_html

        t = self._make_translator()
        node = LightboxOverlay()
        node["uri"] = "i.png"
        node["checkbox_id"] = "l1"
        node.get = lambda k, d: {
            "alt": "A",
            "caption": 'She said "hi"',
            "custom_class": "",
            "size_style": "",
        }.get(k, d)
        visit_lightbox_overlay_html(t, node)
        output = "".join(t.body)
        # Caption uses quote=True for defence-in-depth
        assert "&quot;hi&quot;" in output


# ---------------------------------------------------------------------------
# TestUriResolution (3 tests)
# ---------------------------------------------------------------------------


class TestUriResolution:
    """Test _resolve_output_uri helper."""

    @pytest.mark.unit
    def test_resolve_output_uri_uses_imgpath(self):
        from lightbox.lightbox import _resolve_output_uri

        builder = Mock(images={"test.png": "t1.png"}, imgpath="../../_images")
        assert _resolve_output_uri(builder, "test.png") == "../../_images/t1.png"

    @pytest.mark.unit
    def test_resolve_output_uri_unregistered_fallback(self):
        from lightbox.lightbox import _resolve_output_uri

        builder = Mock(images={})
        assert _resolve_output_uri(builder, "test.png") == "test.png"

    @pytest.mark.unit
    def test_resolve_output_uri_no_imgpath_defaults(self):
        from lightbox.lightbox import _resolve_output_uri

        # Builder with images but no imgpath attribute → defaults to "_images"
        builder = Mock(spec=["images"])
        builder.images = {"test.png": "t1.png"}
        assert _resolve_output_uri(builder, "test.png") == "_images/t1.png"


# ---------------------------------------------------------------------------
# TestStaticPathRegistration (1 test)
# ---------------------------------------------------------------------------


class TestStaticPathRegistration:
    """Test that the extension registers its static directory with Sphinx."""

    @pytest.mark.unit
    def test_builder_inited_appends_static_path(self):
        from lightbox.lightbox import _builder_inited

        app = Mock()
        app.config.html_static_path = []
        
        with patch("os.path.dirname", return_value="/tmp/src"):
            _builder_inited(app)
            
        assert len(app.config.html_static_path) == 1
        assert app.config.html_static_path[0] == "/tmp/src/static"


# ---------------------------------------------------------------------------
# TestImageDimensionCalculation (2 tests)
# ---------------------------------------------------------------------------


class TestImageDimensionCalculation:
    """Test build-time aspect ratio calculation."""

    @pytest.mark.unit
    def test_run_calculates_correct_aspect_ratio(self, sphinx_env):
        state = Mock()
        state.document.settings.env = sphinx_env
        state_machine = Mock()
        state_machine.get_source_and_line.return_value = ("test.rst", 10)
        directive = LightboxDirective(
            "lightbox", ["/land.png"], {}, [], 1, 0, "", state, state_machine
        )
        with (
            patch("lightbox.lightbox.os.path.isfile", return_value=True),
            patch("sphinx.util.images.get_image_size", return_value=(800, 400)),
        ):
            res = directive.run()
        overlay = next(n for n in res[0].children if isinstance(n, LightboxOverlay))
        assert "2.0000" in overlay["size_style"]

    @pytest.mark.unit
    def test_run_handles_dimensions_error_gracefully(self, sphinx_env):
        state = Mock()
        state.document.settings.env = sphinx_env
        state_machine = Mock()
        state_machine.get_source_and_line.return_value = ("test.rst", 10)
        directive = LightboxDirective(
            "lightbox", ["/bad.png"], {}, [], 1, 0, "", state, state_machine
        )
        with (
            patch("lightbox.lightbox.os.path.isfile", return_value=True),
            patch("sphinx.util.images.get_image_size", side_effect=Exception("Read error")),
            patch("lightbox.lightbox.logger") as mock_logger,
        ):
            res = directive.run()
            
        overlay = next(n for n in res[0].children if isinstance(n, LightboxOverlay))
        # Falls back to 1:1 aspect ratio when image reading fails
        assert "1.0000" in overlay["size_style"]
        assert mock_logger.warning.called
        assert mock_logger.warning.call_args.kwargs.get("subtype") == "image_dimensions"
