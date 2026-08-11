# API Reference

Base URL: `http://localhost:8000/api` (dev) — set the real URL via
`VITE_API_BASE_URL` on the frontend.

All endpoints except `/health` require a Firebase ID token sent as:

```
Authorization: Bearer <id_token>
```

Responses are JSON with a `success` boolean. Errors return a non-2xx status
with `{"success": false, "error": "<message>"}`.

---

## Health

### `GET /health`

Public. Returns service status.

```json
{ "success": true, "status": "healthy", "environment": "development", "version": "0.1.0" }
```

---

## Chat

### `POST /chat`

Send a message. With `stream: true` (default) the response is
`text/event-stream`; otherwise a single JSON response.

**Body**

```json
{
  "conversation_id": "uuid",
  "message": "Explain Two Sum",
  "stream": true
}
```

**SSE response (stream)**

```
data: {"chunk":"Here's the key insight"}\n\n
data: {"chunk":" to Two Sum…"}\n\n
data: [DONE]\n\n
```

**JSON response (stream: false)**

```json
{
  "success": true,
  "conversation_id": "uuid",
  "message": { "id": "msg-id", "role": "assistant", "content": "…", "timestamp": "…" }
}
```

- `message` is capped at 10,000 characters (422 otherwise).
- Requires the conversation to exist and belong to the current user.

### `POST /new-chat`

Create an empty conversation.

```json
// body
{ "title": "New Chat" }
```

```json
// response
{ "success": true, "conversation_id": "uuid", "title": "New Chat" }
```

### `GET /chat-history`

List the current user's conversations (newest first).

```json
{
  "success": true,
  "conversations": [{ "id": "uuid", "title": "Two Sum", "updated_at": "…" }]
}
```

### `GET /chat/search?q=<query>`

Search conversations by title or message content.

```json
{ "success": true, "query": "two sum", "conversations": [/* same shape */] }
```

### `GET /chat/{conversation_id}`

Load a full conversation including all messages.

```json
{
  "success": true,
  "conversation": {
    "id": "uuid",
    "user_id": "uid",
    "title": "Two Sum",
    "messages": [
      { "id": "m1", "role": "user", "content": "Explain Two Sum", "timestamp": "…" }
    ],
    "created_at": "…",
    "updated_at": "…"
  }
}
```

### `POST /chat/{conversation_id}/regenerate`

Remove the last user message and its assistant response so the question can
be re-asked without duplicating history.

```json
{ "success": true, "message_count": 2 }
```

### `PATCH /chat/{conversation_id}`

Rename a conversation.

```json
// body
{ "title": "Renamed" }

// response
{ "success": true, "conversation_id": "uuid", "title": "Renamed" }
```

### `DELETE /chat/{conversation_id}`

Delete a conversation.

```json
{ "success": true, "deleted_id": "uuid" }
```

---

## User & profile

### `GET /profile`

Return the authenticated user's profile (from their ID token).

```json
{ "success": true, "user": { "uid": "…", "email": "…", "display_name": "…", "photo_url": "…" } }
```

### `POST /profile/sync`

Persist the profile and refresh the last-login timestamp.

```json
{ "success": true, "user": { /* same shape */ } }
```

### `DELETE /profile/chats`

Permanently delete every conversation belonging to the user.

```json
{ "success": true, "deleted_count": 4 }
```

### `GET /profile/export`

Export all of the user's data (profile + conversations) as JSON — used by
the Settings page "Download my data" button.

```json
{
  "success": true,
  "exported_at": "…",
  "user": { "uid": "…", "email": "…", "display_name": "…", "photo_url": "…" },
  "conversations": [
    { "id": "uuid", "title": "…", "created_at": "…", "updated_at": "…", "messages": [] }
  ]
}
```

### `POST /feedback`

Persist feedback on an AI response.

```json
// body
{ "conversation_id": "uuid", "message_id": "m1", "rating": 5, "comment": "Great" }
```

