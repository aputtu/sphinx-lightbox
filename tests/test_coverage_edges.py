from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from docutils import nodes

from lightbox import lightbox as lightbox_module
from lightbox.lightbox import (
    LightboxContainer,
    LightboxDirective,
    LightboxOverlay,
    LightboxTrigger,
    _clear_gallery_metadata,
    _container_checkbox_id,
    _copy_missing_lightbox_images,
    _gallery_mode,
    _image_digest,
    _is_transform_candidate,
    _lightbox_images_by_doc,
    _merge_lightbox_images,
    _missing_html_image_targets,
    _overlay_for_container,
    _policy,
    _register_lightbox_image,
    _resolve_duplicate_output_uri,
    _resolve_output_uri,
    _source_image_path,
    _visit_skip,
    assign_lightbox_gallery,
    skip_departure,
    visit_lightbox_container_html,
    visit_noop,
)


def _copy_app(tmp_path: Path, env_images: object, image_uris: set[str] | None = None) -> Mock:
    srcdir = tmp_path / "src"
    outdir = tmp_path / "html"
    srcdir.mkdir()
    outdir.mkdir()

    app = Mock()
    app.builder.format = "html"
    app.builder.imgpath = "_images"
    app.outdir = str(outdir)
    app.env.srcdir = str(srcdir)
    app.env.images = env_images
    app.env.lightbox_image_uris_by_doc = {"index": image_uris or set()}
    return app


def _write_source_image(app: Mock, uri: str = "images/missing.png") -> None:
    source_image = Path(app.env.srcdir, uri)
    source_image.parent.mkdir(parents=True, exist_ok=True)
    source_image.write_bytes(b"image")


def _directive(sphinx_env: Mock, image: str = "/i.png") -> LightboxDirective:
    state = Mock()
    state.document.settings.env = sphinx_env
    state_machine = Mock()
    state_machine.get_source_and_line.return_value = ("test.rst", 10)
    return LightboxDirective("lightbox", [image], {}, [], 1, 0, "", state, state_machine)


def _container(checkbox_id: str = "lb-1") -> tuple[LightboxContainer, LightboxOverlay]:
    container = LightboxContainer()
    trigger = LightboxTrigger()
    trigger["checkbox_id"] = checkbox_id
    overlay = LightboxOverlay()
    overlay["checkbox_id"] = checkbox_id
    container += trigger
    container += overlay
    return container, overlay


@pytest.mark.unit
def test_source_image_path_rejects_empty_remote_and_commonpath_errors() -> None:
    assert _source_image_path("", "images/example.png") is None
    assert _source_image_path("/docs", "https://example.invalid/image.png") is None

    with patch("lightbox.lightbox.os.path.commonpath", side_effect=ValueError):
        assert _source_image_path("/docs", "images/example.png") is None


@pytest.mark.unit
def test_image_digest_handles_unresolved_and_unreadable_images() -> None:
    assert _image_digest("/docs", "data:image/png;base64,AAAA") is None

    with patch("builtins.open", side_effect=OSError("cannot read")):
        assert _image_digest("/docs", "images/example.png") is None


@pytest.mark.unit
def test_resolve_output_uri_handles_tuple_and_plain_environment_mappings() -> None:
    builder = Mock(images={"images/example.png": ({"index"}, "example-hash.png")})
    builder.imgpath = "_images"
    assert _resolve_output_uri(builder, "images/example.png") == "_images/example-hash.png"

    builder = Mock()
    builder.images = {}
    builder.imgpath = "_images"
    builder.env.images = {"images/example.png": "plain-name.png"}
    assert _resolve_output_uri(builder, "images/example.png") == "_images/plain-name.png"


@pytest.mark.unit
def test_resolve_duplicate_output_uri_handles_digest_edge_cases(tmp_path: Path) -> None:
    image_dir = tmp_path / "images"
    image_dir.mkdir()
    (image_dir / "first.png").write_bytes(b"first")
    (image_dir / "different.png").write_bytes(b"different")
    (image_dir / "same.png").write_bytes(b"first")

    builder = Mock()
    builder.env.srcdir = str(tmp_path)
    builder.env.images = {
        "images/first.png": "first.png",
        "images/different.png": "different.png",
    }
    builder.images = {"images/different.png": "different.png"}
    assert _resolve_duplicate_output_uri(builder, "images/first.png") == ""

    builder.env.images = {
        "images/first.png": "first.png",
        "images/different.png": "different.png",
        "images/same.png": ({"index"}, "same-hash.png"),
    }
    builder.images = {
        "images/different.png": "different.png",
        "images/same.png": ({"index"}, "same-hash.png"),
    }
    assert _resolve_duplicate_output_uri(builder, "images/first.png") == "same-hash.png"

    assert _resolve_duplicate_output_uri(builder, "images/missing.png") == ""


