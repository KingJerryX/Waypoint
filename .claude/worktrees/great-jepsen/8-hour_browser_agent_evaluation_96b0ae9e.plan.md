---
name: 8-hour browser agent evaluation (Orbit)
overview: Evaluation of whether the browser-agent MVP (Playwright + LLM, single-page summarization/extraction) is plausible in 8 hours, with a reality-check on the hour-by-hour plan and concrete recommendations.
todos: []
isProject: false
---

# 8-hour browser agent MVP — plausibility evaluation

## Verdict: **Plausible, with caveats**

The outline is well-scoped and the 8-hour breakdown is **achievable** for someone who has used Playwright and an LLM API before. For a first-time user of either, budget 10–12 hours or trim scope. Below is a reality check by hour and what to watch for.

---

## Hour-by-hour reality check


| Hour  | Plan                                                          | Plausible? | Notes                                                                                                                |
| ----- | ------------------------------------------------------------- | ---------- | -------------------------------------------------------------------------------------------------------------------- |
| **1** | Project setup, Playwright, LLM SDK, route/CLI                 | Yes        | FastAPI + Playwright + **Gemini** (Google AI SDK). CLI-only keeps it fast.                                            |
| **2** | Open URL, extract title + visible text                        | Yes        | Playwright’s `page.content()` / `page.inner_text()` get you there quickly.                                           |
| **3** | `get_page_state()` — title, url, text, buttons, inputs, links | Yes        | Query `button`, `a`, `input` and build a small JSON. Main work is choosing selectors and trimming text length.       |
| **4** | LLM tool-calling: schema, task + state, parse action          | **Tight**  | Schema + one round is fine. Parsing tool calls (JSON mode or structured output) can eat time if you’re new to it.    |
| **5** | Browser tools: click, type, scroll, extract, done             | Yes        | Thin wrappers over Playwright. Click-by-text is trickier; allow 30 min for “click element containing text” fallback. |
| **6** | Agent loop: cycle, max_steps, stop on done                    | Yes        | Straightforward loop. Most risk is the model not returning valid tool calls; add a retry/fallback.                   |
| **7** | Logging, error handling, screenshot on failure                | **Tight**  | “Basic” is doable; “robust” is not. Do: log each action, try/except around Playwright, one screenshot on error.      |
| **8** | Polish one demo (e.g. job extractor)                          | **Risky**  | Only if hours 1–7 didn’t slip. Otherwise this becomes “fix the one flow that almost works.”                          |


**Where time usually goes over:** Hour 4 (tool-calling/parsing), Hour 5 (reliable click/selector logic), Hour 7 (debugging why the agent loop fails). The spec’s “optional: CLI” is a good time-saver — skip a React form for the MVP.

---

## What makes it plausible

1. **Narrow scope** — One use case (e.g. “extract job qualifications”) and a small tool set keeps the agent loop simple.
2. **Page state as JSON** — Sending title, text preview, buttons, links (not raw HTML) keeps prompts small and behavior more predictable.
3. **Deterministic browser layer** — All AI lives in “what to do”; Playwright does the “how,” which is easy to debug.
4. **Bounded loop** — `max_steps = 5–8` and “done” avoid runaway behavior and make demos stable.
5. **Mature stack** — Playwright + FastAPI + **Gemini** are well-documented; you’re not fighting the stack.

---

## What makes it slip past 8 hours

1. **Tool-calling format** — If the model returns malformed JSON or wrong tool names, you’ll spend time on parsing and retries. Mitigation: use **Gemini** function calling (e.g. `google.generativeai` with declared tools) and a single retry with a “fix your JSON” prompt.
2. **Selectors** — “Click ‘Read more’” often needs fallbacks (text match, aria-label, nth button). Plan one simple heuristic (e.g. “button/link whose text contains X”) and don’t over-generalize.
3. **Dynamic content** — Pages that load content via JS need `wait_for_load_state` or a short delay. Add one generic wait (e.g. `networkidle` or 2s) so the first demo doesn’t fail on SPAs.
4. **Scope creep** — Adding a second use case or “one more tool” in the middle will blow the budget. Stick to one demo path.

---

## Recommended scope for a true 8-hour MVP

