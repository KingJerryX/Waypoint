"""
Orbit browser agent: FastAPI server + CLI.
Set GOOGLE_API_KEY (env or .env) and run:
  CLI:  python main.py --url "https://example.com" --task "Summarize the page"
  API:  uvicorn main:app --reload
"""
import argparse
import asyncio
import os
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent / ".env")
except ImportError:
    pass

from agent_loop import request_approval_cli, run_agent
from browser_tools import BrowserController
from config import UserConstraints

# #region agent log
DEBUG_LOG = Path(__file__).resolve().parent.parent / ".cursor" / "debug-b65a9c.log"
def _debug_log(message: str, data: dict, hypothesis_id: str = ""):
    import json
    try:
        with open(DEBUG_LOG, "a") as f:
            f.write(json.dumps({"sessionId": "b65a9c", "location": "main.py", "message": message, "data": data, "hypothesisId": hypothesis_id, "timestamp": __import__("time").time() * 1000}) + "\n")
    except Exception:
        pass
# #endregion


def _parse_args():
    p = argparse.ArgumentParser(description="Orbit browser agent: open a URL and complete a task.")
    p.add_argument("--url", required=True, help="URL to open")
    p.add_argument("--task", required=True, help="Task, e.g. 'Summarize qualifications and responsibilities'")
    p.add_argument("--max-steps", type=int, default=8, help="Max agent steps (default 8)")
    p.add_argument("--no-click", action="store_true", help="Disallow click tool (read-only)")
    p.add_argument("--approve-clicks", action="store_true", help="Require human approval for click/type")
    p.add_argument("--headed", action="store_true", help="Run browser with visible window")
    p.add_argument("--log-dir", default=None, help="Directory for session logs (default: ./logs)")
    return p.parse_args()


async def _run_cli():
    args = _parse_args()
    if not os.environ.get("GOOGLE_API_KEY"):
        print("Error: set GOOGLE_API_KEY in the environment")
        return 1

    allowed = ["open_url", "get_page_state", "scroll_down", "done"]
    if not args.no_click:
        allowed.extend(["click", "type"])
    constraints = UserConstraints(
        allowed_tools=allowed,
        max_steps=args.max_steps,
        require_approval_for_tools=["click", "type"] if args.approve_clicks else None,
    )
    log_dir = Path(args.log_dir) if args.log_dir else None
    request_approval = request_approval_cli if args.approve_clicks else None

    async with BrowserController(headless=not args.headed) as browser:
        out = await run_agent(
            browser,
            task=args.task,
            url=args.url,
            constraints=constraints,
            request_approval=request_approval,
            max_steps=args.max_steps,
            log_dir=log_dir,
        )

    if out.get("ok"):
        print("\n--- Answer ---")
        print(out.get("answer", ""))
        print("\n--- Metrics ---")
        print(out.get("metrics", {}))
        print("Log:", out.get("log_path", ""))
        return 0
    else:
        print("Error:", out.get("error", "Unknown error"))
        print("Steps:", out.get("steps", []))
        return 1


def cli_main():
    return asyncio.run(_run_cli())


# --- FastAPI ---
app = None  # set below

