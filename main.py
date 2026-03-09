"""
Orbit – AI browser automation with shareable links.
Run: uvicorn main:app --reload
"""
import asyncio
import json
import os
import sys
import threading
import httpx
from pathlib import Path
from typing import Any

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent / ".env")
except ImportError:
    pass

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from manuals import create_manual, get_manual

SKYVERN_API_KEY = os.environ.get("SKYVERN_API_KEY", "")
SKYVERN_BASE = "https://api.skyvern.com/v1"

app = FastAPI(title="Orbit – AI Browser Automation")

# Registry of pause events keyed by session_id — lets /api/resume unblock the agent
PAUSE_EVENTS: dict[str, threading.Event] = {}

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Helpers ──────────────────────────────────────────────────────────────────

def _require_http_url(url: str | None) -> str | None:
    """Reject file://, javascript:, data: and any other non-http(s) scheme."""
    if not url or url.strip() in ("", "about:blank"):
        return url
    from urllib.parse import urlparse
    parsed = urlparse(url.strip())
    if parsed.scheme not in ("http", "https"):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid URL scheme '{parsed.scheme}'. Only http:// and https:// are allowed.",
        )
    return url.strip()

# ── Models ──────────────────────────────────────────────────────────────────

class RunRequest(BaseModel):
    prompt: str
    url: str | None = None
    max_steps: int | None = 15

class ShareRequest(BaseModel):
    title: str
    prompt: str
    url: str | None = None
    max_steps: int = 15

# ── Skyvern helpers ──────────────────────────────────────────────────────────

def _skyvern_headers():
    return {
        "x-api-key": SKYVERN_API_KEY,
        "Content-Type": "application/json",
    }

async def skyvern_run_task(prompt: str, url: str | None, max_steps: int) -> dict:
    payload: dict[str, Any] = {
        "prompt": prompt,
        "engine": "skyvern-2.0",
        "max_steps": max_steps,
    }
    if url:
        payload["url"] = url

    async with httpx.AsyncClient(timeout=120) as client:
        r = await client.post(
            f"{SKYVERN_BASE}/run/tasks",
            headers=_skyvern_headers(),
            json=payload,
        )
        if r.status_code not in (200, 201):
            raise HTTPException(status_code=502, detail=f"Skyvern error {r.status_code}: {r.text}")
        return r.json()

async def skyvern_get_task(run_id: str) -> dict:
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.get(
            f"{SKYVERN_BASE}/run/tasks/{run_id}",
            headers=_skyvern_headers(),
        )
        if r.status_code == 404:
            raise HTTPException(status_code=404, detail="Task not found")
        if r.status_code not in (200, 201):
            raise HTTPException(status_code=502, detail=f"Skyvern error {r.status_code}: {r.text}")
        return r.json()

# ── API Routes ───────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {
        "status": "ok",
        "skyvern_configured": bool(SKYVERN_API_KEY),
    }

@app.post("/api/resume/{session_id}")
def resume_agent(session_id: str):
    """Unblock a paused agent session so it can continue after human login/CAPTCHA."""
    ev = PAUSE_EVENTS.get(session_id)
    if not ev:
        raise HTTPException(status_code=404, detail="No paused session found")
    ev.set()
    return {"ok": True}

@app.post("/api/run")
async def run_task(req: RunRequest):
    """Start a Skyvern task. Returns run_id immediately for polling."""
    if not SKYVERN_API_KEY:
        raise HTTPException(status_code=500, detail="SKYVERN_API_KEY not set")
    result = await skyvern_run_task(req.prompt, req.url, req.max_steps or 15)
    return result

@app.get("/api/run/{run_id}")
async def poll_task(run_id: str):
    """Poll a running Skyvern task for status + screenshots."""
    if not SKYVERN_API_KEY:
        raise HTTPException(status_code=500, detail="SKYVERN_API_KEY not set")
    return await skyvern_get_task(run_id)

@app.post("/api/share")
def create_share(req: ShareRequest):
    """Save an automation as a shareable link."""
    manual = create_manual(
        title=req.title,
        url=req.url or "",
        task=req.prompt,
        max_steps=req.max_steps,
    )
    return manual

@app.get("/api/manuals/{slug}")
def get_share(slug: str):
    manual = get_manual(slug)
    if not manual:
        raise HTTPException(status_code=404, detail="Not found")
    return manual

@app.post("/api/manuals")
def create_manual_compat(req: ShareRequest):
    manual = create_manual(
        title=req.title,
        url=req.url or "",
        task=req.prompt,
        max_steps=req.max_steps,
    )
    return manual

# ── Step estimation ──────────────────────────────────────────────────────────

class EstimateRequest(BaseModel):
    prompt: str

