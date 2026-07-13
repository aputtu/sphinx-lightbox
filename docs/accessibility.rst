=============
Accessibility
=============

The lightbox extension is built with an **accessibility-conscious design**.
The core open/close behavior is HTML/CSS-first, and a small JavaScript file
adds the keyboard and focus behavior that CSS alone cannot provide.

This page covers the extension's interactive HTML output. Non-HTML builders
keep Sphinx's native image and figure behavior; accessibility of a generated
PDF depends on the project's LaTeX/PDF toolchain and requires a separate
PDF/UA-oriented review.

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
- Visually hidden text on the trigger and close controls, describing the
  action that will occur.
- ``aria-hidden="true"`` on the hidden checkbox, so screen readers skip
  the implementation detail.

Keyboard Navigation
-------------------

All visible controls participate in sequential keyboard navigation. The custom
trigger and close controls use ``tabindex="0"``; gallery controls are native
buttons and are keyboard-focusable without an explicit ``tabindex``:

1. **Tab** to the thumbnail control — it receives a visible focus outline.
2. **Enter** or **Space** to open the lightbox.
3. Focus automatically moves to the close button inside the overlay.
4. **Tab** cycles within the overlay (focus is trapped inside the dialog).
5. **ArrowLeft** and **ArrowRight** move between gallery items when gallery
   controls are present.
6. **Enter**, **Space**, or **Esc** to close.
7. Focus returns to the thumbnail that opened the lightbox.

.. note::

   **Progressive enhancement:** At its core, the lightbox uses a pure-CSS
   toggle mechanism that functions even if JavaScript is disabled in the
   browser. The JavaScript enhancement adds:

   - ``Enter`` and ``Space`` key activation for focused controls.
   - ``Escape`` key to close the overlay.
   - **Focus management** — focus moves to the close button when the
     lightbox opens and returns to the triggering thumbnail when it closes.
   - **Focus trap** — ``Tab`` and ``Shift+Tab`` cycle only among focusable
     elements within the open dialog, preventing keyboard focus from
     escaping to the page behind the overlay.
   - Gallery navigation with click, tap, ``ArrowLeft``, and ``ArrowRight``
     when a document contains multiple lightboxes.

Focus Indicators
----------------

Visible focus outlines appear on both the trigger and close controls:

.. code-block:: css

   .lightbox-trigger-control:focus-visible {
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
- Solid black caption and legend panel for readable overlay text.

**Live example** (the image below respects your system's contrast and
motion preferences):

.. figure:: /images/example-screenshot.png
   :alt: Accessibility example that respects reduced-motion and high-contrast.
   :width: 50%
   :class: with-border

   This image adapts to your accessibility preferences.

Testing Recommendations
-----------------------

When using the lightbox extension, consider testing with:

1. **Keyboard-only navigation** — Tab to the image, Enter to open.  Verify
   that focus moves to the close button.  Press Tab and Shift+Tab to confirm
   focus stays trapped within the overlay.  Press Escape, Enter, or Space to
   close and verify focus returns to the thumbnail.
2. **Screen readers** — verify the dialog is announced (NVDA, VoiceOver,
   Orca).
3. **Reflow at 400% zoom or 320 CSS pixels** — ensure the page and overlay do
   not require horizontal scrolling and focused controls remain visible.
4. **Disabled JavaScript** — the lightbox opens and closes via the CSS
   checkbox toggle when activated with a pointer. Keyboard activation, Escape
   handling, focus management, focus trapping, and gallery keyboard navigation
   are unavailable without scripts.
5. **High contrast mode** — check visibility in Windows High Contrast and
   ``prefers-contrast: more``.
6. **Reduced motion** — verify no transitions occur.
