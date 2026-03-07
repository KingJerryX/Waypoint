"""User constraints and agent config for personalization."""
from dataclasses import dataclass, field
from typing import Optional

# Default allowed tools (no click/type for safest default; add as needed)
DEFAULT_ALLOWED_TOOLS = [
    "open_url",
    "get_page_state",
    "click",
    "scroll_down",
    "type",
    "press_key",
    "request_human_help",
    "done",
]


@dataclass
class UserConstraints:
    """Per-run or per-user constraints for the agent."""

    allowed_tools: list[str] = field(default_factory=lambda: list(DEFAULT_ALLOWED_TOOLS))
    max_steps: int = 8
    task_instruction_override: Optional[str] = None  # e.g. "Prefer concise bullet lists"
    allowed_domains: Optional[list[str]] = None  # e.g. ["example.com"]; None = any
    require_approval_for_tools: Optional[list[str]] = None  # e.g. ["click", "type"]

    def is_tool_allowed(self, tool_name: str) -> bool:
        return tool_name in self.allowed_tools

    def is_domain_allowed(self, url: str) -> bool:
        if not self.allowed_domains:
            return True
        from urllib.parse import urlparse
        try:
            domain = urlparse(url).netloc or url
            return any(d in domain for d in self.allowed_domains)
        except Exception:
            return False

    def requires_approval(self, tool_name: str) -> bool:
        if not self.require_approval_for_tools:
            return False
        return tool_name in self.require_approval_for_tools
