# SPDX-License-Identifier: GPL-3.0-or-later

"""
Lightbox extension for Sphinx.
Enhances standard Sphinx image and figure nodes with click-to-enlarge HTML
overlays, optional per-document gallery navigation, and lightweight JavaScript
progressive enhancement for keyboard accessibility.

The legacy ``.. lightbox::`` directive remains available for 0.5.x
compatibility; standard ``image`` and ``figure`` directives are the public
authoring interface.
"""

from __future__ import annotations

import hashlib
import os
import posixpath
import re
import shutil
from html import escape as html_escape
from typing import Any, cast

from docutils import nodes
from docutils.parsers.rst import directives
from sphinx.application import Sphinx
from sphinx.transforms.post_transforms import SphinxPostTransform
from sphinx.util import logging
from sphinx.util.docutils import SphinxDirective
from sphinx.util.texescape import escape as latex_escape
from sphinx.util.typing import ExtensionMetadata

logger = logging.getLogger(__name__)

__version__ = "0.5.1"


class LightboxContainer(nodes.General, nodes.Element):
    """Outer wrapper grouping the trigger thumbnail and the overlay."""


class LightboxTrigger(nodes.General, nodes.Element):
    """Thumbnail image that opens the lightbox when clicked."""


class LightboxOverlay(nodes.General, nodes.Element):
    """Full-size image overlay with caption and close control."""


class LightboxCollector(nodes.General, nodes.Element):
    """
    Wrapper around the collector and fallback image node.
    Triggers Sphinx's ImageCollector for HTML builds and supplies the plain
    image fallback for non-HTML, non-LaTeX builders.
    """


_LIGHTBOX_CLASS = "lightbox"
_NO_LIGHTBOX_CLASS = "no-lightbox"
_POLICIES = {"explicit", "all", "none"}
_GALLERY_MODES = {"document", "none"}
_LIGHTBOX_ENV_VERSION = 2
_SAFE_ID_PART_RE = re.compile(r"[^A-Za-z0-9_.:-]+")
_URI_SCHEME_RE = re.compile(r"^[a-z][a-z0-9+.-]*:")
_SAFE_CSS_WIDTH_RE = re.compile(r"^(?:auto|0|[0-9]+(?:\.[0-9]+)?(?:%|px|em|rem|vw|vh|vmin|vmax)?)$")
_SAFE_STYLE_CHARS_RE = re.compile(r"^[0-9A-Za-z\s.:;,%()+*/-]+$")
_UNSAFE_CSS_TOKENS = ("url(", "expression(", "@import", "\\")


# ---------------------------------------------------------------------------
# Shared Helpers
# ---------------------------------------------------------------------------


def skip_departure(self: Any, node: nodes.Node) -> None:
    """Empty departure function to satisfy Sphinx requirements."""
    pass


def visit_noop(self: Any, node: nodes.Node) -> None:
    """Do-nothing visit function."""
    pass


def _visit_skip(self: Any, node: nodes.Node) -> None:
    """Visit function that skips the node and all its children."""
    raise nodes.SkipNode


def _is_remote_or_data_uri(uri: str) -> bool:
    """Return whether an image URI should stay outside lightbox processing."""
    normalized = uri.strip().lower()
    return normalized.startswith("//") or _URI_SCHEME_RE.match(normalized) is not None


def _is_lightbox_html_builder(builder: Any) -> bool:
    """Return whether a builder supports the interactive lightbox output."""
    # EPUB inherits Sphinx's HTML format marker, but its self-contained output
    # must use the collector image fallback rather than interactive overlays.
    return getattr(builder, "format", "") == "html" and getattr(builder, "name", "") != "epub"


def _safe_html_id_part(value: str, fallback: str = "document") -> str:
    """Return a conservative string for generated HTML id fragments."""
    safe_value = _SAFE_ID_PART_RE.sub("-", value).strip("-")
    return safe_value or fallback


