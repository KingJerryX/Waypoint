"""Site-specific deterministic helpers for brittle UI flows."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class SubmitResult:
    ok: bool
    method: str
    error: Optional[str] = None


class BaseSiteAdapter:
    name = "base"

    def matches(self, url: str) -> bool:
        return False

    async def submit_search(self, page: Any, prefer_enter: bool = True) -> SubmitResult:
        """Default submit behavior for most sites."""
        if prefer_enter:
            try:
                await page.keyboard.press("Enter")
                return SubmitResult(ok=True, method="enter")
            except Exception:
                pass
        try:
            await page.click("button[type='submit']", timeout=1500)
            return SubmitResult(ok=True, method="button[type='submit']")
        except Exception as e:
            return SubmitResult(ok=False, method="none", error=str(e))

    async def sort_by_view_count(self, page: Any) -> SubmitResult:
        """Optional deterministic sort flow; unsupported by default."""
        return SubmitResult(ok=False, method="unsupported", error="sort_by_view_count unsupported")

    async def open_top_result(self, page: Any) -> SubmitResult:
        """Optional deterministic top-result open flow; unsupported by default."""
        return SubmitResult(ok=False, method="unsupported", error="open_top_result unsupported")


class YouTubeAdapter(BaseSiteAdapter):
    name = "youtube"

    def matches(self, url: str) -> bool:
        u = (url or "").lower()
        return "youtube.com" in u or "youtu.be" in u

    async def submit_search(self, page: Any, prefer_enter: bool = True) -> SubmitResult:
        # YouTube is reliable with Enter in search box. Fallback to magnifier button.
        if prefer_enter:
            try:
                await page.keyboard.press("Enter")
                return SubmitResult(ok=True, method="enter")
            except Exception:
                pass

        selectors = [
            "button#search-icon-legacy",
            "ytd-searchbox button#search-icon-legacy",
            "yt-icon-button#search-icon-legacy",
            "button[aria-label*='Search' i]",
        ]
        for selector in selectors:
            try:
                await page.click(selector, timeout=1500)
                return SubmitResult(ok=True, method=selector)
            except Exception:
                continue
        return SubmitResult(ok=False, method="none", error="youtube search submit control not found")

    async def sort_by_view_count(self, page: Any) -> SubmitResult:
        try:
            await page.get_by_role("button", name="Filters").first.click(timeout=2500)
        except Exception as e:
            return SubmitResult(ok=False, method="filters", error=str(e))

        sort_selectors = [
            "text=Sort by",
            "ytd-search-filter-group-renderer:has-text('Sort by')",
        ]
        sort_opened = False
        for selector in sort_selectors:
            try:
                await page.locator(selector).first.click(timeout=2500)
                sort_opened = True
                break
            except Exception:
                continue
        if not sort_opened:
            # Sometimes sort options are already visible after clicking Filters.
            pass

        view_count_selectors = [
            "text=View count",
            "ytd-search-filter-renderer:has-text('View count')",
        ]
        for selector in view_count_selectors:
            try:
                await page.locator(selector).first.click(timeout=2500)
                return SubmitResult(ok=True, method="view_count")
            except Exception:
                continue
        return SubmitResult(ok=False, method="view_count", error="could not select View count")

    async def open_top_result(self, page: Any) -> SubmitResult:
        selectors = [
            "ytd-video-renderer a#video-title",
            "a#video-title",
        ]
        for selector in selectors:
            try:
                await page.locator(selector).first.click(timeout=3000)
                return SubmitResult(ok=True, method=selector)
            except Exception:
                continue
        return SubmitResult(ok=False, method="none", error="top video result link not found")


def get_site_adapter(url: str) -> BaseSiteAdapter:
    adapters = [YouTubeAdapter()]
    for adapter in adapters:
        if adapter.matches(url):
            return adapter
    return BaseSiteAdapter()

