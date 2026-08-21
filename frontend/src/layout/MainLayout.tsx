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
      <linearGradient id="sidebarHexGrad" x1="0" y1="0" x2="64" y2="64">
        <stop offset="0%" stopColor="#4D82FF"/>
        <stop offset="100%" stopColor="#9EBCFF"/>
      </linearGradient>
    </defs>
    <path d="M32 2 L58 17 L58 47 L32 62 L6 47 L6 17 Z" fill="url(#sidebarHexGrad)" stroke="rgba(255,255,255,0.15)" strokeWidth="1"/>
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
    <motion.div
      whileHover={{ x: 4 }}
      className={`group relative flex items-center gap-3.5 h-11 px-4 rounded-2xl text-sm font-medium cursor-pointer transition-all duration-300 ${
        active 
          ? "bg-blue-500/10 text-white border border-blue-500/20 shadow-[0_0_20px_rgba(77,130,255,0.1)]" 
          : "hover:bg-white/[0.03] text-white/40 hover:text-white border border-transparent"
      }`}
      onClick={() => !editing && onSelect()}
    >
      <MessageSquare className={`h-4 w-4 shrink-0 transition-colors ${active ? "text-blue-400" : "text-white/20 group-hover:text-white/40"}`} />
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
          className="flex-1 min-w-0 bg-white/5 border border-white/10 rounded-xl px-2 py-1 text-sm text-white focus:outline-none focus:ring-1 focus:ring-blue-500"
          onClick={(e) => e.stopPropagation()}
        />
      ) : (
        <span className="truncate flex-1 text-left">{item.title}</span>
      )}

      {!editing && (
        <button
          className="opacity-0 group-hover:opacity-100 p-1 rounded-lg hover:bg-white/10 text-white/20 hover:text-white shrink-0 transition-all"
          onClick={(e) => {
            e.stopPropagation();
            setMenuOpen((v) => !v);
          }}
        >
          <MoreHorizontal className="h-4 w-4" />
        </button>
      )}

      {menuOpen && !editing && (
        <>
          <div className="fixed inset-0 z-10" onClick={() => setMenuOpen(false)} />
          <div className="absolute right-2 top-full mt-2 z-20 w-40 glass-card border border-white/10 rounded-2xl shadow-2xl py-2">
            <button
              className="w-full flex items-center gap-2.5 px-4 py-2.5 text-xs font-bold text-white/60 hover:text-white hover:bg-white/5"
              onClick={(e) => {
                e.stopPropagation();
                setEditing(true);
              }}
            >
              <Pencil className="h-3.5 w-3.5" /> RENAME
            </button>
            <button
              className="w-full flex items-center gap-2.5 px-4 py-2.5 text-xs font-bold text-red-400 hover:text-red-300 hover:bg-red-500/10"
              onClick={(e) => {
                e.stopPropagation();
                setMenuOpen(false);
                onDelete();
              }}
            >
              <Trash2 className="h-3.5 w-3.5" /> DELETE
            </button>
          </div>
        </>
      )}
    </motion.div>
  );
};