def _accessible_image_name(alt_text: str, uri: str) -> str:
    """Return explicit alt text or a readable fallback derived from the filename."""
    if alt_text.strip():
        return alt_text.strip()
    stem = posixpath.splitext(posixpath.basename(uri.rstrip("/")))[0]
    return re.sub(r"[-_]+", " ", stem).strip() or "Image"


def _source_image_path(srcdir: str, uri: str) -> str | None:
    """Resolve an image URI to an absolute source path confined to srcdir."""
    if not srcdir or _is_remote_or_data_uri(uri):
        return None

    rel_uri = uri.lstrip("/")
    image_path = os.path.realpath(
        os.path.abspath(os.path.join(srcdir, rel_uri.replace("/", os.sep)))
    )
    safe_srcdir = os.path.realpath(os.path.abspath(srcdir))
    try:
        if os.path.commonpath([safe_srcdir, image_path]) != safe_srcdir:
            return None
    except ValueError:
        return None
    return image_path


def _sanitize_css_width(width: str) -> str:
    """Return a safe CSS width value for inline thumbnail sizing."""
    width = width.strip()
    if _SAFE_CSS_WIDTH_RE.fullmatch(width):
        return width
    logger.warning(
        f"Invalid lightbox thumbnail width {width!r}; falling back to '100%'.",
        type="lightbox",
        subtype="invalid_style",
    )
    return "100%"


def _sanitize_style_attr(style: str) -> str:
    """Return a defensive inline style value for internally generated styles."""
    style = style.strip()
    lowered = style.lower()
    if _SAFE_STYLE_CHARS_RE.fullmatch(style) and not any(
        token in lowered for token in _UNSAFE_CSS_TOKENS
    ):
        return style
    logger.warning(
        "Invalid lightbox inline style suppressed.",
        type="lightbox",
        subtype="invalid_style",
    )
    return ""


def _resolve_output_uri(builder: Any, uri: str) -> str:
    """Resolve a source-relative image URI to its HTML output path."""
    if hasattr(builder, "images") and _has_image_uri(builder.images, uri):
        imgpath = getattr(builder, "imgpath", "_images")
        output_uri = builder.images[uri]
        if isinstance(output_uri, tuple):
            output_uri = output_uri[1]
        return f"{imgpath}/{output_uri}"

    duplicate_uri = _resolve_duplicate_output_uri(builder, uri)
    if duplicate_uri:
        imgpath = getattr(builder, "imgpath", "_images")
        return f"{imgpath}/{duplicate_uri}"

    env = getattr(builder, "env", None)
    env_images = getattr(env, "images", None)
    if _has_image_uri(env_images, uri):
        imgpath = getattr(builder, "imgpath", "_images")
        output_uri = cast(Any, env_images)[uri]
        if isinstance(output_uri, tuple):
            output_uri = output_uri[1]
        return f"{imgpath}/{output_uri}"
    return uri


def _resolve_duplicate_output_uri(builder: Any, uri: str) -> str:
    """Return Sphinx's copied filename when identical source images are deduped."""
    env = getattr(builder, "env", None)
    env_images = getattr(env, "images", None)
    builder_images = getattr(builder, "images", None)
    srcdir = getattr(env, "srcdir", getattr(builder, "srcdir", ""))
    env_image_items = getattr(env_images, "items", None)
    if not srcdir or not builder_images or not callable(env_image_items):
        return ""

    source_digest = _image_digest(srcdir, uri)
    if source_digest is None:
        return ""

    for candidate_uri, _target in env_image_items():
        if candidate_uri == uri or not _has_image_uri(builder_images, candidate_uri):
            continue
        if _image_digest(srcdir, candidate_uri) != source_digest:
            continue
        output_uri = builder_images[candidate_uri]
        if isinstance(output_uri, tuple):
            output_uri = output_uri[1]
        return str(output_uri)

    return ""


def _image_digest(srcdir: str, uri: str) -> str | None:
    """Return a digest for a source image URI, constrained to the source tree."""
    image_path = _source_image_path(srcdir, uri)
    if image_path is None:
        return None
    try:
        with open(image_path, "rb") as image_file:
            return hashlib.sha256(image_file.read()).hexdigest()
    except OSError:
        return None


