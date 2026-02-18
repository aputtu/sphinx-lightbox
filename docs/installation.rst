============
Installation
============

Requirements
------------

- Python 3.10 or later
- Sphinx 7.0 or later

Install from source
-------------------

The lightbox extension is part of the ``migrid-sphinx-ext`` repository:

.. code-block:: bash

   git clone https://github.com/aputtu/migrid-sphinx-ext.git

Copy the ``lightbox/`` directory into your Sphinx project's extensions path,
or add the repository root to ``sys.path`` in your ``conf.py``.

Enable the extension
--------------------

Add ``lightbox`` to your Sphinx ``conf.py``:

.. code-block:: python

   # If the lightbox package is on sys.path:
   extensions = [
       "lightbox",
   ]

   # Make the CSS available to the HTML builder:
   html_static_path = ["path/to/lightbox/static"]

The extension automatically registers its CSS file.  No additional template
changes are needed.

Image directory setup
---------------------

The extension works with Sphinx's standard image pipeline.  Place your
content images under your source tree, for example:

.. code-block:: text

   docs/
   ├── images/
   │   ├── topic-a/
   │   │   ├── screenshot-1.png
   │   │   └── screenshot-2.png
   │   └── topic-b/
   │       └── detail.png
   └── index.rst

Reference them with absolute paths from the source root:

.. code-block:: rst

   .. lightbox:: /images/topic-a/screenshot-1.png

Or with document-relative paths:

.. code-block:: rst

   .. lightbox:: ../images/topic-a/screenshot-1.png

Images are resolved through Sphinx's collector and placed in ``_images/``
in the HTML build output — not ``_static/``.
