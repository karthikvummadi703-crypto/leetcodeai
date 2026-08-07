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

## Errors

| Status | Meaning                                  |
| ------ | ---------------------------------------- |
| 401    | Missing or invalid Firebase ID token     |
| 403    | Action not permitted                     |
| 404    | Conversation not found (or not yours)    |
| 422    | Request validation failed                |
| 502    | LLM / OpenRouter failure                |
| 500    | Unexpected server error                  |