def _has_image_uri(images: Any, uri: str) -> bool:
    """Return whether an image mapping contains a URI, tolerating test mocks."""
    try:
        return uri in images
    except TypeError:
        return False


def _builder_inited(app: Sphinx) -> None:
    """Register the extension's static path natively with Sphinx."""
    static_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "static"))
    if static_dir not in app.config.html_static_path:
        app.config.html_static_path.append(static_dir)


def _lightbox_images_by_doc(env: Any) -> dict[str, set[str]]:
    """Return recorded lightbox image URIs keyed by Sphinx docname."""
    raw_value: Any = getattr(env, "lightbox_image_uris_by_doc", {})
    if not isinstance(raw_value, dict):
        return {}

    image_uris_by_doc: dict[str, set[str]] = {}
    for docname, uris in raw_value.items():
        if not isinstance(docname, str):
            continue
        try:
            image_uris_by_doc[docname] = {str(uri) for uri in uris}
        except TypeError:
            continue
    return image_uris_by_doc


def _all_lightbox_image_uris(env: Any) -> set[str]:
    """Return all lightbox image URIs recorded in the build environment."""
    image_uris: set[str] = set()
    for uris in _lightbox_images_by_doc(env).values():
        image_uris.update(uris)
    return image_uris


def _register_lightbox_image(env: Any, docname: str, uri: str) -> None:
    """Record a source image URI that lightbox HTML directly references."""
    normalized_uri = uri.lstrip("/")
    if not normalized_uri:
        return

    image_uris_by_doc = _lightbox_images_by_doc(env)
    image_uris_by_doc.setdefault(docname, set()).add(normalized_uri)
    env.lightbox_image_uris_by_doc = image_uris_by_doc


def _purge_lightbox_images(app: Sphinx, env: Any, docname: str) -> None:
    """Remove cached lightbox image metadata for a rebuilt or removed document."""
    image_uris_by_doc = _lightbox_images_by_doc(env)
    if docname in image_uris_by_doc:
        del image_uris_by_doc[docname]
        env.lightbox_image_uris_by_doc = image_uris_by_doc


def _merge_lightbox_images(app: Sphinx, env: Any, docnames: set[str], other: Any) -> None:
    """Merge per-document lightbox image metadata from parallel read workers."""
    image_uris_by_doc = _lightbox_images_by_doc(env)
    other_image_uris_by_doc = _lightbox_images_by_doc(other)

    for docname in docnames:
        if docname in other_image_uris_by_doc:
            image_uris_by_doc.setdefault(docname, set()).update(other_image_uris_by_doc[docname])

    env.lightbox_image_uris_by_doc = image_uris_by_doc


def _copy_missing_lightbox_images(app: Sphinx, exception: Exception | None) -> None:
    """Copy lightbox assets that Sphinx skipped after standard image transforms."""
    if exception is not None or not _is_lightbox_html_builder(app.builder):
        return

    image_uris = _all_lightbox_image_uris(app.env)
    env_images = getattr(app.env, "images", None)
    # imagedir, not imgpath: imgpath is relative to the last written document and
    # can escape outdir when joined to it. imagedir is the builder's stable output
    # location, but still enforce containment for custom HTML builders.
    outdir = os.path.realpath(os.path.abspath(app.outdir))
    image_dir = os.path.realpath(
        os.path.abspath(os.path.join(outdir, getattr(app.builder, "imagedir", "_images")))
    )
    try:
        if os.path.commonpath([outdir, image_dir]) != outdir:
            logger.warning(
                f"Refusing to copy lightbox images outside the output directory: '{image_dir}'",
                type="lightbox",
                subtype="unsafe_image_dir",
            )
            return
    except ValueError:
        return
    os.makedirs(image_dir, exist_ok=True)
    missing_targets = _missing_html_image_targets(app.outdir)

    for uri, output_uri in getattr(env_images, "items", lambda: [])():
        if isinstance(output_uri, tuple):
            output_uri = output_uri[1]
        if uri not in image_uris and str(output_uri) not in missing_targets:
            continue
        if not _has_image_uri(env_images, uri):
            continue
        source_path = _source_image_path(app.env.srcdir, uri)
        if source_path is None:
            continue
        target_filename = os.path.basename(str(output_uri))
        if not target_filename:
            continue
        target_path = os.path.realpath(os.path.abspath(os.path.join(image_dir, target_filename)))
        try:
            if os.path.commonpath([image_dir, target_path]) != image_dir:
                continue
        except ValueError:
            continue
        if os.path.exists(target_path):
            continue
        try:
            shutil.copyfile(source_path, target_path)
        except OSError as exc:
            logger.warning(
                f"Could not copy lightbox image '{source_path}' to '{target_path}': {exc}",
                type="lightbox",
                subtype="copy_image",
            )


