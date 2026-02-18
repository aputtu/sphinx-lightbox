=============
Accessibility
=============

The lightbox extension is built with an **accessibility-conscious design** 
following WCAG guidelines. The extension is built with an HTML/CSS-first 
approach, utilizing JavaScript as a progressive enhancement to ensure robust 
keyboard navigation.

CSS-Only Toggle Mechanism
-------------------------

The lightbox uses a hidden ``<input type="checkbox">`` and CSS ``:checked``
selector to toggle the overlay.  This approach works without JavaScript,
ensuring the lightbox functions even when scripts are disabled.

ARIA Attributes
---------------

The generated HTML includes:

- ``role="dialog"`` and ``aria-modal="true"`` on the overlay container,
  so screen readers announce it as a modal dialog.
- ``aria-label="Enlarge image: ..."`` on the trigger, describing the
  action that will occur.
- ``aria-label="Close lightbox"`` on the close button.
- ``aria-hidden="true"`` on the hidden checkbox, so screen readers skip
  the implementation detail.
- ``role="button"`` on the ``<label>`` elements that act as interactive
  controls.

Keyboard Navigation
-------------------

All interactive elements have ``tabindex="0"`` and are reachable via the
Tab key:

1. **Tab** to the thumbnail image — it receives a visible focus outline.
2. **Enter** or **Space** to open the lightbox (activates the label).
3. Focus automatically moves to the close button inside the overlay.
4. **Tab** cycles within the overlay (focus is trapped inside the dialog).
5. **Enter**, **Space**, or **Esc** to close.
6. Focus returns to the thumbnail that opened the lightbox.

.. note::

   **Progressive Enhancement:** At its core, the lightbox uses a pure-CSS 
   toggle mechanism that functions even if JavaScript is disabled in the 
   browser. To strictly comply with WCAG 2.1 AA keyboard requirements, the 
   extension includes a lightweight, CSP-compliant JavaScript file that adds:

   - Native ``Enter`` and ``Space`` key activation for focused controls.
   - ``Escape`` key to close the overlay.
   - **Focus management** — focus moves to the close button when the 
     lightbox opens and returns to the triggering thumbnail when it closes.
   - **Focus trap** — ``Tab`` and ``Shift+Tab`` cycle only among focusable 
     elements within the open dialog, preventing keyboard focus from 
     escaping to the page behind the overlay.

Focus Indicators
----------------

Visible focus outlines appear on both the trigger and close controls:

.. code-block:: css

   .lightbox-trigger-label:focus-visible {
       outline: 3px solid #4A90D9;
       outline-offset: 3px;
   }

The ``:focus:not(:focus-visible)`` pattern ensures outlines appear only
for keyboard navigation, not mouse clicks.

Reduced Motion
--------------

The hover transition on the thumbnail is disabled when the user has
requested reduced motion:

.. code-block:: css

   @media (prefers-reduced-motion: reduce) {
       .lightbox-trigger-label img.lightbox-trigger {
           transition: none;
       }
   }

High Contrast Mode
------------------

When ``prefers-contrast: more`` is active, the CSS applies:

- Solid black/white outlines instead of the default blue.
- A white border around the full-size image for clear delineation.
- Increased backdrop opacity (95% instead of 85%).
- A solid black background with white border on the close button.

**Live example** (the image below respects your system's contrast and
motion preferences):

.. lightbox:: /images/example-detail.png
   :alt: Accessibility example — respects reduced-motion and high-contrast.
   :caption: This image adapts to your accessibility preferences.
   :class: with-border
   :percentage: 50 85

Testing Recommendations
-----------------------

When using the lightbox extension, consider testing with:

1. **Keyboard-only navigation** — Tab to the image, Enter to open.  Verify
   that focus moves to the close button.  Press Tab and Shift+Tab to confirm
   focus stays trapped within the overlay.  Press Escape, Enter, or Space to
   close and verify focus returns to the thumbnail.
2. **Screen readers** — verify the dialog is announced (NVDA, VoiceOver,
   Orca).
3. **Browser zoom at 200%** — ensure the overlay scales properly.
4. **Disabled JavaScript** — the lightbox opens and closes via the CSS
   checkbox toggle, though keyboard focus management and trapping are
   unavailable without scripts.
5. **High contrast mode** — check visibility in Windows High Contrast and
   ``prefers-contrast: more``.
6. **Reduced motion** — verify no transitions occur.
