"""
Tests for sphinx-lightbox.

Covers LaTeX output generation, HTML output generation, directive option
parsing, edge cases, HTML escaping safety, and regression bugs.
"""

from html.parser import HTMLParser
from unittest.mock import Mock, patch

import pytest
from docutils import nodes
from lightbox.lightbox import (
    LightboxContainer,
    LightboxDirective,
    visit_lightbox_container_latex,
)
from sphinx.util.texescape import escape as latex_escape

# ---------------------------------------------------------------------------
# Helper: call the LaTeX visitor and absorb the expected SkipNode signal
# ---------------------------------------------------------------------------

def run_latex_visitor(translator, node):
    """
    Call visit_lightbox_container_latex and absorb nodes.SkipNode.

    visit_lightbox_container_latex raises nodes.SkipNode after writing all
    output — that is the correct Sphinx protocol for a visitor that handles
    its children itself.  Tests must not let the exception propagate, or the
    assertions that follow will never execute.
    """
    with pytest.raises(nodes.SkipNode):
        visit_lightbox_container_latex(translator, node)


# ---------------------------------------------------------------------------
# TestCaptionEscaping
# ---------------------------------------------------------------------------

class TestCaptionEscaping:
    """Test LaTeX special-character escaping in captions.

    Note: sphinx.util.texescape.init() is called once in conftest.py so
    that latex_escape() works without a running Sphinx application.
    """

    @pytest.mark.unit
    def test_percent_sign_escaped(self):
        """Percent signs must be escaped to prevent LaTeX comments."""
        escaped = latex_escape("40% width")
        assert r"\%" in escaped

    @pytest.mark.unit
    def test_ampersand_escaped(self):
        """Ampersands must be escaped to prevent table alignment issues."""
        escaped = latex_escape("A & B")
        assert r"\&" in escaped

    @pytest.mark.unit
    def test_underscore_escaped(self):
        """Underscores must be escaped to prevent subscript mode."""
        escaped = latex_escape("file_name")
        assert r"\_" in escaped

    @pytest.mark.unit
    def test_dollar_sign_escaped(self):
        """Dollar signs must be escaped to prevent math mode."""
        escaped = latex_escape("Cost: $100")
        assert r"\$" in escaped

    @pytest.mark.unit
    def test_hash_escaped(self):
        """Hash symbols must be escaped to prevent parameter markers."""
        escaped = latex_escape("Issue #42")
        assert r"\#" in escaped

    @pytest.mark.unit
    def test_multiple_special_chars_escaped(self):
        """Multiple special characters should all be escaped."""
        escaped = latex_escape("40% width & special: $_#")
        assert r"\%" in escaped
        assert r"\&" in escaped
        assert r"\$" in escaped
        assert r"\_" in escaped
        assert r"\#" in escaped


# ---------------------------------------------------------------------------
# TestLatexOutput
# ---------------------------------------------------------------------------

