Changelog
=========

Version 0.5 Beta (2026-07-01)
-----------------------------

First public beta of ``sphinx-lightbox``.

- Standard Sphinx ``image`` and ``figure`` directives can be transformed into
  lightboxes for HTML output.
- The ``.. lightbox::`` directive is available with ``:percentage:`` and
  ``:latex-width:`` options.
- HTML output includes keyboard activation, Escape-to-close, focus management,
  focus trapping, and optional per-document gallery navigation through the
  external ``lightbox.js`` enhancement.
- Figure captions and legends remain visible on the page and are copied into
  lightbox overlays.
- Non-HTML builders keep standard image/figure behavior for class-based
  transforms. The ``.. lightbox::`` directive renders LaTeX figures for PDF
  output and plain images for other builders.
- Local image paths are constrained to the Sphinx source tree. Remote and
  ``data:`` images bypass lightbox transformation.
- Generated IDs and user-controlled HTML attributes are sanitized or escaped.
- Documentation is built with Sphinx and published at
  ``https://aputtu.github.io/sphinx-lightbox/``.