```json
// response
{ "success": true, "message": "Feedback received. Thank you!" }
```

`rating` must be an integer 1–5; `comment` is optional (max 2000 chars).

---

## LeetCode account

All LeetCode endpoints require authentication (Firebase ID token). The
backend reads the user's **public** LeetCode profile via LeetCode's GraphQL
API — no LeetCode credentials are stored.

### `GET /leetcode/status`

Return whether the user has linked a LeetCode account.

```json
{ "success": true, "enabled": true, "username": "neetode" }
```

### `POST /leetcode/link`

Validate a LeetCode username and persist the link for this user.

```json
// body
{ "username": "neetode" }
```

```json
// success
{ "success": true, "username": "neetode", "message": "Linked neetode. …" }
```

Returns `success: false` with a friendly `message` when the username does
not exist or LeetCode is unreachable.

### `DELETE /leetcode/link`

Unlink the LeetCode account.

```json
{ "success": true, "enabled": false, "username": null }
```

### `GET /leetcode/profile`

Fetch the linked account's profile, progress and recent submissions, plus an
AI-oriented analysis of the solved set.

```json
{
  "success": true,
  "linked": true,
  "username": "neetode",
  "profile": {
    "username": "neetode",
    "real_name": "Neet Ode",
    "avatar": "https://…",
    "ranking": 12345,
    "reputation": 567,
    "country": "India",
    "school": null,
    "accepted": { "easy": 120, "medium": 80, "hard": 15, "total": 215 }
  },
  "progress": {
    "accepted": { "easy": 120, "medium": 80, "hard": 15, "total": 215 },
    "failed": { "easy": 5, "medium": 12, "hard": 3, "total": 20 },
    "untouched": { "easy": 300, "medium": 400, "hard": 150, "total": 850 }
  },
  "recent_ac": [
    { "id": "…", "title": "Two Sum", "title_slug": "two-sum", "timestamp": 1730000000 }
  ],
  "languages": [ { "language": "Python3", "problems_solved": 180 } ],
  "contest": {
    "contests_attended": 12,
    "rating": 1620,
    "global_ranking": 35000,
    "top_percentage": 15
  },
  "analysis": {
    "total_solved": 215,
    "by_difficulty": { "Easy": 120, "Medium": 80, "Hard": 15 },
    "topics_touched": ["array", "hash table", "two pointers"],
    "weak_topics": [],
    "recent_count": 20
  },
  "error": null
}
```

When no account is linked the response is
`{ "success": true, "linked": false, "error": "…" }`.

### `GET /leetcode/recommendations?count=5&difficulty=`

Recommend unsolved problems to practise next, based on the user's recent
accepted submissions and the local 4,000+ problem catalog. `count` is
clamped to 1–10; `difficulty` is optional (`Easy` / `Medium` / `Hard`).

```json
{
  "success": true,
  "username": "neetode",
  "message": "",
  "solved_count": 215,
  "by_difficulty": { "easy": 120, "medium": 80, "hard": 15, "total": 215 },
  "recommendations": [
    {
      "number": 973,
      "title": "K Closest Points to Origin",
      "title_slug": "k-closest-points-to-origin",
      "difficulty": "Medium",
      "acceptance": 65.5,
      "paid_only": false,
      "has_solution": true,
      "topics": ["Array", "Math", "Divide and Conquer", "Sorting", "Heap (Priority Queue)"],
      "url": "https://leetcode.com/problems/k-closest-points-to-origin/"
    }
  ]
}
```

---

## Errors

| Status | Meaning                                  |
| ------ | ---------------------------------------- |
| 401    | Missing or invalid Firebase ID token     |
| 403    | Action not permitted                     |
| 404    | Conversation not found (or not yours)    |
| 422    | Request validation failed                |
| 502    | LLM / OpenRouter failure                |
| 500    | Unexpected server error                  |
