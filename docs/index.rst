.. meta::
   :description: sphinx-lightbox — accessible, CSS-only click-to-enlarge
      images for Sphinx documentation.
   :keywords: sphinx, extension, lightbox, image, zoom, accessible, CSS-only

==================================
sphinx-lightbox Documentation
==================================

**Version:** |release|

.. rubric:: Accessible, CSS-only click-to-enlarge images for Sphinx.

``sphinx-lightbox`` is a Sphinx extension that provides click-to-enlarge image
viewing in HTML output using a pure CSS checkbox-toggle mechanism — no
JavaScript required.  Images are rendered as standard figures in LaTeX/PDF
output, and as plain images in other builders.

.. only:: html

   `📄 Download PDF documentation <sphinx-lightbox.pdf>`_

.. note::

   This documentation is *self-referential*: the live examples below are
   rendered by the extension you are reading about.

Live Example
------------

Click the image below to see the lightbox in action:

.. lightbox:: images/example-screenshot.png
   :alt: Example screenshot demonstrating the lightbox extension.
   :caption: Click anywhere outside the image, or press the × button, to close.
   :class: with-border
   :percentage: 60 90

Key Features
------------

- **Pure CSS** — uses a checkbox-toggle pattern with no JavaScript dependency.
- **Sphinx-native image handling** — images are registered with Sphinx's
  collector, land in ``_images/``, and participate in incremental builds.
- **Multi-builder support** — full lightbox in HTML, ``\includegraphics``
  with caption in LaTeX/PDF, plain image fallback in other builders.
- **WCAG 2.1 AA accessibility** — visible focus indicators, ``role="dialog"``,
  ``aria-modal``, ``aria-label``, ``prefers-reduced-motion``, and
  ``prefers-contrast: more`` support.
- **Proper node architecture** — custom docutils nodes with per-builder
  visitor functions, following Sphinx extension best practices.
- **GPL-3.0-or-later** licensed open source.


Contents
--------

.. toctree::
   :maxdepth: 2
   :caption: User Guide

   installation
   usage
   accessibility

.. toctree::
   :maxdepth: 2
   :caption: Reference

   directive
   api

.. toctree::
   :maxdepth: 1
   :caption: Project

   changelog
   license


Indices and tables
------------------

* :ref:`genindex`
* :ref:`search`
