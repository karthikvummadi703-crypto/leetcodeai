# Architecture

## System overview

LeetCode Guidance AI is a two-tier web application: a React SPA talking to a
FastAPI backend. There is no server-side rendering; the backend exposes a
small, purpose-built REST + SSE API.

```
User
 │
 ▼
┌─────────────────────── React SPA (frontend/) ───────────────────────┐
│ Firebase Auth (Google / email+password) → ID token on every request │
│                                                                     │
│  Landing / Login / Signup   (public)                                │
│  /chat        Chat UI + SSE streaming + sidebar (history)          │
│  /settings    Theme, export data, delete all, link LeetCode        │
│  /progress    LeetCode dashboard (profile + recommendations)       │
└──────────────────────────────┬──────────────────────────────────────┘
                               │ REST (Authorization: Bearer <id token>)
                               ▼
┌─────────────────────── FastAPI (backend/) ─────────────────────────┐
│ Middleware: request logging, CORS                                   │
│ Auth: Firebase JWT verification → UserProfile (uid)                 │
│                                                                     │
│  api/chat      POST /chat, /new-chat, /chat-history, /chat/search,  │
│                GET /chat/{id}, POST /chat/{id}/regenerate,          │
│                DELETE /chat/{id}, PATCH /chat/{id}                  │
│  api/user      GET /profile, POST /profile/sync, DELETE /profile/chats│
│                GET /profile/export, POST /feedback                  │
│  api/health    GET /health                                          │
│  api/leetcode  GET /status, POST /link, DELETE /link,               │
│                GET /profile, GET /recommendations                   │
│                                                                     │
│  Agent: decide intent → retrieve RAG → build prompt → OpenRouter    │
│  Conversation memory: InMemoryStore | FirestoreStore                │
│  LeetCode: GraphQL client → catalog + recommender (local 4k index) │
│  MCP server (mcp_server.py): LeetCode tools over stdio / SSE       │
└─────────────────────────────────────────────────────────────────────┘
```

## Backend

### Application factory (`backend/main.py`)

`create_app()` assembles CORS, custom middleware, exception handlers, the API
router, and a lifespan handler that warms the knowledge base at startup.

### Request lifecycle

1. `RequestLoggingMiddleware` logs method/path/status/latency.
2. Route dependencies call `get_current_user` (`app/auth/firebase_auth.py`),
   which verifies the Firebase ID token from the `Authorization` header and
   returns a `UserProfile`. A 401 is returned for missing/invalid tokens.
3. Every conversation operation is scoped by `uid` — the store and API both
   treat `(uid, conversation_id)` as the lookup key, so users can never read
   or modify each other's data (404 on cross-user access).

### Agent pipeline (`app/agent/`)

For each chat message the agent:

1. **Decides intent** (`decision_engine.py`) — rule/keyword classifier that
   returns one of: `leetocode`, `dsa`, `algorithm`, `programming`,
   `greeting`, `off_topic`, and a strategy (`rag_plus_llm` | `llm_only` |
   `off_topic`).
2. **Retrieves context** (`app/rag/retriever.py`) when the strategy is
   `rag_plus_llm` — scores every document in the in-memory knowledge base by
   term hits (title/body weight) and returns the top chunks.
3. **Builds the prompt** (`app/services/prompt_builder.py`) — system prompt
   (+ optional `## Retrieved Context` block, capped at 8k chars) + last 20
   history turns + the new user message.
4. **Calls OpenRouter** (`app/llm/openrouter_client.py`) — streaming by
   default. Handles rate limits/5xx with exponential backoff, fails fast on
   4xx, and never retries mid-stream once the first token has been emitted
   (prevents duplicated output).

### Conversation storage (`app/services/conversation_memory.py`)

A single module-level API (`create_conversation`, `append_message`,
`load_conversation`, `list_conversations`, `rename_conversation`,
`delete_conversation`, `search_conversations`, `truncate_last_turn`,
`delete_all_conversations`, `sync_profile`, `save_feedback`,
`export_user_data`) is backed by one of two stores selected at startup:

- **`InMemoryStore`** — Python `dict` keyed by uid. Used in tests and when
  Firebase is not configured.
- **`FirestoreStore`** — Firestore collections when Firebase Admin
  credentials are present:

  ```
  users/{uid}
  conversations/{id}              # uid, title, created_at, updated_at
  conversations/{id}/messages/{mid}
  feedback/{id}
  ```

When a conversation's first user message arrives, an automatic title is
generated from it (truncated to 40 chars).

### Streaming contract

`POST /chat` with `stream: true` returns `text/event-stream`. Every chunk is
JSON-encoded so multi-line tokens survive SSE framing:

