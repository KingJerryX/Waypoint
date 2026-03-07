"""Server-side storage for manuals (shareable agent configs)."""
import json
import uuid
from pathlib import Path
from typing import Any

DATA_DIR = Path(__file__).resolve().parent / "data"
MANUALS_FILE = DATA_DIR / "manuals.json"


def _ensure_data_dir() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def _load_manuals() -> dict[str, dict]:
    _ensure_data_dir()
    if not MANUALS_FILE.exists():
        return {}
    try:
        with open(MANUALS_FILE) as f:
            return json.load(f)
    except Exception:
        return {}


def _save_manuals(manuals: dict[str, dict]) -> None:
    _ensure_data_dir()
    with open(MANUALS_FILE, "w") as f:
        json.dump(manuals, f, indent=2)


def create_manual(
    title: str,
    url: str,
    task: str,
    max_steps: int = 8,
    no_click: bool = False,
) -> dict[str, Any]:
    """Create a manual, persist it, return with id and shareable slug."""
    manuals = _load_manuals()
    slug = str(uuid.uuid4())[:8]
    entry = {
        "id": slug,
        "title": title,
        "url": url,
        "task": task,
        "max_steps": max_steps,
        "no_click": no_click,
    }
    manuals[slug] = entry
    _save_manuals(manuals)
    return dict(entry)


def get_manual(slug: str) -> dict | None:
    """Get manual by id/slug. Returns None if not found."""
    manuals = _load_manuals()
    return manuals.get(slug)
