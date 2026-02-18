=============
API Reference
=============

This page documents the internal Python API of ``sphinx-lightbox``.  The
public interface is the ``.. lightbox::`` RST directive; the Python API
below is primarily useful for contributors.

Extension Setup
---------------

.. autofunction:: lightbox.lightbox.setup

Nodes
-----

.. autoclass:: lightbox.lightbox.LightboxContainer

.. autoclass:: lightbox.lightbox.LightboxTrigger

.. autoclass:: lightbox.lightbox.LightboxOverlay

Directive
---------

.. autoclass:: lightbox.lightbox.LightboxDirective
   :members:
