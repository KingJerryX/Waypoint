# Waypoint – Claude Agent Instructions

## Workflow Orchestration

### Plan Mode Default
Before writing any code, enter plan mode. Map out all files to touch, the order of changes, and potential side-effects. Only exit plan mode after the user approves the approach.

### Subagent Strategy
Spawn specialized subagents for parallel workloads (e.g., one agent exploring the codebase while another drafts the implementation). Use `isolation: "worktree"` for risky refactors so main branch stays clean.

### Self-Improvement Loop
After completing a task, re-read the diff and ask: "Is there a simpler way?" If yes, refactor before marking done. Prefer fewer files, fewer abstractions, and less code that does the same thing.

### Verification Before Done
Never mark a task complete without verifying the output. Run the server, check the browser, or read the relevant file. If a build step is required (e.g., `npm run build`), run it and confirm no errors.

### Demand Elegance
Reject solutions that add complexity without clear benefit. If a fix requires more than ~30 lines, question whether the architecture is right first.

### Autonomous Bug Fixing
When a bug is encountered mid-task, fix it immediately rather than noting it for later. Log what was broken and what changed so the user has full visibility.

---

## Task Management

1. **Capture requirements first** – restate the task in your own words before acting so misunderstandings surface early.
2. **Use TodoWrite** – for any task with 3+ steps, maintain a live todo list and update statuses in real time.
3. **One thing in-progress at a time** – complete and verify each step before starting the next.
4. **Surface blockers immediately** – if a required file, env var, or dependency is missing, stop and ask rather than guessing.
5. **Commit only when asked** – never create git commits unless the user explicitly requests it.
6. **Prefer targeted edits** – use `Edit` over `Write` to minimise diff noise and risk of overwriting good code.

---

## Core Principles

**Safety first** – never take irreversible actions (delete, overwrite, publish, purchase) without explicit user confirmation.

**Minimal footprint** – read before writing, ask before assuming, touch only the files the task requires.

**Transparency** – narrate what you are doing and why. If something unexpected happens, explain it clearly instead of silently retrying.

**Respect the stack** – Waypoint uses FastAPI + Playwright + Gemini + React/Vite. Prefer solutions that fit naturally into these tools rather than introducing new dependencies.

**Performance awareness** – every extra network call or sleep adds latency the user feels. Cache aggressively (see `_CACHED_MODEL_CANDIDATES`), avoid redundant waits, and profile before optimising.

**Human-in-the-loop** – when the browser hits a login wall, CAPTCHA, or payment gate, pause immediately via `request_human_help()` and wait for the user to resume. Never attempt to bypass these barriers.