class TestLatexOutput:
    """Test LaTeX code generation via the visitor function.

    visit_lightbox_container_latex raises nodes.SkipNode after writing its
    output (it handles child nodes itself to prevent duplication).  Every
    test calls run_latex_visitor() which catches that exception, then
    inspects translator.body.
    """

    @pytest.mark.integration
    def test_uses_adjustbox_max_width(self, mock_builder):
        """LaTeX output should use adjustbox with max width."""
        node = LightboxContainer()
        node["uri"] = "/images/test.png"
        node["caption"] = ""
        node["latex_width"] = "0.90"

        translator = mock_builder.translator
        run_latex_visitor(translator, node)

        output = "".join(translator.body)
        assert r"\adjustbox{max width=0.90\linewidth}" in output

    @pytest.mark.integration
    def test_includes_figure_environment(self, mock_builder):
        """LaTeX output should be wrapped in a figure environment."""
        node = LightboxContainer()
        node["uri"] = "/images/test.png"
        node["caption"] = ""
        node["latex_width"] = "0.95"

        translator = mock_builder.translator
        run_latex_visitor(translator, node)

        output = "".join(translator.body)
        assert r"\begin{figure}[htbp]" in output
        assert r"\centering" in output
        assert r"\end{figure}" in output

    @pytest.mark.integration
    def test_caption_properly_escaped(self, mock_builder):
        """Captions with special characters should be escaped."""
        node = LightboxContainer()
        node["uri"] = "/images/test.png"
        node["caption"] = "40% width & more"
        node["latex_width"] = "0.95"

        translator = mock_builder.translator
        run_latex_visitor(translator, node)

        output = "".join(translator.body)
        assert r"\caption{40\% width \& more}" in output

    @pytest.mark.integration
    def test_no_caption_omits_caption_command(self, mock_builder):
        r"""If no caption is provided, \caption{} must not appear."""
        node = LightboxContainer()
        node["uri"] = "/images/test.png"
        node["caption"] = ""
        node["latex_width"] = "0.95"

        translator = mock_builder.translator
        run_latex_visitor(translator, node)

        output = "".join(translator.body)
        assert r"\caption" not in output

    @pytest.mark.integration
    def test_latex_width_percentage_conversion(self, mock_builder):
        """LaTeX width should be expressed as a decimal fraction."""
        node = LightboxContainer()
        node["uri"] = "/images/test.png"
        node["caption"] = ""
        node["latex_width"] = "0.75"

        translator = mock_builder.translator
        run_latex_visitor(translator, node)

        output = "".join(translator.body)
        assert r"max width=0.75\linewidth" in output

    @pytest.mark.integration
    def test_image_file_from_builder(self, mock_builder):
        """Should use the builder's image mapping when available."""
        uri = "/images/test.png"
        mock_builder.images = {uri: "test-abc123.png"}

        node = LightboxContainer()
        node["uri"] = uri
        node["caption"] = ""
        node["latex_width"] = "0.95"

        translator = mock_builder.translator
        translator.builder = mock_builder
        run_latex_visitor(translator, node)

        output = "".join(translator.body)
        assert r"\includegraphics{test-abc123.png}" in output


# ---------------------------------------------------------------------------
# TestDirectiveIntegration
# ---------------------------------------------------------------------------

class TestDirectiveIntegration:
    """Test the full directive → node → LaTeX width workflow.

    SphinxDirective.env is a read-only property backed by
    ``self.state.document.settings.env``.  We inject the mock environment
    through that path, and patch os.path.isfile so that _resolve_image_path
    does not reject our dummy image path.
    """

    def _make_directive(self, sphinx_env, arguments, options):
        """Construct a LightboxDirective with the mock env wired in."""
        state = Mock()
        # Wire the env through the real property path
        state.document.settings.env = sphinx_env

        directive = LightboxDirective(
            name="lightbox",
            arguments=arguments,
            options=options,
            content=[],
            lineno=1,
            content_offset=0,
            block_text="",
            state=state,
            state_machine=Mock(
                get_source_and_line=Mock(return_value=("test.rst", 1))
            ),
        )
        return directive

    @pytest.mark.integration
    def test_percentage_option_converts_to_latex_width(self, sphinx_env):
        """Second percentage value (90) should produce latex_width='0.90'."""
        directive = self._make_directive(
            sphinx_env,
            arguments=["/images/test.png"],
            options={"percentage": [50, 90]},
        )

        with patch("lightbox.lightbox.os.path.isfile", return_value=True):
            result_nodes = directive.run()

        assert result_nodes, "directive.run() returned empty list"
        container = result_nodes[0]
        assert container["latex_width"] == "0.90"

    @pytest.mark.integration
    def test_default_percentage_is_95(self, sphinx_env):
        """With no percentage option, latex_width should default to '0.95'."""
        directive = self._make_directive(
            sphinx_env,
            arguments=["/images/test.png"],
            options={},
        )

        with patch("lightbox.lightbox.os.path.isfile", return_value=True):
            result_nodes = directive.run()

        assert result_nodes, "directive.run() returned empty list"
        container = result_nodes[0]
        assert container["latex_width"] == "0.95"


# ---------------------------------------------------------------------------
# TestSizeStyleFormula
# ---------------------------------------------------------------------------

