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

   - **Root directory**: `backend`
   - **Build command**: `pip install -r requirements.txt`
   - **Start command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
     (Railway injects `PORT` automatically).

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

3. Initialize and deploy hosting from the `frontend/` directory:

   ```bash
   cd frontend
   firebase init hosting    # select the project, public dir = dist, SPA = yes
   firebase deploy --only hosting
   ```

   `firebase init hosting` creates a `firebase.json` and `public/`. Use this
   `firebase.json` so it serves the built SPA with a rewrite (client-side
   routes `/chat`, `/settings` must load `index.html`):

   ```json
   {
     "hosting": {
       "public": "dist",
       "ignore": ["firebase.json", "**/.*", "**/node_modules/**"],
       "rewrites": [{ "source": "**", "destination": "/index.html" }]
     }
   }
   ```

   Delete the generated `public/index.html` and keep building into `dist`.

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
- [ ] Monitoring/logs are reachable on the host platform.

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
