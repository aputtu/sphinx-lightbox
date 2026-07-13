"""Browser-level keyboard and focus checks for the generated lightbox docs."""

from __future__ import annotations

import argparse
import asyncio
import re
from pathlib import Path

from playwright.async_api import Browser, Locator, Page, async_playwright


async def _wait_for_focus(
    page: Page,
    locator: Locator,
) -> None:
    handle = await locator.element_handle()
    assert handle is not None
    await page.wait_for_function(
        "element => document.activeElement === element",
        arg=handle,
    )


async def _assert_focused(
    page: Page,
    locator: Locator,
) -> None:
    await _wait_for_focus(page, locator)
    state = await locator.evaluate(
        """element => {
            const rect = element.getBoundingClientRect();
            const style = getComputedStyle(element);
            return {
                rendered: element.getClientRects().length > 0,
                inViewport: rect.bottom > 0 && rect.right > 0 &&
                    rect.top < innerHeight && rect.left < innerWidth,
                notObscured: [
                    [Math.max(0, rect.left), Math.max(0, rect.top)],
                    [Math.min(innerWidth - 1, rect.right - 1), Math.max(0, rect.top)],
                    [Math.max(0, rect.left), Math.min(innerHeight - 1, rect.bottom - 1)],
                    [Math.min(innerWidth - 1, rect.right - 1),
                        Math.min(innerHeight - 1, rect.bottom - 1)],
                    [Math.max(0, Math.min(innerWidth - 1, rect.left + rect.width / 2)),
                        Math.max(0, Math.min(innerHeight - 1, rect.top + rect.height / 2))],
                ].some(([x, y]) => {
                    const hit = document.elementFromPoint(x, y);
                    return hit === element || element.contains(hit);
                }),
                outlineStyle: style.outlineStyle,
                outlineWidth: parseFloat(style.outlineWidth),
            };
        }"""
    )
    assert state["rendered"], "focused control must be rendered"
    assert state["inViewport"], "focused control must not be obscured off-screen"
    assert state["notObscured"], "focused control must not be entirely covered"
    assert state["outlineStyle"] != "none", "focus indicator must be visible"
    assert state["outlineWidth"] > 0, "focus indicator must have non-zero width"


