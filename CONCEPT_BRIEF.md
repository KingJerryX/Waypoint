# Orbit Concept Brief

## Who This Is Built For

Orbit is built for people who need web tasks completed quickly without writing or maintaining custom automation scripts.

Primary users:
- Operators and analysts who repeatedly gather or summarize information from websites.
- Team members who need to share repeatable browser workflows with others using a link.
- Builders/prototypers who want to test agent-driven browser automation with visible, step-by-step execution.

## What Problem It Solves

Many web workflows are repetitive, manual, and hard to delegate:
- A person has to open sites, click through pages, copy details, and summarize findings each time.
- One-off scripts are brittle, difficult for non-engineers to use, and not easily shareable.
- Teams often lack a simple handoff format for "run this exact browser task."

Orbit solves this by turning a plain-language task into a runnable browser automation that can be executed live and shared with others.

## Why This Problem Matters

This matters because repetitive web tasks directly reduce focus and speed:
- Time is lost in manual navigation and copy/paste work.
- Results are inconsistent across team members doing the same task differently.
- Knowledge transfer is weak when instructions are informal instead of executable.

Orbit improves this by providing a consistent, repeatable run flow with visible progress and reusable links.

## What The Product Does

Orbit is an AI browser automation product that accepts a task and optional starting URL, runs the task in a controlled browser session, streams execution screenshots, and returns a final answer. Users can also save and share automations through link-based manuals so others can rerun the same workflow.

## User Experience, Step by Step

1. **Open the app**
   - User opens Orbit home page.
   - System loads the React UI with task input, optional URL, and max-steps control.

2. **Describe the task**
   - User enters a natural-language prompt (for example, summarize content, gather data, perform light interaction).
   - System can estimate a recommended step budget from prompt text through `/api/estimate`.

3. **Start automation**
   - User clicks Run Automation.
   - Frontend calls `POST /api/run/local` with prompt, optional URL, and `max_steps`.
   - Backend starts a local Playwright + agent run and opens an SSE stream.

4. **Watch live execution**
   - User sees status and browser screenshots update in near real time.
   - Agent loop repeatedly:
     - gathers structured page state,
     - asks Gemini which tool to call next,
     - executes the selected browser action via Playwright,
     - continues until done or step limit.

5. **Receive result**
   - User receives final answer in the UI when agent emits `done`.
   - If the run fails or times out, user sees an error state and can rerun with a higher step limit.

6. **Create shareable workflow**
   - User clicks Generate shareable link with title + task + optional URL.
   - Frontend calls `POST /api/share`, backend persists manual config, and returns a short ID.
   - User shares `/go/{slug}` link with others.

7. **Run from shared link**
   - Recipient opens `/go/{slug}` and clicks Run this automation.
   - System fetches manual config from `GET /api/manuals/{slug}` and runs the same local automation flow.

## Five Key Features (Real and Working)

1. **Live local browser runs with streaming screenshots**
   - Implemented via `POST /api/run/local` and SSE event streaming (`status`, `screenshot`, `done`, `error`).

2. **Shareable automation links**
   - Users can create a persistent manual with title/task/URL/max steps and share via `/go/{slug}`.

3. **Saved automation library in browser**
   - Home page supports local save/load/delete of automation presets via `localStorage`.

4. **Prompt-based step estimation**
   - Backend endpoint `/api/estimate` uses Gemini to return a bounded integer estimate for `max_steps`.

5. **Tool-driven agent loop with controlled browser actions**
   - Agent supports `open_url`, `get_page_state`, `click`, `type`, `press_key`, `scroll_down`, and `done`, with constraints and max-step control.

## Tools, APIs, and Models Used

### Application Stack
- **Backend**: FastAPI (`main.py`) with REST + SSE endpoints.
- **Frontend**: React + Vite (`frontend/src`).
- **Browser automation**: Playwright Chromium (`browser_tools.py`).
- **Storage**:
  - Server-side manuals persisted in `data/manuals.json`.
  - Client-side saved automations stored in browser `localStorage`.

### External APIs
- **Google Gemini API** (via `google-generativeai`) for agent decisioning and step estimation.
- **Skyvern API** endpoints are present (`/api/run`, `/api/run/{run_id}`) for remote task execution/polling in the current backend.

### Models
- **Gemini Flash family** with dynamic fallback logic in the agent loop (for example `gemini-2.5-flash`, `gemini-2.5-flash-lite`, `gemini-2.0-flash`).
- **Gemini model for estimation route**: `gemini-2.0-flash`.

## How Gemini Is Used (Explicit)

Gemini is the decision engine, not the browser executor.

1. **Action planning in the main agent loop**
   - Orbit sends task context plus structured page state to Gemini.
   - Gemini is configured for function/tool calling and chooses the next allowed action.
   - Orbit executes that action via Playwright, captures the new state, and asks Gemini again.
   - This repeats until Gemini calls `done(answer)` or step budget is reached.

2. **Model resolution and fallback**
   - Orbit resolves available Gemini models at runtime and tries preferred Flash variants first.
   - If a model is unavailable/unsupported, Orbit falls back to the next candidate.

3. **Step count estimation**
   - Orbit uses a separate Gemini prompt to estimate likely browser steps for a user task.
   - Returned value is parsed and bounded to a safe range for UI control.

What Gemini does **not** do:
- Gemini does not directly click, type, scroll, or navigate webpages.
- Playwright performs execution; Gemini selects actions based on observed state and prompt rules.

## Current MVP Limitations

- Best on relatively simple and mostly public web flows.
- Login walls, CAPTCHA, and sensitive/irreversible actions are intentionally constrained.
- Some selectors/interactions can be brittle on heavily dynamic sites.
- Final quality depends on page accessibility, step budget, and model output quality.

