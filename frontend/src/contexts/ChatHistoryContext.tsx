/* oxlint-disable react/only-export-components */
import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
} from "react";
import { useAuth } from "@/contexts/AuthContext";
import {
  listConversations,
  searchConversations,
  renameConversation,
  deleteConversation,
  type ConversationListItem,
} from "@/lib/api";

interface ChatHistoryContextType {
  conversations: ConversationListItem[];
  loading: boolean;
  searchQuery: string;
  setSearchQuery: (query: string) => void;
  refresh: () => Promise<void>;
  rename: (id: string, title: string) => Promise<void>;
  remove: (id: string) => Promise<void>;
}

const ChatHistoryContext = createContext<ChatHistoryContextType>({
  conversations: [],
  loading: true,
  searchQuery: "",
  setSearchQuery: () => {},
  refresh: async () => {},
  rename: async () => {},
  remove: async () => {},
});

export const useChatHistory = () => useContext(ChatHistoryContext);

export const ChatHistoryProvider = ({ children }: { children: React.ReactNode }) => {
  const { user } = useAuth();
  const [conversations, setConversations] = useState<ConversationListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");

  const fetchItems = useCallback(
    async (query: string): Promise<ConversationListItem[]> => {
      if (!user) return [];
      const q = query.trim();
      return q ? searchConversations(user, q) : listConversations(user);
    },
    [user],
  );

  useEffect(() => {
    if (!user) {
      setConversations([]);
      setLoading(false);
      return;
    }
    setLoading(true);
    const timer = window.setTimeout(async () => {
      try {
        setConversations(await fetchItems(searchQuery));
      } catch (err) {
        console.error("Failed to load chat history", err);
      } finally {
        setLoading(false);
      }
    }, searchQuery.trim() ? 300 : 0);
    return () => window.clearTimeout(timer);
  }, [user, searchQuery, fetchItems]);

  const refresh = useCallback(async () => {
    try {
      setConversations(await fetchItems(searchQuery));
    } catch (err) {
      console.error("Failed to refresh chat history", err);
    }
  }, [searchQuery, fetchItems]);

  const rename = useCallback(async (id: string, title: string) => {
    // Optimistic update; revert by refreshing on failure.
    setConversations((prev) =>
      prev.map((c) => (c.id === id ? { ...c, title } : c)),
    );
    try {
      await renameConversation(user, id, title);
    } catch (err) {
      console.error("Failed to rename conversation", err);
      void refresh();
      throw err;
    }
  }, [user, refresh]);

  const remove = useCallback(async (id: string) => {
    setConversations((prev) => prev.filter((c) => c.id !== id));
    try {
      await deleteConversation(user, id);
    } catch (err) {
      console.error("Failed to delete conversation", err);
      void refresh();
      throw err;
    }
  }, [user, refresh]);

  return (
    <ChatHistoryContext.Provider
      value={{ conversations, loading, searchQuery, setSearchQuery, refresh, rename, remove }}
    >
      {children}
    </ChatHistoryContext.Provider>
  );
};
