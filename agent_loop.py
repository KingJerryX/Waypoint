"""Agent loop: get page state -> Gemini decides action -> execute tool -> repeat until done or max_steps."""
import asyncio
import json
import os
import time
import uuid
from pathlib import Path
from typing import Any, Callable, Optional

from config import UserConstraints
from prompts import build_system_prompt, build_user_message

# Gemini (sync SDK) — we'll call it from a thread to avoid blocking
import google.generativeai as genai

# Tool names the model can request
TOOL_OPEN_URL = "open_url"
TOOL_GET_PAGE_STATE = "get_page_state"
TOOL_CLICK = "click"
TOOL_TYPE = "type"
TOOL_PRESS_KEY = "press_key"
TOOL_SCROLL_DOWN = "scroll_down"
TOOL_REQUEST_HUMAN = "request_human_help"
TOOL_DONE = "done"


# #region agent log
DEBUG_LOG = Path(__file__).resolve().parent.parent / ".cursor" / "debug-b65a9c.log"


def _debug_log(message: str, data: dict, run_id: str = "", hypothesis_id: str = "") -> None:
    try:
        with open(DEBUG_LOG, "a") as f:
            f.write(
                json.dumps(
                    {
                        "sessionId": "b65a9c",
                        "runId": run_id,
                        "hypothesisId": hypothesis_id,
                        "location": "agent_loop.py",
                        "message": message,
                        "data": data,
                        "timestamp": time.time() * 1000,
                    }
                )
                + "\n"
            )
    except Exception:
        pass


# #endregion

# Declarations for Gemini function calling (OpenAPI-style parameters)
GEMINI_TOOL_DECLARATIONS = [
    {
        "name": TOOL_OPEN_URL,
        "description": "Open a URL in the browser. Call this first with the user's link.",
        "parameters": {
            "type": "object",
            "properties": {"url": {"type": "string", "description": "Full URL to open"}},
            "required": ["url"],
        },
    },
    {
        "name": TOOL_GET_PAGE_STATE,
        "description": "Get current page state: url, title, visible text, buttons, links, inputs. Call this to see what is on the page.",
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "name": TOOL_CLICK,
        "description": "Click a button or link by its visible text or CSS selector.",
        "parameters": {
            "type": "object",
            "properties": {
                "text_or_selector": {
                    "type": "string",
                    "description": "Visible text (e.g. 'Read more') or selector (e.g. '#submit')",
                }
            },
            "required": ["text_or_selector"],
        },
    },
    {
        "name": TOOL_TYPE,
        "description": "Type text into an input field. Use the exact placeholder text or label visible on the page (e.g. 'Where to?', 'Search', 'Destination'). Call get_page_state first to see available inputs if unsure.",
        "parameters": {
            "type": "object",
            "properties": {
                "selector": {"type": "string", "description": "Exact placeholder text, label, or CSS selector for the input (e.g. 'Where to?', '#destination', '[name=\"q\"]')"},
                "value": {"type": "string", "description": "Text to type"},
            },
            "required": ["selector", "value"],
        },
    },
    {
        "name": TOOL_PRESS_KEY,
        "description": "Press a keyboard key. Use 'Enter' to confirm/submit or select autocomplete, 'Tab' to move focus, 'Escape' to dismiss, 'ArrowDown'/'ArrowUp' to navigate autocomplete dropdowns.",
        "parameters": {
            "type": "object",
            "properties": {
                "key": {"type": "string", "description": "Key name: Enter, Tab, Escape, ArrowDown, ArrowUp, Backspace, Space"}
            },
            "required": ["key"],
        },
    },
    {
        "name": TOOL_SCROLL_DOWN,
        "description": "Scroll the page down to load more content.",
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "name": TOOL_REQUEST_HUMAN,
        "description": "Pause the agent and ask the human to take over the browser. Use when you encounter a login wall, CAPTCHA, or any screen that requires human credentials or verification. The human will see the live browser window and complete the action, then click Resume to continue.",
        "parameters": {
            "type": "object",
            "properties": {
                "reason": {
                    "type": "string",
                    "description": "Short explanation of why human help is needed (e.g. 'Login required', 'CAPTCHA detected')",
                }
            },
            "required": ["reason"],
        },
    },
    {
        "name": TOOL_DONE,
        "description": "Call when you have enough information to answer the user's task. Provide the final answer.",
        "parameters": {
            "type": "object",
            "properties": {
                "answer": {
                    "type": "string",
                    "description": "The final answer: summary, extracted data, or structured response",
                }
            },
            "required": ["answer"],
        },
    },
]