```
data: {"chunk":"Hello"}\n\n
data: {"chunk":" world"}\n\n
data: [DONE]\n\n
```

The final assistant message is persisted only after streaming completes, even
if the client disconnects mid-stream.

## Frontend

### Auth (`src/contexts/AuthContext.tsx`)

Wraps Firebase Auth. Exposes Google popup sign-in, email/password
sign-in/sign-up, password reset, and sign-out, plus a friendly
error-message mapper. `ProtectedRoute` redirects unauthenticated users.

### State & data flow

- `ChatHistoryContext` — sidebar conversation list, debounced search,
  optimistic rename/delete, `refresh()` after every chat.
- `Toast` — lightweight global notifications.
- `Theme` (`src/lib/theme.ts`) — persisted to `localStorage`, applied before
  React mounts to avoid a flash of the wrong theme.

### Chat page (`src/pages/Chat.tsx`)

- Loads `?conv=` on mount; otherwise creates a conversation lazily on the
  first message (empty chats are never persisted).
- Consumes the SSE stream via `streamChat` and appends chunks to the active
  assistant bubble. Message bubbles are memoized so streaming updates
  re-render only the active message.
- Regenerate truncates the last user/assistant turn on the backend first,
  then re-asks.
- Code blocks are rendered with `react-syntax-highlighter` using `PrismLight`
  with only common languages registered (keeps the bundle small).

### Code splitting

Pages are lazy-loaded (`React.lazy`) so `Chat`/`Settings`/auth pages download
on demand. The Chat chunk is ~192 kB (62 kB gzip).

## RAG knowledge base

Seed documents live in `backend/data/**/*.json`. At startup the loader
normalizes each document into a `DataDocument` (title, number, difficulty,
pattern, tags, description, sections) and builds a lowercase search index.
`retrieve()` ranks documents by weighted term frequency (title hits weigh
more than body hits) and returns up to `top_k` formatted chunks.

## LeetCode integration

### Problem catalog (`app/problems/catalog.py`)

A local index of 4,018 problems is built at startup from
`backend/data/leetcode_catalog.json` (generated by
`backend/scripts/build_leetcode_catalog.py`). It supports lookup by number,
slug or fuzzy title, plus token-overlap search across title/slug/topics.

### Recommendation engine (`app/problems/recommender.py`)

`recommend_next(solved_slugs, solved_problems, …)` scores every *unsolved,
free* catalog problem to nudge the user towards:

- untouched (blind-spot) topics,
- the difficulty level they have solved least,
- high-acceptance, curated problems that have an in-depth solution in the
  knowledge base,
- a varied mix (deterministic jitter so suggestions stay fresh).

### LeetCode client (`app/leetcode/client.py`)

An async GraphQL client that reads **public** LeetCode data (profile,
solved counts, recent accepted submissions, languages, contest rating). No
credentials are stored. Typed errors (`UserNotFoundError`,
`LeetCodeError`, `LeetCodeRateLimitError`) let callers degrade gracefully.
Snapshots are cached in-process with a configurable TTL
(`LEETCODE_CACHE_TTL_SECONDS`, default 300 s) so the agent and dashboard do
not hammer the public API.

### Account-aware agent

The decision engine recognizes personal account questions ("analyze my
solved problems", "what should I solve next?") via `_ACCOUNT_RE` and routes
them to the `LEETCODE_ACCOUNT` intent. The agent then loads the user's
cached snapshot + recommendations and injects a structured account context
block (`app/services/leetcode_context.py`) into the system prompt before
calling the LLM. Linked usernames are persisted per user in the
conversation store (`users/{uid}/leetcode_username` in Firestore).

### MCP server (`backend/mcp_server.py`)

A standalone Model Context Protocol server
(`app/mcp/leetcode_server.py`) exposes the same account/catalog tools to
any MCP client (Claude Desktop, Cursor, VS Code, opencode):

- `get_leetcode_profile`, `get_solved_problems`, `analyze_leetcode_account`
- `recommend_next_problems`
- `search_problems`, `get_problem_detail`

Run it with `python mcp_server.py` (stdio) or `python mcp_server.py --sse`
(HTTP on :8001). The repo root `.mcp.json` wires it up for opencode.

## Configuration matrix

| Env                | Storage           | LLM          | Docs enabled |
| ------------------ | ----------------- | ------------ | ------------ |
| local dev          | InMemory          | OpenRouter   | Yes          |
| local + Firebase   | Firestore         | OpenRouter   | Yes          |
| production         | Firestore         | OpenRouter   | No           |
