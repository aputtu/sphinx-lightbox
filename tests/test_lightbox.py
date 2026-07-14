"""
Tests for sphinx-lightbox.

Covers LaTeX and HTML output generation, directive parsing, security,
and build-time aspect ratio calculations.
"""

from unittest.mock import Mock, patch

import pytest
from docutils import nodes
from sphinx.util.texescape import escape as latex_escape

from lightbox.lightbox import (
    LightboxContainer,
    LightboxDirective,
    LightboxOverlay,
    LightboxTrigger,
    assign_lightbox_gallery,
    transform_lightbox_images,
    visit_lightbox_container_latex,
)

# ---------------------------------------------------------------------------
# Helper: call the LaTeX visitor and absorb the expected SkipNode signal
# ---------------------------------------------------------------------------


def run_latex_visitor(translator, node):
    with pytest.raises(nodes.SkipNode):
        visit_lightbox_container_latex(translator, node)


# ---------------------------------------------------------------------------
# TestCaptionEscaping
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
# TestLatexOutput
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
# TestLatexWidthOption
# ---------------------------------------------------------------------------


class TestLegacyLatexWidthOption:
    """Test the legacy directive's retained PDF width compatibility option."""

    def _make_directive(self, sphinx_env, arguments, options):
        state = Mock()
        state.document.settings.env = sphinx_env
        state_machine = Mock()
        state_machine.get_source_and_line.return_value = ("test.rst", 10)
        return LightboxDirective("lightbox", arguments, options, [], 1, 0, "", state, state_machine)

    @pytest.mark.unit
    def test_latex_width_overrides_percentage(self, sphinx_env):
        """Explicit :latex-width: should override the percentage-derived value."""
        directive = self._make_directive(
            sphinx_env, ["/i.png"], {"percentage": [50, 90], "latex-width": "0.80"}
        )
        with patch("lightbox.lightbox.os.path.isfile", return_value=True):
            res = directive.run()
        assert res[0]["latex_width"] == "0.80"

    @pytest.mark.unit
    def test_latex_width_without_percentage(self, sphinx_env):
        """:latex-width: should work even when :percentage: is not set."""
        directive = self._make_directive(sphinx_env, ["/i.png"], {"latex-width": "0.60"})
        with patch("lightbox.lightbox.os.path.isfile", return_value=True):
            res = directive.run()
        assert res[0]["latex_width"] == "0.60"

    @pytest.mark.unit
    def test_absent_latex_width_falls_back_to_percentage(self, sphinx_env):
        """Without :latex-width:, the second percentage value is used."""
        directive = self._make_directive(sphinx_env, ["/i.png"], {"percentage": [50, 75]})
        with patch("lightbox.lightbox.os.path.isfile", return_value=True):
            res = directive.run()
        assert res[0]["latex_width"] == "0.75"

    @pytest.mark.unit
    def test_absent_latex_width_falls_back_to_default_95(self, sphinx_env):
        """Without :latex-width: or :percentage:, the default 0.95 is used."""
        directive = self._make_directive(sphinx_env, ["/i.png"], {})
        with patch("lightbox.lightbox.os.path.isfile", return_value=True):
            res = directive.run()
        assert res[0]["latex_width"] == "0.95"

    @pytest.mark.unit
    def test_invalid_latex_width_emits_warning_and_falls_back(self, sphinx_env):
        """Invalid values should warn and keep the percentage-based default."""
        directive = self._make_directive(
            sphinx_env, ["/i.png"], {"percentage": [50, 90], "latex-width": "abc"}
        )
        with (
            patch("lightbox.lightbox.os.path.isfile", return_value=True),
            patch("lightbox.lightbox.logger") as mock_logger,
        ):
            res = directive.run()
        # Falls back to percentage-derived value
        assert res[0]["latex_width"] == "0.90"
        assert mock_logger.warning.called
        assert mock_logger.warning.call_args.kwargs.get("subtype") == "invalid_option"

    @pytest.mark.unit
    def test_out_of_range_latex_width_emits_warning(self, sphinx_env):
        """Values outside (0, 1] should warn and keep the default."""
        directive = self._make_directive(sphinx_env, ["/i.png"], {"latex-width": "1.5"})
        with (
            patch("lightbox.lightbox.os.path.isfile", return_value=True),
            patch("lightbox.lightbox.logger") as mock_logger,
        ):
            res = directive.run()
        # Falls back to default 95%
        assert res[0]["latex_width"] == "0.95"
        assert mock_logger.warning.called

    @pytest.mark.unit
    def test_latex_width_does_not_affect_html_size_style(self, sphinx_env):
        """:latex-width: must not change the CSS size_style on the overlay."""
        directive = self._make_directive(
            sphinx_env, ["/i.png"], {"percentage": [50, 90], "latex-width": "0.60"}
        )
        with patch("lightbox.lightbox.os.path.isfile", return_value=True):
            res = directive.run()
        overlay = next(n for n in res[0].children if isinstance(n, LightboxOverlay))
        # CSS should still use the percentage value (90), not the latex-width
        assert "min(90vw," in overlay["size_style"]


