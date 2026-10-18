# Campus Customs Shop + Chatbot (Homework 4)

A Yale apparel shop website with an AI shopping assistant.

- **Frontend:** React + TypeScript + Vite (`frontend/`), at http://localhost:5173
- **Backend:** FastAPI + PydanticAI agent (`backend/`), at http://127.0.0.1:8000
- **Data:** SQLite database and product images in `data/` (local only, not in git)

The agent itself is four files in `backend/`: `prompts/prompt.md` (voice and safety rules), `agent.py`
(runs the agent loop), `tools.py` (read-only database tools) and `models.py` (the data shapes).
How the whole system works is explained in [`output/harness.md`](output/harness.md).

## 1. Place the data pack

The database and product images are not in this repository. Put the course data pack in a folder named
`data` next to `backend/` and `frontend/`:

```
hw4/
├── backend/
├── frontend/
└── data/                      <- add this folder
    ├── campus_customs.db
    └── products/              # product images referenced by the catalogue
```

The backend reads `data/campus_customs.db` and serves the images from `data/products/`. When it starts,
it adds any tables it needs (chat history, product views, product tags) to the database if they are missing.

## 2. One-time setup

You need **Python 3.11 or newer** and **Node.js 20.19 or newer** (22 recommended).

**Backend** (Windows PowerShell; on Mac/Linux use `python3` and `.venv/bin/python`):

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r ..\requirements.txt
```

**API key:** copy `.env.example` to `backend/.env` and replace the placeholder with your Portkey API key:

```powershell
copy ..\.env.example .env
notepad .env
```

**Frontend:**

```powershell
cd ..\frontend
npm install
```

## 3. Run it

Run the backend and frontend at the same time, in two terminals.

**Terminal 1, backend:**

```powershell
cd backend
.\.venv\Scripts\python.exe -m uvicorn main:app --reload --port 8000
```

You should see `Uvicorn running on http://127.0.0.1:8000`.

**Terminal 2, frontend:**

```powershell
cd frontend
npm run dev
```

Open **http://localhost:5173**. The frontend forwards `/api` and `/media` requests to the backend
(see `frontend/vite.config.ts`).

**Windows shortcut:** after the one-time setup, double-click `restart-backend.bat` and
`restart-frontend.bat` in the `hw4` folder. Each one stops anything already running on its port and
starts the server in its own window.

## 4. Run the tests

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest tests -q
```

The tests use a temporary copy of the database and a stand-in AI model, so they need no API key and never
change your data. The live AI tests in `tests/test_agent_prompt.py` are skipped unless you set
`RUN_LIVE_AGENT_TESTS=1`.

**Password reset emails:** after 3 wrong passwords (or "Forgot password?") a reset link is emailed to the
address on file. Without SMTP settings in `backend/.env` the email is saved to `backend/logs/outbox/`
instead, so you can open the `.eml` file and click the link. See `output/harness.md`, "Problem 4".

## What's where

| Path | What it is |
|---|---|
| `AI_prompts.md` | The prompt I wrote for each problem, plus follow-ups |
| `requirements.txt` | Python packages for the backend |
| `.env.example` | Settings the backend needs, with placeholders only |
| `backend/main.py` | FastAPI app: products, login, cart and orders, chat |
| `backend/agent.py`, `tools.py`, `models.py`, `prompts/prompt.md` | The shopping assistant |
| `backend/audit.py` | Writes the append-only audit trail of the agent loop |
| `backend/tests/` | Automatic tests |
| `frontend/` | The website (Vite + React + TypeScript) |
| `output/harness.md` | How the system works: data, model fields, tools, safety rules, specs |
| `output/design.md` | Problem 10: site design and why it helps customers buy |
| `output/usability.md` | Problem 9: usability improvements |
| `output/app_check.html` | Problem 11: live site test with screenshots (open in a browser) |
| `output/app_check_images/` | Screenshots linked from `app_check.html` |
| `output/audit_trail.json` | Problem 12: append-only log of agent-loop activity |
| `output/screenshots/` | Screenshots from Problems 4 to 10 |

## Not in this repository (on purpose)

- `backend/.env` (the real API key). Only `.env.example` with placeholders is included.
- `data/` (`campus_customs.db` and product images), per the course rules.
- `node_modules/`, `.venv/` and backend logs. They are rebuilt by the setup steps above.
