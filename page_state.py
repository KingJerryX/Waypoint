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
    dropdown_options: list[str]


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

    # Inputs: type, placeholder, aria-label, name, id — agent uses these to pick selectors
    inputs: list[dict[str, Any]] = []
    try:
        for el in await page.query_selector_all("input:not([type='hidden']), textarea, [contenteditable='true']"):
            typ = await el.get_attribute("type") or "text"
            placeholder = (await el.get_attribute("placeholder") or "").strip()[:60]
            name = (await el.get_attribute("name") or "").strip()[:40]
            aria_label = (await el.get_attribute("aria-label") or "").strip()[:60]
            el_id = (await el.get_attribute("id") or "").strip()[:40]
            entry: dict[str, Any] = {"type": typ}
            if placeholder:
                entry["placeholder"] = placeholder
            if aria_label:
                entry["aria-label"] = aria_label
            if name:
                entry["name"] = name
            if el_id:
                entry["id"] = el_id
            # For radio/checkbox, include checked state so agent knows current selection
            if typ in ("radio", "checkbox"):
                checked = await el.is_checked()
                entry["checked"] = checked
                label_for = await el.get_attribute("id") or ""
                if label_for:
                    lbl = await page.query_selector(f"label[for='{label_for}']")
                    if lbl:
                        entry["label"] = (await lbl.inner_text()).strip()[:60]
            inputs.append(entry)
    except Exception:
        pass

    # Select dropdowns: include current value and available options
    try:
        for el in await page.query_selector_all("select"):
            aria_label = (await el.get_attribute("aria-label") or "").strip()[:60]
            name = (await el.get_attribute("name") or "").strip()[:40]
            el_id = (await el.get_attribute("id") or "").strip()[:40]
            # Current selected option
            selected = await el.evaluate("e => e.options[e.selectedIndex]?.text || ''")
            options = await el.evaluate("e => Array.from(e.options).map(o => o.text).slice(0, 10)")
            entry: dict[str, Any] = {"type": "select", "value": str(selected)[:40], "options": [str(o)[:40] for o in options]}
            if aria_label:
                entry["aria-label"] = aria_label
            if name:
                entry["name"] = name
            if el_id:
                entry["id"] = el_id
            inputs.append(entry)
    except Exception:
        pass

    # Dropdown / autocomplete options: visible [role="option"] and [role="menuitem"] elements.
    # These are only present when a dropdown or autocomplete list is open — critical for
    # the agent to see what's available after clicking a combobox or typing into a location field.
    dropdown_options: list[str] = []
    try:
        for el in await page.query_selector_all(
            "[role='option'], [role='menuitem'], [role='listbox'] li, [role='menu'] li"
        ):
            try:
                if not await el.is_visible():
                    continue
                t = (await el.inner_text()).strip()[:80]
                if t and t not in dropdown_options:
                    dropdown_options.append(t)
                if len(dropdown_options) >= 15:
                    break
            except Exception:
                continue
    except Exception:
        pass

    return PageState(
        url=url,
        title=title,
        text=text,
        buttons=buttons,
        links=links,
        inputs=inputs,
        dropdown_options=dropdown_options,
    )


def page_state_to_dict(state: PageState) -> dict[str, Any]:
    """For JSON logging and LLM context."""
    d: dict[str, Any] = {
        "url": state.url,
        "title": state.title,
        "text": state.text,
        "buttons": state.buttons,
        "links": state.links[:20],
        "inputs": state.inputs,
    }
    if state.dropdown_options:
        d["dropdown_options"] = state.dropdown_options
    return d