# ---------------------------------------------------------------------------
# TestDirectiveIntegration
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

    @pytest.mark.integration
    def test_checkbox_id_sanitizes_docname_for_html_id_safety(self, sphinx_env):
        sphinx_env.docname = 'nested/page with "quotes"'
        directive = self._make_directive(sphinx_env, ["/i.png"], {})
        with patch("lightbox.lightbox.os.path.isfile", return_value=True):
            res = directive.run()
        trigger = next(n for n in res[0].children if isinstance(n, LightboxTrigger))
        assert trigger["checkbox_id"] == "lightbox-nested-page-with-quotes-1"

    @pytest.mark.unit
    def test_data_uri_returns_standard_image(self, sphinx_env):
        data_uri = "data:image/png;base64,AAAA"
        directive = self._make_directive(sphinx_env, [data_uri], {"alt": "Inline"})
        res = directive.run()
        assert isinstance(res[0], nodes.image)
        assert res[0]["uri"] == data_uri

    @pytest.mark.integration
    def test_collector_image_remains_visible_to_fallback_builders(self, sphinx_env):
        directive = self._make_directive(sphinx_env, ["images/test.png"], {})
        with patch("lightbox.lightbox.os.path.isfile", return_value=True):
            result_nodes = directive.run()
        collector = next(
            n for n in result_nodes[0].children if n.__class__.__name__ == "LightboxCollector"
        )
        assert collector.children[0]["classes"] == []


# ---------------------------------------------------------------------------
# TestStandardImageTransform
# ---------------------------------------------------------------------------


