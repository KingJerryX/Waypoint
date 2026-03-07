"""Extract structured page state for the LLM (what the model sees)."""
from dataclasses import dataclass
from typing import Any

# Max chars to send for visible text to keep prompts small
TEXT_PREVIEW_MAX = 8000
ELEMENTS_PREVIEW_MAX = 120


@dataclass
class PageState:
    url: str
    title: str
    text: str
    buttons: list[str]
    links: list[str]
    inputs: list[dict[str, Any]]
    elements: list[dict[str, Any]]


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

    # Elements index (stable IDs for reliable targeting in prompts/tools)
    elements: list[dict[str, Any]] = []
    element_counter = 0

    def next_element_id() -> str:
        nonlocal element_counter
        element_counter += 1
        return f"e{element_counter}"

    # Buttons: text of visible buttons
    buttons: list[str] = []
    try:
        for el in await page.query_selector_all("button, [role='button'], input[type='submit'], input[type='button']"):
            t = (await el.inner_text()).strip() or (await el.get_attribute("value") or "").strip()
            if t and t not in buttons:
                buttons.append(t[:80])
            if len(elements) < ELEMENTS_PREVIEW_MAX:
                el_id = (await el.get_attribute("id") or "").strip()[:60]
                aria = (await el.get_attribute("aria-label") or "").strip()[:80]
                name = (await el.get_attribute("name") or "").strip()[:60]
                selector = f"#{el_id}" if el_id else None
                elements.append(
                    {
                        "id": next_element_id(),
                        "kind": "button",
                        "text": t[:80] if t else None,
                        "aria_label": aria or None,
                        "name": name or None,
                        "selector": selector,
                    }
                )
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
            if len(elements) < ELEMENTS_PREVIEW_MAX:
                el_id = (await el.get_attribute("id") or "").strip()[:60]
                selector = f"#{el_id}" if el_id else None
                elements.append(
                    {
                        "id": next_element_id(),
                        "kind": "link",
                        "text": t or None,
                        "href": h[:200],
                        "selector": selector,
                    }
                )
            if len(links) >= 30:
                break
    except Exception:
        pass

    # Inputs: type, placeholder, aria-label, name, id — agent uses these to pick selectors
    inputs: list[dict[str, Any]] = []
    try:
        for el in await page.query_selector_all("input:not([type='hidden']), textarea, [contenteditable='true']"):
            typ = await el.get_attribute("type") or "text"
            placeholder = (await el.get_attribute("placeholder") or "").strip()[:60]
            name = (await el.get_attribute("name") or "").strip()[:40]
            aria_label = (await el.get_attribute("aria-label") or "").strip()[:60]
            el_id = (await el.get_attribute("id") or "").strip()[:40]
            autocomplete = (await el.get_attribute("autocomplete") or "").strip()[:40]
            entry: dict[str, Any] = {"type": typ}
            if placeholder:
                entry["placeholder"] = placeholder
            if aria_label:
                entry["aria-label"] = aria_label
            if name:
                entry["name"] = name
            if el_id:
                entry["id"] = el_id
            # For radio/checkbox, include checked state so agent knows current selection.
            if typ in ("radio", "checkbox"):
                checked = await el.is_checked()
                entry["checked"] = checked
                label_for = await el.get_attribute("id") or ""
                if label_for:
                    lbl = await page.query_selector(f"label[for='{label_for}']")
                    if lbl:
                        entry["label"] = (await lbl.inner_text()).strip()[:60]
            element_id = next_element_id()
            entry["element_id"] = element_id
            inputs.append(entry)
            if len(elements) < ELEMENTS_PREVIEW_MAX:
                selector = (
                    f"#{el_id}" if el_id else (f"[name='{name}']" if name else None)
                )
                elements.append(
                    {
                        "id": element_id,
                        "kind": "input",
                        "type": typ,
                        "placeholder": placeholder or None,
                        "aria_label": aria_label or None,
                        "name": name or None,
                        "autocomplete": autocomplete or None,
                        "selector": selector,
                    }
                )
    except Exception:
        pass

    # Select dropdowns: include current value and available options.
    try:
        for el in await page.query_selector_all("select"):
            aria_label = (await el.get_attribute("aria-label") or "").strip()[:60]
            name = (await el.get_attribute("name") or "").strip()[:40]
            el_id = (await el.get_attribute("id") or "").strip()[:40]
            selected = await el.evaluate("e => e.options[e.selectedIndex]?.text || ''")
            options = await el.evaluate("e => Array.from(e.options).map(o => o.text).slice(0, 10)")
            entry = {
                "type": "select",
                "value": str(selected)[:40],
                "options": [str(o)[:40] for o in options],
            }
            if aria_label:
                entry["aria-label"] = aria_label
            if name:
                entry["name"] = name
            if el_id:
                entry["id"] = el_id
            element_id = next_element_id()
            entry["element_id"] = element_id
            inputs.append(entry)
            if len(elements) < ELEMENTS_PREVIEW_MAX:
                selector = f"#{el_id}" if el_id else (f"[name='{name}']" if name else None)
                elements.append(
                    {
                        "id": element_id,
                        "kind": "input",
                        "type": "select",
                        "aria_label": aria_label or None,
                        "name": name or None,
                        "selector": selector,
                    }
                )
    except Exception:
        pass

    return PageState(
        url=url,
        title=title,
        text=text,
        buttons=buttons,
        links=links,
        inputs=inputs,
        elements=elements,
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
        "elements": state.elements[:80],
    }
