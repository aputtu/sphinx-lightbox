==========================
Image and Figure Reference
==========================

``sphinx-lightbox`` builds on the standard ``image`` and ``figure``
directives. There is no separate directive to learn for new documents:

- ``image`` supplies the image, alternative text, size, alignment, classes,
  target, loading behavior, and name;
- ``figure`` adds a caption, legend, figure width, and figure classes; and
- the extension adds the HTML trigger, dialog, optional gallery navigation,
  focus management, and overlay text.

Canonical References
--------------------

This page describes the interaction with ``sphinx-lightbox`` rather than
duplicating the complete upstream option reference. Consult:

- `Sphinx: Images
  <https://www.sphinx-doc.org/en/master/usage/restructuredtext/basics.html#images>`_
  for Sphinx path handling and image behavior;
- `Docutils: image directive
  <https://www.docutils.org/docs/ref/rst/directives.html#image>`_ for
  the canonical image options; and
- `Docutils: figure directive
  <https://www.docutils.org/docs/ref/rst/directives.html#figure>`_ for
  captions, legends, and figure-specific options.

Image
-----

With the default ``lightbox_images = "explicit"`` policy, add the
``lightbox`` class to a standard image:

.. code-block:: rst

   .. image:: /images/photo.png
      :alt: Snow-covered mountains reflected in a lake.
      :width: 60%
      :align: center
      :class: lightbox with-border
      :loading: lazy
      :name: mountain-photo

The extension preserves the native image node inside the HTML trigger, so
Sphinx still renders its size, alignment, loading behavior, name, and ordinary
classes. The enlarged image uses the original ``:alt:`` text. If ``:alt:`` is
omitted, the extension derives a readable accessible name from the filename,
but explicit, context-appropriate alternative text is preferred.

Figure
------

Use a standard figure when the image needs visible explanatory text:

.. code-block:: rst

   .. figure:: /images/photo.png
      :alt: Snow-covered mountains reflected in a lake.
      :width: 60%
      :align: center
      :class: with-border
      :figclass: landscape-example

      Mountains after the first winter snowfall.

      The legend may contain a longer explanation and normal inline markup.

The caption and legend remain in their normal positions on the page. For an
HTML lightbox, their text is also copied into the overlay. Figure-level
properties such as ``:figwidth:`` and ``:figclass:`` remain on the native
outer figure.

Native Option Interactions
--------------------------

``:alt:``
   Names the trigger and dialog and supplies alternative text for the enlarged
   image. Write it for the image's purpose in context; do not repeat the nearby
   caption unnecessarily.

``:width:``, ``:height:``, and ``:scale:``
   Continue to control the native thumbnail. They also retain their ordinary
   Sphinx behavior in PDF and every non-HTML builder. When both dimensions are
   supplied, their interaction is the one defined by the upstream directive.

``:align:``
   Controls normal placement through the native directive. On a transformed
   plain image, the extension aligns the block-level HTML trigger container;
   surrounding text does not flow around that container. Figure alignment
   remains on the native outer figure, so left/right figure wrapping continues
   to follow the selected HTML theme. Combine figure ``:align:`` with
   ``:figwidth:`` when text should flow beside a lightboxed figure.

``:class:``
   Carries the extension's ``lightbox`` or ``no-lightbox`` control token and
   any project styling classes. The control token is consumed; other classes
   are preserved on the transformed images.

``:name:`` and ``:loading:``
   Stay on the native thumbnail and retain Sphinx's generated identifier and
   loading behavior.

``:target:``
   Takes priority over lightbox behavior. An image that already has a target
   remains an ordinary link, avoiding two competing actions on one image.

Figure ``:figwidth:`` and ``:figclass:``
   Remain on the standard figure wrapper and are not reimplemented by the
   extension.

Transformation Policies
-----------------------

Configure images and figures independently in ``conf.py``:

.. code-block:: python

   lightbox_images = "explicit"   # "explicit", "all", or "none"
   lightbox_figures = "all"       # "explicit", "all", or "none"
   lightbox_default_class = "with-shadow"

``"explicit"``
   Transform only directives whose ``:class:`` includes ``lightbox``.

``"all"``
   Transform every eligible local image of that type unless its ``:class:``
   includes ``no-lightbox``.

``"none"``
   Do not transform that directive type.

``lightbox_default_class`` supplies classes added to every transformed image.
Set it to ``""`` when no default visual treatment is wanted.

Gallery Options
---------------

Gallery mode links transformed images in source order within one document:

.. code-block:: python

   lightbox_gallery = "document"  # "document" or "none"
   lightbox_gallery_wrap = False

``"document"`` adds previous and next controls when at least two eligible
images exist. ``lightbox_gallery_wrap = True`` connects the last item back to
the first. ``"none"`` leaves every lightbox independent.

Eligibility and Builder Behavior
--------------------------------

A local image is eligible when its directive type's policy selects it and it
does not have an explicit ``:target:``. Remote URLs and ``data:`` URIs are not
transformed.

The transform runs only for interactive HTML builders. All other builders
receive the untouched Sphinx image or figure node, including its native
options, caption, and legend. Use Sphinx's standard ``only`` directive when a
document intentionally needs different image options for HTML and PDF.

What the Extension Adds
-----------------------

For each eligible HTML image, the extension adds:

- a keyboard-operable click-to-enlarge trigger around Sphinx's native image;
- a labelled modal dialog containing the enlarged image;
- focus movement, focus trapping, Escape-to-close, and focus restoration;
- copied figure caption and legend text; and
- optional previous and next gallery controls.

These are the extension's responsibilities. Image parsing, sizing, alignment,
identifiers, loading behavior, figure layout, paths, and non-HTML rendering
remain the responsibility of Sphinx and Docutils.