- **Input:** CLI only (URL + task as args or prompts). Add a minimal web form only if you have time left.
- **Tools:** `open_url`, `get_page_state`, `click`, `scroll_down`, `done` — skip `type` unless your chosen demo needs it.
- **Demo:** One path only, e.g. “Job posting: extract role, company, qualifications, responsibilities.” Test on 2–3 known URLs (e.g. a simple job page, not LinkedIn).
- **Logging:** Append-only JSON log (one object per action). Screenshot only on failure or on `done`.
- **Error handling:** Try/except around each tool; on failure, re-inject “last action failed” into the next LLM call and consume one step. No fancy recovery.

---

## Suggested folder structure (for when you build)

Use the **simpler** layout so you don’t spend time on structure:

```
orbit/
├── main.py           # FastAPI app or CLI entrypoint
├── agent_loop.py     # Loop: get state → LLM → execute tool
├── browser_tools.py  # Playwright wrappers
├── page_state.py     # get_page_state()
├── prompts.py        # System + user prompt templates
├── requirements.txt  # fastapi, uvicorn, playwright, google-generativeai
├── logs/             # session JSON logs
└── README.md
```

Skip a separate `frontend/` until the backend and one CLI demo work.

---

## Summary

- **Plausible in 8 hours:** Yes, if you keep to one demo, CLI input, and the minimal tool set, and you’re comfortable with Playwright and one LLM API.
- **Likely to hit 8 hours:** Only if you avoid scope creep and use structured tool-calling from the start. Reserve the last hour for “make one URL + one task work end-to-end” rather than new features.
- **Good first step in orbit:** Implement `browser_tools.py` (open URL, get text) and `page_state.py` (structured snapshot), then add the agent loop and a single “extract job info” flow. That’s the minimal path to a demo that matches the project statement.

---

## LLM: Gemini

- Use **Google Gemini** via `google-generativeai` (e.g. `genai.GenerativeModel` with function declarations).
- Configure tool/function calling via Gemini’s native tool schema; the agent parses the model’s `function_call` (or equivalent) and executes the corresponding browser tool.
- Set `GOOGLE_API_KEY` (or equivalent) in env; no other LLM provider needed for this plan.

---

## Bonus features (post-MVP)

These extend the 8-hour MVP and should be scoped as follow-up work.

### 1. Human approval steps

- **Goal:** Let a human approve (or reject) certain agent actions before they run, especially high-impact or irreversible ones.
- **Design:**
  - Before executing a tool, the backend can emit an **approval request** (e.g. “About to click: ‘Submit’ — approve? [y/n]”). In a CLI, this is a blocking prompt; in a future UI, a button or webhook.
  - Define which tools require approval (e.g. `click` when the button text matches a risky pattern, or all `click`/`type` by default). Keep `get_page_state`, `scroll_down`, and `done` auto-approved.
  - Store approval result in the action log (e.g. `approved_by: "user"`, `rejected`, or `timeout`).
- **Implementation sketch:** In the agent loop, after the LLM returns an action but before calling `browser_tools`, check an `requires_approval(action)` predicate; if true, call a `request_approval(action, context)` that blocks until the user responds, then proceed or skip and re-prompt the LLM.
- **Files to touch:** `agent_loop.py` (approval gate), optional `approval.py` or config (which actions need approval, timeouts).

### 2. Evaluation metrics

- **Goal:** Measure how well the agent performs so you can compare runs, tune prompts, and debug.
- **Metrics to capture (per run or per task):**
  - **Task success:** Binary or ordinal (e.g. “full / partial / fail”) — did the final answer satisfy the user’s task?
  - **Steps used:** Number of tool calls until `done` (lower can mean more efficient).
  - **Tool success rate:** Fraction of tool calls that succeeded (no selector error, no timeout).
  - **Latency:** Time to first token and total run time; optional per-step breakdown.
  - **Screenshot / state digest:** Optional hash or summary of final page state for regression checks.
- **Design:**
  - Log each run to a structured format (e.g. `logs/session_<id>.json`) with: `task`, `url`, `steps[]`, `final_answer`, `metrics: { steps_used, tools_ok, total_time_s, success }`.
  - Add a small **evaluation script** (e.g. `eval.py`) that reads a set of (url, task, expected_summary_or_criteria) and runs the agent, then computes success and steps; output a simple report (e.g. CSV or markdown table).