class TestSizeStyleFormula:
    """Test that the overlay size_style CSS formula is computed correctly.

    The formula uses min()/calc() with viewport units to scale the overlay
    image while preserving aspect ratio.  Both width and height expressions
    must use the same percentage value derived from the second :percentage:
    argument (defaulting to 95).
    """

    def _make_directive(self, sphinx_env, arguments, options):
        state = Mock()
        state.document.settings.env = sphinx_env
        return LightboxDirective(
            name="lightbox",
            arguments=arguments,
            options=options,
            content=[],
            lineno=1,
            content_offset=0,
            block_text="",
            state=state,
            state_machine=Mock(
                get_source_and_line=Mock(return_value=("test.rst", 1))
            ),
        )

    def _get_overlay(self, sphinx_env, options):
        """Run the directive and return the LightboxOverlay child node."""
        from lightbox.lightbox import LightboxOverlay
        directive = self._make_directive(
            sphinx_env,
            arguments=["/images/test.png"],
            options=options,
        )
        with patch("lightbox.lightbox.os.path.isfile", return_value=True):
            result_nodes = directive.run()
        container = result_nodes[0]
        return next(n for n in container.children if isinstance(n, LightboxOverlay))

    @pytest.mark.unit
    def test_default_size_style_uses_95(self, sphinx_env):
        """With no :percentage: option, size_style should use 95 for both axes."""
        overlay = self._get_overlay(sphinx_env, options={})
        style = overlay["size_style"]
        assert "min(95vw," in style
        assert "min(95vh," in style

    @pytest.mark.unit
    def test_custom_percentage_used_in_size_style(self, sphinx_env):
        """The second :percentage: value should control the overlay size."""
        overlay = self._get_overlay(sphinx_env, options={"percentage": [50, 80]})
        style = overlay["size_style"]
        assert "min(80vw," in style
        assert "min(80vh," in style

    @pytest.mark.unit
    def test_size_style_contains_aspect_ratio_var(self, sphinx_env):
        """Formula must reference --aspect-ratio for proportional scaling."""
        overlay = self._get_overlay(sphinx_env, options={})
        style = overlay["size_style"]
        assert "var(--aspect-ratio)" in style

    @pytest.mark.unit
    def test_first_percentage_does_not_affect_size_style(self, sphinx_env):
        """The first :percentage: value controls the thumbnail, not the overlay."""
        overlay = self._get_overlay(sphinx_env, options={"percentage": [30, 70]})
        style = overlay["size_style"]
        assert "min(70vw," in style
        assert "30vw" not in style
        

# ---------------------------------------------------------------------------
# TestMissingImage
# ---------------------------------------------------------------------------

class TestMissingImage:
    """Test behaviour when the referenced image file does not exist."""

    def _make_directive(self, sphinx_env, arguments, options):
        state = Mock()
        state.document.settings.env = sphinx_env
        return LightboxDirective(
            name="lightbox",
            arguments=arguments,
            options=options,
            content=[],
            lineno=1,
            content_offset=0,
            block_text="",
            state=state,
            state_machine=Mock(
                get_source_and_line=Mock(return_value=("test.rst", 1))
            ),
        )

    @pytest.mark.unit
    def test_missing_image_returns_empty_list(self, sphinx_env):
        """directive.run() must return [] when the image file is missing."""
        directive = self._make_directive(
            sphinx_env,
            arguments=["/images/does_not_exist.png"],
            options={},
        )

        with patch("lightbox.lightbox.os.path.isfile", return_value=False):
            result = directive.run()

        assert result == []

    @pytest.mark.unit
    def test_missing_image_emits_warning(self, sphinx_env):
        """A Sphinx warning must be emitted when the image file is missing."""
        directive = self._make_directive(
            sphinx_env,
            arguments=["/images/does_not_exist.png"],
            options={},
        )

        with (
            patch("lightbox.lightbox.os.path.isfile", return_value=False),
            patch("lightbox.lightbox.logger") as mock_logger,
        ):
            directive.run()

        mock_logger.warning.assert_called_once()
        call_kwargs = mock_logger.warning.call_args
        # Verify the warning carries the correct Sphinx subtype so it can be
        # suppressed or filtered by users via suppress_warnings in conf.py.
        assert call_kwargs.kwargs.get("subtype") == "image_not_found"


