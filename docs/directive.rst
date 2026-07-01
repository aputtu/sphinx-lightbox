===================
Directive Reference
===================

The primary API is standard Sphinx ``image`` and ``figure`` markup. The
``.. lightbox::`` directive is also available when directive-specific sizing
is useful.

Common project setup:

.. code-block:: python

   lightbox_images = "explicit"
   lightbox_figures = "all"
   lightbox_default_class = "with-shadow"
   lightbox_gallery = "document"
   lightbox_gallery_wrap = False

Standard ``image`` And ``figure`` Directives
--------------------------------------------

Add ``lightbox`` to the directive class list to make an ordinary Sphinx
image clickable in HTML output:

.. code-block:: rst

   .. image:: /images/photo.png
      :alt: Photo.
      :class: lightbox

Figures can also be configured as explicit, but the default is to wrap
all figures:

.. code-block:: rst

   .. figure:: /images/photo.png
      :alt: Photo.
      :class: with-border

      Figure caption.

      Longer explanatory legend text.

For ``figure`` nodes, the normal page caption remains in place and the
caption and legend text are copied into the lightbox overlay. Plain
``image`` nodes do not have built-in Sphinx captions, so their overlays
show only the image. Other classes, such as ``with-border``, are
preserved on the thumbnail and overlay image. The control classes
``lightbox`` and ``no-lightbox`` are not copied to the rendered image
elements.

Use these settings in ``conf.py`` to decide what is transformed:

.. code-block:: python

   lightbox_images = "explicit"   # "explicit", "all", or "none"
   lightbox_figures = "all"       # "explicit", "all", or "none"

When a policy is ``"all"``, opt out of an individual image or figure with
``no-lightbox``:

.. code-block:: rst

   .. image:: /images/icon.png
      :alt: Small icon.
      :class: no-lightbox

The class-based transform runs only for HTML builders. LaTeX/PDF and
other builders keep the original Sphinx image or figure nodes.

``lightbox_default_class`` sets classes applied to transformed HTML
images in addition to any classes on the source directive. The default is
``"with-shadow"``. Set it to an empty string to disable default styling:

.. code-block:: python

   lightbox_default_class = ""

Gallery Options
---------------

Gallery mode links transformed lightboxes in source order within a
document:

.. code-block:: python

   lightbox_gallery = "document"  # "document" or "none"
   lightbox_gallery_wrap = False

When enabled and a document has more than one lightbox, overlays render
previous and next controls. Click, tap, ArrowLeft, and ArrowRight navigate
between items. When ``lightbox_gallery_wrap`` is false, the first item has
no previous control and the last item has no next control.

Set ``lightbox_gallery = "none"`` to suppress gallery metadata and
controls.

.. _directive-lightbox:

``.. lightbox::``
-----------------

The dedicated directive creates a click-to-enlarge image using a
CSS-driven lightbox overlay with optional directive-specific sizing and
LaTeX options.

**Argument:**

``image_path`` *(required)*
   Path to the image file.  Supports absolute paths from the source root
   (starting with ``/``) and document-relative paths.

**Options:**

``:alt:`` *(string)*
   Alt text for the image.  Used for both the thumbnail and the overlay
   image.  Recommended for accessibility.

``:caption:`` *(string)*
   Caption text displayed below the full-size image in the overlay.  Also
   used as the ``\caption`` in LaTeX output.

``:percentage:`` *(one or two integers)*
   Controls image sizing:

   - **First value** — thumbnail width as a percentage of the container
     width.  Default: ``100``.
   - **Second value** — overlay display size as a percentage of the
     viewport.  Used for CSS (``vw``/``vh``) and, unless ``:latex-width:``
     is set, also for the LaTeX ``\linewidth`` fraction.  Default: ``95``.

``:latex-width:`` *(float, optional)*
   LaTeX image width as a fraction of ``\linewidth``, between ``0`` and
   ``1`` (exclusive/inclusive).  When set, this overrides the second
   ``:percentage:`` value for LaTeX/PDF output only — HTML sizing is
   unaffected.

   This option is entirely optional.  When omitted, the extension derives
   the LaTeX width from the second ``:percentage:`` value (default ``0.95``).

   Example: ``:latex-width: 0.8`` produces ``\adjustbox{max width=0.80\linewidth}``.

``:class:`` *(string)*
   Additional CSS class(es) applied to the image elements.  The built-in
   ``with-border`` class adds a subtle border and rounded corners.

**HTML output:**

