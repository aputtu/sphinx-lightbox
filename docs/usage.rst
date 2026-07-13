=====
Usage
=====

Recommended Workflow
--------------------

Author images with Sphinx's standard ``image`` and ``figure`` directives.
The extension augments eligible images in HTML; it does not introduce a third
authoring workflow.

Choose the transform policy in ``conf.py``:

.. code-block:: python

   lightbox_images = "explicit"   # "explicit", "all", or "none"
   lightbox_figures = "all"       # "explicit", "all", or "none"
   lightbox_default_class = "with-shadow"

With the ``"explicit"`` policy, opt in through the standard ``:class:``
option:

.. code-block:: rst

   .. image:: /images/example-screenshot.png
      :alt: Standard image with lightbox behavior.
      :width: 100%
      :align: left
      :class: lightbox

With the ``"all"`` policy, use ``:class: no-lightbox`` to opt out one image
or figure. A ``"none"`` policy disables transformation for that directive
type.

Choose ``image`` or ``figure``
-------------------------------

Use ``image`` when the image stands on its own. The directive has no body in
which to write a caption. Its ``:alt:`` text becomes the accessible name of
the HTML lightbox trigger and dialog as well as the alternative text for the
enlarged image, but it is not displayed as a caption:

.. code-block:: rst

   .. image:: /images/example-screenshot.png
      :alt: Standard image with lightbox behavior.
      :width: 100%
      :align: left
      :class: lightbox

.. raw:: latex

   \clearpage

.. image:: /images/example-screenshot.png
   :alt: Standard image with lightbox behavior.
   :width: 100%
   :align: left
   :class: lightbox

Use ``figure`` when readers need a caption or longer legend. The caption and
legend stay on the page and are also copied into the HTML overlay:

.. code-block:: rst

   .. figure:: /images/example-screenshot.png
      :alt: Figure with lightbox behavior.
      :width: 60%
      :align: center

      This caption appears on the page and in the lightbox overlay.

      This legend is longer explanatory text attached to the figure. It is
      preserved in both places too.

.. raw:: latex

   \clearpage

.. figure:: /images/example-screenshot.png
   :alt: Figure with lightbox behavior.
   :width: 60%
   :align: center

   This caption appears on the page and in the lightbox overlay.

   This legend is longer explanatory text attached to the figure. It is
   preserved in both places too.

Sizing and Alignment
--------------------

Use the directives' native ``:width:``, ``:height:``, ``:scale:``, and
``:align:`` options. The extension preserves them on the HTML thumbnail, and
non-HTML builders process the original image or figure without a lightbox
transform.

The rendered HTML and PDF examples deliberately show the native controls at
visibly different sizes and positions:

- the first image is left-aligned at 100%;
- the figure is centered at 60%; and
- the following image is right-aligned at 40%.

The same standard directive options produce these dimensions and alignments in
both builders; no lightbox-specific sizing option is involved:

.. code-block:: rst

   .. image:: /images/example-screenshot.png
      :alt: Smaller standard image, right aligned.
      :width: 40%
      :align: right
      :class: lightbox with-border

.. raw:: latex

   \clearpage

.. image:: /images/example-screenshot.png
   :alt: Smaller standard image, right aligned.
   :width: 40%
   :align: right
   :class: lightbox with-border

Text Flow in HTML
-----------------

Docutils normally lets following HTML text flow around a left- or right-aligned
image or figure. For a lightboxed ``figure``, that behavior remains on the
native outer figure. Use ``:figwidth:`` for the space occupied by the figure
and its caption, and ``:width:`` for the image inside it:

.. code-block:: rst

   .. figure:: /images/example-screenshot.png
      :alt: Screenshot floated to the right of the following text.
      :figwidth: 40%
      :width: 100%
      :align: right

      An optional caption stays inside the 40% figure width.

   This paragraph flows around the figure in HTML when the selected Sphinx
   theme implements the standard left/right alignment styles.

A transformed plain ``image`` has a block-level lightbox container. Its
``:align:`` option positions the trigger, but surrounding text does not wrap
around that container. Use ``figure`` when wrapping and lightbox behavior are
both required. To retain the native plain-image float instead, leave the image
untransformed or add ``:class: no-lightbox`` under an ``"all"`` policy.

The standard Sphinx LaTeX/PDF builders use these options for sizing and
alignment, not paragraph wrapping. PDF wraparound requires project-specific
LaTeX customization outside this extension.

For all native options and their precise semantics, use the
`Sphinx image documentation
<https://www.sphinx-doc.org/en/master/usage/restructuredtext/basics.html#images>`_,
the canonical `Docutils image directive
<https://www.docutils.org/docs/ref/rst/directives.html#image>`_, and
`Docutils figure directive
<https://www.docutils.org/docs/ref/rst/directives.html#figure>`_. The
local :doc:`directive` page explains only the lightbox-specific augmentation
and the interactions that matter when using it.

Gallery Mode
------------

Gallery navigation adds previous and next controls between transformed images
in source order within the same document. It does not change authoring markup:

.. code-block:: python

   lightbox_gallery = "document"  # "document" or "none"
   lightbox_gallery_wrap = False

When a document has more than one lightbox, users can also navigate with
Left Arrow and Right Arrow. A single lightbox does not render gallery controls.
Set ``lightbox_gallery = "none"`` to keep every lightbox independent.

Styling
-------

Classes other than the ``lightbox`` and ``no-lightbox`` control tokens are
preserved on the thumbnail and enlarged image:

.. code-block:: rst

   .. image:: /images/example-screenshot.png
      :alt: Screenshot with a custom visual treatment.
      :width: 40%
      :class: lightbox with-border product-screenshot

``lightbox_default_class`` adds project-wide classes to transformed images.
Set it to an empty string to disable the default ``with-shadow`` styling:

.. code-block:: python

   lightbox_default_class = ""

Paths, Links, and Builders
--------------------------

Use normal source-root-relative or document-relative image paths. Sphinx owns
path resolution, dependency tracking, copying, and builder-specific output:

.. code-block:: rst

   .. image:: /images/topic/screenshot.png
      :alt: Topic screenshot.
      :class: lightbox

   .. image:: ../images/topic/detail.png
      :alt: Topic detail.
      :class: lightbox

An image with ``:target:`` remains a normal link because its explicit link
destination takes priority over click-to-enlarge behavior. Remote URLs and
``data:`` URIs also remain ordinary images.

Only interactive HTML builders receive the lightbox transform. LaTeX/PDF,
EPUB, text, manual-page, and Texinfo builders keep Sphinx's original image and
figure nodes. Consequently the native sizing, alignment, caption, legend, and
fallback behavior remains under Sphinx and Docutils control.

JavaScript Disabled
-------------------

The CSS checkbox mechanism still supports pointer-based opening and closing
when JavaScript is disabled. Keyboard activation, Escape-to-close, focus
movement, focus trapping, and arrow-key gallery navigation require the
external ``lightbox.js`` enhancement.

Content Security Policy
-----------------------

The extension uses an external JavaScript file and does not inject inline
JavaScript. Sphinx may serialize native image sizing as inline CSS. If a site
uses a strict Content Security Policy, its ``style-src`` policy must permit
the styles emitted by the selected Sphinx builder and theme.
