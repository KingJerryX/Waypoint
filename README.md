# Orbit — Browser agent MVP

A lightweight browser agent that opens a URL and completes a task (summarize, extract, or light interaction) using **Playwright** and **Google Gemini**.

## What’s in this repo

- **CLI and FastAPI** entrypoint: paste URL + task, get an answer.
- **Browser layer** (`browser_tools.py`): open URL, get page state, click, scroll, type.
- **Page state** (`page_state.py`): structured snapshot (title, text, buttons, links, inputs) for the LLM.
- **Agent loop** (`agent_loop.py`): Gemini chooses tools → execute → repeat until `done` or max steps.
- **Bonus:** human approval (CLI), evaluation script, personalization via constraints.

## Setup (you do this)

### 1. Python env and deps

```bash
cd orbit
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Playwright browsers

```bash
playwright install chromium
```

### 3. Gemini API key

Create an API key (e.g. [Google AI Studio](https://aistudio.google.com/)), then:

```bash
export GOOGLE_API_KEY="your-key"
```

Or add to a `.env` in `orbit/` and load with `python-dotenv` (optional):

```
GOOGLE_API_KEY=your-key
```

## Run

### Generate a link and run the agent in the browser

1. **One-time setup:** In `orbit/`, set `GOOGLE_API_KEY` (env or `.env`), create venv, `pip install -r requirements.txt`, `playwright install chromium`, and build the frontend: `cd frontend && npm install && npm run build && cd ..`.
2. **Start the server:** From `orbit/`, run `uvicorn main:app --reload`.
3. **Create a manual:** Open http://localhost:8000, fill **Title**, **URL to open**, and **Task for the agent**. Optionally check **Auto-run when link is opened**. Click **Create & get link**.
4. **Share the link:** Copy the link (e.g. `http://localhost:8000/go/abc12345` or with `?auto=1` for auto-run). When someone opens it, they see the task and can click **Run agent** (or the agent runs automatically if you used the auto-run option).
5. **Run:** The server runs the agent (Playwright + Gemini) and returns the answer on the page.

### CLI

```bash
python main.py --url "https://example.com" --task "Summarize the main content in 2 sentences"
```

Options:

- `--max-steps 8` — max tool calls (default 8).
- `--no-click` — read-only (no click/type).
- `--approve-clicks` — prompt for approval before each click/type.
- `--headed` — show browser window.
- `--log-dir ./logs` — where to write session JSON logs.

### Web app (React frontend — manuals + shareable links)

**Production (serve built React app from FastAPI):**

```bash
cd frontend && npm install && npm run build && cd ..
uvicorn main:app --reload
```

Open **http://localhost:8000**. The React app is served from `frontend/dist/`.

**Development (React dev server with API proxy):**

```bash
# Terminal 1: backend
uvicorn main:app --reload

# Terminal 2: frontend (from project root; proxies /api, /run to backend)
npm install   # once, installs frontend deps via postinstall
npm run dev
```

Open **http://localhost:5173** for the Vite dev server (hot reload). API and run requests are proxied to port 8000.

- **Create a manual:** Enter title, URL, and task → "Create & get link" → copy the shareable link (e.g. `http://localhost:8000/go/abc123`).
- **Send the link:** When someone opens it, they see the manual and a "Run agent" button; clicking it runs the browser agent and shows the result.
- **My agents:** Save configs in this browser (localStorage) with "Save as My Agent"; use "Use" to fill the form and reuse when creating new manuals.

### API

```bash
curl -X POST http://localhost:8000/run \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com", "task": "Summarize the page"}'
```

- `POST /api/manuals` — create manual (body: `title`, `url`, `task`, `max_steps`, `no_click`); returns `id` for the shareable link `/go/{id}`.
- `GET /api/manuals/{id}` — get manual by id (for the run page).

## Evaluation

1. Edit `eval_dataset.json`: list of `{ "url", "task", "expected_keywords" }` (optional) or `expected_summary_length_min`.
2. Run:

```bash
python eval.py --dataset eval_dataset.json --output eval_report.json
```

This writes `eval_report.json` and `eval_report.md` with per-run metrics and a small table.

## What you need to do (can’t be fully automated)

| Step | What to do |
|------|------------|
| **API key** | Create and set `GOOGLE_API_KEY` (see above). |
| **Playwright** | Run `playwright install chromium` in your env. |
| **Eval dataset** | Add your own URLs and tasks to `eval_dataset.json` (and optional expected keywords/length). |
| **Human approval in API** | The API has no interactive prompt. For approval in a web UI, add a webhook or polling endpoint that your frontend calls; the plan in `8-hour_browser_agent_evaluation_96b0ae9e.plan.md` describes the approval gate — you’d plug in your own `request_approval` that waits on your backend. |

## Project layout

```
orbit/
├── main.py           # FastAPI app + CLI
├── agent_loop.py     # Gemini + tools + approval + metrics
├── browser_tools.py  # Playwright wrappers
├── page_state.py     # get_page_state()
├── prompts.py        # System prompt + constraint injection
├── config.py         # UserConstraints
├── manuals.py        # Server-side manual storage (shareable links)
├── eval.py           # Batch eval script
├── eval_dataset.json
├── requirements.txt
├── frontend/        # React (Vite) app: create manual, My Agents, run-by-link page
├── static/          # Legacy static HTML (used if frontend/dist not built)
├── data/             # manuals.json (created on first manual)
├── logs/             # Session logs and screenshots
└── README.md
```

## Limits (MVP)

- Works best on simple, static-ish pages.
- No login, CAPTCHA, or payments.
- Selector/click matching can be brittle; “click by text” is best for buttons/links.
- Set `GOOGLE_API_KEY` and run Playwright install as above or the agent won’t run.