@app.post("/api/estimate")
async def estimate_steps(req: EstimateRequest):
    """Ask Gemini to estimate how many browser steps this task will need."""
    import google.generativeai as genai
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        return {"steps": 15}
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-2.0-flash")
        result = model.generate_content(
            f"""You are estimating how many browser steps an AI agent needs to complete a task.
Each step is one action: open a URL, read page content, click, type, or scroll.

Rules:
- Simple single-site lookup: 3-5 steps
- Single site with search/interaction: 5-8 steps
- Multiple sites (2-3): 10-15 steps
- Complex multi-site research (4+ sites): 15-20 steps
- Max allowed: 25

Task: {req.prompt}

Reply with ONLY a single integer. No explanation."""
        )
        import re
        match = re.search(r'\b(\d+)\b', result.text or "")
        if not match:
            return {"steps": 15}
        steps = max(5, min(25, int(match.group(1))))
        return {"steps": steps}
    except Exception:
        return {"steps": 15}

# ── Local Playwright streaming ───────────────────────────────────────────────

@app.post("/api/run/local")
async def run_local_stream(req: RunRequest, request: Request):
    """Run automation locally with Playwright + Gemini. Streams screenshots via SSE."""
    if not os.environ.get("GOOGLE_API_KEY"):
        raise HTTPException(status_code=500, detail="GOOGLE_API_KEY not set — add it to .env")

    # Validate URL scheme before launching any browser process
    validated_url = _require_http_url(req.url)

    from browser_tools import BrowserController
    from agent_loop import run_agent as _run_agent

    queue: asyncio.Queue = asyncio.Queue()
    main_loop = asyncio.get_running_loop()

    # Pre-generate session id so the resume endpoint can reference it before the agent starts
    import uuid as _uuid
    session_id = str(_uuid.uuid4())[:8]
    pause_event = threading.Event()
    stop_event = threading.Event()   # set when the SSE client disconnects
    PAUSE_EVENTS[session_id] = pause_event

    def run_in_thread():
        """
        Playwright requires ProactorEventLoop on Windows for subprocess support.
        We create a fresh ProactorEventLoop in this thread, run the agent there,
        and bridge events back to the main loop's queue via run_coroutine_threadsafe.
        """
        if sys.platform == "win32":
            loop = asyncio.ProactorEventLoop()
        else:
            loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        def put(event):
            try:
                asyncio.run_coroutine_threadsafe(queue.put(event), main_loop).result(timeout=10)
            except Exception:
                pass  # SSE stream already closed — discard silently

        async def on_step(step: int, tool: str, b64: str):
            put({"type": "screenshot", "step": step, "tool": tool, "data": b64})

        async def on_activity(step: int, message: str):
            put({"type": "activity", "step": step, "message": message})

        async def on_pause(reason: str):
            """Emit human_required event, then block until the user clicks Resume or disconnects."""
            put({"type": "human_required", "session_id": session_id, "reason": reason})
            # Wait for resume OR client disconnect (whichever comes first)
            await asyncio.get_event_loop().run_in_executor(None, pause_event.wait, 300)
            if stop_event.is_set():
                raise RuntimeError("Client disconnected — aborting session")
            pause_event.clear()
            put({"type": "status", "status": "running"})

        async def _run():
            try:
                from config import UserConstraints
                steps = req.max_steps or 15
                constraints = UserConstraints(max_steps=steps)
                async with BrowserController(headless=False) as browser:
                    result = await _run_agent(
                        browser,
                        task=req.prompt,
                        url=validated_url or "about:blank",
                        max_steps=steps,
                        constraints=constraints,
                        on_step=on_step,
                        on_pause=on_pause,
                        on_activity=on_activity,
                        session_id=session_id,
                    )
                    put({"type": "done", "ok": result.get("ok"),
                         "answer": result.get("answer"), "error": result.get("error")})
            except Exception as e:
                put({"type": "error", "error": str(e)})
            finally:
                put(None)

        try:
            loop.run_until_complete(_run())
        finally:
            loop.close()

    async def event_stream():
        try:
            yield f"data: {json.dumps({'type': 'status', 'status': 'running'})}\n\n"
            asyncio.create_task(asyncio.to_thread(run_in_thread))
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=30)
                except asyncio.TimeoutError:
                    # Check for client disconnect every 30 s instead of blocking for 2 min
                    if await request.is_disconnected():
                        break
                    yield f"data: {json.dumps({'type': 'ping'})}\n\n"
                    continue
                if event is None:
                    break
                yield f"data: {json.dumps(event)}\n\n"
        finally:
            # Client closed tab or connection dropped — unblock any waiting pause and clean up
            stop_event.set()
            pause_event.set()   # wake on_pause so the agent thread can exit
            PAUSE_EVENTS.pop(session_id, None)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no", "Connection": "keep-alive"},
    )

# ── Frontend serving ─────────────────────────────────────────────────────────

FRONTEND_DIST = Path(__file__).resolve().parent / "frontend" / "dist"

if FRONTEND_DIST.exists():
    from fastapi.staticfiles import StaticFiles

    @app.get("/")
    def index():
        return FileResponse(FRONTEND_DIST / "index.html")

    @app.get("/go/{slug}")
    def go_page(slug: str):
        return FileResponse(FRONTEND_DIST / "index.html")

    @app.get("/orbit.svg")
    def favicon():
        svg = FRONTEND_DIST / "orbit.svg"
        if svg.exists():
            return FileResponse(svg)
        raise HTTPException(status_code=404)

    assets_dir = FRONTEND_DIST / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")
