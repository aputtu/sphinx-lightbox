# This file is part of the MiGrid Sphinx Extension for Sphinx documentation.
# SPDX-License-Identifier: GPL-3.0-or-later

"""
Lightbox extension for Sphinx.
Provides a .. lightbox:: directive that renders click-to-enlarge images
in HTML output using a CSS checkbox-toggle mechanism, with lightweight
JavaScript progressive enhancement for strict accessibility (keyboard navigation).
"""

from __future__ import annotations

import os
import posixpath
from html import escape as html_escape
from typing import Any

from docutils import nodes
from docutils.parsers.rst import directives
from sphinx.application import Sphinx
from sphinx.util import logging
from sphinx.util.docutils import SphinxDirective
from sphinx.util.texescape import escape as latex_escape

logger = logging.getLogger(__name__)

__version__ = "2.0.10"


class LightboxContainer(nodes.General, nodes.Element):
    """Outer wrapper grouping the trigger thumbnail and the overlay."""


class LightboxTrigger(nodes.General, nodes.Element):
    """Thumbnail image that opens the lightbox when clicked."""


class LightboxOverlay(nodes.General, nodes.Element):
    """Full-size image overlay with caption and close control."""


class LightboxCollector(nodes.General, nodes.Element):
    """
    Invisible wrapper around the hidden collector image node.
    Exists solely to trigger Sphinx's ImageCollector during the read phase. [cite: 32]
    """


# ---------------------------------------------------------------------------
# Shared Helpers
# ---------------------------------------------------------------------------


def skip_departure(self: Any, node: nodes.Node) -> None:
    """Empty departure function to satisfy Sphinx requirements."""
    pass  # pragma: no cover

def visit_noop(self: Any, node: nodes.Node) -> None:
    """Do-nothing visit function."""
    pass  # pragma: no cover

def _visit_skip(self: Any, node: nodes.Node) -> None:
    """Visit function that skips the node and all its children."""
    raise nodes.SkipNode  # pragma: no cover


def _resolve_output_uri(builder: Any, uri: str) -> str:
    """Resolve a source-relative image URI to its HTML output path."""
    if hasattr(builder, "images") and uri in builder.images:
        imgpath = getattr(builder, "imgpath", "_images")
        return f"{imgpath}/{builder.images[uri]}"
    return uri


def _builder_inited(app: Sphinx) -> None:
    """Register the extension's static path natively with Sphinx."""
    static_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "static"))
    app.config.html_static_path.append(static_dir)


# ---------------------------------------------------------------------------
# HTML visitors
# ---------------------------------------------------------------------------


def visit_lightbox_container_html(self: Any, node: LightboxContainer) -> None:
    self.body.append('<div class="lightbox-container">\n')


def depart_lightbox_container_html(self: Any, node: LightboxContainer) -> None:
    self.body.append("</div>\n")


def visit_lightbox_trigger_html(self: Any, node: LightboxTrigger) -> None:
    # ISSUE #1: Escape checkbox_id
    checkbox_id = html_escape(node["checkbox_id"], quote=True)
    image_uri = html_escape(_resolve_output_uri(self.builder, node["uri"]), quote=True)
    alt_text = html_escape(node.get("alt", ""), quote=True)
    # ISSUE #3: Escape thumbnail_width
    thumbnail_width = html_escape(node.get("thumbnail_width", "100%"), quote=True)
    custom_class = html_escape(node.get("custom_class", ""), quote=True)

    # FIXED: custom_class defined before cls assignment
    cls = f"lightbox-trigger {custom_class}".strip()
    self.body.append(
        f'<label for="{checkbox_id}" class="lightbox-trigger-label" '
        f'tabindex="0" role="button" '
        f'aria-label="Enlarge image: {alt_text}">\n'
        f'  <img src="{image_uri}" alt="{alt_text}" class="{cls}" '
        f'style="width: {thumbnail_width};">\n'
        f"</label>\n"
    )


def depart_lightbox_trigger_html(self: Any, node: LightboxTrigger) -> None:
    pass