def _build_tools_for_gemini(tool_names: list[str]):
    """Build tools list in format accepted by google-generativeai (protos or dict)."""
    declarations = [d for d in GEMINI_TOOL_DECLARATIONS if d["name"] in tool_names]
    # Try genai.protos (older SDK)
    try:
        if hasattr(genai, "protos"):
            FD = getattr(genai.protos, "FunctionDeclaration", None)
            Tool = getattr(genai.protos, "Tool", None)
            if FD and Tool:
                fd_list = [FD(name=d["name"], description=d.get("description", ""), parameters=d.get("parameters")) for d in declarations]
                return [Tool(function_declarations=fd_list)]
    except Exception:
        pass
    # Try google.generativeai.types
    try:
        from google.generativeai.types import Tool
        from google.generativeai.protos import FunctionDeclaration
        fd_list = [FunctionDeclaration(name=d["name"], description=d.get("description", ""), parameters=d.get("parameters")) for d in declarations]
        return [Tool(function_declarations=fd_list)]
    except Exception:
        pass
    # Fallback: dict (REST API style; some SDK versions accept this)
    return [{"function_declarations": declarations}]


def _resolve_model_name() -> str:
    """
    Pick a model that is actually available for generateContent on this key.
    Order:
      1) ORBIT_GEMINI_MODEL (if present and available, otherwise still used as fallback)
      2) Preferred flash models that exist in list_models()
      3) Any available flash model
      4) First available generateContent model
      5) Final fallback to env/default
    """
    env_model = (os.environ.get("ORBIT_GEMINI_MODEL") or "").strip()
    preferred = [
        m
        for m in [
            env_model,
            "gemini-2.5-flash",
            "gemini-2.5-flash-lite",
            "gemini-2.0-flash",
            "gemini-2.0-flash-lite",
            "gemini-1.5-flash",
        ]
        if m
    ]
    try:
        available_raw = list(genai.list_models())
    except Exception:
        available_raw = []

    available: list[str] = []
    for m in available_raw:
        methods = getattr(m, "supported_generation_methods", None) or []
        if "generateContent" not in methods:
            continue
        name = getattr(m, "name", "") or ""
        if name.startswith("models/"):
            name = name[len("models/") :]
        if name:
            available.append(name)

    if available:
        available_set = set(available)
        for candidate in preferred:
            if candidate in available_set:
                return candidate
        for candidate in available:
            if "flash" in candidate.lower():
                return candidate
        return available[0]

    return env_model or "gemini-2.5-flash"


def _resolve_model_candidates() -> list[str]:
    """
    Return an ordered candidate list to try for generateContent.
    First candidate is preferred; next are fallbacks.
    """
    first = _resolve_model_name()
    defaults = [
        "gemini-2.5-flash",
        "gemini-2.5-flash-lite",
        "gemini-2.0-flash",
        "gemini-2.0-flash-lite",
        "gemini-1.5-flash",
    ]
    out: list[str] = []
    for m in [first] + defaults:
        if m and m not in out:
            out.append(m)
    return out


def _call_gemini_sync(
    system_prompt: str,
    user_message: str,
    history: list[dict],
    tool_names: list[str],
    run_id: str = "",
) -> tuple[Optional[str], Optional[dict], Optional[dict]]:
    """
    Call Gemini (sync). Returns (function_name, function_args_dict, error_or_text_dict).
    Single turn: user_message contains task + current state (+ last error). History used for chat.
    """
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        return None, None, {"error": "GOOGLE_API_KEY not set"}
    genai.configure(api_key=api_key)

    tools = _build_tools_for_gemini(tool_names)
    candidates = _resolve_model_candidates()
    # #region agent log
    _debug_log("gemini model candidates", {"candidates": candidates}, run_id=run_id, hypothesis_id="H8")
    # #endregion

    response = None
    last_error = None
    used_model = None
    for model_name in candidates:
        used_model = model_name
        model = genai.GenerativeModel(
            model_name=model_name,
            tools=tools,
            system_instruction=system_prompt,
        )
        # Single message for MVP: full context in user_message; no multi-turn to avoid content format issues
        try:
            # mode=ANY forces Gemini to always call one of the provided tools
            try:
                response = model.generate_content(
                    user_message,
                    tool_config={"function_calling_config": {"mode": "ANY"}},
                )
            except Exception:
                response = model.generate_content(user_message)
            # #region agent log
            _debug_log("gemini generate_content success", {"model_name": model_name}, run_id=run_id, hypothesis_id="H8")
            # #endregion
            break
        except Exception as e:
            err_text = str(e)
            last_error = err_text
            # #region agent log
            _debug_log("gemini generate_content error", {"error": err_text, "model_name": model_name}, run_id=run_id, hypothesis_id="H8")
            # #endregion
            lower = err_text.lower()
            should_try_next = (
                "no longer available" in lower
                or "not found" in lower
                or "is not supported for generatecontent" in lower
            )
            if should_try_next:
                continue
            return None, None, {"error": err_text}

    if response is None:
        return None, None, {"error": last_error or "Gemini request failed for all model candidates"}

    if not response.candidates:
        return None, None, {"error": "No candidates in response"}

    parts = response.candidates[0].content.parts
    fn_name, fn_args = None, None
    text_parts = []
    for p in parts:
        if getattr(p, "function_call", None):
            fc = p.function_call
            fn_name = getattr(fc, "name", None) or (fc.get("name") if isinstance(fc, dict) else None)
            args = getattr(fc, "args", None) or (fc.get("args") if isinstance(fc, dict) else {})
            fn_args = dict(args) if args else {}
            break
        if getattr(p, "text", None):
            text_parts.append(p.text)
    text = " ".join(text_parts).strip() if text_parts else None
    return fn_name, fn_args, {"text": text} if text else None


