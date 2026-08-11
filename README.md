# LeetCode Guidance AI

Your personal Data Structures & Algorithms mentor. Ask about LeetCode
problems, DSA concepts, algorithm patterns, complexity analysis, and
interview prep — the AI guides you to the answer instead of just handing
it over, grounded in a curated local knowledge base.

Link your public LeetCode profile and it will analyse your solved problems,
point out weak areas, and recommend exactly which problem to practise next —
either in the chat, on the `/progress` dashboard, or through any MCP-capable
client (Claude Desktop, VS Code, opencode).

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
                                │  ├─────────────┤   │  ┌─────────────┐
                                │  │ LeetCode    │───▶ │ LeetCode    │
                                │  │ catalog +   │   │  GraphQL API │
                                │  │ recommender │   └─────────────┘
                                └───────────────────┘
```

- **Frontend** — `frontend/` (React 19 + Vite 8 + TypeScript + Tailwind 4).
  Uses Firebase Auth (Google / email-password). No direct Firestore access.
- **Backend** — `backend/` (FastAPI + Python 3.13). Decides intent, retrieves
  RAG context, streams answers over SSE, persists conversations, and serves
  the LeetCode account API.
- **RAG** — 33+ curated JSON documents in `backend/data/**` loaded into memory
  at startup and searched with a lightweight keyword/term scorer.
- **LeetCode** — a local catalog of 4,018 problems + a recommendation engine
  that suggests "solve next" problems from your accepted history, plus an
  async client for LeetCode's public GraphQL API (no credentials needed).
- **MCP** — `backend/mcp_server.py` exposes the LeetCode tools to any
  Model Context Protocol client over stdio or SSE.
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
| `LEETCODE_CACHE_TTL_SECONDS`| ✅       | Cache TTL for LeetCode account data (default 300) |

> `FIREBASE_PRIVATE_KEY` is a PEM block. When set in a shell or `dotenv`
> file, keep the `\n` sequences intact (the loader unescapes them).

## LeetCode account + MCP

No LeetCode API key is required — the backend reads your **public** profile
through LeetCode's GraphQL API.

- **Link your account** in **Settings → LeetCode account** (or ask the chat
  "link my LeetCode account").
- **See your progress** on the `/progress` dashboard: solved counts, weak
  areas, recent submissions and recommended problems.
- **Ask the AI**: "analyze my solved problems", "what should I solve next?".
- **MCP tools**: `python mcp_server.py` starts the LeetCode MCP server for
  any MCP client (stdio by default, `--sse` for HTTP on :8001). The repo's
  `.mcp.json` registers it for opencode.

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
    api/              # FastAPI routers (chat, user, health, leetcode)
    auth/             # Firebase JWT verification
    config/           # pydantic-settings configuration
    core/             # logging + exception handlers
    leetcode/         # async LeetCode GraphQL client (public data)
    llm/              # OpenRouter client (streaming + retries)
    mcp/              # LeetCode MCP server (tools for MCP clients)
    problems/         # 4,018-problem catalog + recommendation engine
    prompts/          # system / mentor / coding-rules markdown
    rag/              # loader, retriever, context formatter
    schemas/          # Pydantic request/response models
    services/         # conversation memory, LeetCode context builder
    data/             # curated JSON knowledge base (seed content)
  scripts/            # catalog build script (build_leetcode_catalog.py)
  tests/              # pytest suite
  main.py             # FastAPI application factory
  mcp_server.py       # standalone LeetCode MCP server entry point
frontend/
  src/
    components/       # reusable UI (Toast, ui/*)
    contexts/         # Auth, ChatHistory, Theme
    firebase/         # Firebase app init (auth only)
    layout/           # sidebar + topbar shell
    lib/              # API client, history helpers, theme utils
    pages/            # Landing, Login, Signup, Chat, Settings, LeetCode
firebase/
  firestore.rules     # security rules (defense-in-depth)
  firestore.indexes.json
docs/                 # architecture, API, deployment docs
```