try:
    from fastapi import FastAPI, HTTPException
    from fastapi.responses import FileResponse
    from pydantic import BaseModel

    from manuals import create_manual, get_manual

    app = FastAPI(title="Orbit Browser Agent", description="Open a URL and complete a task with an LLM agent.")

    class TaskRequest(BaseModel):
        url: str
        task: str
        max_steps: int = 8
        allowed_tools: list[str] | None = None
        require_approval: bool = False

    class ManualCreate(BaseModel):
        title: str
        url: str
        task: str
        max_steps: int = 8
        no_click: bool = False

    @app.post("/run")
    async def run_task(req: TaskRequest):
        # #region agent log
        _debug_log("run_task entry", {"url": req.url, "task_len": len(req.task or ""), "max_steps": req.max_steps}, "H2")
        # #endregion
        if not os.environ.get("GOOGLE_API_KEY"):
            # #region agent log
            _debug_log("run_task no api key", {}, "H2")
            # #endregion
            raise HTTPException(status_code=500, detail="GOOGLE_API_KEY not set")
        constraints = UserConstraints(
            allowed_tools=req.allowed_tools or ["open_url", "get_page_state", "click", "scroll_down", "type", "done"],
            max_steps=req.max_steps,
            require_approval_for_tools=["click", "type"] if req.require_approval else None,
        )
        try:
            async with BrowserController(headless=True) as browser:
                result = await run_agent(
                    browser,
                    task=req.task,
                    url=req.url,
                    constraints=constraints,
                    request_approval=None,
                    max_steps=req.max_steps,
                )
        except Exception as e:
            # #region agent log
            _debug_log("run_task exception", {"error": str(e)}, "H5")
            # #endregion
            raise
        if not result.get("ok") and "error" not in result:
            result["error"] = "Agent did not produce an answer"
        # #region agent log
        _debug_log("run_task exit", {"ok": result.get("ok"), "has_error": "error" in result}, "H2")
        # #endregion
        return result

    @app.post("/api/manuals")
    def api_create_manual(req: ManualCreate):
        manual = create_manual(
            title=req.title,
            url=req.url,
            task=req.task,
            max_steps=req.max_steps,
            no_click=req.no_click,
        )
        # #region agent log
        _debug_log("api_create_manual", {"slug": manual.get("id"), "url": req.url}, "H1")
        # #endregion
        return manual

    @app.get("/api/manuals/{slug}")
    def api_get_manual(slug: str):
        manual = get_manual(slug)
        # #region agent log
        _debug_log("api_get_manual", {"slug": slug, "found": manual is not None}, "H1")
        # #endregion
        if not manual:
            raise HTTPException(status_code=404, detail="Manual not found")
        return manual

    FRONTEND_DIST = Path(__file__).resolve().parent / "frontend" / "dist"
    STATIC_DIR = Path(__file__).resolve().parent / "static"

    @app.get("/health")
    def health():
        return {"status": "ok", "gemini_configured": bool(os.environ.get("GOOGLE_API_KEY"))}

    # React app (SPA): explicit routes for / and /go/* so no catch-all eats them; assets under /assets
    if FRONTEND_DIST.exists():
        @app.get("/")
        def index():
            return FileResponse(FRONTEND_DIST / "index.html")

        @app.get("/go/{slug}")
        def go_page(slug: str):
            # #region agent log
            _debug_log("go_page called", {"slug": slug, "dist_exists": FRONTEND_DIST.exists(), "index_exists": (FRONTEND_DIST / "index.html").exists()}, "H2")
            # #endregion
            return FileResponse(FRONTEND_DIST / "index.html")

        @app.get("/orbit.svg")
        def favicon():
            return FileResponse(FRONTEND_DIST / "orbit.svg")

        from fastapi.staticfiles import StaticFiles
        assets_dir = FRONTEND_DIST / "assets"
        if assets_dir.exists():
            app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")
    else:
        # Fallback: legacy static/ HTML
        @app.get("/")
        def index():
            if STATIC_DIR.joinpath("index.html").exists():
                return FileResponse(STATIC_DIR / "index.html")
            return {"message": "Orbit API. Run 'cd frontend && npm run build' for the web app."}

        @app.get("/go/{slug}")
        def go_page(slug: str):
            if STATIC_DIR.joinpath("go.html").exists():
                return FileResponse(STATIC_DIR / "go.html")
            raise HTTPException(status_code=404, detail="Run page not found")

        if STATIC_DIR.exists():
            from fastapi.staticfiles import StaticFiles
            app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

except ImportError:
    app = None


if __name__ == "__main__":
    exit(cli_main())