# ---------------------------------------------------------------------------
# TestEdgeCases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    """Edge cases and boundary conditions."""

    @pytest.mark.unit
    def test_empty_caption_escaping(self):
        """Empty caption should not cause errors."""
        assert latex_escape("") == ""

    @pytest.mark.unit
    def test_caption_with_only_safe_chars(self):
        """Caption with no special chars should be returned unchanged."""
        assert latex_escape("Simple caption") == "Simple caption"

    @pytest.mark.unit
    def test_caption_with_braces(self):
        """Curly braces should be escaped."""
        escaped = latex_escape("Value: {x}")
        assert r"\{" in escaped
        assert r"\}" in escaped

    @pytest.mark.integration
    def test_zero_percent_latex_width(self, mock_builder):
        """Edge case: 0% width should still produce valid LaTeX."""
        node = LightboxContainer()
        node["uri"] = "/images/test.png"
        node["caption"] = ""
        node["latex_width"] = "0.00"

        translator = mock_builder.translator
        run_latex_visitor(translator, node)

        output = "".join(translator.body)
        assert r"max width=0.00\linewidth" in output

    @pytest.mark.integration
    def test_hundred_percent_latex_width(self, mock_builder):
        """Full width: 100% → 1.00."""
        node = LightboxContainer()
        node["uri"] = "/images/test.png"
        node["caption"] = ""
        node["latex_width"] = "1.00"

        translator = mock_builder.translator
        run_latex_visitor(translator, node)

        output = "".join(translator.body)
        assert r"max width=1.00\linewidth" in output


# ---------------------------------------------------------------------------
# TestHtmlOutput
# ---------------------------------------------------------------------------

