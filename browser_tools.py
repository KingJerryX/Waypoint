"""Playwright browser control — deterministic, no AI. Used by the agent loop."""
import asyncio
from pathlib import Path
from typing import Any, Optional

from playwright.async_api import async_playwright, Browser, BrowserContext, Page

from page_state import get_page_state, page_state_to_dict

# Default timeout for navigation and actions
NAV_TIMEOUT_MS = 15000
ACTION_TIMEOUT_MS = 10000
DEFAULT_WAIT_AFTER_LOAD_MS = 1500

# Screenshots saved here on failure or on done
SCREENSHOT_DIR = Path(__file__).resolve().parent / "logs"


class BrowserController:
    """Holds Playwright browser/context/page and exposes tool implementations."""

    def __init__(self, headless: bool = True):
        self._headless = headless
        self._pw: Optional[Any] = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None

    async def __aenter__(self) -> "BrowserController":
        self._pw = await async_playwright().start()
        self._browser = await self._pw.chromium.launch(
            headless=self._headless,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-infobars",
            ],
        )
        self._context = await self._browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            locale="en-US",
            ignore_https_errors=True,
        )
        # Remove webdriver fingerprint
        await self._context.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )
        self._page = await self._context.new_page()
        self._page.set_default_timeout(ACTION_TIMEOUT_MS)
        return self

    async def __aexit__(self, *args: Any) -> None:
        if self._context:
            await self._context.close()
        if self._browser:
            await self._browser.close()
        if self._pw:
            await self._pw.stop()

    @property
    def page(self) -> Page:
        if self._page is None:
            raise RuntimeError("Browser not started; use async with BrowserController()")
        return self._page

    # --- Tools (return dict with result or error for the agent) ---

    async def open_url(self, url: str) -> dict[str, Any]:
        """Open a URL and wait for load. Returns page state summary or error."""
        try:
            await self.page.goto(url, wait_until="domcontentloaded", timeout=NAV_TIMEOUT_MS)
            await asyncio.sleep(DEFAULT_WAIT_AFTER_LOAD_MS / 1000.0)
            state = await get_page_state(self.page)
            return {"ok": True, "state": page_state_to_dict(state)}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    async def get_page_state(self) -> dict[str, Any]:
        """Return current page state (url, title, text, buttons, links, inputs)."""
        try:
            state = await get_page_state(self.page)
            return {"ok": True, "state": page_state_to_dict(state)}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    async def click(self, text_or_selector: str) -> dict[str, Any]:
        """Click element by visible text or selector. Prefer text match for buttons/links."""
        try:
            # Try as selector first (e.g. "#submit")
            try:
                await self.page.click(text_or_selector, timeout=3000)
            except Exception:
                # Fallback: click by text (button or link containing this text)
                await self.page.get_by_role("button", name=text_or_selector).first.click(timeout=3000)
            await asyncio.sleep(0.5)
            state = await get_page_state(self.page)
            return {"ok": True, "state": page_state_to_dict(state)}
        except Exception as e1:
            try:
                await self.page.locator(f"text={text_or_selector}").first.click(timeout=3000)
                await asyncio.sleep(0.5)
                state = await get_page_state(self.page)
                return {"ok": True, "state": page_state_to_dict(state)}
            except Exception as e2:
                return {"ok": False, "error": f"click failed: {e1}; fallback: {e2}"}

    async def type_text(self, selector: str, value: str) -> dict[str, Any]:
        """Type into an input using keyboard events (triggers autocomplete in SPAs)."""
        try:
            # Try multiple strategies to find and focus the element
            clicked = False
            for attempt in [
                lambda: self.page.locator(selector).first,
                lambda: self.page.get_by_placeholder(selector).first,
                lambda: self.page.get_by_label(selector).first,
                lambda: self.page.locator(f"[aria-label='{selector}']").first,
                lambda: self.page.locator(f"[aria-label*='{selector}']").first,
                lambda: self.page.locator(f"#{selector}").first,
                lambda: self.page.locator(f"[name='{selector}']").first,
            ]:
                try:
                    el = attempt()
                    await el.click(timeout=2000)
                    await asyncio.sleep(0.3)
                    # Triple-click to select all text already in the field (not the whole page)
                    await el.click(click_count=3, timeout=1000)
                    clicked = True
                    break
                except Exception:
                    continue

            if not clicked:
                return {"ok": False, "error": f"Could not find input: '{selector}'. Try get_page_state to see available inputs, then use the exact placeholder or label text."}

            # Type character-by-character to fire events (triggers autocomplete etc.)
            await self.page.keyboard.type(value, delay=60)
            await asyncio.sleep(1.2)  # Wait for autocomplete to appear
            state = await get_page_state(self.page)
            return {"ok": True, "state": page_state_to_dict(state)}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    async def press_key(self, key: str) -> dict[str, Any]:
        """Press a keyboard key (e.g. Enter, Tab, Escape, ArrowDown, ArrowUp)."""
        try:
            await self.page.keyboard.press(key)
            await asyncio.sleep(0.6)
            state = await get_page_state(self.page)
            return {"ok": True, "state": page_state_to_dict(state)}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    async def scroll_down(self) -> dict[str, Any]:
        """Scroll the page down and return updated state."""
        try:
            await self.page.evaluate("window.scrollBy(0, window.innerHeight * 0.8)")
            await asyncio.sleep(0.5)
            state = await get_page_state(self.page)
            return {"ok": True, "state": page_state_to_dict(state)}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    async def take_screenshot(self, name: str = "screenshot") -> dict[str, Any]:
        """Save a screenshot to logs/ and return path."""
        SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
        path = SCREENSHOT_DIR / f"{name}.png"
        try:
            await self.page.screenshot(path=str(path))
            return {"ok": True, "path": str(path)}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    async def screenshot_b64(self) -> str:
        """Take a screenshot and return as base64-encoded PNG string."""
        import base64
        data = await self.page.screenshot(type="png")
        return base64.b64encode(data).decode()