def request_approval_cli(action_name: str, action_args: dict, timeout_seconds: int = 60) -> bool:
    """Blocking CLI approval. Returns True to proceed, False to reject."""
    print(f"\n[Approval] About to run: {action_name}({action_args}) — proceed? [y/n] ", end="")
    try:
        import sys
        line = sys.stdin.readline()
        return line.strip().lower() in ("y", "yes")
    except Exception:
        return False


async def run_agent(
    browser,
    task: str,
    url: str,
    constraints: Optional[UserConstraints] = None,
    request_approval: Optional[Callable[[str, dict], bool]] = None,
    max_steps: int = 8,
    log_dir: Optional[Path] = None,
    on_step: Optional[Callable] = None,
    on_pause: Optional[Callable] = None,
    session_id: Optional[str] = None,
) -> dict[str, Any]:
    """
    Run the agent loop: open url, then repeatedly get state -> Gemini -> execute tool until done or max_steps.
    request_approval: sync callable(action_name, action_args) -> bool. If None, no approval step.
    """
    constraints = constraints or UserConstraints()
    max_steps = min(max_steps, constraints.max_steps)
    session_id = session_id or str(uuid.uuid4())[:8]
    log_path = (log_dir or Path(__file__).resolve().parent / "logs") / f"session_{session_id}.json"
    log_path.parent.mkdir(parents=True, exist_ok=True)

    steps_log: list[dict] = []
    current_state: Optional[dict] = None
    last_error: Optional[str] = None
    final_answer: Optional[str] = None
    tools_ok = 0
    tools_failed = 0
    start_time = time.perf_counter()

    system_prompt = build_system_prompt(constraints)

    # Step 0: open_url so we have a page
    if not constraints.is_domain_allowed(url):
        return {
            "ok": False,
            "error": f"URL domain not allowed by constraints",
            "session_id": session_id,
        }
    result = await browser.open_url(url)
    if not result.get("ok"):
        last_error = result.get("error", "open_url failed")
        steps_log.append({"tool": TOOL_OPEN_URL, "args": {"url": url}, "ok": False, "error": last_error})
        tools_failed += 1
    else:
        current_state = result.get("state")
        steps_log.append({"tool": TOOL_OPEN_URL, "args": {"url": url}, "ok": True})
        tools_ok += 1
        if on_step:
            try:
                b64 = await browser.screenshot_b64()
                await on_step(0, TOOL_OPEN_URL, b64)
            except Exception:
                pass

    step_count = 1
    resume_note: Optional[str] = None
    while step_count < max_steps and final_answer is None:
        user_message = build_user_message(task, current_state, last_error, resume_note=resume_note)
        last_error = None
        resume_note = None  # only inject once, immediately after a pause

        # Call Gemini in a thread so we don't block event loop
        fn_name, fn_args, err = await asyncio.to_thread(
            _call_gemini_sync,
            system_prompt,
            user_message,
            [],  # history not used in single-turn MVP
            constraints.allowed_tools,
            session_id,
        )
        if err and err.get("error"):
            last_error = err["error"]
            steps_log.append({"tool": "gemini", "ok": False, "error": last_error})
            tools_failed += 1
            # Stop early for quota/billing errors; retries will not help.
            err_lower = last_error.lower()
            if "quota exceeded" in err_lower or "billing" in err_lower or "429" in err_lower:
                # #region agent log
                _debug_log(
                    "gemini quota/billing hard-stop",
                    {"error": last_error},
                    run_id=session_id,
                    hypothesis_id="H7",
                )
                # #endregion
                break
            step_count += 1
            continue

        if not fn_name:
            # Model responded with text instead of a tool call — treat as final answer
            if err and err.get("text"):
                final_answer = err["text"]
                steps_log.append({"tool": "done", "answer": final_answer, "note": "text_response"})
                break
            last_error = "You must respond with a tool call. Call open_url() to navigate, get_page_state() to read the page, or done() to finish. Do NOT write plain text."
            step_count += 1
            continue

        fn_args = fn_args or {}

        # Constraint: tool allowed?
        if not constraints.is_tool_allowed(fn_name):
            last_error = f"Tool '{fn_name}' is not allowed by constraints."
            step_count += 1
            continue

        # Human approval (if configured)
        if request_approval and constraints.requires_approval(fn_name):
            approved = await asyncio.to_thread(request_approval, fn_name, fn_args)
            if not approved:
                last_error = "User rejected the action."
                steps_log.append({"tool": fn_name, "args": fn_args, "approved": False})
                step_count += 1
                continue
            steps_log.append({"tool": fn_name, "args": fn_args, "approved": True})

        # Execute tool
        if fn_name == TOOL_REQUEST_HUMAN:
            reason = fn_args.get("reason", "Human assistance required")
            steps_log.append({"tool": TOOL_REQUEST_HUMAN, "reason": reason})
            if on_pause:
                # Emit the pause event and block until the human clicks Resume
                await on_pause(reason)
                # Refresh page state — the human may have logged in or solved a CAPTCHA
                try:
                    refresh = await browser.get_page_state()
                    if refresh.get("ok"):
                        current_state = refresh.get("state")
                except Exception:
                    pass
                # Tell the agent the human is done so it doesn't call request_human_help again
                resume_note = (
                    "The human has just completed the required action (login / CAPTCHA / verification). "
                    "Authentication is now done. Do NOT call request_human_help again. "
                    "Continue the original task using the current page shown below."
                )
                # Take a fresh screenshot so the UI updates
                if on_step:
                    try:
                        b64 = await browser.screenshot_b64()
                        await on_step(step_count, TOOL_REQUEST_HUMAN, b64)
                    except Exception:
                        pass
            step_count += 1
            continue

        if fn_name == TOOL_DONE:
            final_answer = fn_args.get("answer", "")
            steps_log.append({"tool": TOOL_DONE, "answer": final_answer})
            break

        result = {}
        if fn_name == TOOL_OPEN_URL:
            u = fn_args.get("url", "")
            if not constraints.is_domain_allowed(u):
                last_error = "That URL's domain is not allowed."
                result = {"ok": False, "error": last_error}
            else:
                result = await browser.open_url(u)
                if result.get("ok"):
                    current_state = result.get("state")
                    tools_ok += 1
                else:
                    last_error = result.get("error")
                    tools_failed += 1
        elif fn_name == TOOL_GET_PAGE_STATE:
            result = await browser.get_page_state()
            if result.get("ok"):
                current_state = result.get("state")
                tools_ok += 1
            else:
                last_error = result.get("error")
                tools_failed += 1
        elif fn_name == TOOL_CLICK:
            result = await browser.click(fn_args.get("text_or_selector", ""))
            if result.get("ok"):
                current_state = result.get("state")
                tools_ok += 1
            else:
                last_error = result.get("error")
                tools_failed += 1
        elif fn_name == TOOL_TYPE:
            result = await browser.type_text(
                fn_args.get("selector", ""),
                fn_args.get("value", ""),
            )
            if result.get("ok"):
                current_state = result.get("state")
                tools_ok += 1
            else:
                last_error = result.get("error")
                tools_failed += 1
        elif fn_name == TOOL_PRESS_KEY:
            result = await browser.press_key(fn_args.get("key", "Enter"))
            if result.get("ok"):
                current_state = result.get("state")
                tools_ok += 1
            else:
                last_error = result.get("error")
                tools_failed += 1
        elif fn_name == TOOL_SCROLL_DOWN:
            result = await browser.scroll_down()
            if result.get("ok"):
                current_state = result.get("state")
                tools_ok += 1
            else:
                last_error = result.get("error")
                tools_failed += 1
        else:
            last_error = f"Unknown tool: {fn_name}"

        steps_log.append({"tool": fn_name, "args": fn_args, "ok": result.get("ok", False), "error": last_error})
        if on_step:
            try:
                b64 = await browser.screenshot_b64()
                await on_step(step_count, fn_name, b64)
            except Exception:
                pass
        step_count += 1

    total_time = time.perf_counter() - start_time
    total_calls = tools_ok + tools_failed
    metrics = {
        "steps_used": len(steps_log),
        "tools_ok": tools_ok,
        "tools_failed": tools_failed,
        "total_time_s": round(total_time, 2),
        "success": final_answer is not None,
    }

    run_log = {
        "session_id": session_id,
        "task": task,
        "url": url,
        "steps": steps_log,
        "final_answer": final_answer,
        "metrics": metrics,
    }
    try:
        with open(log_path, "w") as f:
            json.dump(run_log, f, indent=2)
    except Exception:
        pass

    return {
        "ok": final_answer is not None,
        "session_id": session_id,
        "answer": final_answer,
        "error": None if final_answer is not None else (last_error or "Agent did not produce an answer"),
        "steps": steps_log,
        "metrics": metrics,
        "log_path": str(log_path),
    }