class TestHtmlOutput:
    """Test HTML visitor functions directly.

    We call the visitor functions in the order Sphinx would:
    visit_container -> visit_trigger -> depart_trigger ->
    visit_overlay -> depart_overlay -> depart_container.
    """

    @staticmethod
    def _make_translator():
        t = Mock()
        t.body = []
        # _resolve_output_uri does `uri in builder.images`, so builder.images
        # must be a real dict (a bare Mock is not iterable).
        t.builder = Mock()
        t.builder.images = {}
        return t

    @staticmethod
    def _make_container(uri="/images/test.png", caption="", latex_width="0.95"):
        node = LightboxContainer()
        node["uri"] = uri
        node["caption"] = caption
        node["latex_width"] = latex_width
        return node

    @staticmethod
    def _make_trigger(uri="/images/test.png", alt="Alt text",
                      thumbnail_width="100%", custom_class="",
                      checkbox_id="lightbox-1"):
        from lightbox.lightbox import LightboxTrigger
        node = LightboxTrigger()
        node["uri"] = uri
        node["alt"] = alt
        node["thumbnail_width"] = thumbnail_width
        node["custom_class"] = custom_class
        node["checkbox_id"] = checkbox_id
        return node

    @staticmethod
    def _make_overlay(uri="/images/test.png", alt="Alt text", caption="",
                      size_style="", custom_class="", checkbox_id="lightbox-1"):
        from lightbox.lightbox import LightboxOverlay
        node = LightboxOverlay()
        node["uri"] = uri
        node["alt"] = alt
        node["caption"] = caption
        node["size_style"] = size_style
        node["custom_class"] = custom_class
        node["checkbox_id"] = checkbox_id
        return node

    # -- container --

    @pytest.mark.unit
    def test_container_opens_div(self):
        """visit_lightbox_container_html should open a lightbox-container div."""
        from lightbox.lightbox import visit_lightbox_container_html
        t = self._make_translator()
        visit_lightbox_container_html(t, self._make_container())
        assert '<div class="lightbox-container">' in "".join(t.body)

    @pytest.mark.unit
    def test_container_closes_div(self):
        """depart_lightbox_container_html should close the div."""
        from lightbox.lightbox import depart_lightbox_container_html
        t = self._make_translator()
        depart_lightbox_container_html(t, self._make_container())
        assert "</div>" in "".join(t.body)

    # -- trigger --

    @pytest.mark.unit
    def test_trigger_renders_label_and_img(self):
        """Trigger should render a <label> wrapping an <img>."""
        from lightbox.lightbox import visit_lightbox_trigger_html
        t = self._make_translator()
        visit_lightbox_trigger_html(t, self._make_trigger())
        output = "".join(t.body)
        assert "lightbox-trigger-label" in output
        assert "<img " in output

    @pytest.mark.unit
    def test_trigger_contains_alt_text(self):
        """Trigger img should carry the alt attribute."""
        from lightbox.lightbox import visit_lightbox_trigger_html
        t = self._make_translator()
        visit_lightbox_trigger_html(t, self._make_trigger(alt="My diagram"))
        assert 'alt="My diagram"' in "".join(t.body)

    @pytest.mark.unit
    def test_trigger_links_to_checkbox_id(self):
        """Trigger label for= should match the checkbox id."""
        from lightbox.lightbox import visit_lightbox_trigger_html
        t = self._make_translator()
        visit_lightbox_trigger_html(t, self._make_trigger(checkbox_id="lightbox-42"))
        assert 'for="lightbox-42"' in "".join(t.body)

    @pytest.mark.unit
    def test_trigger_thumbnail_width_applied(self):
        """Thumbnail width should appear as an inline style."""
        from lightbox.lightbox import visit_lightbox_trigger_html
        t = self._make_translator()
        visit_lightbox_trigger_html(t, self._make_trigger(thumbnail_width="60%"))
        assert "width: 60%;" in "".join(t.body)

    @pytest.mark.unit
    def test_trigger_custom_class_included(self):
        """Custom class should be merged into the img class attribute."""
        from lightbox.lightbox import visit_lightbox_trigger_html
        t = self._make_translator()
        visit_lightbox_trigger_html(t, self._make_trigger(custom_class="with-border"))
        assert "with-border" in "".join(t.body)

    # -- overlay --

    @pytest.mark.unit
    def test_overlay_renders_checkbox_input(self):
        """Overlay should contain the hidden checkbox toggle."""
        from lightbox.lightbox import visit_lightbox_overlay_html
        t = self._make_translator()
        visit_lightbox_overlay_html(t, self._make_overlay())
        output = "".join(t.body)
        assert 'type="checkbox"' in output
        assert 'class="lightbox-toggle"' in output

    @pytest.mark.unit
    def test_overlay_renders_dialog_div(self):
        """Overlay div should have role=dialog and aria-modal."""
        from lightbox.lightbox import visit_lightbox_overlay_html
        t = self._make_translator()
        visit_lightbox_overlay_html(t, self._make_overlay())
        output = "".join(t.body)
        assert 'role="dialog"' in output
        assert 'aria-modal="true"' in output

    @pytest.mark.unit
    def test_overlay_caption_rendered_when_present(self):
        """A non-empty caption should appear as a <p> in the overlay."""
        from lightbox.lightbox import visit_lightbox_overlay_html
        t = self._make_translator()
        visit_lightbox_overlay_html(
            t, self._make_overlay(caption="Click to enlarge")
        )
        output = "".join(t.body)
        assert "lightbox-caption" in output
        assert "Click to enlarge" in output

    @pytest.mark.unit
    def test_overlay_caption_omitted_when_empty(self):
        """An empty caption should not produce a caption paragraph."""
        from lightbox.lightbox import visit_lightbox_overlay_html
        t = self._make_translator()
        visit_lightbox_overlay_html(t, self._make_overlay(caption=""))
        assert "lightbox-caption" not in "".join(t.body)

    @pytest.mark.unit
    def test_overlay_backdrop_close_present(self):
        """Backdrop close label must be present for click-outside-to-close."""
        from lightbox.lightbox import visit_lightbox_overlay_html
        t = self._make_translator()
        visit_lightbox_overlay_html(t, self._make_overlay())
        assert "lightbox-backdrop-close" in "".join(t.body)

    @pytest.mark.unit
    def test_overlay_custom_class_on_img(self):
        """Custom class should appear on the overlay img element."""
        from lightbox.lightbox import visit_lightbox_overlay_html
        t = self._make_translator()
        visit_lightbox_overlay_html(
            t, self._make_overlay(custom_class="with-border")
        )
        assert "with-border" in "".join(t.body)


