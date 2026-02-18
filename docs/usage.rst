=====
Usage
=====

Basic Lightbox
--------------

The ``.. lightbox::`` directive creates a click-to-enlarge image.  The
argument is the path to the image file:

.. code-block:: rst

   .. lightbox:: /images/example-screenshot.png
      :alt: Description of the image.

**Live example:**

.. lightbox:: /images/example-screenshot.png
   :alt: A basic lightbox with default settings.

Click the image above to open the lightbox overlay.  Click the × button
or click outside the image to close it.


Adding a Caption
----------------

Use the ``:caption:`` option to add descriptive text below the full-size
image in the overlay:

.. code-block:: rst

   .. lightbox:: /images/example-screenshot.png
      :alt: Screenshot with caption.
      :caption: This caption appears below the image in the lightbox overlay.

**Live example:**

.. lightbox:: /images/example-screenshot.png
   :alt: Screenshot with caption.
   :caption: This caption appears below the image in the lightbox overlay.


Controlling Size
----------------

The ``:percentage:`` option accepts one or two integers:

- **First value** — thumbnail width as a percentage of the container.
- **Second value** — lightbox display size (used for both ``vw``/``vh`` in
  CSS and ``\linewidth`` fraction in LaTeX).

.. code-block:: rst

   .. lightbox:: /images/example-detail.png
      :alt: Smaller thumbnail, large overlay.
      :caption: 40% thumbnail width, 95% overlay size.
      :percentage: 40 95

**Live example:**

.. lightbox:: /images/example-detail.png
   :alt: Smaller thumbnail, large overlay.
   :caption: 40% thumbnail width, 95% overlay size.
   :percentage: 40 95


Adding a Border
---------------

The ``:class: with-border`` option adds a subtle shadow and rounded corners
to the thumbnail:

.. code-block:: rst

   .. lightbox:: /images/example-screenshot.png
      :alt: Image with decorative border.
      :class: with-border
      :percentage: 50 90

**Live example:**

.. lightbox:: /images/example-screenshot.png
   :alt: Image with decorative border.
   :class: with-border
   :percentage: 50 90


Image Paths
-----------

The extension supports two path styles:

**Absolute paths** (from the source root):

.. code-block:: rst

   .. lightbox:: /images/topic/screenshot.png

**Document-relative paths:**

.. code-block:: rst

   .. lightbox:: ../images/topic/screenshot.png

Both styles are resolved through Sphinx's standard image pipeline.  If the
image file does not exist, a clear warning is emitted at build time with the
resolved absolute path.


LaTeX / PDF Output
------------------

In LaTeX builds, each lightbox renders as a ``figure`` environment with
``\includegraphics`` and ``\caption``.  The second ``:percentage:`` value
controls the width as a fraction of ``\linewidth`` (e.g. ``95`` becomes
``0.95\linewidth``).  The thumbnail is skipped — only the full-size image
appears.


Other Builders
--------------

For builders that are neither HTML nor LaTeX (epub, man, texinfo, text),
the extension emits a plain ``image`` node with the alt text, ensuring
content is never silently dropped.


Content Security Policy (CSP)
-----------------------------

The lightbox extension uses a lightweight, external JavaScript file to handle strict 
WCAG keyboard navigation. Because it is loaded externally rather than inline, it 
completely avoids the need for ``script-src 'unsafe-inline'``. 

However, it utilizes dynamically generated inline styles to perfectly fit images to 
the viewport without distortion.

If your documentation is hosted on a domain with a strict Content Security 
Policy, ensure your policy permits inline styles:

.. code-block:: text

   Content-Security-Policy: style-src 'self' 'unsafe-inline';