const SkeletonRow = () => (
  <div className="h-11 px-4 flex items-center gap-4 animate-pulse bg-white/[0.02] rounded-2xl mb-1">
    <div className="h-4 w-4 rounded bg-white/5" />
    <div className="h-3 flex-1 rounded bg-white/5" />
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
    <div className="h-full flex flex-col glass-sidebar bg-[#05070D]/80">
      {/* Brand Header */}
      <div className="p-7 flex items-center justify-between">
        <Link to="/" className="flex items-center gap-3 group transition-all">
          <HexLogo size={34} />
          <div className="flex flex-col">
            <span className="font-bold text-lg tracking-tight text-white group-hover:text-blue-400 transition-colors">LeetCode AI</span>
            <span className="text-[10px] font-bold tracking-[0.2em] text-white/20 uppercase">Core Workspace</span>
          </div>
        </Link>
        <Button variant="ghost" size="icon" className="md:hidden text-white/40 hover:text-white" onClick={() => setIsSidebarOpen(false)}>
          <X className="h-5 w-5" />
        </Button>
      </div>

      {/* New Chat Button */}
      <div className="px-5 py-2">
        <Button
          onClick={handleNewChat}
          className="w-full h-13 btn-gradient rounded-[1.25rem] font-bold text-sm flex items-center justify-center gap-3 shadow-[0_8px_30px_rgba(77,130,255,0.2)]"
        >
          <Plus className="h-5 w-5" />
          NEW SESSION
        </Button>
      </div>

      {/* Navigation Links */}
      <div className="px-5 py-6 space-y-2">
        <button
          onClick={handleNewChat}
          className="w-full flex items-center gap-4 px-4 py-3.5 rounded-2xl text-sm font-bold text-white/40 hover:text-white hover:bg-white/[0.04] transition-all"
        >
          <MessageSquare className="h-5 w-5" />
          CHATS
        </button>
        <button
          onClick={() => {
            setIsSidebarOpen(false);
            navigate("/progress");
          }}
          className="w-full flex items-center gap-4 px-4 py-3.5 rounded-2xl text-sm font-bold text-white/40 hover:text-white hover:bg-white/[0.04] transition-all"
        >
          <BarChart3 className="h-5 w-5" />
          PROGRESS
        </button>
        <button
          onClick={() => {
            setIsSidebarOpen(false);
            navigate("/settings");
          }}
          className="w-full flex items-center gap-4 px-4 py-3.5 rounded-2xl text-sm font-bold text-white/40 hover:text-white hover:bg-white/[0.04] transition-all"
        >
          <SettingsIcon className="h-5 w-5" />
          SETTINGS
        </button>
        <button
          onClick={handleLogout}
          className="w-full flex items-center gap-4 px-4 py-3.5 rounded-2xl text-sm font-bold text-red-400/60 hover:text-red-400 hover:bg-red-500/10 transition-all"
        >
          <LogOut className="h-5 w-5" />
          LOGOUT
        </button>
      </div>

      <div className="px-6 mb-4">
        <div className="h-[1px] w-full bg-white/5" />
      </div>

      {/* Search chats */}
      <div className="px-5 py-2 relative group">
        <Search className="absolute left-9 top-1/2 -translate-y-1/2 h-4 w-4 text-white/20 group-focus-within:text-blue-400 transition-colors" />
        <input
          type="text"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          placeholder="SEARCH HISTORY..."
          className="w-full h-12 bg-white/[0.02] border border-white/5 rounded-2xl pl-12 pr-4 text-[10px] font-bold tracking-widest text-white placeholder:text-white/10 focus:outline-none focus:border-blue-500/30 transition-all"
        />
      </div>

      {/* Recent Chats Section */}
      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-6">
        <div>
          <h4 className="text-[10px] font-bold text-white/20 px-4 mb-4 uppercase tracking-[0.25em]">
            History Feed
          </h4>
          <div className="space-y-1">
            {loading && conversations.length === 0 ? (
              <div className="space-y-1">
                <SkeletonRow />
                <SkeletonRow />
                <SkeletonRow />
              </div>
            ) : isSearching ? (
              conversations.length === 0 ? (
                <p className="text-[10px] font-bold text-white/20 text-center py-8 tracking-widest">
                  NO MATCHES FOUND
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
              <p className="text-[10px] font-bold text-white/20 text-center py-8 tracking-widest">
                NO HISTORY YET
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
      <div className="p-4 border-t border-white/5 bg-white/[0.01]">
        <motion.div 
          whileHover={{ x: 2 }}
          className="flex items-center gap-4 p-3 rounded-2xl hover:bg-white/[0.03] cursor-pointer transition-all border border-transparent hover:border-white/5" 
          onClick={() => navigate("/settings")}
        >
          {user?.photoURL ? (
            <img src={user.photoURL} alt="Avatar" className="w-10 h-10 rounded-full border border-white/10 shadow-lg" />
          ) : (
            <div className="w-10 h-10 rounded-full bg-blue-500/10 border border-blue-500/20 flex items-center justify-center">
              <UserIcon className="h-5 w-5 text-blue-400" />
            </div>
          )}
          <div className="flex-1 min-w-0">
            <p className="text-sm font-bold truncate text-white">{user?.displayName || "Developer"}</p>
            <p className="text-[10px] font-bold text-white/20 truncate tracking-tight">{user?.email}</p>
          </div>
        </motion.div>
      </div>
    </div>
  );

  return (
    <div className="flex h-screen bg-[#05070D] text-white overflow-hidden">
      {/* Mobile Drawer Overlay */}
      <AnimatePresence>
        {isSidebarOpen && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-[#05070D]/80 backdrop-blur-md z-40 md:hidden"
            onClick={() => setIsSidebarOpen(false)}
          />
        )}
      </AnimatePresence>

      {/* Sidebar - Desktop and Mobile Wrapper */}
      <aside className="hidden md:block w-[300px] h-full shrink-0">
        {sidebarContent}
      </aside>

      <AnimatePresence>
        {isSidebarOpen && (
          <motion.aside
            initial={{ x: "-100%" }}
            animate={{ x: 0 }}
            exit={{ x: "-100%" }}
            transition={{ type: "spring", damping: 30, stiffness: 300 }}
            className="fixed inset-y-0 left-0 z-50 w-[300px] h-full md:hidden"
          >
            {sidebarContent}
          </motion.aside>
        )}
      </AnimatePresence>

      {/* Main Content Area */}
      <div className="flex flex-col flex-1 min-w-0 relative">
        {/* Background glow for content */}
        <div className="absolute top-0 right-0 w-[600px] h-[600px] bg-blue-500/5 rounded-full blur-[150px] pointer-events-none" />

        <header className="h-16 glass bg-transparent border-b border-white/5 flex items-center justify-between px-6 z-30">
          <div className="flex items-center gap-4">
            <Button variant="ghost" size="icon" className="md:hidden text-white/40 hover:text-white" onClick={() => setIsSidebarOpen(true)}>
              <Menu className="h-5 w-5" />
            </Button>
            <div className="flex flex-col">
              <span className="text-xs font-bold tracking-[0.2em] text-blue-400 uppercase">
                {activeConvId ? "ACTIVE SESSION" : "NEW NEURAL LINK"}
              </span>
              <span className="text-[10px] font-bold text-white/20 tracking-widest uppercase">
                {activeConvId ? `ID: ${activeConvId.slice(0, 8)}` : "READY FOR INPUT"}
              </span>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <Button variant="ghost" size="icon" onClick={toggleTheme} className="text-white/20 hover:text-white hover:bg-white/5 rounded-xl transition-all">
              {isDark ? <Sun className="h-5 w-5" /> : <Moon className="h-5 w-5" />}
            </Button>
          </div>
        </header>

        <main className="flex-1 overflow-hidden relative">
          {children}
        </main>
      </div>
    </div>
  );
};


export default MainLayout;