def visit_lightbox_overlay_html(self: Any, node: LightboxOverlay) -> None:
    # ISSUE #1: Escape checkbox_id
    checkbox_id = html_escape(node["checkbox_id"], quote=True)
    image_uri = html_escape(_resolve_output_uri(self.builder, node["uri"]), quote=True)
    alt_text = html_escape(node.get("alt", ""), quote=True)
    caption = html_escape(node.get("caption", ""), quote=True)
    # ISSUE #2: Escape size_style
    size_style = html_escape(node.get("size_style", ""), quote=True)
    custom_class = html_escape(node.get("custom_class", ""), quote=True)

    cls = custom_class.strip() if custom_class else ""
    self.body.append(
        f'<input type="checkbox" id="{checkbox_id}" '
        f'class="lightbox-toggle" aria-hidden="true" tabindex="-1">\n'
        f'<div class="lightbox-overlay" role="dialog" aria-modal="true" '
        f'aria-label="{alt_text}">\n'
        f'  <label for="{checkbox_id}" class="lightbox-close" '
        f'tabindex="0" role="button" aria-label="Close lightbox">'
        f"&times;</label>\n"
        '  <div class="lightbox-content">\n'
    )

    img_class = f' class="{cls}"' if cls else ""
    self.body.append(
        f'    <img src="{image_uri}" alt="{alt_text}"{img_class} '
        f'style="{size_style}">\n'
    )

    if caption:
        self.body.append(f'    <p class="lightbox-caption">{caption}</p>\n')

    self.body.append(
        "  </div>\n"
        f'  <label for="{checkbox_id}" class="lightbox-backdrop-close" '
        f'aria-hidden="true"></label>\n'
        "</div>\n"
    )


def depart_lightbox_overlay_html(self: Any, node: LightboxOverlay) -> None:
    pass


# ---------------------------------------------------------------------------
# LaTeX visitors
# ---------------------------------------------------------------------------


def visit_lightbox_container_latex(self: Any, node: LightboxContainer) -> None:
    uri = node.get("uri")
    if hasattr(self.builder, "images") and uri in self.builder.images:
        image_file = self.builder.images[uri]
    else:
        image_file = os.path.basename(uri)

    latex_width = node.get("latex_width", "0.95")
    caption = node.get("caption", "")

    self.body.append("\n\\begin{figure}[htbp]\n\\centering\n")
    self.body.append(
        f"\\adjustbox{{max width={latex_width}\\linewidth}}{{\\includegraphics{{{image_file}}}}}\n"
    )
    if caption:
        escaped_caption = latex_escape(caption)
        self.body.append(f"\\caption{{{escaped_caption}}}\n")
    self.body.append("\\end{figure}\n")

    raise nodes.SkipNode


# ---------------------------------------------------------------------------
# Directive
# ---------------------------------------------------------------------------


