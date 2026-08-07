# LeetCode Guidance AI

Your personal Data Structures & Algorithms mentor. Ask about LeetCode
problems, DSA concepts, algorithm patterns, complexity analysis, and
interview prep — the AI guides you to the answer instead of just handing
it over, grounded in a curated local knowledge base.

## Architecture at a glance

```
┌──────────────┐   REST / SSE    ┌───────────────────┐
│  React + Vite │ ──────────────▶ │   FastAPI backend  │
│  (Firebase    │                 │  ┌─────────────┐   │
│   Auth only)  │                 │  │  Agent (AI) │   │
└──────────────┘                 │  ├─────────────┤   │
                                │  │ RAG (local  │   │  ┌─────────────┐
                                │  │  JSON KB)   │───▶ │  OpenRouter  │
                                │  ├─────────────┤   │  │   (LLM)     │
                                │  │ Firestore   │   │  └─────────────┘
                                │  │ (optional)  │   │
                                └───────────────────┘
```

- **Frontend** — `frontend/` (React 19 + Vite 8 + TypeScript + Tailwind 4).
  Uses Firebase Auth (Google / email-password). No direct Firestore access.
- **Backend** — `backend/` (FastAPI + Python 3.13). Decides intent, retrieves
  RAG context, streams answers over SSE, persists conversations.
- **RAG** — 33+ curated JSON documents in `backend/data/**` loaded into memory
  at startup and searched with a lightweight keyword/term scorer.
- **LLM** — OpenRouter (default model `google/gemini-2.5-flash`).
- **Storage** — conversations persist to Cloud Firestore when Firebase Admin
  credentials are configured; otherwise an in-memory store is used (ideal for
  local development and tests).

## Quick start

### 1. Backend

```bash
cd backend
python -m venv .venv
# Windows:  .\.venv\Scripts\activate        # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt

copy .env.example .env      # Windows   (macOS/Linux: cp .env.example .env)
# Set OPENROUTER_API_KEY. Firebase creds are optional for local dev.

uvicorn main:app --reload --port 8000
```

Docs are served at <http://localhost:8000/docs> in development.

### 2. Frontend

```bash
cd frontend
npm install
copy .env.example .env.local      # set VITE_API_BASE_URL + Firebase web keys
npm run dev
```

Open <http://localhost:5173>.

## Scripts

| Where     | Command                | Purpose                      |
| --------- | ---------------------- | ---------------------------- |
| backend   | `pytest -q`            | Run all backend tests        |
| backend   | `uvicorn main:app --reload --port 8000` | Run API locally |
| frontend  | `npm run dev`          | Dev server with HMR          |
| frontend  | `npm run build`        | Type-check + production build |
| frontend  | `npm run lint`         | oxlint (0 warnings)          |
| frontend  | `npm run preview`      | Preview the production build |

## Configuration

All configuration is via environment variables. See
[`backend/.env.example`](backend/.env.example) and
[`frontend/.env.example`](frontend/.env.example).

| Variable                    | Backend? | Description                                   |
| --------------------------- | -------- | --------------------------------------------- |
| `OPENROUTER_API_KEY`        | ✅       | OpenRouter API key (required for LLM calls)   |
| `OPENROUTER_MODEL`          | ✅       | Model id, default `google/gemini-2.5-flash`   |
| `FIREBASE_PROJECT_ID`       | ✅       | Firebase project id (enables Firestore store) |
| `FIREBASE_CLIENT_EMAIL`     | ✅       | Service-account client email                  |
| `FIREBASE_PRIVATE_KEY`      | ✅       | Service-account private key (PEM)             |
| `APP_ENV`                   | ✅       | `development` / `production`                  |
| `FRONTEND_URL`              | ✅       | CORS origins when `APP_ENV=production` (comma-separated for multiple) |
| `BACKEND_URL`               | ✅       | Public backend URL (OpenRouter referer)       |
| `RATE_LIMIT_ENABLED`        | ✅       | Per-user rate limiting, default `true`        |
| `RATE_LIMIT_MAX_REQUESTS`   | ✅       | Max requests per window per user (default 20) |
| `RATE_LIMIT_WINDOW_SECONDS` | ✅       | Rate-limit window length (default 60)         |
| `VITE_API_BASE_URL`         | ❌       | Backend API base URL (frontend `.env.local`)  |
| `VITE_FIREBASE_*`           | ❌       | Firebase web-app config (frontend `.env.local`) |

> `FIREBASE_PRIVATE_KEY` is a PEM block. When set in a shell or `dotenv`
> file, keep the `\n` sequences intact (the loader unescapes them).

## Documentation

- [Architecture](docs/ARCHITECTURE.md)
- [API reference](docs/API.md)
- [Deployment guide](docs/DEPLOYMENT.md)

## Testing

Backend uses `pytest` with an in-memory store and stubbed LLM/agent so the
whole suite runs offline. Run from `backend/`:

```bash
.\.venv\Scripts\python.exe -m pytest -q
```

## Repository layout

```
backend/
  app/
    agent/            # intent/strategy decision engine + orchestration
    api/              # FastAPI routers (chat, user, health)
    auth/             # Firebase JWT verification
    config/           # pydantic-settings configuration
    core/             # logging + exception handlers
    llm/              # OpenRouter client (streaming + retries)
    prompts/          # system / mentor / coding-rules markdown
    rag/              # loader, retriever, context formatter
    schemas/          # Pydantic request/response models
    services/         # conversation memory, prompt builder/loader
    data/             # curated JSON knowledge base (seed content)
  tests/              # pytest suite
  main.py             # FastAPI application factory
frontend/
  src/
    components/       # reusable UI (Toast, ui/*)
    contexts/         # Auth, ChatHistory, Theme
    firebase/         # Firebase app init (auth only)
    layout/           # sidebar + topbar shell
    lib/              # API client, history helpers, theme utils
    pages/            # Landing, Login, Signup, Chat, Settings
firebase/
  firestore.rules     # security rules (defense-in-depth)
  firestore.indexes.json
docs/                 # architecture, API, deployment docs
```
