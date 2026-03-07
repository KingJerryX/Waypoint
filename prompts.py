"""System and user prompt templates; injects user constraints into the system prompt."""
import json
from typing import Any

from config import UserConstraints


SYSTEM_PROMPT_BASE = """You are a browser agent. Your job is to complete the user's task by using the provided tools to open a page, read or interact with it, then return a clear answer.

Rules:
- Complete the task in as few steps as possible.
- Use only the tools you are given. Do not make up tools or parameters.
- Navigate directly to websites when you know the URL (e.g. open_url("https://news.ycombinator.com")). Only use Google Search (https://www.google.com/search?q=...) when the task is a search query or you need to find something across multiple sources.
- If the current page is about:blank or irrelevant, call open_url with the correct destination immediately as your first action.
- Prefer extracting visible information (get_page_state) before clicking or typing.
- Stop with "done" as soon as you have enough information to answer the user's task.
- Never take irreversible actions (e.g. submit forms that change data) unless the task explicitly asks you to.
- When you have the answer, call done(answer) with a clear, structured response (e.g. bullets or short paragraphs).
- CRITICAL: You MUST ALWAYS respond with a tool call. NEVER respond with plain text alone.
- LOGIN WALLS & CAPTCHAS: If a page requires login, shows a signup form, or shows a CAPTCHA/human verification, call request_human_help(reason="...") immediately. Do NOT attempt to log in yourself. Wait for the human to complete it — they will see the live browser window. After they click Resume, continue the task.
- For job searches: use Google Search (e.g. open_url("https://www.google.com/search?q=software+engineering+jobs+Austin+TX+%24150k")) — Google shows job listings directly in results without login.
"""


def build_system_prompt(constraints: UserConstraints | None = None) -> str:
    """Build system prompt, optionally including user constraints."""
    parts = [SYSTEM_PROMPT_BASE]
    if constraints:
        parts.append("User constraints (you must follow these):")
        parts.append(f"- Allowed tools: {', '.join(constraints.allowed_tools)}")
        parts.append(f"- Maximum steps: {constraints.max_steps}")
        if constraints.task_instruction_override:
            parts.append(f"- Instruction: {constraints.task_instruction_override}")
        if constraints.allowed_domains:
            parts.append(f"- Only visit domains: {', '.join(constraints.allowed_domains)}")
    return "\n".join(parts)


def format_page_state_for_prompt(state: dict[str, Any]) -> str:
    """Turn page state dict into a short string for the model."""
    return json.dumps(state, indent=2)


def build_user_message(task: str, current_state: dict[str, Any] | None, last_error: str | None = None, resume_note: str | None = None) -> str:
    """Build the user-facing message: task + current page state + optional error."""
    parts = [f"Task: {task}"]
    if resume_note:
        parts.append(f"\n[SYSTEM NOTE] {resume_note}")
    if last_error:
        parts.append(f"\nLast action failed: {last_error}")
    if current_state:
        parts.append("\nCurrent page state:")
        parts.append(format_page_state_for_prompt(current_state))
    return "\n".join(parts)
