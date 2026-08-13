import React, { useEffect, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { useAuth } from "@/contexts/AuthContext";
import { useChatHistory } from "@/contexts/ChatHistoryContext";
import { useToast } from "@/components/Toast";
import { useTheme } from "@/lib/theme";
import { syncProfile } from "@/lib/api";
import type { ConversationListItem } from "@/lib/api";
import { motion, AnimatePresence } from "framer-motion";
import {
  MessageSquare,
  Plus,
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
  Settings as SettingsIcon,
  BarChart3,
} from "lucide-react";
import { Button } from "@/components/ui/button";

const HexLogo = ({ size = 28 }: { size?: number }) => (
  <svg width={size} height={size} viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
    <defs>
      <linearGradient id="hexLogoSidebar" x1="0" y1="0" x2="64" y2="64">
        <stop offset="0%" stopColor="#7c3aed"/>
        <stop offset="100%" stopColor="#3b82f6"/>
      </linearGradient>
    </defs>
    <path d="M32 2 L58 17 L58 47 L32 62 L6 47 L6 17 Z" fill="url(#hexLogoSidebar)" stroke="rgba(255,255,255,0.15)" strokeWidth="1"/>
    <text x="32" y="42" textAnchor="middle" fontFamily="monospace" fontWeight="bold" fontSize="24" fill="white">&lt;/&gt;</text>
  </svg>
);

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
      className={`group relative flex items-center gap-3.5 h-10 px-3 rounded-xl text-sm font-medium cursor-pointer transition-all duration-200 ${
        active 
          ? "bg-primary/20 text-foreground border border-primary/30" 
          : "hover:bg-accent/40 text-muted-foreground hover:text-foreground border border-transparent"
      }`}
      onClick={() => !editing && onSelect()}
    >
      <MessageSquare className={`h-4 w-4 shrink-0 ${active ? "text-primary" : "text-muted-foreground group-hover:text-foreground"}`} />
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
          className="flex-1 min-w-0 bg-background/80 border border-border/60 rounded-lg px-2 py-0.5 text-sm focus:outline-none focus:ring-1 focus:ring-primary"
          onClick={(e) => e.stopPropagation()}
        />
      ) : (
        <span className="truncate flex-1 text-left">{item.title}</span>
      )}

      {!editing && (
        <button
          className="opacity-0 group-hover:opacity-100 p-1 rounded hover:bg-background/60 text-muted-foreground hover:text-foreground shrink-0 transition-opacity"
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
          <div className="absolute right-2 top-full mt-1 z-20 w-36 glass-card border border-border/50 rounded-xl shadow-lg py-1">
            <button
              className="w-full flex items-center gap-2 px-3 py-2 text-sm hover:bg-accent rounded-lg"
              onClick={(e) => {
                e.stopPropagation();
                setEditing(true);
              }}
            >
              <Pencil className="h-3.5 w-3.5" /> Rename
            </button>
            <button
              className="w-full flex items-center gap-2 px-3 py-2 text-sm text-red-400 hover:bg-red-500/10 rounded-lg"
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
  <div className="h-10 px-3 flex items-center gap-3 animate-pulse">
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

  const isSearching = searchQuery.trim().length > 0;

  const sidebarContent = (
    <div className="h-full flex flex-col glass-sidebar">
      {/* Brand Header */}
      <div className="p-5 flex items-center justify-between">
        <Link to="/" className="flex items-center gap-3 hover:opacity-85 transition-opacity">
          <HexLogo size={32} />
          <span className="font-bold text-lg tracking-tight text-foreground">LeetCode AI</span>
        </Link>
        <Button variant="ghost" size="icon" className="md:hidden text-muted-foreground hover:text-foreground" onClick={() => setIsSidebarOpen(false)}>
          <X className="h-5 w-5" />
        </Button>
      </div>

      {/* New Chat Button */}
      <div className="px-4 py-2">
        <Button
          onClick={handleNewChat}
          className="w-full h-11 btn-gradient rounded-xl font-semibold flex items-center justify-center gap-2 shadow-md"
        >
          <Plus className="h-5 w-5" />
          New Chat
        </Button>
      </div>

      {/* Navigation Links */}
      <div className="px-4 py-3 space-y-1">
        <button
          onClick={handleNewChat}
          className="w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium text-muted-foreground hover:text-foreground hover:bg-accent/40 transition-colors"
        >
          <MessageSquare className="h-4.5 w-4.5 text-muted-foreground" />
          Chats
        </button>
        <button
          onClick={() => {
            setIsSidebarOpen(false);
            navigate("/progress");
          }}
          className="w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium text-muted-foreground hover:text-foreground hover:bg-accent/40 transition-colors"
        >
          <BarChart3 className="h-4.5 w-4.5 text-muted-foreground" />
          Progress
        </button>
        <button
          onClick={() => {
            setIsSidebarOpen(false);
            navigate("/settings");
          }}
          className="w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium text-muted-foreground hover:text-foreground hover:bg-accent/40 transition-colors"
        >
          <SettingsIcon className="h-4.5 w-4.5 text-muted-foreground" />
          Settings
        </button>
        <button
          onClick={handleLogout}
          className="w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium text-red-400 hover:text-red-300 hover:bg-red-500/10 transition-colors"
        >
          <LogOut className="h-4.5 w-4.5" />
          Logout
        </button>
      </div>

      <hr className="border-border/30 mx-4 my-2" />

      {/* Search chats */}
      <div className="px-4 py-2 relative">
        <Search className="absolute left-7 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
        <input
          type="text"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          placeholder="Search chats..."
          className="w-full h-10 bg-background/40 border border-border/30 rounded-xl pl-10 pr-3 text-sm focus:outline-none focus:border-primary/50 transition-colors"
        />
      </div>

      {/* Recent Chats Section */}
      <div className="flex-1 overflow-y-auto px-3 py-2 space-y-4">
        <div>
          <h4 className="text-xs font-semibold text-muted-foreground/60 px-3 mb-2 uppercase tracking-wider">
            Recent Chats
          </h4>
          <div className="space-y-1">
            {loading && conversations.length === 0 ? (
              <div className="space-y-1">
                <SkeletonRow />
                <SkeletonRow />
              </div>
            ) : isSearching ? (
              conversations.length === 0 ? (
                <p className="text-xs text-muted-foreground text-center py-4">
                  No matches found
                </p>
              ) : (
                conversations.map((item) => (
                  <ConversationRow
                    key={item.id}
                    item={item}
                    active={item.id === activeConvId}
                    onSelect={() => handleSelect(item.id)}
                    onRename={(title) => handleRename(item.id, title)}
                    onDelete={() => handleDelete(item.id)}
                  />
                ))
              )
            ) : conversations.length === 0 ? (
              <p className="text-xs text-muted-foreground text-center py-4">
                No chats yet
              </p>
            ) : (
              conversations.map((item) => (
                <ConversationRow
                  key={item.id}
                  item={item}
                  active={item.id === activeConvId}
                  onSelect={() => handleSelect(item.id)}
                  onRename={(title) => handleRename(item.id, title)}
                  onDelete={() => handleDelete(item.id)}
                />
              ))
            )}
          </div>
        </div>
      </div>

      {/* User profile bottom */}
      <div className="p-3 border-t border-border/30 bg-background/20">
        <div className="flex items-center gap-3 p-2 rounded-xl hover:bg-accent/40 cursor-pointer transition-colors" onClick={() => navigate("/settings")}>
          {user?.photoURL ? (
            <img src={user.photoURL} alt="Avatar" className="w-9 h-9 rounded-full border border-border/50" />
          ) : (
            <div className="w-9 h-9 rounded-full bg-primary/10 border border-primary/20 flex items-center justify-center">
              <UserIcon className="h-4.5 w-4.5 text-primary" />
            </div>
          )}
          <div className="flex-1 min-w-0">
            <p className="text-sm font-semibold truncate text-foreground">{user?.displayName || "User"}</p>
            <p className="text-xs text-muted-foreground truncate">{user?.email}</p>
          </div>
        </div>
      </div>
    </div>
  );

  return (
    <div className="flex h-screen bg-background text-foreground overflow-hidden">
      {/* Mobile Drawer Overlay */}
      <AnimatePresence>
        {isSidebarOpen && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-background/80 backdrop-blur-sm z-40 md:hidden"
            onClick={() => setIsSidebarOpen(false)}
          />
        )}
      </AnimatePresence>

      {/* Sidebar - Desktop and Mobile Wrapper */}
      <aside className="hidden md:block w-72 h-full shrink-0">
        {sidebarContent}
      </aside>

      <AnimatePresence>
        {isSidebarOpen && (
          <motion.aside
            initial={{ x: "-100%" }}
            animate={{ x: 0 }}
            exit={{ x: "-100%" }}
            transition={{ type: "spring", damping: 25, stiffness: 200 }}
            className="fixed inset-y-0 left-0 z-50 w-72 h-full md:hidden"
          >
            {sidebarContent}
          </motion.aside>
        )}
      </AnimatePresence>

      {/* Main Content Area */}
      <div className="flex flex-col flex-1 min-w-0">
        <header className="h-14 glass border-b border-border/30 flex items-center justify-between px-4 z-30">
          <div className="flex items-center gap-2">
            <Button variant="ghost" size="icon" className="md:hidden text-muted-foreground hover:text-foreground" onClick={() => setIsSidebarOpen(true)}>
              <Menu className="h-5 w-5" />
            </Button>
            <span className="font-semibold text-sm text-foreground">
              {activeConvId ? "Chat Room" : "New Chat"}
            </span>
          </div>

          <div className="flex items-center gap-2">
            <Button variant="ghost" size="icon" onClick={toggleTheme} className="text-muted-foreground hover:text-foreground">
              {isDark ? <Sun className="h-5 w-5" /> : <Moon className="h-5 w-5" />}
            </Button>
          </div>
        </header>

        <main className="flex-1 overflow-hidden relative bg-background/40">
          {children}
        </main>
      </div>
    </div>
  );
};

export default MainLayout;