# ---------------------------------------------------------------------------
# TestHtmlEscaping
# ---------------------------------------------------------------------------

class TestHtmlEscaping:
    """Test that user-supplied values are HTML-escaped in visitor output.

    Unescaped alt text, captions, or URIs can produce malformed HTML.
    A double-quote in an attribute value breaks attribute parsing; angle
    brackets in text content inject raw tags.  All user-controlled fields
    must be passed through html.escape() before interpolation.
    """

    @staticmethod
    def _make_translator():
        t = Mock()
        t.body = []
        t.builder = Mock()
        t.builder.images = {}
        return t

    # -- alt text in trigger --

    @pytest.mark.unit
    def test_trigger_alt_double_quote_escaped(self):
        """A double-quote in alt text must not break the attribute."""
        from lightbox.lightbox import LightboxTrigger, visit_lightbox_trigger_html
        t = self._make_translator()
        node = LightboxTrigger()
        node["uri"] = "images/test.png"
        node["alt"] = 'Say "hello"'
        node["thumbnail_width"] = "100%"
        node["custom_class"] = ""
        node["checkbox_id"] = "lightbox-1"

        visit_lightbox_trigger_html(t, node)
        output = "".join(t.body)

        assert '"' not in output.split('alt="')[1].split('"')[0]
        assert "&quot;" in output

    @pytest.mark.unit
    def test_trigger_alt_angle_bracket_escaped(self):
        """Angle brackets in alt text must be escaped to &lt; / &gt;."""
        from lightbox.lightbox import LightboxTrigger, visit_lightbox_trigger_html
        t = self._make_translator()
        node = LightboxTrigger()
        node["uri"] = "images/test.png"
        node["alt"] = "<script>alert(1)</script>"
        node["thumbnail_width"] = "100%"
        node["custom_class"] = ""
        node["checkbox_id"] = "lightbox-1"

        visit_lightbox_trigger_html(t, node)
        output = "".join(t.body)

        assert "<script>" not in output
        assert "&lt;script&gt;" in output

    # -- alt text in overlay --

    @pytest.mark.unit
    def test_overlay_alt_double_quote_escaped(self):
        """A double-quote in overlay alt text must not break the attribute."""
        from lightbox.lightbox import LightboxOverlay, visit_lightbox_overlay_html
        t = self._make_translator()
        node = LightboxOverlay()
        node["uri"] = "images/test.png"
        node["alt"] = 'foo "bar"'
        node["caption"] = ""
        node["size_style"] = ""
        node["custom_class"] = ""
        node["checkbox_id"] = "lightbox-1"

        visit_lightbox_overlay_html(t, node)
        output = "".join(t.body)

        assert "&quot;" in output
        assert 'aria-label="foo &quot;bar&quot;"' in output

    # -- caption in overlay --

    @pytest.mark.unit
    def test_overlay_caption_html_escaped(self):
        """HTML special characters in caption must be escaped in output."""
        from lightbox.lightbox import LightboxOverlay, visit_lightbox_overlay_html
        t = self._make_translator()
        node = LightboxOverlay()
        node["uri"] = "images/test.png"
        node["alt"] = ""
        node["caption"] = "<b>Bold</b> & 'quoted'"
        node["size_style"] = ""
        node["custom_class"] = ""
        node["checkbox_id"] = "lightbox-1"

        visit_lightbox_overlay_html(t, node)
        output = "".join(t.body)

        assert "<b>" not in output
        assert "&lt;b&gt;" in output
        assert "&amp;" in output

    @pytest.mark.unit
    def test_overlay_caption_script_tag_escaped(self):
        """A <script> tag in caption must not appear literally in output."""
        from lightbox.lightbox import LightboxOverlay, visit_lightbox_overlay_html
        t = self._make_translator()
        node = LightboxOverlay()
        node["uri"] = "images/test.png"
        node["alt"] = ""
        node["caption"] = "<script>alert('xss')</script>"
        node["size_style"] = ""
        node["custom_class"] = ""
        node["checkbox_id"] = "lightbox-1"

        visit_lightbox_overlay_html(t, node)
        output = "".join(t.body)

        assert "<script>" not in output
        assert "&lt;script&gt;" in output

    # -- image URI --

    @pytest.mark.unit
    def test_trigger_uri_ampersand_escaped(self):
        """An ampersand in a URI (query string) must be escaped to &amp;."""
        from lightbox.lightbox import LightboxTrigger, visit_lightbox_trigger_html
        t = self._make_translator()
        node = LightboxTrigger()
        node["uri"] = "images/test.png?foo=1&bar=2"
        node["alt"] = ""
        node["thumbnail_width"] = "100%"
        node["custom_class"] = ""
        node["checkbox_id"] = "lightbox-1"

        visit_lightbox_trigger_html(t, node)
        output = "".join(t.body)

        assert "foo=1&bar=2" not in output
        assert "foo=1&amp;bar=2" in output

    # -- custom class --

    @pytest.mark.unit
    def test_trigger_custom_class_quote_escaped(self):
        """A double-quote in a custom class must not break the class attribute."""
        from lightbox.lightbox import LightboxTrigger, visit_lightbox_trigger_html
        t = self._make_translator()
        node = LightboxTrigger()
        node["uri"] = "images/test.png"
        node["alt"] = ""
        node["thumbnail_width"] = "100%"
        node["custom_class"] = 'evil" onmouseover="alert(1)'
        node["checkbox_id"] = "lightbox-1"

        visit_lightbox_trigger_html(t, node)
        output = "".join(t.body)

        assert 'onmouseover="alert(1)"' not in output
        assert "&quot;" in output


