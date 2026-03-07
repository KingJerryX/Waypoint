"""System and user prompt templates; injects user constraints into the system prompt."""
import json
from typing import Any

from config import UserConstraints


SYSTEM_PROMPT_BASE = """You are a browser agent. Your job is to complete the user's task by using the provided tools to open a page, read or interact with it, then return a clear answer.

Rules:
- Complete the task in as few steps as possible.
- Use only the tools you are given. Do not make up tools or parameters.
- Prefer extracting visible information (get_page_state) before clicking or typing.
- Stop with "done" as soon as you have enough information to answer the user's task.
- Never take irreversible actions (e.g. submit forms that change data) unless the task explicitly asks you to.
- When you have the answer, call done(answer) with a clear, structured response (e.g. bullets or short paragraphs).
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


def build_user_message(task: str, current_state: dict[str, Any] | None, last_error: str | None = None) -> str:
    """Build the user-facing message: task + current page state + optional error."""
    parts = [f"Task: {task}"]
    if last_error:
        parts.append(f"\nLast action failed: {last_error}")
    if current_state:
        parts.append("\nCurrent page state:")
        parts.append(format_page_state_for_prompt(current_state))
    return "\n".join(parts)