@pytest.mark.unit
def test_environment_image_metadata_ignores_malformed_values() -> None:
    env = Mock()
    env.lightbox_image_uris_by_doc = {
        42: {"ignored.png"},
        "broken": None,
        "index": [1, "images/example.png"],
    }

    assert _lightbox_images_by_doc(env) == {"index": {"1", "images/example.png"}}


@pytest.mark.unit
def test_register_lightbox_image_ignores_empty_normalized_uri() -> None:
    env = Mock()
    env.lightbox_image_uris_by_doc = {"index": {"images/existing.png"}}

    _register_lightbox_image(env, "index", "/")

    assert env.lightbox_image_uris_by_doc == {"index": {"images/existing.png"}}


@pytest.mark.unit
def test_merge_lightbox_images_skips_unrequested_docs() -> None:
    env = Mock()
    env.lightbox_image_uris_by_doc = {}
    other = Mock()
    other.lightbox_image_uris_by_doc = {"usage": {"images/usage.png"}}

    _merge_lightbox_images(Mock(), env, {"missing"}, other)

    assert env.lightbox_image_uris_by_doc == {}


@pytest.mark.unit
def test_copy_missing_lightbox_images_returns_when_build_failed() -> None:
    app = Mock()
    app.builder.format = "html"

    with patch("lightbox.lightbox.os.makedirs") as makedirs:
        _copy_missing_lightbox_images(app, RuntimeError("failed"))

    makedirs.assert_not_called()


@pytest.mark.unit
def test_copy_missing_lightbox_images_skips_unreferenced_images(tmp_path: Path) -> None:
    app = _copy_app(tmp_path, {"images/unused.png": "unused.png"})
    _write_source_image(app, "images/unused.png")

    _copy_missing_lightbox_images(app, None)

    assert not Path(app.outdir, "_images", "unused.png").exists()


class _ItemsWithoutContains:
    def items(self) -> list[tuple[str, str]]:
        return [("images/missing.png", "missing.png")]

    def __contains__(self, uri: object) -> bool:
        return False


@pytest.mark.unit
def test_copy_missing_lightbox_images_respects_image_mapping_membership(tmp_path: Path) -> None:
    app = _copy_app(tmp_path, _ItemsWithoutContains(), {"images/missing.png"})
    _write_source_image(app)

    _copy_missing_lightbox_images(app, None)

    assert not Path(app.outdir, "_images", "missing.png").exists()


@pytest.mark.unit
def test_copy_missing_lightbox_images_skips_empty_target_filename(tmp_path: Path) -> None:
    app = _copy_app(tmp_path, {"images/missing.png": ""}, {"images/missing.png"})
    _write_source_image(app)

    _copy_missing_lightbox_images(app, None)

    assert list(Path(app.outdir, "_images").iterdir()) == []


@pytest.mark.unit
def test_copy_missing_lightbox_images_skips_target_outside_image_dir(tmp_path: Path) -> None:
    app = _copy_app(tmp_path, {"images/missing.png": "missing.png"}, {"images/missing.png"})
    _write_source_image(app)

    with patch(
        "lightbox.lightbox.os.path.commonpath",
        side_effect=[str(Path(app.env.srcdir).resolve()), str(tmp_path.resolve())],
    ):
        _copy_missing_lightbox_images(app, None)

    assert not Path(app.outdir, "_images", "missing.png").exists()


@pytest.mark.unit
def test_copy_missing_lightbox_images_ignores_target_commonpath_errors(tmp_path: Path) -> None:
    app = _copy_app(tmp_path, {"images/missing.png": "missing.png"}, {"images/missing.png"})
    _write_source_image(app)

    with patch(
        "lightbox.lightbox.os.path.commonpath",
        side_effect=[str(Path(app.env.srcdir).resolve()), ValueError],
    ):
        _copy_missing_lightbox_images(app, None)

    assert not Path(app.outdir, "_images", "missing.png").exists()


@pytest.mark.unit
def test_copy_missing_lightbox_images_warns_when_copy_fails(tmp_path: Path) -> None:
    app = _copy_app(tmp_path, {"images/missing.png": "missing.png"}, {"images/missing.png"})
    _write_source_image(app)

    with (
        patch("lightbox.lightbox.shutil.copyfile", side_effect=OSError("disk full")),
        patch("lightbox.lightbox.logger") as logger,
    ):
        _copy_missing_lightbox_images(app, None)

    assert logger.warning.call_args.kwargs["subtype"] == "copy_image"