def _missing_html_image_targets(outdir: str) -> set[str]:
    """Return image filenames referenced by HTML but absent from the output tree."""
    missing_targets: set[str] = set()
    image_src = re.compile(r'<img\b[^>]*\bsrc="([^"]+)"')
    for root, _dirs, files in os.walk(outdir):
        for filename in files:
            if not filename.endswith(".html"):
                continue
            html_path = os.path.join(root, filename)
            try:
                with open(html_path, encoding="utf-8") as html_file:
                    html = html_file.read()
            except OSError:
                continue
            for match in image_src.finditer(html):
                src = match.group(1).split("#", 1)[0].split("?", 1)[0]
                if _is_remote_or_data_uri(src):
                    continue
                target_path = os.path.abspath(os.path.join(root, src))
                if not os.path.exists(target_path):
                    missing_targets.add(os.path.basename(target_path))
    return missing_targets


def _figure_child_text(image: nodes.image, node_type: type[nodes.Element]) -> str:
    """Return plain text from a specific child type on the image's figure."""
    if not isinstance(image.parent, nodes.figure):
        return ""
    for child in image.parent:
        if isinstance(child, node_type):
            return child.astext()
    return ""


def _image_classes(app: Sphinx, image: nodes.image) -> str:
    """Return user classes, excluding lightbox control classes."""
    default_class = cast(str, app.config.lightbox_default_class).strip()
    classes = cast(list[str], image.get("classes", []))
    image_classes = [cls for cls in classes if cls not in {_LIGHTBOX_CLASS, _NO_LIGHTBOX_CLASS}]
    return " ".join([default_class, *image_classes]).strip()


def _policy(app: Sphinx, config_name: str) -> str:
    """Return a validated image/figure transform policy from Sphinx config."""
    policy = cast(str, getattr(app.config, config_name)).lower()
    if policy not in _POLICIES:
        logger.warning(
            f"Invalid {config_name!s} value {policy!r}; expected one of "
            "'explicit', 'all', or 'none'. Falling back to 'explicit'.",
            type="lightbox",
            subtype="invalid_config",
        )
        return "explicit"
    return policy


def _gallery_mode(app: Sphinx) -> str:
    """Return a validated gallery mode from Sphinx config."""
    mode = cast(str, app.config.lightbox_gallery).lower()
    if mode not in _GALLERY_MODES:
        logger.warning(
            f"Invalid lightbox_gallery value {mode!r}; expected 'document' or "
            "'none'. Falling back to 'document'.",
            type="lightbox",
            subtype="invalid_config",
        )
        return "document"
    return mode


def _is_transform_candidate(app: Sphinx, image: nodes.image) -> bool:
    """Decide whether a standard image node should be converted to a lightbox."""
    uri = image.get("uri", "")
    if not uri or _is_remote_or_data_uri(uri):
        return False

    classes = cast(list[str], image.get("classes", []))
    if _NO_LIGHTBOX_CLASS in classes:
        return False
    if isinstance(image.parent, (nodes.reference, nodes.TextElement, LightboxContainer)):
        return False
    ancestor = image.parent
    while ancestor is not None:
        if isinstance(ancestor, LightboxContainer):
            return False
        ancestor = ancestor.parent

    config_name = (
        "lightbox_figures" if isinstance(image.parent, nodes.figure) else "lightbox_images"
    )
    policy = _policy(app, config_name)
    if policy == "explicit" and app.config.lightbox_all_images:
        policy = "all"

    if policy == "none":
        return False
    if policy == "all":
        return True
    return _LIGHTBOX_CLASS in classes


