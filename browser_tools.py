"""Playwright browser control — deterministic, no AI. Used by the agent loop."""
import asyncio
from pathlib import Path
from typing import Any, Optional

from playwright.async_api import async_playwright, Browser, BrowserContext, Page

from page_state import get_page_state, page_state_to_dict
from site_adapters import get_site_adapter

# Default timeout for navigation and actions
NAV_TIMEOUT_MS = 15000
ACTION_TIMEOUT_MS = 10000
DEFAULT_WAIT_AFTER_LOAD_MS = 700

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
        self._element_index: dict[str, str] = {}

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
        # Close in order, swallowing errors so cleanup always completes
        for coro, obj in [
            (lambda o: o.close(), self._context),
            (lambda o: o.close(), self._browser),
            (lambda o: o.stop(),  self._pw),
        ]:
            if obj is not None:
                try:
                    await coro(obj)
                except Exception:
                    pass
        # Force-kill the browser process if it's still alive (prevents zombie chrome.exe)
        try:
            if self._browser is not None:
                proc = getattr(self._browser, "process", None)
                if proc is not None and proc.returncode is None:
                    proc.kill()
        except Exception:
            pass

    @property
    def page(self) -> Page:
        if self._page is None:
            raise RuntimeError("Browser not started; use async with BrowserController()")
        return self._page

    # --- Tools (return dict with result or error for the agent) ---

    def _cache_element_index(self, state_dict: dict[str, Any]) -> None:
        """Store element-id -> selector map from latest page state."""
        self._element_index = {}
        for el in state_dict.get("elements", []) or []:
            el_id = str(el.get("id", "")).strip()
            selector = str(el.get("selector", "")).strip()
            if el_id and selector:
                self._element_index[el_id] = selector

    def _resolve_selector(self, selector_or_element_id: str) -> str:
        """Allow selector strings or element IDs (e.g. 'e12' or 'elem:e12')."""
        raw = (selector_or_element_id or "").strip()
        if raw.startswith("elem:"):
            raw = raw.split(":", 1)[1].strip()
        if raw in self._element_index:
            return self._element_index[raw]
        return selector_or_element_id

    async def open_url(self, url: str) -> dict[str, Any]:
        """Open a URL and wait for load. Returns page state summary or error."""
        try:
            is_blank = url in ("about:blank", "", None)
            wait_until = "commit" if is_blank else "domcontentloaded"
            await self.page.goto(url, wait_until=wait_until, timeout=NAV_TIMEOUT_MS)
            if not is_blank:
                await asyncio.sleep(DEFAULT_WAIT_AFTER_LOAD_MS / 1000.0)
            state = await get_page_state(self.page)
            out = page_state_to_dict(state)
            self._cache_element_index(out)
            return {"ok": True, "state": out}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    async def get_page_state(self) -> dict[str, Any]:
        """Return current page state (url, title, text, buttons, links, inputs)."""
        try:
            state = await get_page_state(self.page)
            out = page_state_to_dict(state)
            self._cache_element_index(out)
            return {"ok": True, "state": out}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    async def click(self, text_or_selector: str) -> dict[str, Any]:
        """Click element by visible text or selector. Prefer text match for buttons/links."""
        text_or_selector = self._resolve_selector(text_or_selector)
        _is_css = text_or_selector.startswith(("#", ".", "[", "/")) or " > " in text_or_selector

        # (strategy, timeout_ms)
        strategies: list[tuple] = []

        if _is_css:
            # Looks like a real selector — try it directly first
            strategies.append((lambda: self.page.locator(text_or_selector).first, 3000))

        # ARIA role matches (fast-fail when role doesn't exist)
        t = text_or_selector
        strategies += [
            (lambda: self.page.get_by_role("tab",      name=t).first,     1500),
            (lambda: self.page.get_by_role("link",     name=t).first,     1500),
            (lambda: self.page.get_by_role("button",   name=t).first,     1500),
            (lambda: self.page.get_by_role("menuitem", name=t).first,     1500),
            # Visible interactive elements including dropdown list items
            (lambda: self.page.locator(
                "a, button, [role='tab'], [role='link'], [role='menuitem'], [role='option'], "
                "li, [role='listitem'], [role='radio'], label, [role='treeitem']"
            ).filter(has_text=t).first,                                    3000),
        ]

        last_err = ""
        for make_locator, timeout in strategies:
            try:
                await make_locator().click(timeout=timeout)
                await asyncio.sleep(0.3)
                state = await get_page_state(self.page)
                out = page_state_to_dict(state)
                self._cache_element_index(out)
                return {"ok": True, "state": out}
            except Exception as e:
                last_err = str(e)
                continue
        return {"ok": False, "error": f"click failed after all strategies: {last_err}"}

    async def click_search_button(self) -> dict[str, Any]:
        """
        Click a likely search/submit button.
        Includes YouTube-specific selectors first, then generic search/submit controls.
        """
        selectors = [
            # YouTube
            "button#search-icon-legacy",
            "ytd-searchbox button#search-icon-legacy",
            "yt-icon-button#search-icon-legacy",
            "button[aria-label*='Search' i]",
            # Generic search buttons
            "button[type='submit']",
            "input[type='submit']",
            "[role='button'][aria-label*='search' i]",
            "[title*='search' i]",
        ]
        for selector in selectors:
            result = await self.click(selector)
            if result.get("ok"):
                result["clicked"] = selector
                return result

        labels = ["Search", "Go", "Find", "Submit"]
        for label in labels:
            result = await self.click(label)
            if result.get("ok"):
                result["clicked"] = label
                return result

        return {"ok": False, "error": "Could not find a search/submit button to click"}

    async def type_text(self, selector: str, value: str) -> dict[str, Any]:
        """Type into an input using keyboard events (triggers autocomplete in SPAs)."""
        selector = self._resolve_selector(selector)
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
            await self.page.keyboard.type(value, delay=40)
            await asyncio.sleep(0.3)

            # Auto-submit search inputs so the agent never has to guess
            _is_search = any(kw in selector.lower() for kw in ("search", "query", "q", "find", "keyword"))
            if _is_search:
                await self.page.keyboard.press("Enter")
                await asyncio.sleep(1.2)  # wait for results page to load

            state = await get_page_state(self.page)
            out = page_state_to_dict(state)
            self._cache_element_index(out)
            return {"ok": True, "state": out}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    async def press_key(self, key: str) -> dict[str, Any]:
        """Press a keyboard key (e.g. Enter, Tab, Escape, ArrowDown, ArrowUp)."""
        try:
            await self.page.keyboard.press(key)
            # Enter/Return may trigger navigation — wait longer for page to settle
            wait = 1.2 if key in ("Enter", "Return") else 0.3
            await asyncio.sleep(wait)
            state = await get_page_state(self.page)
            out = page_state_to_dict(state)
            self._cache_element_index(out)
            return {"ok": True, "state": out}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    async def scroll_down(self) -> dict[str, Any]:
        """Scroll the page down and return updated state."""
        try:
            await self.page.evaluate("window.scrollBy(0, window.innerHeight * 0.8)")
            await asyncio.sleep(0.5)
            state = await get_page_state(self.page)
            out = page_state_to_dict(state)
            self._cache_element_index(out)
            return {"ok": True, "state": out}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    async def submit_search(self, prefer_enter: bool = True) -> dict[str, Any]:
        """Deterministically submit a filled search input using site adapter logic."""
        adapter = get_site_adapter(self.page.url)
        result = await adapter.submit_search(self.page, prefer_enter=prefer_enter)
        if not result.ok:
            return {"ok": False, "error": result.error or "submit_search failed"}
        await asyncio.sleep(1.0)
        state = await get_page_state(self.page)
        out = page_state_to_dict(state)
        self._cache_element_index(out)
        return {"ok": True, "state": out, "method": result.method}

    async def sort_by_view_count(self) -> dict[str, Any]:
        """Deterministically sort supported search results by view count (site adapter)."""
        adapter = get_site_adapter(self.page.url)
        result = await adapter.sort_by_view_count(self.page)
        if not result.ok:
            return {"ok": False, "error": result.error or "sort_by_view_count failed"}
        await asyncio.sleep(1.0)
        state = await get_page_state(self.page)
        out = page_state_to_dict(state)
        self._cache_element_index(out)
        return {"ok": True, "state": out, "method": result.method}

    async def open_top_result(self) -> dict[str, Any]:
        """Open top result for supported sites (site adapter)."""
        adapter = get_site_adapter(self.page.url)
        result = await adapter.open_top_result(self.page)
        if not result.ok:
            return {"ok": False, "error": result.error or "open_top_result failed"}
        await asyncio.sleep(1.0)
        state = await get_page_state(self.page)
        out = page_state_to_dict(state)
        self._cache_element_index(out)
        return {"ok": True, "state": out, "method": result.method}

    async def take_screenshot(self, name: str = "screenshot") -> dict[str, Any]:
        """Save a screenshot to logs/ and return path."""
        SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
        path = SCREENSHOT_DIR / f"{name}.png"
        try:
            await self.page.screenshot(path=str(path))
            return {"ok": True, "path": str(path)}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    async def wait_for_settled(self, timeout_ms: int = 5000) -> None:
        """Wait for the page to finish navigating/loading after human interaction."""
        try:
            await self.page.wait_for_load_state("domcontentloaded", timeout=timeout_ms)
        except Exception:
            pass
        await asyncio.sleep(1.5)

    async def screenshot_b64(self) -> str:
        """Take a screenshot and return as base64-encoded PNG string."""
        import base64
        data = await self.page.screenshot(type="png")
        return base64.b64encode(data).decode()
