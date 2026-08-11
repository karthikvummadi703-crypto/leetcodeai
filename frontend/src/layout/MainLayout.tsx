import React, { useEffect, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { useAuth } from "@/contexts/AuthContext";
import { useChatHistory } from "@/contexts/ChatHistoryContext";
import { useToast } from "@/components/Toast";
import { groupConversations } from "@/lib/history";
import { useTheme } from "@/lib/theme";
import { syncProfile } from "@/lib/api";
import type { ConversationListItem } from "@/lib/api";
import {
  Code2,
  MessageSquare,
  PlusCircle,
  Search,
  MoreHorizontal,
  LogOut,
  User as UserIcon,
  Sun,
  Moon,
  Menu,
  X,
  Pencil,
  Trash2,
  Settings,
  BarChart3,
} from "lucide-react";
import { Button } from "@/components/ui/button";

interface ConversationRowProps {
  item: ConversationListItem;
  active: boolean;
  onSelect: () => void;
  onRename: (title: string) => void;
  onDelete: () => void;
}

const ConversationRow = ({ item, active, onSelect, onRename, onDelete }: ConversationRowProps) => {
  const [menuOpen, setMenuOpen] = useState(false);
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(item.title);

  const commit = () => {
    const title = draft.trim();
    setEditing(false);
    setMenuOpen(false);
    if (title && title !== item.title) onRename(title);
  };

  return (
    <div
      className={`group relative flex items-center gap-2 h-9 px-2 rounded-md text-sm font-normal cursor-pointer transition-colors ${
        active ? "bg-accent text-accent-foreground" : "hover:bg-accent/60 text-foreground"
      }`}
      onClick={() => !editing && onSelect()}
    >
      <MessageSquare className="h-4 w-4 text-muted-foreground shrink-0" />
      {editing ? (
        <input
          autoFocus
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") commit();
            if (e.key === "Escape") {
              setDraft(item.title);
              setEditing(false);
            }
          }}
          onBlur={commit}
          className="flex-1 min-w-0 bg-background border border-border/60 rounded px-1.5 py-0.5 text-sm focus:outline-none focus:ring-1 focus:ring-primary"
          onClick={(e) => e.stopPropagation()}
        />
      ) : (
        <span className="truncate flex-1 text-left">{item.title}</span>
      )}

      {!editing && (
        <button
          className="opacity-0 group-hover:opacity-100 p-1 rounded hover:bg-background/60 text-muted-foreground shrink-0"
          onClick={(e) => {
            e.stopPropagation();
            setMenuOpen((v) => !v);
          }}
          aria-label="Conversation options"
        >
          <MoreHorizontal className="h-4 w-4" />
        </button>
      )}

      {menuOpen && !editing && (
        <>
          <div className="fixed inset-0 z-10" onClick={() => setMenuOpen(false)} />
          <div className="absolute right-0 top-full mt-1 z-20 w-36 glass-card border border-border/50 rounded-md shadow-lg py-1">
            <button
              className="w-full flex items-center gap-2 px-3 py-1.5 text-sm hover:bg-accent"
              onClick={(e) => {
                e.stopPropagation();
                setEditing(true);
              }}
            >
              <Pencil className="h-3.5 w-3.5" /> Rename
            </button>
            <button
              className="w-full flex items-center gap-2 px-3 py-1.5 text-sm text-red-400 hover:bg-red-500/10"
              onClick={(e) => {
                e.stopPropagation();
                setMenuOpen(false);
                onDelete();
              }}
            >
              <Trash2 className="h-3.5 w-3.5" /> Delete
            </button>
          </div>
        </>
      )}
    </div>
  );
};

const SkeletonRow = () => (
  <div className="h-9 px-2 flex items-center gap-2 animate-pulse">
    <div className="h-4 w-4 rounded bg-muted" />
    <div className="h-3 flex-1 rounded bg-muted" />
  </div>
);