async def _exercise(page: Page, index_path: Path) -> None:
    await page.goto(index_path.resolve().as_uri())

    triggers = page.locator(".lightbox-trigger-control")
    assert await triggers.count() >= 2, "browser fixture needs a gallery"
    first_trigger = triggers.first
    first_label = first_trigger.locator("xpath=..")
    first_container = first_trigger.locator("xpath=../..")
    first_toggle = first_container.locator(".lightbox-toggle")
    first_overlay = first_container.locator(".lightbox-overlay")
    first_close = first_overlay.locator(".lightbox-close")

    # WCAG 2.4.7 / 2.4.11: keyboard focus remains visible and is not
    # clipped by the lightbox container.
    assert await first_trigger.get_attribute("role") == "button"
    assert await first_close.get_attribute("role") == "button"
    # The thumbnail is decorative because the custom button owns the
    # accessible name; the enlarged image retains the author's alt text.
    assert await first_trigger.locator("img").get_attribute("alt") == ""
    overlay_alt = await first_overlay.locator(".lightbox-content img").get_attribute("alt")
    assert overlay_alt
    assert (
        await first_label.get_by_role(
            "button", name=f"Enlarge image: {overlay_alt}", exact=True
        ).count()
        == 1
    )
    assert await first_container.evaluate(
        "element => getComputedStyle(element).overflow === 'visible'"
    )

    # Native label activation remains the pointer path when JavaScript is
    # enabled, while the change handler still moves and restores focus.
    await first_trigger.click()
    await first_overlay.wait_for(state="visible")
    await _wait_for_focus(page, first_close)
    await first_close.click()
    await first_overlay.wait_for(state="hidden")
    await _wait_for_focus(page, first_trigger)

    # Custom controls with role="button" support both Space and Enter. Verify
    # Space on the trigger and close control before exercising Escape below.
    await first_trigger.focus()
    await page.keyboard.press("Space")
    await first_overlay.wait_for(state="visible")
    await _assert_focused(page, first_close)
    await page.keyboard.press("Space")
    await first_overlay.wait_for(state="hidden")
    await _assert_focused(page, first_trigger)

    # WCAG 2.1.1 / 2.4.3 and the modal-dialog pattern: keyboard activation
    # moves focus into the dialog; Escape closes it and restores focus to
    # the invoking control.
    await page.keyboard.press("Enter")
    await first_overlay.wait_for(state="visible")
    assert await first_toggle.is_checked()
    assert await first_overlay.get_by_role("button", name="Close lightbox", exact=True).count() == 1
    await _assert_focused(page, first_close)
    for control in (first_close, first_overlay.locator(".lightbox-gallery-control").first):
        bounds = await control.bounding_box()
        assert bounds is not None
        assert bounds["width"] >= 24 and bounds["height"] >= 24, (
            "lightbox controls must meet WCAG 2.5.8 minimum target size"
        )
    await page.keyboard.press("Escape")
    await first_overlay.wait_for(state="hidden")
    assert not await first_toggle.is_checked()
    await _assert_focused(page, first_trigger)

    # Regression: switching A -> B must not consume B's focus-return target
    # when A dispatches its synchronous close event.
    await page.keyboard.press("Enter")
    await first_overlay.wait_for(state="visible")
    await _assert_focused(page, first_close)
    gallery_next = first_overlay.locator(".lightbox-gallery-next")
    target_id = await gallery_next.get_attribute("data-lightbox-target")
    assert target_id
    target_toggle = page.locator(f'[id="{target_id}"]')
    target_container = target_toggle.locator("xpath=..")
    target_trigger = target_container.locator(".lightbox-trigger-control")
    target_overlay = target_container.locator(".lightbox-overlay")
    target_close = target_overlay.locator(".lightbox-close")

    await gallery_next.focus()
    await page.keyboard.press("Enter")
    await target_overlay.wait_for(state="visible")
    assert await target_toggle.is_checked()
    assert not await first_toggle.is_checked()
    await _assert_focused(page, target_close)
    await page.keyboard.press("Escape")
    await target_overlay.wait_for(state="hidden")
    await _assert_focused(page, target_trigger)

    # WCAG 2.1.2: a modal may contain Tab focus while open, but forward and
    # reverse navigation must remain operable. This also proves fixed-position
    # controls are not filtered out of the focus trap.
    await page.keyboard.press("Enter")
    await target_overlay.wait_for(state="visible")
    await _assert_focused(page, target_close)
    gallery_controls = target_overlay.locator(".lightbox-gallery-control")
    assert await gallery_controls.count() >= 1
    first_control = gallery_controls.first
    await page.keyboard.press("Tab")
    await _assert_focused(page, first_control)
    await page.keyboard.press("Shift+Tab")
    await _assert_focused(page, target_close)

    last_control = gallery_controls.last
    await last_control.focus()
    await page.keyboard.press("Tab")
    await _assert_focused(page, target_close)
    await page.keyboard.press("Shift+Tab")
    await _assert_focused(page, last_control)
    await page.keyboard.press("Escape")
    await target_overlay.wait_for(state="hidden")
    await _assert_focused(page, target_trigger)

    assert await page.locator(".lightbox-toggle:checked").count() == 0
    assert await page.locator(".lightbox-overlay:visible").count() == 0


async def _exercise_css_fallback(browser: Browser, index_path: Path) -> None:
    """Verify that native labels still operate the lightbox without JavaScript."""
    context = await browser.new_context(
        java_script_enabled=False,
        viewport={"width": 1280, "height": 800},
    )
    try:
        page = await context.new_page()
        await page.goto(index_path.resolve().as_uri())
        container = page.locator(".lightbox-container").first
        toggle = container.locator(".lightbox-toggle")
        overlay = container.locator(".lightbox-overlay")

        await container.locator(".lightbox-trigger-control").click()
        assert await toggle.is_checked()
        await overlay.wait_for(state="visible")

        await overlay.locator(".lightbox-close").click()
        assert not await toggle.is_checked()
        await overlay.wait_for(state="hidden")
    finally:
        await context.close()


async def _exercise_single_image(browser: Browser, index_path: Path) -> None:
    """Verify plain open-to-Escape focus restoration without gallery state."""
    single_image_path = index_path.with_name("accessibility.html")
    assert single_image_path.is_file(), "browser fixture needs the accessibility page"

    page = await browser.new_page(viewport={"width": 1280, "height": 800})
    page.set_default_timeout(10_000)
    try:
        await page.goto(single_image_path.resolve().as_uri())
        triggers = page.locator(".lightbox-trigger-control")
        assert await triggers.count() == 1, "browser fixture must contain one lightbox"

        trigger = triggers.first
        container = trigger.locator("xpath=../..")
        overlay = container.locator(".lightbox-overlay")
        close = overlay.locator(".lightbox-close")
        assert await overlay.locator(".lightbox-gallery-control").count() == 0

        await trigger.focus()
        await page.keyboard.press("Enter")
        await overlay.wait_for(state="visible")
        await _assert_focused(page, close)
        await page.keyboard.press("Escape")
        await overlay.wait_for(state="hidden")
        await _assert_focused(page, trigger)
    finally:
        await page.close()


