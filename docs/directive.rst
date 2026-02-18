===================
Directive Reference
===================

.. _directive-lightbox:

``.. lightbox::``
-----------------

Creates a click-to-enlarge image with a CSS-only lightbox overlay.

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
     viewport.  Used for both CSS (``vw``/``vh``) and LaTeX
     (``\linewidth`` fraction).  Default: ``95``.

``:class:`` *(string)*
   Additional CSS class(es) applied to the image elements.  The built-in
   ``with-border`` class adds a shadow and rounded corners.

**HTML output:**

.. code-block:: html

   <div class="lightbox-container">
     <label for="lightbox-0" class="lightbox-trigger-label"
            tabindex="0" role="button"
            aria-label="Enlarge image: Alt text">
       <img src="_images/photo.png" alt="Alt text"
            class="lightbox-trigger with-border"
            style="width: 60%;">
     </label>
     <input type="checkbox" id="lightbox-0"
            class="lightbox-toggle" aria-hidden="true">
     <div class="lightbox-overlay" role="dialog"
          aria-modal="true" aria-label="Alt text">
       <label for="lightbox-0" class="lightbox-close"
              tabindex="0" role="button"
              aria-label="Close lightbox">&times;</label>
       <div class="lightbox-content">
         <img src="_images/photo.png" alt="Alt text"
              class="with-border"
              style="width: min(90vw, ...); height: min(90vh, ...);"
              onload="this.style.setProperty('--aspect-ratio', ...);">
         <p class="lightbox-caption">Caption text here.</p>
       </div>
       <label for="lightbox-0" class="lightbox-backdrop-close"
              aria-hidden="true"></label>
     </div>
   </div>

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

A plain ``image`` node with alt text — no content is dropped.

Examples
--------

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
   the overlay via the CSS checkbox toggle.  Suppressed in LaTeX and all
   other non-HTML builders.

``LightboxOverlay``
   The full-size image, caption paragraph, close button, and backdrop
   label.  Suppressed in LaTeX and all other non-HTML builders (the
   container visitor handles LaTeX output directly).

``LightboxCollector``
   An invisible wrapper around a standard ``image`` node.  Its only
   purpose is to be present in the doctree during Sphinx's read phase so
   that the ``ImageCollector`` registers the file and copies it to
   ``_images/``.  All output-format visitors suppress it entirely via
   ``SkipNode`` — the image content is already rendered by
   ``LightboxTrigger`` and ``LightboxOverlay``.

Each node has visitor function pairs registered for ``html``, ``latex``,
``text``, ``man``, and ``texinfo`` builders.