def _container_checkbox_id(container: LightboxContainer) -> str:
    """Return the checkbox id for a lightbox container."""
    for child in container:
        if isinstance(child, (LightboxTrigger, LightboxOverlay)) and "checkbox_id" in child:
            return cast(str, child["checkbox_id"])
    return ""


def _set_container_checkbox_id(container: LightboxContainer, checkbox_id: str) -> None:
    """Set one checkbox id on every control node in a lightbox container."""
    for child in container:
        if isinstance(child, (LightboxTrigger, LightboxOverlay)):
            child["checkbox_id"] = checkbox_id


def _overlay_for_container(container: LightboxContainer) -> LightboxOverlay | None:
    """Return the overlay child for a lightbox container."""
    for child in container:
        if isinstance(child, LightboxOverlay):
            return child
    return None


def _clear_gallery_metadata(overlay: LightboxOverlay) -> None:
    """Remove gallery attributes so disabled or single-item galleries render plainly."""
    for key in (
        "gallery_id",
        "gallery_index",
        "gallery_count",
        "gallery_prev_target",
        "gallery_next_target",
    ):
        if key in overlay:
            del overlay[key]


def _collector_for_image(uri: str, alt_text: str) -> LightboxCollector:
    """Return an image node collected for HTML and rendered by fallback builders."""
    collector_uri = uri if uri.startswith("/") else f"/{uri}"
    candidate_uri = uri.lstrip("/")
    fallback_img = nodes.image(uri=collector_uri, alt=alt_text)
    fallback_img["candidates"] = {"*": candidate_uri}
    collector = LightboxCollector()
    collector += fallback_img
    return collector


def assign_lightbox_gallery(app: Sphinx, doctree: nodes.document, docname: str) -> None:
    """Assign per-document gallery metadata to lightbox overlays."""
    containers = [
        container
        for container in doctree.findall(LightboxContainer)
        if _overlay_for_container(container) is not None
    ]
    for container in containers:
        overlay = _overlay_for_container(container)
        if overlay is not None:
            _clear_gallery_metadata(overlay)

    if _gallery_mode(app) == "none" or len(containers) <= 1:
        return

    safe_docname = _safe_html_id_part(docname)
    gallery_id = f"lightbox-gallery-{safe_docname}"
    gallery_wrap = bool(app.config.lightbox_gallery_wrap)

    for index, container in enumerate(containers):
        overlay = _overlay_for_container(container)
        if overlay is None:
            continue

        overlay["gallery_id"] = gallery_id
        overlay["gallery_index"] = index + 1
        overlay["gallery_count"] = len(containers)

        previous_container = None
        next_container = None
        if index > 0:
            previous_container = containers[index - 1]
        elif gallery_wrap:
            previous_container = containers[-1]

        if index < len(containers) - 1:
            next_container = containers[index + 1]
        elif gallery_wrap:
            next_container = containers[0]

        if previous_container is not None:
            overlay["gallery_prev_target"] = _container_checkbox_id(previous_container)
        if next_container is not None:
            overlay["gallery_next_target"] = _container_checkbox_id(next_container)