.. code-block:: html

   <div class="lightbox-container">
     <label for="lightbox-usage-1" class="lightbox-trigger-label"
            tabindex="0">
       <span class="lightbox-visually-hidden">Enlarge image: Alt text</span>
       <img src="_images/photo.png" alt="Alt text"
            class="lightbox-trigger with-border"
            style="width: 60%;">
     </label>
     <input type="checkbox" id="lightbox-usage-1"
            class="lightbox-toggle" aria-hidden="true">
     <div class="lightbox-overlay" role="dialog"
       aria-modal="true" aria-label="Alt text">
       <label for="lightbox-usage-1" class="lightbox-close"
              tabindex="0">
         <span aria-hidden="true">&times;</span>
         <span class="lightbox-visually-hidden">Close lightbox</span>
       </label>
       <div class="lightbox-content">
            <img src="_images/photo.png" alt="Alt text"
                 class="with-border"
                 style="width: min(90vw, calc(90vh * 1.3333)); height: min(90vh, calc(90vw / 1.3333));">
         <div class="lightbox-text">
           <p class="lightbox-caption">Caption text here.</p>
         </div>
       </div>
       <label for="lightbox-usage-1" class="lightbox-backdrop-close"></label>
     </div>
   </div>

The overlay image dimensions are calculated at build time from the actual
image file. The ``width`` and ``height`` use CSS ``min()`` with the
pre-calculated aspect ratio, so the image fits the viewport without
distortion. If Sphinx cannot calculate the dimensions of a highly compressed 
or corrupted image, a warning is emitted during the build and the overlay 
gracefully falls back to a 1:1 aspect ratio to prevent crashes.

**External URLs:**

.. code-block:: rst

   .. lightbox:: https://example.com/remote-image.png

*Note: Because the lightbox requires build-time image dimension calculations
to properly size the CSS overlay, external URLs and ``data:`` URIs bypass the
lightbox and are gracefully rendered as standard Sphinx ``image`` nodes.*

**LaTeX output:**

.. code-block:: latex

   \begin{figure}[htbp]
   \centering
   \adjustbox{max width=0.90\linewidth}{\includegraphics{photo.png}}
   \caption{Caption text here.}
   \end{figure}

The ``\adjustbox{max width=...}`` wrapper prevents small images from being
upscaled beyond their natural size while still constraining large images to
the specified fraction of ``\linewidth``.

**Other builders:**

A plain ``image`` node with alt text - no content is dropped.

Directive Examples
------------------

Minimal:

.. code-block:: rst

   .. lightbox:: /images/photo.png

Fully specified:

.. code-block:: rst

   .. lightbox:: /images/archives/frozen-archives.png
      :alt: Frozen Archives screenshot with example archives.
      :caption: Example of the Archives page with a finalised archive.
      :class: with-border
      :percentage: 80 95

Independent PDF sizing:

.. code-block:: rst

   .. lightbox:: /images/architecture.png
      :alt: System architecture diagram.
      :caption: High-level architecture overview.
      :percentage: 60 90
      :latex-width: 0.8

Here the HTML thumbnail is 60% wide with a 90% overlay, while the PDF
figure is constrained to 80% of ``\linewidth``.

Document-relative path:

.. code-block:: rst

   .. lightbox:: ../images/detail-view.png
      :alt: Detail view of the settings panel.
      :percentage: 50

Node Architecture
-----------------

The extension defines four custom docutils nodes:

``LightboxContainer``
   Outer wrapper grouping all child nodes.  In HTML: a ``<div
   class="lightbox-container">``.  In LaTeX: handles the complete
   ``figure`` environment and raises ``SkipNode`` to prevent children
   from rendering a second time.

``LightboxTrigger``
   The thumbnail ``<img>`` and its ``<label>`` wrapper.  Clicking opens
   the overlay via the CSS checkbox toggle.  Suppressed outside HTML.

``LightboxOverlay``
   The full-size image, caption paragraph, close button, and backdrop
   label.  Suppressed outside HTML; the container visitor handles LaTeX
   output directly.

``LightboxCollector``
   A wrapper around a standard ``image`` node.  In HTML, it is present in
   the doctree during Sphinx's read phase so that ``ImageCollector``
   registers the file and copies it to ``_images/``; its visitor then
   raises ``SkipNode`` so it is not rendered.  In LaTeX, the container
   visitor handles output and skips the children.  In epub, text, man, and
   texinfo builders, the collector's child image supplies the plain image
   fallback.

Each node has visitor function pairs registered for ``html``, ``latex``,
``epub``, ``text``, ``man``, and ``texinfo`` builders.


Content Security Policy (CSP)
-----------------------------

The lightbox extension uses an external JavaScript file (``lightbox.js``) for
keyboard activation, Escape-to-close, gallery navigation, and focus management.
It does not inject inline JavaScript.

The generated HTML still uses inline styles for thumbnail width and overlay
sizing. A strict CSP that disallows inline styles will block those declarations.
If your documentation is served with CSP headers, allow inline styles for the
documentation pages:

.. code-block:: text

   Content-Security-Policy: style-src 'self' 'unsafe-inline';
