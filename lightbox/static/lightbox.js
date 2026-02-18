/* lightbox.js — Progressive enhancement for sphinx-lightbox
 * SPDX-License-Identifier: GPL-3.0-or-later
 *
 * This script enhances the pure-CSS checkbox-toggle lightbox with:
 *   1. Keyboard activation (Enter/Space) on <label> trigger and close controls
 *   2. Escape key to close any open lightbox
 *   3. Focus management — move focus into overlay on open, restore on close
 *   4. Focus trap — confine Tab cycling within the open dialog
 *
 * The CSS-only mechanism remains fully functional without this script.
 * All enhancements here target strict WCAG 2.1 AA keyboard compliance
 * that CSS alone cannot provide.
 */
(function () {
    'use strict';

    /* ------------------------------------------------------------------
     * Idempotency guard
     * Prevents duplicate initialisation if the script is loaded more
     * than once (e.g. a theme bundles it alongside the extension).
     * ------------------------------------------------------------------ */
    if (window.__sphinxLightboxInit) {
        return;
    }
    window.__sphinxLightboxInit = true;

    document.addEventListener('DOMContentLoaded', function () {

        /* ==============================================================
         * State: track which trigger opened the lightbox so we can
         * return focus to it on close.
         * ============================================================== */
        var _lastTrigger = null;

        /* ==============================================================
         * Helpers
         * ============================================================== */

        /**
         * Return all focusable elements inside a container.
         * Limits the query to elements that are visible and have a
         * non-negative tabindex.
         */
        function getFocusableElements(container) {
            var candidates = container.querySelectorAll(
                'a[href], button, input:not([type="hidden"]), select, textarea, ' +
                '[tabindex]:not([tabindex="-1"])'
            );
            var result = [];
            for (var i = 0; i < candidates.length; i++) {
                /* Skip elements hidden by CSS or with aria-hidden="true" */
                if (candidates[i].offsetParent !== null &&
                    candidates[i].getAttribute('aria-hidden') !== 'true') {
                    result.push(candidates[i]);
                }
            }
            return result;
        }

        /**
         * Find the overlay <div> that is a sibling of the given checkbox.
         */
        function getOverlayForCheckbox(checkbox) {
            var container = checkbox.closest('.lightbox-container');
            return container ? container.querySelector('.lightbox-overlay') : null;
        }

        /**
         * Find the trigger <label> that targets the given checkbox id.
         */
        function getTriggerForCheckbox(checkbox) {
            var container = checkbox.closest('.lightbox-container');
            return container ? container.querySelector('.lightbox-trigger-label') : null;
        }

        /* ==============================================================
         * 1. Keyboard activation (Enter / Space) for label controls
         *
         * <label> elements with tabindex="0" receive keyboard focus but
         * do NOT natively fire their associated checkbox toggle on
         * keydown/keypress events — only on a real click event.  We
         * must therefore manually toggle the checkbox in the keydown
         * handler.  This is the reason for the getAttribute('for') +
         * getElementById pattern rather than simply calling .click().
         * ============================================================== */
        var controls = document.querySelectorAll(
            '.lightbox-trigger-label, .lightbox-close'
        );

        controls.forEach(function (control) {
            control.addEventListener('keydown', function (e) {
                if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();

                    /* Record trigger before toggling so the change handler
                     * can pick it up for focus-return later. */
                    if (this.classList.contains('lightbox-trigger-label')) {
                        _lastTrigger = this;
                    }

                    var targetId = this.getAttribute('for');
                    if (targetId) {
                        var checkbox = document.getElementById(targetId);
                        if (checkbox) {
                            checkbox.checked = !checkbox.checked;
                            /* Manually dispatch change — programmatic
                             * property assignment does not fire it. */
                            checkbox.dispatchEvent(new Event('change'));
                        }
                    }
                }
            });
        });

        /* ==============================================================
         * 2. Escape key — close any open lightbox
         * ============================================================== */
        document.addEventListener('keydown', function (e) {
            if (e.key === 'Escape') {
                var openToggles = document.querySelectorAll(
                    '.lightbox-toggle:checked'
                );
                openToggles.forEach(function (toggle) {
                    toggle.checked = false;
                    toggle.dispatchEvent(new Event('change'));
                });
            }
        });

        /* ==============================================================
         * 3. Focus management — on open / close
         *
         * We listen for `change` events on every .lightbox-toggle
         * checkbox.  This catches all toggle sources: label click,
         * our keyboard handler, backdrop click, and Escape key.
         *
         * On open  → move focus to the close button inside the overlay
         * On close → return focus to the trigger that opened it
         * ============================================================== */
        var toggles = document.querySelectorAll('.lightbox-toggle');

        toggles.forEach(function (toggle) {
            /* Track the trigger for mouse/click-initiated opens.
             * The trigger label's native click fires *before* the
             * checkbox change event, so we capture it here. */
            var trigger = getTriggerForCheckbox(toggle);
            if (trigger) {
                trigger.addEventListener('click', function () {
                    _lastTrigger = this;
                });
            }

            toggle.addEventListener('change', function () {
                if (this.checked) {
                    /* --- OPEN --- */
                    var overlay = getOverlayForCheckbox(this);
                    if (overlay) {
                        var closeBtn = overlay.querySelector('.lightbox-close');
                        if (closeBtn) {
                            /* Defer focus so the browser completes the
                             * CSS display:none → display:flex transition
                             * before we attempt to focus an element that
                             * was previously hidden. */
                            requestAnimationFrame(function () {
                                closeBtn.focus();
                            });
                        }
                    }
                } else {
                    /* --- CLOSE --- */
                    if (_lastTrigger) {
                        _lastTrigger.focus();
                        _lastTrigger = null;
                    }
                }
            });
        });

        /* ==============================================================
         * 4. Focus trap — confine Tab within the open overlay
         *
         * When a role="dialog" aria-modal="true" overlay is visible,
         * Tab / Shift+Tab must cycle only among focusable elements
         * inside the dialog.  We attach a keydown listener to each
         * overlay that intercepts Tab and wraps at the boundaries.
         * ============================================================== */
        var overlays = document.querySelectorAll('.lightbox-overlay');

        overlays.forEach(function (overlay) {
            overlay.addEventListener('keydown', function (e) {
                if (e.key !== 'Tab') {
                    return;
                }

                var focusable = getFocusableElements(this);
                if (focusable.length === 0) {
                    e.preventDefault();
                    return;
                }

                var first = focusable[0];
                var last = focusable[focusable.length - 1];

                if (e.shiftKey) {
                    /* Shift+Tab on first element → wrap to last */
                    if (document.activeElement === first) {
                        e.preventDefault();
                        last.focus();
                    }
                } else {
                    /* Tab on last element → wrap to first */
                    if (document.activeElement === last) {
                        e.preventDefault();
                        first.focus();
                    }
                }
            });
        });
    });
})();