class TestStandardImageTransform:
    """Test class-based lightbox wrapping for normal image and figure nodes."""

    @staticmethod
    def _make_app(
        builder_format="html",
        builder_name="html",
        all_images=False,
        image_policy="explicit",
        figure_policy="all",
        default_class="",
        gallery_mode="document",
        gallery_wrap=False,
    ):
        app = Mock()
        app.builder.format = builder_format
        app.builder.name = builder_name
        app.config.lightbox_all_images = all_images
        app.config.lightbox_images = image_policy
        app.config.lightbox_figures = figure_policy
        app.config.lightbox_default_class = default_class
        app.config.lightbox_gallery = gallery_mode
        app.config.lightbox_gallery_wrap = gallery_wrap

        return app

    @staticmethod
    def _make_doc(*children):
        doc = nodes.document("", "")
        doc += list(children)
        return doc

    @pytest.mark.unit
    def test_image_with_lightbox_class_is_transformed(self):
        image = nodes.image(uri="sample.png", alt="Sample", classes=["lightbox"])
        doc = self._make_doc(image)
        app = self._make_app()

        transform_lightbox_images(app, doc, "index")

        assert isinstance(doc[0], LightboxContainer)
        assert doc[0][0]["uri"] == "sample.png"
        assert doc[0][0]["alt"] == "Sample"
        assert doc[0][0]["checkbox_id"] == "lightbox-index-1"
        app.env.new_serialno.assert_not_called()

    @pytest.mark.unit
    def test_transform_is_idempotent_when_all_images_are_enabled(self):
        image = nodes.image(uri="sample.png", alt="Sample")
        doc = self._make_doc(image)
        app = self._make_app(image_policy="all")

        transform_lightbox_images(app, doc, "index")
        transform_lightbox_images(app, doc, "index")

        assert len(list(doc.findall(LightboxContainer))) == 1
        assert len(list(doc.findall(LightboxOverlay))) == 1

    @pytest.mark.unit
    def test_standard_ids_do_not_collide_with_legacy_containers(self):
        legacy = LightboxContainer()
        legacy_trigger = LightboxTrigger(checkbox_id="lightbox-index-1")
        legacy_overlay = LightboxOverlay(checkbox_id="lightbox-index-1")
        legacy += legacy_trigger
        legacy += legacy_overlay
        image = nodes.image(uri="sample.png", classes=["lightbox"])
        doc = self._make_doc(legacy, image)

        transform_lightbox_images(self._make_app(), doc, "index")

        assert doc[1][0]["checkbox_id"] == "lightbox-index-2"

    @pytest.mark.unit
    def test_checkbox_id_does_not_collide_with_native_named_image(self):
        image = nodes.image(
            uri="sample.png",
            classes=["lightbox"],
            ids=["lightbox-index-1"],
        )
        doc = self._make_doc(image)

        transform_lightbox_images(self._make_app(), doc, "index")

        trigger = next(child for child in doc[0] if isinstance(child, LightboxTrigger))
        thumbnail = next(child for child in trigger if isinstance(child, nodes.image))
        assert trigger["checkbox_id"] == "lightbox-index-2"
        assert thumbnail["ids"] == ["lightbox-index-1"]

    @pytest.mark.unit
    def test_legacy_checkbox_id_is_renamed_when_native_id_collides(self):
        legacy = LightboxContainer()
        legacy_trigger = LightboxTrigger(checkbox_id="lightbox-index-1")
        legacy_overlay = LightboxOverlay(checkbox_id="lightbox-index-1")
        legacy += legacy_trigger
        legacy += legacy_overlay
        image = nodes.image(
            uri="sample.png",
            classes=["lightbox"],
            ids=["lightbox-index-1"],
        )
        doc = self._make_doc(legacy, image)

        transform_lightbox_images(self._make_app(), doc, "index")

        standard_trigger = next(child for child in doc[1] if isinstance(child, LightboxTrigger))
        assert legacy_trigger["checkbox_id"] == "lightbox-index-2"
        assert legacy_overlay["checkbox_id"] == "lightbox-index-2"
        assert standard_trigger["checkbox_id"] == "lightbox-index-3"

    @pytest.mark.unit
    def test_remote_image_with_lightbox_class_is_not_transformed(self):
        image = nodes.image(uri="https://example.invalid/sample.png", classes=["lightbox"])
        doc = self._make_doc(image)

        transform_lightbox_images(self._make_app(), doc, "index")

        assert isinstance(doc[0], nodes.image)

    @pytest.mark.unit
    def test_data_image_with_lightbox_class_is_not_transformed(self):
        image = nodes.image(uri="data:image/png;base64,AAAA", classes=["lightbox"])
        doc = self._make_doc(image)

        transform_lightbox_images(self._make_app(), doc, "index")

        assert isinstance(doc[0], nodes.image)

    @pytest.mark.unit
    def test_transformed_image_keeps_native_thumbnail_for_asset_copying(self):
        image = nodes.image(uri="images/sample.png", alt="Sample", classes=["lightbox"])
        doc = self._make_doc(image)

        transform_lightbox_images(self._make_app(), doc, "index")

        trigger = next(child for child in doc[0] if isinstance(child, LightboxTrigger))
        thumbnail = next(child for child in trigger if isinstance(child, nodes.image))
        assert thumbnail["uri"] == "images/sample.png"
        assert thumbnail["alt"] == ""

    @pytest.mark.unit
    def test_image_without_lightbox_class_is_left_alone(self):
        image = nodes.image(uri="sample.png", alt="Sample")
        doc = self._make_doc(image)

        transform_lightbox_images(self._make_app(), doc, "index")

        assert isinstance(doc[0], nodes.image)

    @pytest.mark.unit
    def test_global_enable_wraps_plain_images(self):
        image = nodes.image(uri="sample.png", alt="Sample")
        doc = self._make_doc(image)

        transform_lightbox_images(self._make_app(image_policy="all"), doc, "index")

        assert isinstance(doc[0], LightboxContainer)

    @pytest.mark.unit
    def test_no_lightbox_class_opts_out_of_global_enable(self):
        image = nodes.image(uri="sample.png", classes=["no-lightbox"])
        doc = self._make_doc(image)

        transform_lightbox_images(self._make_app(image_policy="all"), doc, "index")

        assert isinstance(doc[0], nodes.image)

    @pytest.mark.unit
    def test_non_html_builds_do_not_transform_images(self):
        image = nodes.image(uri="sample.png", classes=["lightbox"])
        doc = self._make_doc(image)

        transform_lightbox_images(self._make_app(builder_format="latex"), doc, "index")

        assert isinstance(doc[0], nodes.image)

    @pytest.mark.unit
    def test_epub_builds_do_not_transform_images(self):
        image = nodes.image(uri="sample.png", classes=["lightbox"])
        doc = self._make_doc(image)

        transform_lightbox_images(
            self._make_app(builder_format="html", builder_name="epub"), doc, "index"
        )

        assert isinstance(doc[0], nodes.image)

    @pytest.mark.unit
    def test_figure_caption_is_copied_to_lightbox_overlay(self):
        image = nodes.image(uri="sample.png")
        caption = nodes.caption("", "Figure caption.")
        figure = nodes.figure("", image, caption)
        doc = self._make_doc(figure)

        transform_lightbox_images(self._make_app(), doc, "index")

        container = figure[0]
        overlay = next(child for child in container if isinstance(child, LightboxOverlay))
        assert overlay["caption"] == "Figure caption."
        assert figure[1].astext() == "Figure caption."

    @pytest.mark.unit
    def test_figure_legend_is_copied_to_lightbox_overlay(self):
        image = nodes.image(uri="sample.png")
        caption = nodes.caption("", "Figure caption.")
        legend = nodes.legend("", nodes.paragraph("", "Longer explanation."))
        figure = nodes.figure("", image, caption, legend)
        doc = self._make_doc(figure)

        transform_lightbox_images(self._make_app(), doc, "index")

        container = figure[0]
        overlay = next(child for child in container if isinstance(child, LightboxOverlay))
        assert overlay["legend"] == "Longer explanation."
        assert figure[2].astext() == "Longer explanation."

    @pytest.mark.unit
    def test_plain_images_do_not_use_alt_as_caption(self):
        image = nodes.image(uri="sample.png", alt="Not a caption", classes=["lightbox"])
        doc = self._make_doc(image)

        transform_lightbox_images(self._make_app(), doc, "index")

        overlay = next(child for child in doc[0] if isinstance(child, LightboxOverlay))
        assert overlay["caption"] == ""
        assert overlay["legend"] == ""

    @pytest.mark.unit
    def test_figure_policy_none_disables_implicit_figure_wrapping(self):
        image = nodes.image(uri="sample.png")
        figure = nodes.figure("", image, nodes.caption("", "Caption."))
        doc = self._make_doc(figure)

        transform_lightbox_images(self._make_app(figure_policy="none"), doc, "index")

        assert isinstance(figure[0], nodes.image)

    @pytest.mark.unit
    def test_figure_policy_explicit_requires_lightbox_class(self):
        image = nodes.image(uri="sample.png")
        figure = nodes.figure("", image, nodes.caption("", "Caption."))
        doc = self._make_doc(figure)

        transform_lightbox_images(self._make_app(figure_policy="explicit"), doc, "index")

        assert isinstance(figure[0], nodes.image)

    @pytest.mark.unit
    def test_all_images_switch_still_wraps_plain_images(self):
        image = nodes.image(uri="sample.png")
        doc = self._make_doc(image)

        transform_lightbox_images(self._make_app(all_images=True), doc, "index")

        assert isinstance(doc[0], LightboxContainer)

    @pytest.mark.unit
    def test_default_class_is_applied_to_transformed_images(self):
        image = nodes.image(uri="sample.png", classes=["lightbox"])
        doc = self._make_doc(image)

        transform_lightbox_images(self._make_app(default_class="with-shadow"), doc, "index")

        trigger = doc[0][0]
        assert trigger["custom_class"] == "with-shadow"

    @pytest.mark.unit
    def test_user_classes_are_preserved_without_control_class(self):
        image = nodes.image(uri="sample.png", classes=["lightbox", "with-border"])
        doc = self._make_doc(image)

        transform_lightbox_images(self._make_app(), doc, "index")

        trigger = doc[0][0]
        assert trigger["custom_class"] == "with-border"

    @pytest.mark.unit
    def test_native_thumbnail_preserves_image_options(self):
        image = nodes.image(
            uri="sample.png",
            alt="Example",
            classes=["lightbox", "custom"],
            width="45%",
            height="120px",
            scale=50,
            loading="lazy",
            ids=["named-image"],
        )
        doc = self._make_doc(image)

        transform_lightbox_images(self._make_app(), doc, "index")

        trigger = next(child for child in doc[0] if isinstance(child, LightboxTrigger))
        thumbnail = next(child for child in trigger if isinstance(child, nodes.image))
        assert thumbnail["alt"] == ""
        assert thumbnail["width"] == "45%"
        assert thumbnail["height"] == "120px"
        assert thumbnail["scale"] == 50
        assert thumbnail["loading"] == "lazy"
        assert thumbnail["ids"] == ["named-image"]
        assert thumbnail["classes"] == ["lightbox-trigger", "no-scaled-link", "custom"]

    @pytest.mark.unit
    def test_image_alignment_is_preserved_on_container(self):
        image = nodes.image(uri="sample.png", classes=["lightbox"], align="center")
        doc = self._make_doc(image)

        transform_lightbox_images(self._make_app(), doc, "index")

        assert doc[0]["align"] == "center"


