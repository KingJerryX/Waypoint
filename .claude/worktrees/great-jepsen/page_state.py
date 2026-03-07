"""Extract structured page state for the LLM (what the model sees)."""
from dataclasses import dataclass
from typing import Any

# Max chars to send for visible text to keep prompts small
TEXT_PREVIEW_MAX = 8000


@dataclass
class PageState:
    url: str
    title: str
    text: str
    buttons: list[str]
    links: list[str]
    inputs: list[dict[str, Any]]


async def get_page_state(page: Any, text_max: int = TEXT_PREVIEW_MAX) -> PageState:
    """
    Build a structured snapshot: url, title, visible text preview, buttons, links, inputs.
    Uses the Playwright page object; no AI here.
    """
    url = page.url
    title = await page.title()

    # Visible text (main content)
    try:
        body = await page.query_selector("body")
        text = await body.inner_text() if body else ""
    except Exception:
        text = ""
    text = (text or "").strip()[:text_max]
    if len((text or "").strip()) > text_max:
        text = text + "\n...[truncated]"

    # Buttons: text of visible buttons
    buttons: list[str] = []
    try:
        for el in await page.query_selector_all("button, [role='button'], input[type='submit'], input[type='button']"):
            t = (await el.inner_text()).strip() or (await el.get_attribute("value") or "").strip()
            if t and t not in buttons:
                buttons.append(t[:80])
    except Exception:
        pass

    # Links: text and href (truncated)
    links: list[str] = []
    try:
        for el in await page.query_selector_all("a[href]"):
            t = (await el.inner_text()).strip()[:60]
            h = await el.get_attribute("href") or ""
            if h.startswith("#") or not h.strip():
                continue
            if t:
                links.append(f"{t} ({h[:50]})")
            else:
                links.append(h[:60])
            if len(links) >= 30:
                break
    except Exception:
        pass

    # Inputs: type and placeholder
    inputs: list[dict[str, Any]] = []
    try:
        for el in await page.query_selector_all("input:not([type='hidden']), textarea"):
            typ = await el.get_attribute("type") or "text"
            placeholder = (await el.get_attribute("placeholder") or "").strip()[:60]
            name = (await el.get_attribute("name") or "").strip()[:40]
            inputs.append({"type": typ, "placeholder": placeholder or None, "name": name or None})
    except Exception:
        pass

    return PageState(
        url=url,
        title=title,
        text=text,
        buttons=buttons,
        links=links,
        inputs=inputs,
    )


def page_state_to_dict(state: PageState) -> dict[str, Any]:
    """For JSON logging and LLM context."""
    return {
        "url": state.url,
        "title": state.title,
        "text": state.text,
        "buttons": state.buttons,
        "links": state.links[:20],
        "inputs": state.inputs,
    }
