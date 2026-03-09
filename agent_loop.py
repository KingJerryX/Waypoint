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
        "description": "Get current page state: url, title, visible text, buttons, links, inputs, and dropdown_options (the list of visible options when a dropdown or autocomplete is open). Call this after clicking a dropdown trigger or typing into an autocomplete field to see what options are available.",
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
        "description": "Type text into an input field. Use the exact placeholder text or label visible on the page (e.g. 'Where to?', 'Search', 'Destination'). Call get_page_state first to see available inputs if unsure. IMPORTANT: After typing into a search bar, you MUST call press_key with key='Enter' as your very next action — do NOT call type again.",
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


def _describe_action(tool_name: str, args: dict) -> str:
    """Return a short human-readable description of an agent action for the activity log."""
    if tool_name == TOOL_OPEN_URL:
        url = args.get("url", "")
        try:
            from urllib.parse import urlparse
            host = urlparse(url).netloc or url
        except Exception:
            host = url[:50]
        return f"Opening {host}"
    if tool_name == TOOL_GET_PAGE_STATE:
        return "Reading page content"
    if tool_name == TOOL_CLICK:
        t = args.get("text_or_selector", "")
        return f'Clicking "{t}"'
    if tool_name == TOOL_TYPE:
        val = args.get("value", "")
        sel = args.get("selector", "")
        return f'Typing "{val}" into {sel}'
    if tool_name == TOOL_PRESS_KEY:
        return f"Pressing {args.get('key', '?')}"
    if tool_name == TOOL_SCROLL_DOWN:
        return "Scrolling down to load more"
    if tool_name == TOOL_REQUEST_HUMAN:
        return f"Pausing — {args.get('reason', 'human action required')}"
    if tool_name == TOOL_DONE:
        return "Preparing final answer"
    return f"Running {tool_name}"


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


_CACHED_MODEL_CANDIDATES: list[str] | None = None