# ---------------------------------------------------------------------------
# TestGalleryMetadata
# ---------------------------------------------------------------------------


class TestGalleryMetadata:
    """Test source-order gallery metadata for transformed lightboxes."""

    @staticmethod
    def _make_app(gallery_mode="document", gallery_wrap=False):
        app = Mock()
        app.config.lightbox_gallery = gallery_mode
        app.config.lightbox_gallery_wrap = gallery_wrap
        return app

    @staticmethod
    def _make_container(checkbox_id):
        container = LightboxContainer()
        trigger = LightboxTrigger()
        trigger["checkbox_id"] = checkbox_id
        overlay = LightboxOverlay()
        overlay["checkbox_id"] = checkbox_id
        container += trigger
        container += overlay
        return container, overlay

    @staticmethod
    def _make_doc(*children):
        doc = nodes.document("", "")
        doc += list(children)
        return doc

    @pytest.mark.unit
    def test_gallery_metadata_assigned_in_source_order(self):
        first, first_overlay = self._make_container("lb-1")
        second, second_overlay = self._make_container("lb-2")
        third, third_overlay = self._make_container("lb-3")
        doc = self._make_doc(first, second, third)

        assign_lightbox_gallery(self._make_app(), doc, "nested/page")

        assert first_overlay["gallery_id"] == "lightbox-gallery-nested-page"
        assert first_overlay["gallery_index"] == 1
        assert first_overlay["gallery_count"] == 3
        assert first_overlay["gallery_next_target"] == "lb-2"
        assert "gallery_prev_target" not in first_overlay
        assert second_overlay["gallery_prev_target"] == "lb-1"
        assert second_overlay["gallery_next_target"] == "lb-3"
        assert third_overlay["gallery_prev_target"] == "lb-2"
        assert "gallery_next_target" not in third_overlay

    @pytest.mark.unit
    def test_gallery_id_sanitizes_docname(self):
        first, first_overlay = self._make_container("lb-1")
        second, _second_overlay = self._make_container("lb-2")
        doc = self._make_doc(first, second)

        assign_lightbox_gallery(self._make_app(), doc, 'nested/page with "quotes"')

        assert first_overlay["gallery_id"] == "lightbox-gallery-nested-page-with-quotes"

    @pytest.mark.unit
    def test_gallery_wrap_cycles_first_and_last_items(self):
        first, first_overlay = self._make_container("lb-1")
        second, second_overlay = self._make_container("lb-2")
        doc = self._make_doc(first, second)

        assign_lightbox_gallery(self._make_app(gallery_wrap=True), doc, "index")

        assert first_overlay["gallery_prev_target"] == "lb-2"
        assert second_overlay["gallery_next_target"] == "lb-1"

    @pytest.mark.unit
    def test_gallery_none_suppresses_metadata(self):
        first, first_overlay = self._make_container("lb-1")
        second, second_overlay = self._make_container("lb-2")
        doc = self._make_doc(first, second)

        assign_lightbox_gallery(self._make_app(gallery_mode="none"), doc, "index")

        assert "gallery_next_target" not in first_overlay
        assert "gallery_prev_target" not in second_overlay

    @pytest.mark.unit
    def test_single_item_document_suppresses_metadata(self):
        container, overlay = self._make_container("lb-1")
        doc = self._make_doc(container)

        assign_lightbox_gallery(self._make_app(), doc, "index")

        assert "gallery_index" not in overlay
        assert "gallery_next_target" not in overlay

    @pytest.mark.unit
    def test_transformed_images_get_gallery_metadata(self):
        app = TestStandardImageTransform._make_app(image_policy="all")
        first = nodes.image(uri="first.png", alt="First")
        second = nodes.image(uri="second.png", alt="Second")
        doc = self._make_doc(first, second)

        transform_lightbox_images(app, doc, "index")

        first_overlay = next(child for child in doc[0] if isinstance(child, LightboxOverlay))
        second_overlay = next(child for child in doc[1] if isinstance(child, LightboxOverlay))
        assert first_overlay["gallery_next_target"] == "lightbox-index-2"
        assert second_overlay["gallery_prev_target"] == "lightbox-index-1"