@pytest.mark.unit
def test_missing_html_image_targets_ignores_unreadable_html(tmp_path: Path) -> None:
    outdir = tmp_path / "html"
    outdir.mkdir()
    (outdir / "index.html").write_text("<img src='_images/missing.png'>", encoding="utf-8")

    with patch("builtins.open", side_effect=OSError("cannot read")):
        assert _missing_html_image_targets(str(outdir)) == set()


@pytest.mark.unit
def test_invalid_transform_policy_warns_and_falls_back() -> None:
    app = Mock()
    app.config.lightbox_images = "invalid"

    with patch("lightbox.lightbox.logger") as logger:
        assert _policy(app, "lightbox_images") == "explicit"

    assert logger.warning.call_args.kwargs["subtype"] == "invalid_config"


@pytest.mark.unit
def test_invalid_gallery_mode_warns_and_falls_back() -> None:
    app = Mock()
    app.config.lightbox_gallery = "invalid"

    with patch("lightbox.lightbox.logger") as logger:
        assert _gallery_mode(app) == "document"

    assert logger.warning.call_args.kwargs["subtype"] == "invalid_config"


@pytest.mark.unit
def test_transform_candidate_ignores_linked_images() -> None:
    app = Mock()
    image = nodes.image(uri="images/example.png", classes=["lightbox"])
    nodes.reference("", "", image)

    assert _is_transform_candidate(app, image) is False


@pytest.mark.unit
def test_container_lookup_helpers_handle_missing_children() -> None:
    container = LightboxContainer()
    container += nodes.paragraph("", "ignored")
    container += LightboxTrigger()

    assert _container_checkbox_id(container) == ""
    assert _overlay_for_container(container) is None


@pytest.mark.unit
def test_clear_gallery_metadata_removes_existing_attributes() -> None:
    overlay = LightboxOverlay()
    overlay["gallery_id"] = "gallery"
    overlay["gallery_index"] = 1
    overlay["gallery_count"] = 2
    overlay["gallery_prev_target"] = "previous"
    overlay["gallery_next_target"] = "next"
    overlay["caption"] = "Caption"

    _clear_gallery_metadata(overlay)

    assert "gallery_id" not in overlay
    assert "gallery_index" not in overlay
    assert "gallery_count" not in overlay
    assert "gallery_prev_target" not in overlay
    assert "gallery_next_target" not in overlay
    assert overlay["caption"] == "Caption"


@pytest.mark.unit
def test_assign_gallery_tolerates_overlay_lookup_changes() -> None:
    first, first_overlay = _container("lb-1")
    second, second_overlay = _container("lb-2")
    doc = nodes.document("", "")
    doc += first
    doc += second
    app = Mock()
    app.config.lightbox_gallery = "document"
    app.config.lightbox_gallery_wrap = False

    with patch(
        "lightbox.lightbox._overlay_for_container",
        side_effect=[
            first_overlay,
            second_overlay,
            None,
            second_overlay,
            None,
            second_overlay,
        ],
    ):
        assign_lightbox_gallery(app, doc, "index")

    assert second_overlay["gallery_prev_target"] == "lb-1"


@pytest.mark.unit
def test_lightbox_container_html_includes_alignment_class() -> None:
    translator = Mock()
    translator.body = []
    node = LightboxContainer()
    node["align"] = "center"

    visit_lightbox_container_html(translator, node)

    assert 'class="lightbox-container align-center"' in "".join(translator.body)


@pytest.mark.unit
def test_directive_keeps_square_ratio_when_image_size_is_incomplete(sphinx_env: Mock) -> None:
    directive = _directive(sphinx_env, "/zero-width.png")

    with (
        patch("lightbox.lightbox.os.path.isfile", return_value=True),
        patch("sphinx.util.images.get_image_size", return_value=(0, 400)),
    ):
        result = directive.run()

    overlay = next(node for node in result[0].children if isinstance(node, LightboxOverlay))
    assert "1.0000" in overlay["size_style"]


@pytest.mark.unit
def test_transform_on_read_uses_doctree_environment_docname() -> None:
    app = Mock()
    doctree = nodes.document("", "")
    doctree.settings = Mock()
    doctree.settings.env.docname = "nested/page"

    with patch("lightbox.lightbox.transform_lightbox_images") as transform:
        lightbox_module._transform_lightbox_images_on_read(app, doctree)

    transform.assert_called_once_with(app, doctree, "nested/page")


@pytest.mark.unit
def test_required_sphinx_noop_visitors_are_callable() -> None:
    translator = Mock()
    node = nodes.Element()

    assert skip_departure(translator, node) is None
    assert visit_noop(translator, node) is None
    with pytest.raises(nodes.SkipNode):
        _visit_skip(translator, node)