def transform_lightbox_images(app: Sphinx, doctree: nodes.document, docname: str) -> None:
    """Convert standard image/figure nodes with class ``lightbox`` for HTML builds."""
    if not _is_lightbox_html_builder(app.builder):
        return

    safe_docname = _safe_html_id_part(docname)
    checkbox_prefix = f"lightbox-{safe_docname}-"
    used_html_ids: set[str] = set()
    for element in doctree.findall(nodes.Element):
        used_html_ids.update(cast(list[str], element.get("ids", [])))
    next_serial = 1

    def allocate_checkbox_id() -> str:
        nonlocal next_serial
        checkbox_id = f"{checkbox_prefix}{next_serial}"
        while checkbox_id in used_html_ids:
            next_serial += 1
            checkbox_id = f"{checkbox_prefix}{next_serial}"
        used_html_ids.add(checkbox_id)
        next_serial += 1
        return checkbox_id

    # Compatibility-directive IDs are assigned during parsing, before later
    # ``:name:`` targets are known. Normalize them here, when the complete
    # document is available, so they cannot create duplicate HTML ids.
    for container in doctree.findall(LightboxContainer):
        checkbox_id = _container_checkbox_id(container)
        if checkbox_id and checkbox_id not in used_html_ids:
            used_html_ids.add(checkbox_id)
        else:
            _set_container_checkbox_id(container, allocate_checkbox_id())

    for image in list(doctree.findall(nodes.image)):
        if not _is_transform_candidate(app, image):
            continue

        checkbox_id = allocate_checkbox_id()

        uri = image.get("uri", "")
        alt_text = image.get("alt", "")
        custom_class = _image_classes(app, image)
        caption = _figure_child_text(image, nodes.caption)
        legend = _figure_child_text(image, nodes.legend)

        container = LightboxContainer()
        if image.get("align"):
            container["align"] = image["align"]
        container.source = image.source
        container.line = image.line

        trigger = LightboxTrigger()
        trigger["uri"] = uri
        trigger["alt"] = alt_text
        trigger["custom_class"] = custom_class
        trigger["checkbox_id"] = checkbox_id

        # Let Sphinx render the thumbnail's native image node. This preserves
        # built-in image/figure options such as width, height, scale, loading,
        # name, and their builder-specific behavior instead of duplicating a
        # changing subset in the extension's HTML visitor. The trigger's
        # accessible name carries the original alt text, so its child image is
        # deliberately decorative.
        thumbnail = image.deepcopy()
        thumbnail["alt"] = ""
        # Sphinx normally wraps resized images in a link to the source file.
        # The lightbox trigger already provides that enlargement behavior, so
        # suppress the nested link while preserving all sizing semantics.
        thumbnail["classes"] = ["lightbox-trigger", "no-scaled-link", *custom_class.split()]
        trigger += thumbnail

        overlay = LightboxOverlay()
        overlay["uri"] = uri
        overlay["alt"] = alt_text
        overlay["caption"] = caption
        overlay["legend"] = legend
        overlay["size_style"] = ""
        overlay["custom_class"] = custom_class
        overlay["checkbox_id"] = checkbox_id

        container += trigger
        container += overlay
        image.replace_self(container)

    assign_lightbox_gallery(app, doctree, docname)


class LightboxImageTransform(SphinxPostTransform):
    """Add HTML lightboxes after Sphinx has filtered ``only`` branches."""

    default_priority = 60
    formats = ("html",)

    def run(self, **_kwargs: Any) -> None:
        # Sphinx 8 introduced ``current_document`` and Sphinx 9 moved the
        # application reference from ``env.app`` to ``env._app``. Support the
        # complete declared Sphinx 7-9 range without invoking deprecated
        # compatibility properties on newer versions.
        app = getattr(self.env, "_app", None)
        if app is None:
            app = self.env.app
        current_document = getattr(self.env, "current_document", None)
        docname = current_document.docname if current_document is not None else self.env.docname
        transform_lightbox_images(
            app,
            self.document,
            docname,
        )


# ---------------------------------------------------------------------------
# HTML visitors
# ---------------------------------------------------------------------------


def visit_lightbox_container_html(self: Any, node: LightboxContainer) -> None:
    classes = ["lightbox-container"]
    if node.get("align"):
        classes.append(f"align-{node['align']}")
    class_attr = html_escape(" ".join(classes), quote=True)
    self.body.append(f'<div class="{class_attr}">\n')


def depart_lightbox_container_html(self: Any, node: LightboxContainer) -> None:
    self.body.append("</div>\n")


