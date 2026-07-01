=====
Usage
=====

Standard Images And Figures
---------------------------

The recommended API is ordinary Sphinx ``image`` and ``figure`` markup.
The extension transforms eligible images only for HTML output.

Configure the transform policy in ``conf.py``:

.. code-block:: python

   lightbox_images = "explicit"   # "explicit", "all", or "none"
   lightbox_figures = "all"       # "explicit", "all", or "none"
   lightbox_default_class = "with-shadow"

With ``lightbox_images = "explicit"``, opt a normal image into lightbox
handling with ``:class: lightbox``:

.. code-block:: rst

   .. image:: /images/example-screenshot.png
      :alt: Standard image with lightbox behavior.
      :class: lightbox

Plain images do not have built-in Sphinx captions, so the overlay shows
only the image:

.. image:: /images/example-screenshot.png
   :alt: Standard image with lightbox behavior.
   :width: 60%
   :class: lightbox

With ``lightbox_figures = "all"``, figures are transformed by default.
The normal figure caption and legend remain in the page and are copied
into the lightbox overlay:

.. code-block:: rst

   .. figure:: /images/example-screenshot.png
      :alt: Figure with lightbox behavior.

      This caption appears in the page and in the lightbox overlay.

      This legend is longer explanatory text attached to the figure.

.. figure:: /images/example-screenshot.png
   :alt: Figure with lightbox behavior.
   :width: 60%

   This caption appears in the page and in the lightbox overlay.

   This legend is longer explanatory text attached to the figure.

Add ``:class: no-lightbox`` to an individual image or figure to opt out
when its policy is ``"all"``.


Gallery Mode
------------

Gallery navigation is optional. It adds previous and next controls between
lightboxes in the same document without changing the authoring markup:

.. code-block:: python

   lightbox_gallery = "document"  # "document" or "none"
   lightbox_gallery_wrap = False

When gallery mode is ``"document"``, transformed images and figures are
ordered by source order. If a document has more than one lightbox, overlays
show previous and next controls. ArrowLeft and ArrowRight navigate the same
gallery. A single lightbox does not render gallery controls.

Use ``lightbox_gallery = "none"`` to keep each lightbox independent.


Captions And Legends
--------------------

Plain ``image`` directives do not have Sphinx-native captions, so their
overlays show only the image. Use ``figure`` when an image needs caption
or legend text:

.. code-block:: rst

   .. figure:: /images/example-screenshot.png
      :alt: Detail screenshot.
      :width: 55%

      The caption is copied into the lightbox overlay.

      The legend is copied too.


Sizing And Styling
------------------

Use standard Sphinx image options for thumbnails:

.. code-block:: rst

   .. image:: /images/example-screenshot.png
      :alt: Smaller thumbnail.
      :width: 40%
      :align: center
      :class: lightbox with-border

Classes other than ``lightbox`` and ``no-lightbox`` are preserved on the
thumbnail and overlay image. ``lightbox_default_class`` adds a default CSS
class to transformed images; set it to an empty string to disable the
default styling.


Lightbox Directive
------------------

The ``.. lightbox::`` directive creates a lightbox directly and provides
directive-specific sizing options.

The directive argument is the image path:

.. code-block:: rst

   .. lightbox:: /images/example-screenshot.png
      :alt: Lightbox directive example.
      :caption: Caption text shown in the overlay.
      :class: with-border
      :percentage: 60 90

The ``:percentage:`` option accepts one or two integers:

- **First value** — thumbnail width as a percentage of the container.
- **Second value** — lightbox display size in HTML and, unless
  ``:latex-width:`` is set, the ``\linewidth`` fraction in LaTeX.

To control PDF sizing independently, add ``:latex-width:``:

.. code-block:: rst

   .. lightbox:: /images/example-screenshot.png
      :alt: Lightbox directive with independent PDF sizing.
      :caption: 40% thumbnail, 95% HTML overlay, 60% PDF width.
      :percentage: 40 95
      :latex-width: 0.60

**Rendered example:**

.. lightbox:: /images/example-screenshot.png
   :alt: Lightbox directive with independent PDF sizing.
   :caption: 40% thumbnail, 95% HTML overlay, 60% PDF width.
   :percentage: 40 95
   :latex-width: 0.60

Directive lightboxes participate in gallery mode alongside transformed
standard images and figures.


Image Paths
-----------

The extension supports two path styles:

**Absolute paths** (from the source root):

.. code-block:: rst

   .. image:: /images/topic/screenshot.png
      :alt: Topic screenshot.
      :class: lightbox

**Document-relative paths:**

.. code-block:: rst

   .. image:: ../images/topic/screenshot.png
      :alt: Topic screenshot.
      :class: lightbox

Both styles are resolved through Sphinx's standard image pipeline.  If the
image file does not exist, a clear warning is emitted at build time with the
resolved absolute path.


LaTeX / PDF Output
------------------

In LaTeX builds, each lightbox renders as a ``figure`` environment with
``\includegraphics`` and ``\caption``.  By default, the second
``:percentage:`` value controls the width as a fraction of ``\linewidth``
(e.g. ``95`` becomes ``0.95\linewidth``).  The thumbnail is skipped — only
the full-size image appears.

To control PDF sizing independently of HTML, use the optional
``:latex-width:`` option:

.. code-block:: rst

   .. lightbox:: /images/diagram.png
      :alt: Architecture diagram.
      :percentage: 60 90
      :latex-width: 0.8

This sets the HTML overlay to 90% of the viewport while the PDF figure
uses 80% of ``\linewidth``.  When ``:latex-width:`` is omitted, the
second ``:percentage:`` value is used as before.


Other Builders
--------------

For the class-based ``image`` and ``figure`` transform, non-HTML builders
keep the original Sphinx nodes. For the ``.. lightbox::`` directive,
builders that are neither HTML nor LaTeX (epub, man, texinfo, text) receive
a plain ``image`` node with the alt text, ensuring content is never silently
dropped.


JavaScript Disabled
-------------------

The CSS checkbox-toggle mechanism still supports pointer-based opening and
closing when JavaScript is disabled. Keyboard activation, Escape-to-close,
focus movement, focus trapping, and arrow-key gallery navigation require the
external ``lightbox.js`` enhancement.


Content Security Policy (CSP)
-----------------------------

The lightbox extension uses an external JavaScript file for keyboard activation,
Escape-to-close, focus management, and gallery navigation. It does not inject
inline JavaScript.

The generated HTML does use inline styles for thumbnail width and overlay
sizing. If your documentation is hosted with a strict Content Security Policy,
ensure your policy permits inline styles:

.. code-block:: text

   Content-Security-Policy: style-src 'self' 'unsafe-inline';