# ---------------------------------------------------------------------------
# TestSizeStyleFormula
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
# TestMissingImage
# ---------------------------------------------------------------------------


class TestMissingImage:
    """Test behaviour for invalid image paths."""

    @pytest.mark.unit
    def test_missing_image_returns_empty_list(self, sphinx_env):
        state = Mock()
        state.document.settings.env = sphinx_env
        directive = LightboxDirective("lightbox", ["/no.png"], {}, [], 1, 0, "", state, Mock())
        with (
            patch("lightbox.lightbox.os.path.isfile", return_value=False),
            patch("lightbox.lightbox.logger"),
        ):
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

    @pytest.mark.unit
    def test_symlink_outside_source_directory_is_rejected(self, sphinx_env, tmp_path):
        srcdir = tmp_path / "src"
        srcdir.mkdir()
        outside = tmp_path / "outside.png"
        outside.write_bytes(b"outside")
        try:
            srcdir.joinpath("linked.png").symlink_to(outside)
        except OSError as exc:
            pytest.skip(f"symlinks unavailable: {exc}")

        sphinx_env.srcdir = str(srcdir)
        state = Mock()
        state.document.settings.env = sphinx_env
        directive = LightboxDirective("lightbox", ["/linked.png"], {}, [], 1, 0, "", state, Mock())

        with patch("lightbox.lightbox.logger") as mock_logger:
            assert directive.run() == []

        assert mock_logger.warning.call_args.kwargs.get("subtype") == "path_traversal"