class LightboxDirective(SphinxDirective):
    has_content = False
    required_arguments = 1
    optional_arguments = 0
    final_argument_whitespace = True
    option_spec = {
        "alt": directives.unchanged,
        "caption": directives.unchanged,
        "percentage": directives.positive_int_list,
        "class": directives.unchanged,
    }

    def run(self) -> list[nodes.Node]:
        env = self.env
        raw_path = self.arguments[0].strip()
        alt_text = self.options.get("alt", "")

        if raw_path.startswith(("http://", "https://")):
            return [nodes.image(uri=raw_path, alt=alt_text)]

        image_path = self._resolve_image_path(raw_path)
        if image_path is None:
            return []

        env.images.add_file(env.docname, image_path)

        abs_fs_path = os.path.normpath(os.path.join(env.srcdir, image_path.replace("/", os.sep)))
        aspect_ratio = 1.0
        try:
            from sphinx.util.images import get_image_size
            width, height = get_image_size(abs_fs_path)
            if width and height:
                aspect_ratio = width / height
        except Exception as e:
            logger.warning(
                f"Could not calculate image dimensions for '{raw_path}': {e}. "
                "Falling back to 1:1 aspect ratio.",
                location=(env.docname, self.lineno),
                type="lightbox",
                subtype="image_dimensions",
            )

        caption = self.options.get("caption", "")
        percentages = self.options.get("percentage", [])
        custom_class = self.options.get("class", "")

        thumbnail_width = f"{percentages[0]}%" if percentages else "100%"
        lightbox_pct = percentages[1] if len(percentages) > 1 else 95
        latex_width = f"{lightbox_pct / 100:.2f}"

        safe_docname = env.docname.replace("/", "-")
        checkbox_id = f"lightbox-{safe_docname}-{env.new_serialno('lightbox')}"

        container = LightboxContainer()
        container["uri"] = image_path
        container["caption"] = caption
        container["latex_width"] = latex_width
        container.source, container.line = self.state_machine.get_source_and_line(self.lineno)

        trigger = LightboxTrigger()
        trigger["uri"] = image_path
        trigger["alt"] = alt_text
        trigger["thumbnail_width"] = thumbnail_width
        trigger["custom_class"] = custom_class
        trigger["checkbox_id"] = checkbox_id

        overlay = LightboxOverlay()
        overlay["uri"] = image_path
        overlay["alt"] = alt_text
        overlay["caption"] = caption
        overlay["size_style"] = (
            f"width: min({lightbox_pct}vw, calc({lightbox_pct}vh * {aspect_ratio:.4f}));"
            f"height: min({lightbox_pct}vh, calc({lightbox_pct}vw / {aspect_ratio:.4f}));"
        )
        overlay["custom_class"] = custom_class
        overlay["checkbox_id"] = checkbox_id

        container += trigger
        container += overlay

        hidden_img = nodes.image(uri=f"/{image_path}", alt=alt_text)
        hidden_img["candidates"] = {"*": image_path}
        collector = LightboxCollector()
        collector += hidden_img
        container += collector

        return [container]

    def _resolve_image_path(self, raw_path: str) -> str | None:
        env = self.env
        if raw_path.startswith("/"):
            rel_to_source = raw_path.lstrip("/")
        else:
            current_dir = posixpath.dirname(env.docname)
            rel_to_source = posixpath.normpath(posixpath.join(current_dir, raw_path))

        # Use abspath to fully resolve the generated path
        abs_fs_path = os.path.abspath(os.path.join(env.srcdir, rel_to_source.replace("/", os.sep)))
        safe_srcdir = os.path.abspath(env.srcdir)

        # Compare the common path to ensure the target is strictly inside srcdir
        try:
            if os.path.commonpath([safe_srcdir, abs_fs_path]) != safe_srcdir:
                raise ValueError
        except ValueError:
            logger.warning(
                f"Lightbox image path traverses outside source directory: {raw_path}",
                location=(env.docname, self.lineno),
                type="lightbox",
                subtype="path_traversal",
            )
            return None

        if not os.path.isfile(abs_fs_path):
            logger.warning(
                f"Lightbox image not found: {abs_fs_path}",
                location=(env.docname, self.lineno),
                type="lightbox",
                subtype="image_not_found",
            )
            return None

        return rel_to_source


# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------


def setup(app: Sphinx) -> dict[str, Any]:  # pragma: no cover
    app.add_node(
        LightboxContainer,
        html=(visit_lightbox_container_html, depart_lightbox_container_html),
        latex=(visit_lightbox_container_latex, skip_departure),
        epub=(visit_noop, skip_departure),
        text=(visit_noop, skip_departure),
        man=(visit_noop, skip_departure),
        texinfo=(visit_noop, skip_departure),
    )
    app.add_node(
        LightboxTrigger,
        html=(visit_lightbox_trigger_html, depart_lightbox_trigger_html),
        latex=(visit_noop, skip_departure),
        epub=(visit_noop, skip_departure),
        text=(visit_noop, skip_departure),
        man=(visit_noop, skip_departure),
        texinfo=(visit_noop, skip_departure),
    )
    app.add_node(
        LightboxOverlay,
        html=(visit_lightbox_overlay_html, depart_lightbox_overlay_html),
        latex=(visit_noop, skip_departure),
        epub=(visit_noop, skip_departure),
        text=(visit_noop, skip_departure),
        man=(visit_noop, skip_departure),
        texinfo=(visit_noop, skip_departure),
    )
    app.add_node(
        LightboxCollector,
        html=(_visit_skip, skip_departure),
        latex=(visit_noop, skip_departure),
        epub=(visit_noop, skip_departure),
        text=(visit_noop, skip_departure),
        man=(visit_noop, skip_departure),
        texinfo=(visit_noop, skip_departure),
    )

    app.add_directive("lightbox", LightboxDirective)
    app.connect("builder-inited", _builder_inited)
    app.add_css_file("lightbox.css")
    app.add_js_file("lightbox.js")

    return {
        "version": __version__,
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