# ---------------------------------------------------------------------------
# Helpers for structural HTML validation
# ---------------------------------------------------------------------------



class _TagTracker(HTMLParser):
    """Tracks open/close tag balance to detect structural HTML errors.

    Void elements (self-closing by spec) are excluded from balance checks.
    """

    VOID_ELEMENTS = frozenset({
        "area", "base", "br", "col", "embed", "hr", "img", "input",
        "link", "meta", "param", "source", "track", "wbr",
    })

    def __init__(self):
        super().__init__()
        self._stack = []
        self.errors = []

    def handle_starttag(self, tag, attrs):
        if tag not in self.VOID_ELEMENTS:
            self._stack.append(tag)

    def handle_endtag(self, tag):
        if tag in self.VOID_ELEMENTS:
            return
        if self._stack and self._stack[-1] == tag:
            self._stack.pop()
        else:
            self.errors.append(
                f"Unexpected </{tag}>; open tags: {list(self._stack)}"
            )

    @property
    def unclosed_tags(self):
        return list(self._stack)


def _render_full_lightbox(uri="/images/test.png", alt="Alt text",
                           caption="", custom_class="",
                           checkbox_id="lightbox-1",
                           thumbnail_width="60%",
                           size_style="") -> str:
    """Render a complete lightbox HTML fragment by calling all six visitors."""
    from lightbox.lightbox import (
        LightboxContainer,
        LightboxOverlay,
        LightboxTrigger,
        depart_lightbox_container_html,
        depart_lightbox_overlay_html,
        depart_lightbox_trigger_html,
        visit_lightbox_container_html,
        visit_lightbox_overlay_html,
        visit_lightbox_trigger_html,
    )

    t = Mock()
    t.body = []
    t.builder = Mock()
    t.builder.images = {}

    container = LightboxContainer()
    container["uri"] = uri
    container["caption"] = caption
    container["latex_width"] = "0.95"

    trigger = LightboxTrigger()
    trigger["uri"] = uri
    trigger["alt"] = alt
    trigger["thumbnail_width"] = thumbnail_width
    trigger["custom_class"] = custom_class
    trigger["checkbox_id"] = checkbox_id

    overlay = LightboxOverlay()
    overlay["uri"] = uri
    overlay["alt"] = alt
    overlay["caption"] = caption
    overlay["size_style"] = size_style
    overlay["custom_class"] = custom_class
    overlay["checkbox_id"] = checkbox_id

    visit_lightbox_container_html(t, container)
    visit_lightbox_trigger_html(t, trigger)
    depart_lightbox_trigger_html(t, trigger)
    visit_lightbox_overlay_html(t, overlay)
    depart_lightbox_overlay_html(t, overlay)
    depart_lightbox_container_html(t, container)

    return "".join(t.body)