# ---------------------------------------------------------------------------
# TestHtmlOutput
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
        node.get = lambda k, d: {"alt": "A", "thumbnail_width": "1%", "custom_class": ""}.get(k, d)
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
        node.get = lambda k, d: {"alt": "A", "thumbnail_width": "60%", "custom_class": ""}.get(k, d)
        visit_lightbox_trigger_html(t, node)
        assert "width: 60%;" in "".join(t.body)

    @pytest.mark.unit
    def test_trigger_rejects_unsafe_thumbnail_width(self):
        from lightbox.lightbox import visit_lightbox_trigger_html

        t = self._make_translator()
        node = LightboxTrigger()
        node["uri"] = "i.png"
        node["checkbox_id"] = "l1"
        node.get = lambda k, d: {
            "alt": "A",
            "thumbnail_width": "1%; background: url(javascript:alert(1))",
            "custom_class": "",
        }.get(k, d)
        visit_lightbox_trigger_html(t, node)
        output = "".join(t.body)
        assert "javascript:" not in output
        assert "width: 100%;" in output

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
        assert (
            '<span class="lightbox-visually-hidden">Enlarge image: Server diagram</span>'
            in "".join(t.body)
        )

    @pytest.mark.unit
    def test_trigger_uses_filename_when_alt_text_is_empty(self):
        from lightbox.lightbox import visit_lightbox_trigger_html

        t = self._make_translator()
        node = LightboxTrigger(
            uri="images/server_diagram-final.png",
            checkbox_id="l1",
            alt="",
            thumbnail_width="100%",
            custom_class="",
        )

        visit_lightbox_trigger_html(t, node)

        output = "".join(t.body)
        assert "Enlarge image: server diagram final" in output
        assert 'alt=""' in output

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
    def test_overlay_uses_filename_for_dialog_name_when_alt_text_is_empty(self):
        from lightbox.lightbox import visit_lightbox_overlay_html

        t = self._make_translator()
        node = LightboxOverlay(
            uri="images/server_diagram-final.png",
            checkbox_id="l1",
            alt="",
            caption="",
            legend="",
            custom_class="",
            size_style="",
        )

        visit_lightbox_overlay_html(t, node)

        output = "".join(t.body)
        assert 'aria-label="server diagram final"' in output
        assert 'alt="server diagram final"' in output

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
        assert '<span class="lightbox-visually-hidden">Close lightbox</span>' in output
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
    def test_overlay_rejects_unsafe_inline_style(self):
        from lightbox.lightbox import visit_lightbox_overlay_html

        t = self._make_translator()
        node = LightboxOverlay()
        node["uri"] = "t.png"
        node["checkbox_id"] = "l1"
        node.get = lambda k, d: {
            "alt": "A",
            "caption": "",
            "custom_class": "",
            "size_style": "width: url(javascript:alert(1));",
        }.get(k, d)
        visit_lightbox_overlay_html(t, node)
        output = "".join(t.body)
        assert "javascript:" not in output
        assert "style=" not in output

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
        output = "".join(t.body)
        assert '<div class="lightbox-text">' in output
        assert '<p class="lightbox-caption">Figure 1</p>' in output

    @pytest.mark.unit
    def test_overlay_legend_rendered_when_present(self):
        from lightbox.lightbox import visit_lightbox_overlay_html

        t = self._make_translator()
        node = LightboxOverlay()
        node["uri"] = "t.png"
        node["checkbox_id"] = "l1"
        node.get = lambda k, d: {
            "alt": "A",
            "caption": "",
            "legend": "Longer explanation.",
            "custom_class": "",
            "size_style": "",
        }.get(k, d)
        visit_lightbox_overlay_html(t, node)
        output = "".join(t.body)
        assert '<div class="lightbox-text">' in output
        assert '<div class="lightbox-legend">Longer explanation.</div>' in output

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
        output = "".join(t.body)
        assert "lightbox-caption" not in output
        assert "lightbox-text" not in output

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

    @pytest.mark.unit
    def test_overlay_gallery_controls_render_when_targets_present(self):
        from lightbox.lightbox import visit_lightbox_overlay_html

        t = self._make_translator()
        node = LightboxOverlay()
        node["uri"] = "t.png"
        node["checkbox_id"] = "l1"
        node["gallery_index"] = 2
        node["gallery_count"] = 3
        node["gallery_prev_target"] = "l0"
        node["gallery_next_target"] = "l2"
        node.get = lambda k, d: {
            "alt": "A",
            "caption": "",
            "custom_class": "",
            "size_style": "",
            "gallery_index": 2,
            "gallery_count": 3,
            "gallery_prev_target": "l0",
            "gallery_next_target": "l2",
        }.get(k, d)
        visit_lightbox_overlay_html(t, node)
        output = "".join(t.body)
        assert 'class="lightbox-gallery-control lightbox-gallery-prev"' in output
        assert 'data-lightbox-target="l0"' in output
        assert 'class="lightbox-gallery-control lightbox-gallery-next"' in output
        assert 'data-lightbox-target="l2"' in output

    @pytest.mark.unit
    def test_overlay_gallery_controls_omitted_without_targets(self):
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
        assert "lightbox-gallery-control" not in "".join(t.body)


