# Deployment Guide

This app is composed of a FastAPI backend and a React SPA. This guide covers
the recommended production setup: **Railway (backend)** + **Firebase Hosting
(frontend)** + **Firebase (Auth + Firestore)**.

## 1. Prerequisites

- A Firebase project with:
  - **Authentication** enabled: *Google* and *Email/Password* sign-in methods.
  - **Cloud Firestore** created (production mode is fine).
  - A **service account** (`Project settings → Service accounts → Generate
    new private key`) for the backend Admin SDK.
  - The web app config keys (`Project settings → Your apps → SDK setup`).
- An **OpenRouter** API key: <https://openrouter.ai/keys>.
- A **Railway** account and the **Firebase CLI** (`npm install -g firebase-tools`).
- `git` and the repo cloned locally (you'll push it to GitHub first).

## 2. Configure Firebase

1. Deploy the security rules and index:

   ```bash
   firebase login
   # From the repo root, after linking your project:
   firebase deploy --only firestore:rules,firestore:indexes
   ```

   The composite index on `conversations` (`user_id` ASC + `updated_at`
   DESC) is required for the chat-history query.

2. Enable sign-in providers in the Firebase console:
   **Authentication → Sign-in method → Google** and **Email/Password**.

> The frontend never talks to Firestore directly — only the backend does,
> via the Admin SDK. The deployed rules are a defense-in-depth layer.

## 3. Backend (Railway)

1. Push the repo to GitHub (e.g. `git init && git add -A && git commit`).

2. In Railway, **New Project → Deploy from GitHub repo**, then set:

   - **Root directory**: `backend` — required, otherwise Railpack builds the
     wrong app (the repo root contains a `package.json` and will be detected
     as Node). In Railway it lives at **Settings → Source → Root Directory**.
   - Build/start commands are **automatic**: `railway.json` is committed at
     the **repo root** (Railway only auto-detects the config file at the root
     — it does not follow the Root Directory path) and tells Railpack to run
     `uvicorn main:app --host 0.0.0.0 --port $PORT` with a `/api/health`
     healthcheck. (If you prefer, set them manually instead:
     Build `pip install -r requirements.txt`,
     Start `uvicorn main:app --host 0.0.0.0 --port $PORT`.)

3. Add these environment variables in the Railway dashboard
   (**Variables**):

   | Variable                 | Value                                    |
   | ------------------------ | ---------------------------------------- |
   | `OPENROUTER_API_KEY`     | your key                                 |
   | `OPENROUTER_MODEL`       | `google/gemini-2.5-flash` (or your model)|
   | `FIREBASE_PROJECT_ID`    | firebase project id                      |
   | `FIREBASE_CLIENT_EMAIL`  | service-account email                    |
   | `FIREBASE_PRIVATE_KEY`   | service-account PEM key                  |
   | `APP_ENV`                | `production`                             |
   | `FRONTEND_URL`           | your Firebase Hosting URL(s)             |
   | `BACKEND_URL`            | your Railway service URL                 |
   | `LOG_LEVEL`              | `INFO`                                   |
   | `RATE_LIMIT_ENABLED`     | `true` (default; set `false` to disable) |
   | `LEETCODE_CACHE_TTL_SECONDS` | `300` (optional) — cache TTL for LeetCode data |

   > `FIREBASE_PRIVATE_KEY` is a PEM block. Paste it as a multi-line value;
   > if you set it inline, keep the `\n` escapes intact.

4. `FRONTEND_URL` is the CORS allow-list. Firebase Hosting exposes **two**
   URLs for every project, so set both, comma-separated (no spaces):

   ```
   FRONTEND_URL=https://<project>.web.app,https://<project>.firebaseapp.com
   ```

   Add your custom domain here too if you attach one (still comma-separated).

5. Deploy. Railway builds from `backend/` and runs the start command.

> Rate limiting: the backend ships a per-user sliding-window limiter
> (`RATE_LIMIT_MAX_REQUESTS=20` / `RATE_LIMIT_WINDOW_SECONDS=60`) on
> `POST /chat` and `POST /new-chat`. It's in-process memory — accurate for a
> single Railway container. If you scale horizontally later, add a shared
> limiter (e.g. Redis) or a Railway edge/rate-limit layer.

## 4. Frontend (Firebase Hosting)

1. Create the production build:

   ```bash
   cd frontend
   npm run build
   ```

2. Set the frontend environment variables (used at build time by Vite).
   Either export them in your shell or create `frontend/.env.production`:

   | Variable                    | Value                        |
   | --------------------------- | ---------------------------- |
   | `VITE_API_BASE_URL`         | `https://<railway-url>/api`  |
   | `VITE_FIREBASE_API_KEY`     | from Firebase web config     |
   | `VITE_FIREBASE_AUTH_DOMAIN` | `<project>.firebaseapp.com`  |
   | `VITE_FIREBASE_PROJECT_ID`  | project id                   |
   | `VITE_FIREBASE_STORAGE_BUCKET` | `<project>.appspot.com`   |
   | `VITE_FIREBASE_MESSAGING_SENDER_ID` | from web config       |
   | `VITE_FIREBASE_APP_ID`      | from web config              |

   Example `frontend/.env.production`:

   ```
   VITE_API_BASE_URL=https://your-backend.up.railway.app/api
   VITE_FIREBASE_API_KEY=...
   VITE_FIREBASE_AUTH_DOMAIN=your-project.firebaseapp.com
   VITE_FIREBASE_PROJECT_ID=your-project
   VITE_FIREBASE_STORAGE_BUCKET=your-project.appspot.com
   VITE_FIREBASE_MESSAGING_SENDER_ID=...
   VITE_FIREBASE_APP_ID=...
   ```

3. Deploy hosting and Firestore together from the **repo root**. A
   `firebase.json` already exists at the root that serves the built SPA from
   `frontend/dist` with a rewrite (client-side routes `/chat`, `/settings`
   must load `index.html`) and points Firestore at the rules/index files in
   `firebase/`:

   ```json
   {
     "hosting": {
       "public": "frontend/dist",
       "ignore": ["firebase.json", "**/.*", "**/node_modules/**"],
       "rewrites": [{ "source": "**", "destination": "/index.html" }]
     },
     "firestore": {
       "rules": "firebase/firestore.rules",
       "indexes": "firebase/firestore.indexes.json"
     }
   }
   ```

   You do **not** need `firebase init hosting` — the file is already
   configured. Just log in and deploy:

   ```bash
   firebase login
   firebase deploy
   ```

   On the first run it asks which project to use (select your Firebase
   project) and deploys both hosting and Firestore rules/indexes.

4. Make sure the Railway `FRONTEND_URL` matches the deployed Firebase Hosting
   URLs exactly (scheme + host, no trailing slash).

## 5. Post-deploy checklist

- [ ] `GET <railway-url>/api/health` returns `{"status":"healthy",…}`.
- [ ] Google sign-in works on the live frontend.
- [ ] Email/password sign-up and sign-in work.
- [ ] A chat message streams a response (verifies OpenRouter key).
- [ ] Refresh the page mid-conversation — history persists (verifies
      Firestore + composite index).
- [ ] CORS: open the browser console and confirm no cross-origin errors on
      first chat.
- [ ] `/docs` is disabled (it is when `APP_ENV=production`).
- [ ] Settings → LeetCode account: linking a username succeeds and the
      `/progress` dashboard renders solved counts + recommendations.
- [ ] Monitoring/logs are reachable on the host platform.

> The LeetCode feature needs **no extra keys**: it reads public profiles via
> LeetCode's GraphQL API and matches them against the bundled problem
> catalog. The optional `LEETCODE_CACHE_TTL_SECONDS` only tunes how long
> account data is cached in-process.

## 6. Production hardening notes

- **Secrets**: only ever in Railway env vars / secret managers; never in
  the repo. The root `.gitignore` blocks `.env`.
- **Rate limiting**: enabled by default — per-user, 20 req / 60 s on
  `POST /chat` and `POST /new-chat` (in-memory, single container).
  Tune via `RATE_LIMIT_MAX_REQUESTS` / `RATE_LIMIT_WINDOW_SECONDS`.
- **Model costs**: `max_tokens` is capped at 4096 per request; the RAG
  context block is capped at 8k chars. Monitor OpenRouter usage.
- **Backups**: Firestore is automatically replicated; enable point-in-time
  recovery if you need it.
- **Scalability**: if you run more than one Railway container, the in-memory
  rate limiter and conversation store are per-instance. Use the
  Firestore-backed store (already supported) and add a shared limiter.

## 7. Run locally (localhost)

Run the backend and frontend on your machine with **PowerShell**. You still
need the Firebase project + OpenRouter key from the prerequisites above —
local mode uses the same services, just with development-friendly defaults
(open CORS, `/docs` enabled).

### 7.1 Backend (FastAPI, port 8000)

```powershell
# From the repo root
cd backend

# One-time setup: virtual environment + dependencies
python -m venv .venv
.\.venv\Scripts\Activate.ps1        # if blocked: Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
pip install -r requirements.txt

# One-time setup: backend secrets in backend\.env
#   OPENROUTER_API_KEY=...
#   FIREBASE_PROJECT_ID=...
#   FIREBASE_CLIENT_EMAIL=...
#   FIREBASE_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
# (APP_ENV / FRONTEND_URL already default to development values.)

# Start the API (auto-reload on code changes)
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Verify:

- Health check: <http://localhost:8000/api/health>
- Swagger UI: <http://localhost:8000/docs>

> The ChromaDB vector index for RAG is built automatically on first startup
> (`backend/data/chroma/`). The first run also downloads the ~80 MB embedding
> model to `~/.cache/chroma` — later starts are fast and offline.

### 7.2 Frontend (Vite dev server, port 5173)

Open a **second** PowerShell window:

```powershell
# From the repo root
cd frontend

# One-time setup: dependencies
npm install

# One-time setup: Firebase web config in frontend\.env.local
#   VITE_FIREBASE_API_KEY=...
#   VITE_FIREBASE_AUTH_DOMAIN=<project>.firebaseapp.com
#   VITE_FIREBASE_PROJECT_ID=<project>
#   VITE_FIREBASE_STORAGE_BUCKET=<project>.appspot.com
#   VITE_FIREBASE_MESSAGING_SENDER_ID=...
#   VITE_FIREBASE_APP_ID=...
# VITE_API_BASE_URL is optional locally — it defaults to http://localhost:8000/api.

# Start the dev server
npm run dev
```

Then open <http://localhost:5173>.

### 7.3 Local checklist

- [ ] Backend healthy at `http://localhost:8000/api/health`.
- [ ] Frontend loads at `http://localhost:5173` with no CORS errors in the
      browser console (development mode allows all origins).
- [ ] Sign-in works (Firebase Auth is still cloud-hosted).
- [ ] A chat message streams a response (verifies OpenRouter key).
- [ ] Logs show `Vector index built: N documents` on backend startup.