- **Implementation sketch:** Instrument `agent_loop.py` to record every tool call and result; at `done`, compute and persist metrics. Keep eval dataset and scoring logic in `eval.py` so the main app stays simple.
- **Files to touch:** `agent_loop.py` (logging fields), `eval.py` (batch runs + metrics), `logs/` schema.

### 3. Personalization with constraints

- **Goal:** Adapt the agent’s behavior to user preferences or guardrails without changing code (e.g. “only summarize, never click” or “prefer extracting bullet points”).
- **Design:**
  - **User constraints / profile:** A small config or API payload per run (or per user) that encodes:
    - **Allowed tools:** e.g. `["open_url", "get_page_state", "scroll_down", "done"]` — no `click` or `type`.
    - **Task bias:** e.g. “Prefer concise bullet lists” or “Always include source URL in the answer.”
    - **Hard limits:** e.g. `max_steps: 3`, “Do not visit any URL outside this domain.”
  - The **prompt** and **tool execution** layer both respect these: the system prompt includes the user’s constraints, and the backend filters or blocks tool calls that violate them (e.g. if `click` is disallowed and the LLM returns `click`, skip it and re-prompt with “That action is not allowed”).
- **Implementation sketch:**
  - Define a `UserConstraints` (or `AgentConfig`) dataclass: `allowed_tools`, `max_steps`, `task_instruction_override`, optional `allowed_domains`.
  - In `prompts.py`, inject constraint text into the system prompt (e.g. “Allowed tools: …”, “User preference: …”).
  - In `agent_loop.py`, before executing a tool: check `action.name in constraints.allowed_tools`, and optionally check `allowed_domains` for `open_url`. If violated, don’t execute and pass a short message back to the LLM.
  - CLI or API can accept constraints via flags (e.g. `--no-click`) or a small config file / JSON body.
- **Files to touch:** `prompts.py` (constraint injection), `agent_loop.py` (constraint checks, optional `config.py` or request schema for constraints).

---

## Bonus features — summary

| Feature | Purpose | Main files |
|--------|---------|------------|
| Human approval | Safety and control over sensitive actions | `agent_loop.py`, optional `approval.py` |
| Evaluation metrics | Measure success, steps, latency; batch eval | `agent_loop.py`, `eval.py`, logs schema |
| Personalization with constraints | User-specific tools, limits, and style | `prompts.py`, `agent_loop.py`, config/request schema |

Implement the 8-hour MVP and one demo first; then add these in order: constraints (easiest to wire), evaluation (helps iterate), human approval (needs UX or CLI flow).

---

## Implementation checklist (what’s built vs what you do)

**Already in the repo (orbit/):**

- `main.py` — CLI and FastAPI; `--url`, `--task`, `--no-click`, `--approve-clicks`, `--headed`, `--log-dir`
- `agent_loop.py` — Gemini tool-calling loop, max_steps, constraint checks, approval gate, metrics logging
- `browser_tools.py` — open_url, get_page_state, click, type, scroll_down, screenshot
- `page_state.py` — structured page snapshot (title, text, buttons, links, inputs)
- `prompts.py` — system prompt and constraint injection
- `config.py` — UserConstraints (allowed_tools, max_steps, task_instruction_override, allowed_domains, require_approval_for_tools)
- `eval.py` — batch run on a JSON dataset; writes JSON + Markdown report
- `eval_dataset.json` — example rows (url, task, expected_keywords / expected_summary_length_min)
- `requirements.txt`, `README.md`, `.env.example`, `logs/.gitkeep`

**You do these (cannot be fully automated):**

1. **Environment:** `cd orbit && python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt && playwright install chromium`
2. **API key:** Set `GOOGLE_API_KEY` (see README and `.env.example`).
3. **Eval data:** Edit `eval_dataset.json` with your URLs/tasks and optional expected criteria; run `python eval.py --dataset eval_dataset.json --output eval_report.json`.
4. **API approval (optional):** For human-in-the-loop in the HTTP API, add a webhook or polling endpoint that your UI calls; pass a custom `request_approval` into `run_agent` that blocks until your backend records approval/reject (see “Human approval steps” above).
5. **If Gemini tool format errors:** Adjust `_build_tools_for_gemini()` in `agent_loop.py` for your `google-generativeai` version (see README limits).