async def _exercise_late_script_load(browser: Browser, index_path: Path) -> None:
    """Verify initialization when the enhancement is loaded after DOMContentLoaded."""
    html = index_path.read_text(encoding="utf-8")
    html = re.sub(
        r'\s*<script\b[^>]*\bsrc="[^"]*lightbox\.js[^"]*"[^>]*></script>',
        "",
        html,
    )
    base_url = f"{index_path.parent.resolve().as_uri()}/"
    html = html.replace("<head>", f'<head><base href="{base_url}">', 1)

    page = await browser.new_page(viewport={"width": 1280, "height": 800})
    page.set_default_timeout(10_000)
    try:
        await page.set_content(html, wait_until="load")
        assert not await page.evaluate("Boolean(window.__sphinxLightboxInit)")
        script_path = (index_path.parent / "_static" / "lightbox.js").resolve()
        await page.add_script_tag(path=str(script_path))

        container = page.locator(".lightbox-container").first
        trigger = container.locator(".lightbox-trigger-control")
        toggle = container.locator(".lightbox-toggle")
        close = container.locator(".lightbox-close")
        await trigger.focus()
        await page.keyboard.press("Enter")
        assert await toggle.is_checked()
        await _assert_focused(page, close)
    finally:
        await page.close()


async def _exercise_reflow(browser: Browser, index_path: Path) -> None:
    """Verify WCAG 1.4.10 reflow at a 320 CSS-pixel viewport."""
    page = await browser.new_page(viewport={"width": 320, "height": 800})
    page.set_default_timeout(10_000)
    try:
        for html_path in sorted(index_path.parent.rglob("*.html")):
            await page.goto(html_path.resolve().as_uri())
            dimensions = await page.evaluate(
                """() => ({
                    clientWidth: document.documentElement.clientWidth,
                    scrollWidth: document.documentElement.scrollWidth,
                })"""
            )
            assert dimensions["scrollWidth"] <= dimensions["clientWidth"] + 1, (
                f"{html_path.relative_to(index_path.parent)} requires horizontal scrolling "
                "at 320 CSS pixels"
            )
            if html_path == index_path:
                distorted_images = await page.locator(
                    'img[data-docs-intrinsic-size="true"]'
                ).evaluate_all(
                    """images => images.filter(image => {
                        const rect = image.getBoundingClientRect();
                        if (rect.width === 0 || rect.height === 0) {
                            return false;
                        }
                        const naturalRatio = image.naturalWidth / image.naturalHeight;
                        const renderedRatio = rect.width / rect.height;
                        return Math.abs(naturalRatio - renderedRatio) > 0.01;
                    }).length"""
                )
                assert distorted_images == 0, (
                    "intrinsic dimensions must not distort percentage-sized documentation images"
                )
                title_lines = await page.locator("div.body h1").evaluate(
                    """heading => {
                        const range = document.createRange();
                        const text = heading.firstChild;
                        const lines = [];
                        for (let index = 0; index < text.length; index += 1) {
                            range.setStart(text, index);
                            range.setEnd(text, index + 1);
                            const rect = range.getBoundingClientRect();
                            const line = lines.find(item => Math.abs(item.top - rect.top) < 1);
                            if (line) {
                                line.text += text.data[index];
                            } else {
                                lines.push({top: rect.top, text: text.data[index]});
                            }
                        }
                        return lines.map(item => item.text.trim()).filter(Boolean);
                    }"""
                )
                assert "Documentation" in title_lines, (
                    "the index title must keep 'Documentation' intact at 320 CSS pixels; "
                    f"rendered lines were {title_lines!r}"
                )
    finally:
        await page.close()


async def _run(index_path: Path) -> None:
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch()
        try:
            for viewport in (
                {"width": 1280, "height": 800},
                {"width": 390, "height": 844},
            ):
                page = await browser.new_page(viewport=viewport)
                page.set_default_timeout(10_000)
                try:
                    await _exercise(page, index_path)
                finally:
                    await page.close()
            await _exercise_css_fallback(browser, index_path)
            await _exercise_single_image(browser, index_path)
            await _exercise_late_script_load(browser, index_path)
            await _exercise_reflow(browser, index_path)
        finally:
            await browser.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "index",
        nargs="?",
        type=Path,
        default=Path("docs/_build/html/index.html"),
        help="generated documentation index to exercise",
    )
    args = parser.parse_args()
    asyncio.run(_run(args.index))


if __name__ == "__main__":
    main()
