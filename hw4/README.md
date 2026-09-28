# Campus Customs: Yale Merch Storefront with an AI Shop Assistant

A storefront for **Campus Customs** (Yale Bulldog Blue, 57 Broadway, New Haven) with a chat assistant, "Handsome Dan", that answers from the shop's real database.

- **Frontend:** React + Vite + TypeScript.
- **Backend:** Python FastAPI, whose "brain" is a PydanticAI agent.

Shoppers can:
- browse and filter products
- search with a live search bar
- create an account and log in
- chat about merch and watch matching items appear on the page
- get honest price and stock answers straight from `campus_customs.db`

## What's in this folder

```
hw4/
├── backend/                 FastAPI app (run with Uvicorn from this folder)
│   ├── main.py              API: products, search, auth, chat, chat history
│   ├── prompts/prompt.md    ┐
│   ├── agent.py             │ the agent itself: system prompt, wiring/run loop,
│   ├── tools.py             │ tools it can call, and Pydantic types
│   ├── models.py            ┘
│   ├── search.py            one search engine shared by the site and the agent
│   ├── auth.py  memory.py  audit.py  db.py
├── frontend/                React + Vite + TypeScript site
├── scripts/                 app check, screenshots, DB evidence, agent measurements
├── output/                  write-ups and evidence (see "Deliverables")
├── screenshots/             Problem 9 and 10 screenshots used by the write-ups
├── AI_prompts.md            log of the prompts used to build this
├── requirements.txt         Python dependencies
└── .env.example             placeholder for the API key (copy to .env)
```

**Not in the repo, on purpose:** the real `.env`, `campus_customs.db`, and the product images (the course data pack). See `.gitignore`.

## Requirements

- **Python** 3.11+ (tested on 3.14)
- **Node.js** 22+ (tested on 24)
- A **Portkey API key** with access to OpenAI (the agent uses `gpt-5.6 luna` through Portkey)

## Setup

All commands start in this `hw4/` folder.

### 1. Place the data pack

Unzip the course data pack (`data.zip`) **into `hw4/`**. It contains a `data/` folder, so you should end up with:

```
hw4/data/campus_customs.db
hw4/data/products/*.jpg        (102 product photos)
```

```bash
unzip data.zip -d .
ls data            # → campus_customs.db  products
```

The backend reads `data/campus_customs.db` and serves images from `data/products/`. On first start it adds a `sessions` table and a nullable `results_heading` column to `chat_messages` if they're missing. Your catalogue and inventory rows aren't changed.

### 2. Add your API key

```bash
cp .env.example .env
# then edit .env and set PORTKEY_API_KEY=<your key>
```

Instead of `hw4/.env`, you can use a `.env` in the parent folder, or `export PORTKEY_API_KEY=...` in your shell. **Never commit `.env`.**

### 3. Install

```bash
python3 -m venv venv
venv/bin/pip install -r requirements.txt

cd frontend
npm install
cd ..
```

## Run it

Use two terminals.

**Backend** (FastAPI + agent, port 8000). It must be started from `backend/`:

```bash
cd backend
source ../venv/bin/activate          # Windows: ..\venv\Scripts\activate
uvicorn main:app --reload --port 8000
```

Check it: http://127.0.0.1:8000/api/health should show `{"status":"ok","agent_loaded":true}`. If `agent_loaded` is `false`, the API key wasn't found. The shop still works, but the chat is offline.

**Frontend** (React + Vite, port 5173):

```bash
cd frontend
npm run dev
```

Open **http://127.0.0.1:5173**. The Vite dev server forwards `/api` and `/media` to the backend on port 8000, so no other configuration is needed.

### Try it

- **Log in** with the seed test account `test@campuscustoms.yale.edu` / `password`, or create your own account.
- **Ask Dan** (bottom-right) things like:
  - "Do you have the fencing hoodie in medium?"
  - "What crewnecks do you have?"
  - "Any navy hoodies under $70 in XL?"
  - On a product page: "Do you have this in large?"
- **Search** from the nav bar ("hockey", "Saybrook", "quarter zip"), or filter the Products page by category, size in stock, color, and price.

## Optional scripts

Run these from `hw4/` while both servers are running.

| Command | What it does |
|---|---|
| `venv/bin/python scripts/app_check.py` | Live test: drives the site, checks answers against the DB, writes `output/app_check.html` + `output/app_check_images/` |
| `venv/bin/python scripts/screenshots.py problem9` | Retakes screenshots (`problem3` … `problem10`) |
| `venv/bin/python scripts/db_evidence.py` | Writes `output/db_writes.md` (users, sessions, saved chats) |
| `venv/bin/python scripts/measure_agent.py after` | Measures agent effort (model calls, tool calls, tokens, time) |

The browser scripts use Playwright with your installed Google Chrome (`channel="chrome"`). Without Chrome, run `venv/bin/playwright install chromium` and remove `channel="chrome"` from the script.

## Deliverables

| File | What it is |
|---|---|
| `output/harness.md` | How the system works: architecture, specs, models, tools, safety rules, and a build log by problem |
| `output/app_check.html` | Live app check (open by double-clicking). Uses `output/app_check_images/`. |
| `output/audit_trail.json` | Append-only log of agent-loop activity: time, tools, short args and results, stop reason |
| `output/usability.md` | The four usability improvements, with before/after measurements |
| `output/design.md` | Design changes and why they help shoppers stay and buy |
| `output/db_writes.md` | Evidence of database writes (accounts, sessions, saved chats) |
| `backend/prompts/prompt.md` | The agent's system prompt, including its safety rules |
| `AI_prompts.md` | Prompt log |

## Troubleshooting

- **"address already in use"**: another server is using port 8000 or 5173. Stop it, or pick another port. If you change the backend port, update `frontend/vite.config.ts` to match.
- **Products don't load or images are broken**: the data pack isn't in the right place. `hw4/data/campus_customs.db` and `hw4/data/products/` must exist.
- **`ModuleNotFoundError` when starting the backend**: start Uvicorn from inside `backend/` (the imports are plain, e.g. `import agent`).
