Changelog
=========

Version 0.6.0 (2026-07-14)
--------------------------

- Make all extension-owned interface labels and warnings translatable through
  Sphinx's extension localization API and a dedicated ``sphinx-lightbox``
  gettext domain. Authored image text remains under the documentation
  project's translation workflow, and catalogs belonging to Sphinx or other
  extensions remain under their respective upstream projects.
- Add a complete bundled Danish translation as the first localization,
  covering accessible enlarge, close, previous, and next controls as well as
  extension diagnostics. Danish builds activate it through the standard
  ``language = "da"`` setting without project-specific locale paths.
- Ship the source, translation, and compiled message catalogs in wheels and
  source distributions. Document the Babel extraction and compilation
  workflow, and add catalog, Sphinx-build, and distribution regression tests.
- Exercise every supported Python 3.10 through 3.14 and Sphinx 7.0 through 9.1
  combination in tox and CI with distinct minor-series constraints, including
  the Sphinx 7.0 lower bound.

Version 0.5.1 (2026-07-13)
--------------------------

- Fix focus restoration when gallery navigation switches between lightboxes.
  Closing the incoming lightbox with Escape now returns focus to its own
  trigger without briefly focusing the outgoing trigger.
- Fix the focus trap for fixed-position lightbox controls and keep keyboard
  focus visible and unobscured. Trigger and overlay controls expose accessible
  button names and support Enter, Space, Escape, Tab, and Shift+Tab behavior
  consistent with the applicable WCAG 2.2 success criteria.
- Preserve ordinary visible images in EPUB and other non-lightbox builders,
  provide readable accessible-name fallbacks, and initialize the JavaScript
  enhancement correctly when it is loaded after ``DOMContentLoaded``.
- Keep the image post-transform compatible with the complete supported Sphinx
  7.0 through 9.1 range, including their different current-document and
  application environment APIs.
- Copy missing transformed images through Sphinx's configured image directory,
  recognize remote URI schemes consistently, and prevent local image paths or
  symlinks from escaping the compatibility directive's source and output trees.
- Keep generated checkbox identifiers unique even when compatibility-directive
  serials collide with native ``:name:`` identifiers later in the document.
- Restrict the installed package payload to runtime Python, CSS, JavaScript,
  and typing files. Harden distribution and generated-HTML validation against
  unsafe paths, duplicate entries, links, source/archive mismatches, missing
  accessible names, and invalid ARIA references. Add a current Nu HTML/CSS
  standards gate with checksum verification for its downloaded validator.
- Add real-browser regression coverage for pointer and keyboard interaction,
  gallery switching, focus visibility, compact viewports, late script loading,
  and the no-JavaScript fallback. Browser checks now gate package publication.
- Make the standard ``image`` and ``figure`` directives the sole documented
  authoring interface while retaining the original directive as an
  undocumented 0.5.x compatibility bridge.
- Preserve native image options such as width, height, scale, alignment,
  loading behavior, names, and ordinary classes on transformed thumbnails.
  Document builder-specific PDF examples and HTML figure wrapping with standard
  Sphinx directives.
- Keep Sphinx doctrees outside the deployable HTML directory and reject leaked
  build-state files during documentation validation. Deduplicate generated
  viewport metadata, add the project favicon, and keep the documentation title
  readable without horizontal scrolling at 320 CSS pixels. Emit intrinsic
  dimensions for local documentation images without changing their CSS sizing.

Version 0.5.0 Beta (2026-07-01)
-------------------------------

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
