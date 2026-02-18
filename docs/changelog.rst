=========
Changelog
=========

Version 2.0.10 (2026)
----------------------

Bug fixes and infrastructure improvements.
Revised accessibility documentation regarding strict WCAG 2.1 AA adherence. 
A pure CSS implementation cannot physically trap keyboard focus or support 
the Escape key. Lightweight JavaScript added for better adherence.

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
- **Accessibility Upgrades (Progressive Enhancement)** — Added a lightweight, 
  CSP-compliant JavaScript file (``lightbox.js``) to achieve strict WCAG keyboard 
  compliance. The ``Enter`` and ``Space`` keys now natively activate focused image 
  thumbnails, the ``Escape`` key closes any open lightbox, focus moves to the 
  close button when the lightbox opens and returns to the trigger on close, and 
  ``Tab``/``Shift+Tab`` are trapped within the open dialog. An idempotency guard 
  prevents issues if the script is loaded twice.
- **Fixed CSS/JS Registration** — Replaced the fragile manual asset copying 
  mechanism with Sphinx's native ``builder-inited`` hook. The extension now 
  safely injects its ``_static`` directory into ``html_static_path``, 
  resolving race conditions where the CSS file would fail to load in the browser.
- **Path Traversal Security Fix** — Replaced basic string-prefix checking 
  with strict ``os.path.commonpath`` bounds checking to prevent malicious directory 
  traversal payloads from reading files outside the Sphinx source directory.
- **Graceful Aspect Ratio Fallback** — When Sphinx's native image parser fails 
  to calculate dimensions for heavily compressed PNGs, the extension now emits a 
  helpful build warning and gracefully falls back to a 1:1 aspect ratio to 
  prevent build crashes.  
- **LaTeX ``adjustbox`` package declared** — The extension now registers the
  ``adjustbox`` package via ``app.add_latex_package()``, removing the implicit
  dependency on users adding ``\usepackage{adjustbox}`` to their ``conf.py``
  preamble.
- **Hidden collector image class** — The invisible collector ``image`` node
  now carries the ``lightbox-hidden`` CSS class, aligning the doctree with the
  existing CSS rule and making intent explicit.
- **Idempotent static path registration** — ``_builder_inited`` now guards
  against duplicate ``html_static_path`` entries if the extension is loaded
  more than once.
- **New ``:latex-width:`` option** — Optional directive option to control PDF
  image width independently of HTML sizing.  Accepts a float between 0 and 1
  representing a fraction of ``\linewidth``.  When omitted, the second
  ``:percentage:`` value is used as before.

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