def visit_lightbox_trigger_html(self: Any, node: LightboxTrigger) -> None:
    checkbox_id = html_escape(node["checkbox_id"], quote=True)
    alt_text = html_escape(_accessible_image_name(node.get("alt", ""), node["uri"]), quote=True)

    self.body.append(
        f'<label for="{checkbox_id}" class="lightbox-trigger-label">\n'
        f'  <span class="lightbox-trigger-control" role="button" tabindex="0" '
        f'data-lightbox-target="{checkbox_id}">\n'
        f'    <span class="lightbox-visually-hidden">Enlarge image: {alt_text}</span>\n'
    )

    # Legacy directive nodes do not contain a native image child. Keep their
    # 0.5.x HTML output working without making that duplicate API prominent.
    has_native_thumbnail = next(node.findall(nodes.image), None) is not None
    if not has_native_thumbnail:
        image_uri = html_escape(_resolve_output_uri(self.builder, node["uri"]), quote=True)
        custom_class = html_escape(node.get("custom_class", ""), quote=True)
        thumbnail_width = html_escape(
            _sanitize_css_width(node.get("thumbnail_width", "100%")), quote=True
        )
        cls = f"lightbox-trigger {custom_class}".strip()
        self.body.append(
            f'    <img src="{image_uri}" alt="" class="{cls}" style="width: {thumbnail_width};">\n'
        )


def depart_lightbox_trigger_html(self: Any, node: LightboxTrigger) -> None:
    self.body.append("  </span>\n</label>\n")


