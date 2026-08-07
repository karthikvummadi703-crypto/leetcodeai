import type { User } from "firebase/auth";

/**
 * Minimal typed wrapper around the FastAPI backend.
 */

const API_BASE_URL =
  (import.meta.env.VITE_API_BASE_URL as string | undefined) ??
  "http://localhost:8000/api";

export interface BackendMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: string;
}

export interface ChatMessage extends BackendMessage {
  isStreaming?: boolean;
}

export interface ConversationListItem {
  id: string;
  title: string;
  updated_at: string;
}

export interface Conversation extends ConversationListItem {
  user_id: string;
  messages: BackendMessage[];
  created_at: string;
}

export interface ExportPayload {
  user: {
    uid: string;
    email?: string | null;
    display_name?: string | null;
    photo_url?: string | null;
  };
  conversations: Conversation[];
  exported_at: string;
}

async function getToken(user: User | null): Promise<string | null> {
  if (!user) return null;
  return user.getIdToken();
}

function authHeaders(token: string | null): Record<string, string> {
  return {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
}

async function request<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url, init);
  if (!res.ok) {
    const body = await res.text().catch(() => "");
    throw new Error(`Request failed (${res.status}): ${body}`);
  }
  return (await res.json()) as T;
}

export async function createConversation(
  user: User | null,
  title = "New Chat",
): Promise<string> {
  const token = await getToken(user);
  const data = await request<{ conversation_id: string }>(
    `${API_BASE_URL}/new-chat`,
    {
      method: "POST",
      headers: authHeaders(token),
      body: JSON.stringify({ title }),
    },
  );
  return data.conversation_id;
}

export async function listConversations(
  user: User | null,
): Promise<ConversationListItem[]> {
  const token = await getToken(user);
  const data = await request<{ conversations: ConversationListItem[] }>(
    `${API_BASE_URL}/chat-history`,
    { headers: authHeaders(token) },
  );
  return data.conversations;
}

export async function searchConversations(
  user: User | null,
  query: string,
): Promise<ConversationListItem[]> {
  const token = await getToken(user);
  const data = await request<{ conversations: ConversationListItem[] }>(
    `${API_BASE_URL}/chat/search?q=${encodeURIComponent(query)}`,
    { headers: authHeaders(token) },
  );
  return data.conversations;
}

export async function loadConversation(
  user: User | null,
  conversationId: string,
): Promise<Conversation> {
  const token = await getToken(user);
  const data = await request<{ conversation: Conversation }>(
    `${API_BASE_URL}/chat/${encodeURIComponent(conversationId)}`,
    { headers: authHeaders(token) },
  );
  return data.conversation;
}

export async function renameConversation(
  user: User | null,
  conversationId: string,
  title: string,
): Promise<void> {
  const token = await getToken(user);
  await request(`${API_BASE_URL}/chat/${encodeURIComponent(conversationId)}`, {
    method: "PATCH",
    headers: authHeaders(token),
    body: JSON.stringify({ title }),
  });
}

export async function deleteConversation(
  user: User | null,
  conversationId: string,
): Promise<void> {
  const token = await getToken(user);
  await request(`${API_BASE_URL}/chat/${encodeURIComponent(conversationId)}`, {
    method: "DELETE",
    headers: authHeaders(token),
  });
}

export async function truncateLastTurn(
  user: User | null,
  conversationId: string,
): Promise<void> {
  const token = await getToken(user);
  await request(
    `${API_BASE_URL}/chat/${encodeURIComponent(conversationId)}/regenerate`,
    { method: "POST", headers: authHeaders(token) },
  );
}

export async function syncProfile(user: User | null): Promise<void> {
  const token = await getToken(user);
  await request(`${API_BASE_URL}/profile/sync`, {
    method: "POST",
    headers: authHeaders(token),
  });
}

export async function deleteAllChats(user: User | null): Promise<number> {
  const token = await getToken(user);
  const data = await request<{ deleted_count: number }>(
    `${API_BASE_URL}/profile/chats`,
    { method: "DELETE", headers: authHeaders(token) },
  );
  return data.deleted_count;
}

export async function exportData(user: User | null): Promise<ExportPayload> {
  const token = await getToken(user);
  return request<ExportPayload>(`${API_BASE_URL}/profile/export`, {
    headers: authHeaders(token),
  });
}

/**
 * Streams a chat completion from the backend over SSE.
 *
 * Each SSE event is a JSON-encoded object `{"chunk": "..."}`. `onChunk`
 * receives the raw text for every token; the promise resolves when the
 * stream completes, or rejects on error/abort.
 */
export async function streamChat(
  user: User | null,
  conversationId: string,
  message: string,
  onChunk: (chunk: string) => void,
  signal?: AbortSignal,
): Promise<string> {
  const token = await getToken(user);

  const res = await fetch(`${API_BASE_URL}/chat`, {
    method: "POST",
    headers: authHeaders(token),
    body: JSON.stringify({
      conversation_id: conversationId,
      message,
      stream: true,
    }),
    signal,
  });

  if (!res.ok) {
    const body = await res.text().catch(() => "");
    throw new Error(`Chat request failed (${res.status}): ${body}`);
  }
  if (!res.body) {
    throw new Error("Chat request returned an empty body.");
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let full = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const events = buffer.split("\n\n");
    buffer = events.pop() ?? "";

    for (const event of events) {
      const line = event.trim();
      if (!line.startsWith("data:")) continue;
      const payload = line.slice(5).trim();
      if (payload === "[DONE]") return full;
      try {
        const parsed = JSON.parse(payload) as { chunk?: string };
        if (parsed.chunk) {
          full += parsed.chunk;
          onChunk(parsed.chunk);
        }
      } catch {
        // Ignore malformed frames and keep streaming.
      }
    }
  }

  return full;
}
