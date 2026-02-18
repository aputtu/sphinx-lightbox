=========
Changelog
=========

Version 2.0.10 (2026)
----------------------

Bug fixes and infrastructure improvements.

- **Fixed HTML image paths** — HTML visitor functions now resolve source-relative
  URIs to ``_images/<filename>`` output paths via ``builder.images``.
  Previously images were broken in the rendered HTML.
- **Fixed phantom image** — Introduced ``LightboxCollector`` node wrapping the
  hidden collector ``image`` node.  All output visitors suppress it via
  ``SkipNode``, eliminating the full-size duplicate image that appeared
  beside the thumbnail in HTML output.
- **``conf.py`` relocated to ``docs/``** — Sphinx requires ``conf.py`` in the
  source directory.  Path setup updated to ``sys.path.insert(0,
  os.path.abspath(".."))``.  ``html_static_path`` updated accordingly.
- **PDF build support** — ``make docs-pdf`` and ``make all`` targets added.
  ``make all`` builds PDF first, copies it into the HTML output directory,
  then builds HTML so the download link in ``index.rst`` resolves correctly.
- **No blank pages in PDF** — ``extraclassoptions: oneside`` added to
  ``latex_elements`` in ``conf.py``.
- **Reduced code-block page breaks in PDF** — ``needspace`` and ``etoolbox``
  added to the LaTeX preamble; ``\preto{\sphinxVerbatim}{\needspace{6\baselineskip}}``
  keeps short code blocks together.
- **Test suite fixed** — Three root-cause bugs corrected: ``texescape.init()``
  called in ``conftest.py`` so ``latex_escape()`` works without a running
  Sphinx app; ``nodes.SkipNode`` now caught by ``run_latex_visitor()`` helper;
  ``SphinxDirective.env`` injected via ``state.document.settings.env`` instead
  of direct assignment.  ``TestHtmlOutput`` class added (13 new tests).
  Coverage raised from 36% to 87%.
- **HTML test mock fixed** — ``_make_translator()`` in ``TestHtmlOutput`` now
  provides ``translator.builder.images = {}`` so ``_resolve_output_uri()``
  does not fail with ``TypeError: argument of type 'Mock' is not iterable``.

Version 2.0.0 (2025)
---------------------

Complete rewrite of the lightbox extension.

- **Node-based architecture** — custom docutils nodes (``LightboxContainer``,
  ``LightboxTrigger``, ``LightboxOverlay``) with per-builder visitor
  functions, replacing the raw HTML string approach.
- **Sphinx-native image handling** — images registered with
  ``env.images.add_file()``, served from ``_images/``, with full dependency
  tracking and incremental build support.
- **Multi-builder support** — full lightbox in HTML, ``\includegraphics``
  with caption in LaTeX/PDF, plain image fallback for epub/man/text.
- **WCAG 2.1 AA accessibility** — ``role="dialog"``, ``aria-modal``,
  ``aria-label``, visible focus indicators, ``prefers-reduced-motion``,
  ``prefers-contrast: more``.
- **SphinxDirective base class** — consistent with modern Sphinx extension
  conventions.
- Fixed uninitialised ``size_style`` variable when ``:percentage:`` was
  omitted or had fewer than 2 values.
- Fixed image path resolution for absolute source-root paths (``/images/...``).
- Removed manual ``copy_asset_file`` into ``_static/``.
- ``parallel_read_safe: True`` and ``parallel_write_safe: True``.

Version 1.x (2024)
-------------------

- Initial iterative development for the MiGrid User Guides project.
- Pure CSS checkbox-toggle mechanism.
- Raw HTML output via ``nodes.raw()``.
- Manual image copying to ``_static/``.