# ---------------------------------------------------------------------------
# TestHtmlEscaping
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
            "alt": "<script>alert(1)</script>",
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
        assert (
            "onmouseover" not in output.split("&quot;onmouseover")[0]
            if "&quot;onmouseover" in output
            else True
        )
        assert "&quot;" in output

    @pytest.mark.unit
    def test_uri_special_chars_escaped(self):
        from lightbox.lightbox import visit_lightbox_trigger_html

        t = self._make_translator()
        node = LightboxTrigger()
        node["uri"] = 'img "name".png'
        node["checkbox_id"] = "l1"
        node.get = lambda k, d: {"alt": "A", "thumbnail_width": "1%", "custom_class": ""}.get(k, d)
        visit_lightbox_trigger_html(t, node)
        output = "".join(t.body)
        # Double quotes inside the src attribute must be escaped
        assert "&quot;name&quot;" in output

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

    @pytest.mark.unit
    def test_gallery_targets_are_escaped(self):
        from lightbox.lightbox import visit_lightbox_overlay_html

        t = self._make_translator()
        node = LightboxOverlay()
        node["uri"] = "i.png"
        node["checkbox_id"] = "l1"
        node.get = lambda k, d: {
            "alt": "A",
            "caption": "",
            "custom_class": "",
            "size_style": "",
            "gallery_index": 1,
            "gallery_count": 2,
            "gallery_next_target": 'bad" onclick="alert(1)',
        }.get(k, d)
        visit_lightbox_overlay_html(t, node)
        output = "".join(t.body)
        assert 'onclick="alert(1)' not in output
        assert "bad&quot; onclick=&quot;alert(1)" in output


# ---------------------------------------------------------------------------
# TestUriResolution
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

    @pytest.mark.unit
    def test_resolve_output_uri_uses_environment_images(self):
        from lightbox.lightbox import _resolve_output_uri

        builder = Mock()
        builder.images = {}
        builder.imgpath = "_images"
        builder.env.images = {"images/test.png": ({"index"}, "test-hash.png")}
        assert _resolve_output_uri(builder, "images/test.png") == "_images/test-hash.png"

    @pytest.mark.unit
    def test_resolve_output_uri_uses_deduplicated_builder_image(self, tmp_path):
        from lightbox.lightbox import _resolve_output_uri

        image_dir = tmp_path / "images"
        image_dir.mkdir()
        (image_dir / "first.png").write_bytes(b"same image content")
        (image_dir / "second.png").write_bytes(b"same image content")

        builder = Mock()
        builder.images = {"images/second.png": "second.png"}
        builder.imgpath = "_images"
        builder.env.srcdir = str(tmp_path)
        builder.env.images = {
            "images/first.png": ({"index"}, "first.png"),
            "images/second.png": ({"index"}, "second.png"),
        }

        assert _resolve_output_uri(builder, "images/first.png") == "_images/second.png"


# ---------------------------------------------------------------------------
# TestMissingImageCopy
# ---------------------------------------------------------------------------


class TestMissingImageCopy:
    """Test build-finished copying for transformed lightbox image assets."""

    @pytest.mark.unit
    def test_missing_html_image_targets_finds_only_missing_local_images(self, tmp_path):
        from lightbox.lightbox import _missing_html_image_targets

        outdir = tmp_path / "html"
        image_dir = outdir / "_images"
        image_dir.mkdir(parents=True)
        (image_dir / "present.png").write_bytes(b"present")
        (outdir / "index.html").write_text(
            '<img src="_images/present.png">'
            '<img src="_images/missing.png">'
            '<img src="https://example.invalid/remote.png">'
            '<img src="data:image/png;base64,abc">',
            encoding="utf-8",
        )

        assert _missing_html_image_targets(str(outdir)) == {"missing.png"}

    @pytest.mark.unit
    def test_copy_missing_lightbox_images_copies_referenced_env_image(self, tmp_path):
        from lightbox.lightbox import _copy_missing_lightbox_images

        srcdir = tmp_path / "src"
        outdir = tmp_path / "html"
        source_image = srcdir / "images" / "missing.png"
        source_image.parent.mkdir(parents=True)
        source_image.write_bytes(b"image")
        outdir.mkdir()
        (outdir / "index.html").write_text(
            '<img src="_images/missing.png">',
            encoding="utf-8",
        )

        app = Mock()
        app.builder.format = "html"
        app.builder.imagedir = "_images"
        app.outdir = str(outdir)
        app.env.srcdir = str(srcdir)
        app.env.images = {
            "images/missing.png": ({"index"}, "missing.png"),
        }
        app.env.lightbox_image_uris = set()

        _copy_missing_lightbox_images(app, None)

        assert (outdir / "_images" / "missing.png").read_bytes() == b"image"

    @pytest.mark.unit
    def test_copy_missing_lightbox_images_blocks_source_traversal(self, tmp_path):
        from lightbox.lightbox import _copy_missing_lightbox_images

        srcdir = tmp_path / "src"
        outside = tmp_path / "outside.png"
        outdir = tmp_path / "html"
        srcdir.mkdir()
        outside.write_bytes(b"outside")
        outdir.mkdir()
        (outdir / "index.html").write_text(
            '<img src="_images/outside.png">',
            encoding="utf-8",
        )

        app = Mock()
        app.builder.format = "html"
        app.builder.imagedir = "_images"
        app.outdir = str(outdir)
        app.env.srcdir = str(srcdir)
        app.env.images = {
            "../outside.png": ({"index"}, "outside.png"),
        }
        app.env.lightbox_image_uris = set()

        _copy_missing_lightbox_images(app, None)

        assert not (outdir / "_images" / "outside.png").exists()