def visit_lightbox_overlay_html(self: Any, node: LightboxOverlay) -> None:
    checkbox_id = html_escape(node["checkbox_id"], quote=True)
    image_uri = html_escape(_resolve_output_uri(self.builder, node["uri"]), quote=True)
    alt_text = html_escape(_accessible_image_name(node.get("alt", ""), node["uri"]), quote=True)
    caption = html_escape(node.get("caption", ""), quote=True)
    legend = html_escape(node.get("legend", ""), quote=True)
    raw_size_style = node.get("size_style", "")
    size_style = (
        html_escape(_sanitize_style_attr(raw_size_style), quote=True) if raw_size_style else ""
    )
    size_attr = f' style="{size_style}"' if size_style else ""
    custom_class = html_escape(node.get("custom_class", ""), quote=True)
    gallery_index = int(node.get("gallery_index", 0))
    gallery_count = int(node.get("gallery_count", 0))
    prev_target = html_escape(node.get("gallery_prev_target", ""), quote=True)
    next_target = html_escape(node.get("gallery_next_target", ""), quote=True)
    prev_label = html_escape(
        f"Previous image in gallery ({gallery_index} of {gallery_count})",
        quote=True,
    )
    next_label = html_escape(
        f"Next image in gallery ({gallery_index} of {gallery_count})",
        quote=True,
    )

    cls = custom_class.strip() if custom_class else ""
    self.body.append(
        f'<input type="checkbox" id="{checkbox_id}" '
        f'class="lightbox-toggle" aria-hidden="true" tabindex="-1">\n'
        f'<div class="lightbox-overlay" role="dialog" aria-modal="true" '
        f'aria-label="{alt_text}">\n'
        f'  <label for="{checkbox_id}" class="lightbox-close-label">'
        f'<span class="lightbox-close" role="button" tabindex="0" '
        f'data-lightbox-target="{checkbox_id}">'
        f'<span aria-hidden="true">&times;</span>'
        f'<span class="lightbox-visually-hidden">Close lightbox</span></span></label>\n'
    )
    if prev_target:
        self.body.append(
            '  <button type="button" '
            'class="lightbox-gallery-control lightbox-gallery-prev" '
            f'data-lightbox-target="{prev_target}" aria-label="{prev_label}">'
            "&lsaquo;</button>\n"
        )
    if next_target:
        self.body.append(
            '  <button type="button" '
            'class="lightbox-gallery-control lightbox-gallery-next" '
            f'data-lightbox-target="{next_target}" aria-label="{next_label}">'
            "&rsaquo;</button>\n"
        )
    self.body.append('  <div class="lightbox-content">\n')

    img_class = f' class="{cls}"' if cls else ""
    self.body.append(f'    <img src="{image_uri}" alt="{alt_text}"{img_class}{size_attr}>\n')

    if caption or legend:
        self.body.append('    <div class="lightbox-text">\n')
        if caption:
            self.body.append(f'      <p class="lightbox-caption">{caption}</p>\n')
        if legend:
            self.body.append(f'      <div class="lightbox-legend">{legend}</div>\n')
        self.body.append("    </div>\n")

    self.body.append(
        f'  </div>\n  <label for="{checkbox_id}" class="lightbox-backdrop-close"></label>\n</div>\n'
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
    """Compatibility directive retained for documents authored with 0.5.x."""

    has_content = False
    required_arguments = 1
    optional_arguments = 0
    final_argument_whitespace = True
    option_spec = {
        "alt": directives.unchanged,
        "caption": directives.unchanged,
        "percentage": directives.positive_int_list,
        "class": directives.unchanged,
        "latex-width": directives.unchanged,
    }

    def run(self) -> list[nodes.Node]:
        env = self.env
        raw_path = self.arguments[0].strip()
        alt_text = self.options.get("alt", "")

        if _is_remote_or_data_uri(raw_path):
            return [nodes.image(uri=raw_path, alt=alt_text)]

        image_path = self._resolve_image_path(raw_path)
        if image_path is None:
            return []

        env.images.add_file(env.docname, image_path)
        _register_lightbox_image(env, env.docname, image_path)

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

        # Optional override: :latex-width: decouples PDF sizing from HTML
        latex_width_override = self.options.get("latex-width")
        if latex_width_override is not None:
            try:
                val = float(latex_width_override)
                if not 0.0 < val <= 1.0:
                    raise ValueError
                latex_width = f"{val:.2f}"
            except ValueError:
                logger.warning(
                    f"Invalid :latex-width: value '{latex_width_override}'. "
                    "Expected a float between 0 and 1 (e.g. 0.8). "
                    "Falling back to percentage-based width.",
                    location=(env.docname, self.lineno),
                    type="lightbox",
                    subtype="invalid_option",
                )

        safe_docname = _safe_html_id_part(env.docname)
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

        container += _collector_for_image(image_path, alt_text)

        return [container]

    def _resolve_image_path(self, raw_path: str) -> str | None:
        env = self.env
        if raw_path.startswith("/"):
            rel_to_source = raw_path.lstrip("/")
        else:
            current_dir = posixpath.dirname(env.docname)
            rel_to_source = posixpath.normpath(posixpath.join(current_dir, raw_path))

        # Resolve symlinks as well as ``..`` components before checking the
        # boundary; otherwise a path inside srcdir can point to an outside file.
        abs_fs_path = os.path.realpath(
            os.path.abspath(os.path.join(env.srcdir, rel_to_source.replace("/", os.sep)))
        )
        safe_srcdir = os.path.realpath(os.path.abspath(env.srcdir))

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


def setup(app: Sphinx) -> ExtensionMetadata:
    app.require_sphinx("7.0")
    app.add_config_value("lightbox_all_images", False, "env", bool)
    app.add_config_value("lightbox_images", "explicit", "env", str)
    app.add_config_value("lightbox_figures", "all", "env", str)
    app.add_config_value("lightbox_default_class", "with-shadow", "env", str)
    app.add_config_value("lightbox_gallery", "document", "env", str)
    app.add_config_value("lightbox_gallery_wrap", False, "env", bool)
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
    app.connect("env-purge-doc", _purge_lightbox_images)
    app.connect("env-merge-info", _merge_lightbox_images)
    app.add_post_transform(LightboxImageTransform)
    app.connect("build-finished", _copy_missing_lightbox_images)
    app.add_css_file("lightbox.css")
    app.add_js_file("lightbox.js")
    app.add_latex_package("adjustbox")

    return {
        "version": __version__,
        "env_version": _LIGHTBOX_ENV_VERSION,
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