# ---------------------------------------------------------------------------
# TestHtmlStructure
# ---------------------------------------------------------------------------

class TestHtmlStructure:
    """Verify that the full HTML fragment is structurally well-formed.

    These tests catch tag-balance errors (e.g. a missing </div>) that
    substring-based tests cannot detect.
    """

    @pytest.mark.unit
    def test_basic_output_is_well_formed(self):
        """A basic lightbox fragment must have balanced tags."""
        tracker = _TagTracker()
        tracker.feed(_render_full_lightbox())
        assert tracker.errors == [], f"Tag errors: {tracker.errors}"
        assert tracker.unclosed_tags == [], f"Unclosed tags: {tracker.unclosed_tags}"

    @pytest.mark.unit
    def test_with_caption_is_well_formed(self):
        """A lightbox with a caption must still produce balanced HTML."""
        tracker = _TagTracker()
        tracker.feed(_render_full_lightbox(caption="This is a caption"))
        assert tracker.errors == [], f"Tag errors: {tracker.errors}"
        assert tracker.unclosed_tags == [], f"Unclosed tags: {tracker.unclosed_tags}"

    @pytest.mark.unit
    def test_with_special_chars_in_caption_is_well_formed(self):
        """HTML-escaped caption characters must not break tag structure."""
        tracker = _TagTracker()
        tracker.feed(_render_full_lightbox(caption='<em>italic</em> & "quoted"'))
        assert tracker.errors == [], f"Tag errors: {tracker.errors}"
        assert tracker.unclosed_tags == [], f"Unclosed tags: {tracker.unclosed_tags}"

    @pytest.mark.unit
    def test_with_custom_class_is_well_formed(self):
        """A lightbox with a custom class must produce balanced HTML."""
        tracker = _TagTracker()
        tracker.feed(_render_full_lightbox(custom_class="with-border"))
        assert tracker.errors == [], f"Tag errors: {tracker.errors}"
        assert tracker.unclosed_tags == [], f"Unclosed tags: {tracker.unclosed_tags}"


# ---------------------------------------------------------------------------
# TestRegressionBugs
# ---------------------------------------------------------------------------

class TestRegressionBugs:
    """Tests for previously fixed bugs (prevent regressions)."""

    @pytest.mark.integration
    def test_regression_percent_in_caption_causes_runaway_arg(self, mock_builder):
        """
        Regression: % in caption caused LaTeX 'Runaway argument' error.

        Bug: "40% width" made LaTeX treat the rest of the line as a comment,
        corrupting the \\caption{} argument.
        Fix: latex_escape() is applied to all caption text.
        """
        import re

        node = LightboxContainer()
        node["uri"] = "/images/test.png"
        node["caption"] = "40% thumbnail width, 95% overlay size."
        node["latex_width"] = "0.95"

        translator = mock_builder.translator
        run_latex_visitor(translator, node)

        output = "".join(translator.body)

        # Escaped forms must be present
        assert r"40\% thumbnail width" in output
        assert r"95\% overlay size" in output

        # Extract caption content and verify no bare (unescaped) % remains.
        # The escaped form \% still contains a % character, so we cannot
        # simply count("%") == 0.  Instead assert there is no % that is
        # NOT preceded by a backslash.
        match = re.search(r"\\caption\{([^}]+)\}", output)
        assert match, r"\caption{} not found in output"
        caption_content = match.group(1)
        bare_percent = re.search(r"(?<!\\)%", caption_content)
        assert bare_percent is None, (
            f"Unescaped % found in caption: {caption_content!r}"
        )
        assert caption_content.count(r"\%") >= 2