# ---------------------------------------------------------------------------
# TestSphinxEnvironmentMetadata
# ---------------------------------------------------------------------------


class TestSphinxEnvironmentMetadata:
    """Test Sphinx environment metadata used for parallel-safe reads."""

    @pytest.mark.unit
    def test_register_lightbox_image_tracks_uris_by_doc(self):
        from lightbox.lightbox import _register_lightbox_image

        env = Mock()

        _register_lightbox_image(env, "index", "/images/example.png")

        assert env.lightbox_image_uris_by_doc == {"index": {"images/example.png"}}

    @pytest.mark.unit
    def test_purge_lightbox_images_removes_only_target_doc(self):
        from lightbox.lightbox import _purge_lightbox_images

        env = Mock()
        env.lightbox_image_uris_by_doc = {
            "index": {"images/index.png"},
            "usage": {"images/usage.png"},
        }

        _purge_lightbox_images(Mock(), env, "index")

        assert env.lightbox_image_uris_by_doc == {"usage": {"images/usage.png"}}

    @pytest.mark.unit
    def test_merge_lightbox_images_merges_requested_parallel_docs(self):
        from lightbox.lightbox import _merge_lightbox_images

        env = Mock()
        env.lightbox_image_uris_by_doc = {"index": {"images/index.png"}}
        other = Mock()
        other.lightbox_image_uris_by_doc = {
            "usage": {"images/usage.png"},
            "ignored": {"images/ignored.png"},
        }

        _merge_lightbox_images(Mock(), env, {"usage"}, other)

        assert env.lightbox_image_uris_by_doc == {
            "index": {"images/index.png"},
            "usage": {"images/usage.png"},
        }

    @pytest.mark.unit
    def test_setup_declares_sphinx_metadata_and_parallel_events(self):
        from lightbox.lightbox import __version__, setup

        app = Mock()
        app.config.html_static_path = []

        metadata = setup(app)

        app.require_sphinx.assert_called_once_with("7.0")
        assert metadata["version"] == __version__
        assert metadata["env_version"] == 2
        assert metadata["parallel_read_safe"] is True
        assert metadata["parallel_write_safe"] is True
        connected_events = [call.args[0] for call in app.connect.call_args_list]
        assert "env-purge-doc" in connected_events
        assert "env-merge-info" in connected_events
        app.add_post_transform.assert_called_once()
        assert app.add_post_transform.call_args.args[0].__name__ == "LightboxImageTransform"

    @pytest.mark.unit
    def test_runtime_version_matches_distribution_metadata(self):
        from importlib.metadata import version

        from lightbox.lightbox import __version__

        assert __version__ == version("sphinx-lightbox")


# ---------------------------------------------------------------------------
# TestStaticPathRegistration
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

    @pytest.mark.unit
    def test_builder_inited_is_idempotent(self):
        """Calling _builder_inited twice should not duplicate the static path."""
        from lightbox.lightbox import _builder_inited

        app = Mock()
        app.config.html_static_path = []

        with patch("os.path.dirname", return_value="/tmp/src"):
            _builder_inited(app)
            _builder_inited(app)

        assert len(app.config.html_static_path) == 1


# ---------------------------------------------------------------------------
# TestImageDimensionCalculation
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


# ---------------------------------------------------------------------------
# TestLatexPackageRegistration (1 test)
# ---------------------------------------------------------------------------


class TestLatexPackageRegistration:
    """Test that the extension declares its LaTeX package dependency."""

    @pytest.mark.unit
    def test_setup_registers_adjustbox_package(self):
        """setup() should call app.add_latex_package('adjustbox')."""
        from unittest.mock import Mock

        from lightbox.lightbox import setup

        app = Mock()
        app.config.html_static_path = []

        setup(app)

        app.add_latex_package.assert_any_call("adjustbox")
