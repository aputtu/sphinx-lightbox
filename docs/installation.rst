============
Installation
============

Requirements
------------

- Python 3.10 or later
- Sphinx 7.0 through 9.x

Install From PyPI
-----------------

.. code-block:: bash

   pip install sphinx-lightbox

Install the package into the same Python environment that runs Sphinx.

Install From A Checkout
-----------------------

Install the package into the same Python environment that runs Sphinx:

.. code-block:: bash

   pip install -e .

This keeps the package importable as ``lightbox`` while the project is
being developed locally.

Enable the extension
--------------------

Add ``lightbox`` to your Sphinx ``conf.py``:

.. code-block:: python

   # If the lightbox package is on sys.path:
   extensions = [
       "lightbox",
   ]

The extension automatically registers its CSS and JavaScript files.  No
additional template changes are needed.

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

Reference them with standard Sphinx markup. Absolute paths are resolved
from the source root:

.. code-block:: rst

   .. image:: /images/topic-a/screenshot-1.png
      :alt: Topic A screenshot.
      :class: lightbox

Or with document-relative paths:

.. code-block:: rst

   .. image:: ../images/topic-a/screenshot-1.png
      :alt: Topic A screenshot.
      :class: lightbox

Images are resolved through Sphinx's collector and placed in ``_images/``
in the HTML build output — not ``_static/``.