def _resolve_model_candidates() -> list[str]:
    """
    Return an ordered candidate list to try for generateContent.
    Calls list_models() ONCE and caches the result for the process lifetime.
    """
    global _CACHED_MODEL_CANDIDATES
    if _CACHED_MODEL_CANDIDATES is not None:
        return _CACHED_MODEL_CANDIDATES

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

    # Single network call — cached after first run
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

    # Pick best model, then build fallback list
    first = None
    if available:
        available_set = set(available)
        for candidate in preferred:
            if candidate in available_set:
                first = candidate
                break
        if not first:
            for candidate in available:
                if "flash" in candidate.lower():
                    first = candidate
                    break
        if not first:
            first = available[0]
    first = first or env_model or "gemini-2.5-flash"

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

    _CACHED_MODEL_CANDIDATES = out
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

    # configure once per process (idempotent but avoid repeated calls)
    if not getattr(_call_gemini_sync, "_configured", False):
        genai.configure(api_key=api_key)
        _call_gemini_sync._configured = True

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
        try:
            # Multi-turn chat: Gemini sees its own past decisions + tool results
            try:
                chat = model.start_chat(history=history)
            except Exception:
                chat = model.start_chat(history=[])  # bad history format — degrade gracefully
            try:
                response = chat.send_message(
                    user_message,
                    tool_config={"function_calling_config": {"mode": "ANY"}},
                )
            except Exception:
                response = chat.send_message(user_message)
            # #region agent log
            _debug_log("gemini start_chat success", {"model_name": model_name, "history_len": len(history)}, run_id=run_id, hypothesis_id="H8")
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
    on_activity: Optional[Callable] = None,
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
    # Chat history for multi-turn memory. Must start with a "user" role entry so subsequent
    # (model → user) action pairs always have a valid predecessor.
    conversation_history: list[dict] = [
        {"role": "user", "parts": [{"text": f"Task: {task}"}]}
    ]
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

        # Repetition guard:
        #   (1) Warn on actions that have FAILED 2+ times — model must try a different approach
        #   (2) Warn on ANY action repeated 3+ times total — catches infinite loops where the
        #       same action "succeeds" (e.g. clicking "Round trip" reopens the dropdown) but
        #       the agent isn't making progress
        _fail_counts: dict[str, int] = {}
        _all_counts: dict[str, int] = {}
        for _s in steps_log:
            if _s.get("tool") in ("gemini", TOOL_DONE, TOOL_REQUEST_HUMAN):
                continue
            _key = f"{_s['tool']}({json.dumps(_s.get('args', {}), sort_keys=True)})"
            _all_counts[_key] = _all_counts.get(_key, 0) + 1
            if not _s.get("ok"):
                _fail_counts[_key] = _fail_counts.get(_key, 0) + 1
        _repeated_fail = [k for k, n in _fail_counts.items() if n >= 2]
        _repeated_loop = [k for k, n in _all_counts.items() if n >= 3]
        if _repeated_fail:
            user_message += (
                f"\n\n⚠️ IMPORTANT: These exact actions have failed 2+ times — "
                f"do NOT retry them, try a completely different approach: {_repeated_fail}"
            )
        if _repeated_loop:
            user_message += (
                f"\n\n⚠️ LOOP DETECTED: These actions have been repeated 3+ times — "
                f"you are stuck in a loop and not making progress. "
                f"Stop repeating and try a completely different approach: {_repeated_loop}"
            )

        # Call Gemini in a thread so we don't block event loop
        fn_name, fn_args, err = await asyncio.to_thread(
            _call_gemini_sync,
            system_prompt,
            user_message,
            conversation_history,
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

        # Broadcast what the agent is about to do (visible in the activity log)
        if on_activity:
            try:
                await on_activity(step_count, _describe_action(fn_name, fn_args or {}))
            except Exception:
                pass

        # Execute tool
        if fn_name == TOOL_REQUEST_HUMAN:
            reason = fn_args.get("reason", "Human assistance required")
            steps_log.append({"tool": TOOL_REQUEST_HUMAN, "reason": reason})
            if on_pause:
                # Emit the pause event and block until the human clicks Resume
                await on_pause(reason)
                # Wait for any post-CAPTCHA/login redirect to fully settle before reading state
                await browser.wait_for_settled()
                # Refresh page state — the human may have logged in or solved a CAPTCHA
                try:
                    refresh = await browser.get_page_state()
                    if refresh.get("ok"):
                        current_state = refresh.get("state")
                except Exception:
                    pass
                # Tell the agent the human is done and give it clear direction to restart the task
                resume_note = (
                    "The human just completed the required action (CAPTCHA / login / verification) and clicked Resume. "
                    "The page has reloaded — check the current page state below. "
                    "Do NOT call request_human_help again. "
                    "Re-read the current page with get_page_state(), then continue the original task from where it left off. "
                    "If the page is a home page or search form, start the task over from the beginning (open the right URL or fill in the search)."
                )
                # Take a fresh screenshot so the UI updates
                if on_step:
                    try:
                        b64 = await browser.screenshot_b64()
                        await on_step(step_count, TOOL_REQUEST_HUMAN, b64)
                    except Exception:
                        pass
            # Record the pause + resume in history so the model knows a human intervened
            conversation_history.extend([
                {"role": "model", "parts": [{"function_call": {"name": TOOL_REQUEST_HUMAN, "args": fn_args or {}}}]},
                {"role": "user",  "parts": [{"function_response": {"name": TOOL_REQUEST_HUMAN, "response": {"result": "human_completed_action"}}}]},
            ])
            step_count += 1
            continue

        if fn_name == TOOL_DONE:
            final_answer = fn_args.get("answer", "")
            steps_log.append({"tool": TOOL_DONE, "answer": final_answer})
            break

        result = {}
        if fn_name == TOOL_OPEN_URL:
            u = fn_args.get("url", "")
            # Reject non-http(s) schemes — prevents file://, javascript:, data: injection
            _scheme = u.split("://")[0].lower() if "://" in u else ""
            if _scheme and _scheme not in ("http", "https"):
                last_error = f"URL scheme '{_scheme}' is not allowed. Only http:// and https:// are permitted."
                result = {"ok": False, "error": last_error}
            elif not constraints.is_domain_allowed(u):
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

        # Update conversation history with what the model decided and what actually happened.
        # Compact format: only function_call + function_response (no page state blobs) to
        # keep token cost low while giving Gemini full action memory.
        _hist_result = {"result": "success"} if result.get("ok") else {"error": last_error or "failed"}
        conversation_history.extend([
            {"role": "model", "parts": [{"function_call": {"name": fn_name, "args": fn_args or {}}}]},
            {"role": "user",  "parts": [{"function_response": {"name": fn_name, "response": _hist_result}}]},
        ])
        # Cap: keep the synthetic opener (index 0) + the last 10 action pairs (20 entries)
        if len(conversation_history) > 21:
            conversation_history = conversation_history[:1] + conversation_history[-20:]

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