const MainLayout = ({ children }: { children: React.ReactNode }) => {
  const { user, signOut } = useAuth();
  const { conversations, loading, searchQuery, setSearchQuery, rename, remove } =
    useChatHistory();
  const { toast } = useToast();
  const { isDark, toggleTheme } = useTheme();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const activeConvId = searchParams.get("conv");

  useEffect(() => {
    if (user) void syncProfile(user);
  }, [user]);

  const handleLogout = async () => {
    await signOut();
    navigate("/login");
  };

  const handleNewChat = () => {
    setIsSidebarOpen(false);
    navigate("/chat");
  };

  const handleSelect = (id: string) => {
    setIsSidebarOpen(false);
    navigate(`/chat?conv=${encodeURIComponent(id)}`);
  };

  const handleRename = async (id: string, title: string) => {
    try {
      await rename(id, title);
      toast("Conversation renamed", "success");
    } catch {
      toast("Could not rename conversation", "error");
    }
  };

  const handleDelete = (id: string) => {
    if (!window.confirm("Delete this conversation permanently?")) return;
    void remove(id)
      .then(() => {
        if (activeConvId === id) navigate("/chat");
        toast("Conversation deleted", "success");
      })
      .catch(() => toast("Could not delete conversation", "error"));
  };

  const groups = groupConversations(conversations);
  const isSearching = searchQuery.trim().length > 0;

  return (
    <div className="flex h-screen bg-background text-foreground overflow-hidden">
      {isSidebarOpen && (
        <div
          className="fixed inset-0 bg-background/80 backdrop-blur-sm z-40 md:hidden"
          onClick={() => setIsSidebarOpen(false)}
        />
      )}

      <aside
        className={`fixed md:static inset-y-0 left-0 z-50 w-64 glass-card border-r border-border/50 flex flex-col transition-transform duration-300 ease-in-out md:translate-x-0 ${isSidebarOpen ? "translate-x-0" : "-translate-x-full"}`}
      >
        <div className="p-4 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-2 text-primary hover:opacity-80 transition-opacity">
            <Code2 className="h-6 w-6" />
            <span className="font-semibold tracking-tight hidden sm:block">DSA Mentor</span>
          </Link>
          <Button variant="ghost" size="icon" className="md:hidden" onClick={() => setIsSidebarOpen(false)}>
            <X className="h-5 w-5" />
          </Button>
        </div>

        <div className="px-4 py-2">
          <Button
            variant="outline"
            className="w-full justify-start gap-2 bg-background/50 border-border/50"
            onClick={handleNewChat}
          >
            <PlusCircle className="h-4 w-4" />
            New Chat
          </Button>
        </div>

        <div className="px-4 py-2">
          <Button
            variant="ghost"
            className="w-full justify-start gap-2"
            onClick={() => {
              setIsSidebarOpen(false);
              navigate("/progress");
            }}
          >
            <BarChart3 className="h-4 w-4" />
            LeetCode Progress
          </Button>
        </div>

        <div className="px-4 py-2 relative">
          <Search className="absolute left-6 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search chats..."
            className="w-full h-9 bg-background/50 border border-border/50 rounded-md pl-9 pr-3 text-sm focus:outline-none focus:ring-1 focus:ring-primary"
          />
        </div>

        <div className="flex-1 overflow-y-auto px-2 py-4 space-y-6">
          {loading && conversations.length === 0 ? (
            <div className="space-y-2 px-2">
              <SkeletonRow />
              <SkeletonRow />
              <SkeletonRow />
            </div>
          ) : isSearching ? (
            conversations.length === 0 ? (
              <p className="text-xs text-muted-foreground text-center px-2 py-6">
                No conversations match "{searchQuery.trim()}"
              </p>
            ) : (
              <div className="space-y-1">
                {conversations.map((item) => (
                  <ConversationRow
                    key={item.id}
                    item={item}
                    active={item.id === activeConvId}
                    onSelect={() => handleSelect(item.id)}
                    onRename={(title) => handleRename(item.id, title)}
                    onDelete={() => handleDelete(item.id)}
                  />
                ))}
              </div>
            )
          ) : conversations.length === 0 ? (
            <p className="text-xs text-muted-foreground text-center px-2 py-6">
              No conversations yet. Start a new chat!
            </p>
          ) : (
            groups.map((group) => (
              <div key={group.key}>
                <h4 className="text-xs font-medium text-muted-foreground px-2 mb-2 uppercase tracking-wider">
                  {group.key}
                </h4>
                <div className="space-y-1">
                  {group.items.map((item) => (
                    <ConversationRow
                      key={item.id}
                      item={item}
                      active={item.id === activeConvId}
                      onSelect={() => handleSelect(item.id)}
                      onRename={(title) => handleRename(item.id, title)}
                      onDelete={() => handleDelete(item.id)}
                    />
                  ))}
                </div>
              </div>
            ))
          )}
        </div>

        <div className="p-2 border-t border-border/50">
          <div className="flex items-center gap-2 p-2 rounded-md hover:bg-accent/60 cursor-pointer" onClick={() => navigate("/settings")}>
            {user?.photoURL ? (
              <img src={user.photoURL} alt="Avatar" className="w-8 h-8 rounded-full" />
            ) : (
              <div className="w-8 h-8 rounded-full bg-primary/10 border border-primary/20 flex items-center justify-center">
                <UserIcon className="h-4 w-4 text-primary" />
              </div>
            )}
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium truncate">{user?.displayName || "User"}</p>
              <p className="text-xs text-muted-foreground truncate">{user?.email}</p>
            </div>
          </div>
          <div className="flex items-center gap-1 mt-1">
            <Button variant="ghost" size="sm" className="flex-1 justify-start gap-2" onClick={() => navigate("/settings")}>
              <Settings className="h-4 w-4" />
              Settings
            </Button>
            <Button variant="ghost" size="icon" onClick={toggleTheme} aria-label="Toggle theme">
              {isDark ? <Sun className="h-4 w-4 text-muted-foreground" /> : <Moon className="h-4 w-4 text-muted-foreground" />}
            </Button>
            <Button variant="ghost" size="icon" onClick={handleLogout} aria-label="Log out">
              <LogOut className="h-4 w-4 text-muted-foreground" />
            </Button>
          </div>
        </div>
      </aside>

      <div className="flex flex-col flex-1 min-w-0">
        <header className="h-14 glass border-b border-border/50 flex items-center justify-between px-4 z-30">
          <div className="flex items-center gap-2">
            <Button variant="ghost" size="icon" className="md:hidden" onClick={() => setIsSidebarOpen(true)}>
              <Menu className="h-5 w-5" />
            </Button>
            <span className="font-medium text-sm md:hidden">Chat</span>
          </div>

          <div className="flex items-center gap-2 ml-auto">
            <Button variant="ghost" size="icon" onClick={toggleTheme} className="md:hidden">
              {isDark ? <Sun className="h-5 w-5 text-muted-foreground" /> : <Moon className="h-5 w-5 text-muted-foreground" />}
            </Button>
          </div>
        </header>

        <main className="flex-1 overflow-hidden relative">{children}</main>
      </div>
    </div>
  );
};

export default MainLayout;
