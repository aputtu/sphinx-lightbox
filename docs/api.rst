=============
API Reference
=============

This page documents the internal Python API of ``sphinx-lightbox``. The public
authoring interface is standard Sphinx ``image`` and ``figure`` markup; see
:doc:`directive`. The Python API below is primarily useful for contributors.

Extension Setup
---------------

.. autofunction:: lightbox.lightbox.setup

Nodes
-----

.. autoclass:: lightbox.lightbox.LightboxContainer

.. autoclass:: lightbox.lightbox.LightboxTrigger

.. autoclass:: lightbox.lightbox.LightboxOverlay

Transforms
----------

.. autofunction:: lightbox.lightbox.transform_lightbox_images

.. autofunction:: lightbox.lightbox.assign_lightbox_gallery
