import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import {
  ArrowLeft,
  Download,
  Moon,
  Sun,
  User as UserIcon,
  Loader2,
  Link2,
  ExternalLink,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useAuth } from "@/contexts/AuthContext";
import { useChatHistory } from "@/contexts/ChatHistoryContext";
import { useToast } from "@/components/Toast";
import { useTheme } from "@/lib/theme";
import {
  deleteAllChats,
  exportData,
  getLeetCodeStatus,
  linkLeetCode,
  unlinkLeetCode,
} from "@/lib/api";

const containerVariants = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: {
      staggerChildren: 0.1,
    },
  },
};

const itemVariants = {
  hidden: { opacity: 0, y: 15 },
  show: { opacity: 1, y: 0, transition: { type: "spring" as const, stiffness: 100 } },
};

const Settings = () => {
  const { user } = useAuth();
  const { refresh } = useChatHistory();
  const { toast } = useToast();
  const { isDark, toggleTheme } = useTheme();
  const navigate = useNavigate();
  const [exporting, setExporting] = useState(false);
  const [deleting, setDeleting] = useState(false);

  // ── LeetCode account linking ────────────────────────────────
  const [accountInput, setAccountInput] = useState("");
  const [linkedUsername, setLinkedUsername] = useState<string | null>(null);
  const [lcLoading, setLcLoading] = useState(true);
  const [linking, setLinking] = useState(false);
  const [unlinking, setUnlinking] = useState(false);

  const loadStatus = useCallback(async () => {
    setLcLoading(true);
    try {
      const status = await getLeetCodeStatus(user);
      setLinkedUsername(status.enabled ? status.username : null);
    } catch {
      setLinkedUsername(null);
    } finally {
      setLcLoading(false);
    }
  }, [user]);

  const handleLink = async () => {
    const value = accountInput.trim();
    if (!value) {
      toast("Enter your LeetCode profile link or username first", "error");
      return;
    }
    setLinking(true);
    try {
      const result = await linkLeetCode(user, value);
      if (result.success) {
        setLinkedUsername(result.username);
        setAccountInput("");
        toast(result.message, "success");
      } else {
        toast(result.message, "error");
      }
    } catch {
      toast("Could not reach the server. Try again.", "error");
    } finally {
      setLinking(false);
    }
  };

  const handleUnlink = async () => {
    setUnlinking(true);
    try {
      await unlinkLeetCode(user);
      setLinkedUsername(null);
      toast("LeetCode account unlinked", "success");
    } catch {
      toast("Could not unlink your LeetCode account", "error");
    } finally {
      setUnlinking(false);
    }
  };

  useEffect(() => {
    void loadStatus();
  }, [loadStatus]);

  const handleExport = async () => {
    setExporting(true);
    try {
      const data = await exportData(user);
      const blob = new Blob([JSON.stringify(data, null, 2)], {
        type: "application/json",
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "dsa-mentor-export.json";
      a.click();
      URL.revokeObjectURL(url);
      toast("Data exported successfully", "success");
    } catch {
      toast("Could not export your data", "error");
    } finally {
      setExporting(false);
    }
  };

  const handleDeleteAll = async () => {
    if (!window.confirm("Delete ALL of your conversations? This cannot be undone.")) return;
    setDeleting(true);
    try {
      const count = await deleteAllChats(user);
      await refresh();
      toast(`${count} conversation${count === 1 ? "" : "s"} deleted`, "success");
      navigate("/chat");
    } catch {
      toast("Could not delete your chats", "error");
      setDeleting(false);
    }
  };

  return (
    <div className="h-full overflow-y-auto">
      <motion.div 
        variants={containerVariants}
        initial="hidden"
        animate="show"
        className="max-w-2xl mx-auto px-4 py-8 space-y-6"
      >
        <motion.div variants={itemVariants} className="flex items-center gap-3">
          <Button variant="ghost" size="icon" onClick={() => navigate("/chat")} aria-label="Back">
            <ArrowLeft className="h-5 w-5" />
          </Button>
          <h1 className="text-2xl font-bold">Settings</h1>
        </motion.div>

        <motion.section variants={itemVariants} className="glass-card border border-border/50 rounded-xl p-5 flex items-center gap-4">
          {user?.photoURL ? (
            <img src={user.photoURL} alt="Avatar" className="w-12 h-12 rounded-full border border-border/50" />
          ) : (
            <div className="w-12 h-12 rounded-full bg-primary/10 border border-primary/20 flex items-center justify-center">
              <UserIcon className="h-5 w-5 text-primary" />
            </div>
          )}
          <div className="min-w-0">
            <p className="font-semibold text-lg truncate">{user?.displayName || "User"}</p>
            <p className="text-sm text-muted-foreground truncate">{user?.email}</p>
          </div>
        </motion.section>

        <motion.section variants={itemVariants} className="glass-card border border-border/50 rounded-xl p-5">
          <h2 className="text-xs font-semibold text-muted-foreground/60 uppercase tracking-wider mb-4">
            Appearance
          </h2>
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium">Dark mode</span>
            <Button variant="outline" size="sm" onClick={toggleTheme} className="rounded-xl border-border/60">
              {isDark ? <Sun className="h-4 w-4 mr-2" /> : <Moon className="h-4 w-4 mr-2" />}
              {isDark ? "Switch to Light" : "Switch to Dark"}
            </Button>
          </div>
        </motion.section>

        <motion.section variants={itemVariants} className="glass-card border border-border/50 rounded-xl p-5">
          <h2 className="text-xs font-semibold text-muted-foreground/60 uppercase tracking-wider mb-4">
            LeetCode Account
          </h2>

          {lcLoading ? (
            <div className="flex items-center gap-2 text-sm text-muted-foreground py-2">
              <Loader2 className="h-4 w-4 animate-spin text-primary" />
              Checking account status…
            </div>
          ) : linkedUsername ? (
            <div className="space-y-4">
              <div className="flex items-center justify-between gap-3">
                <div className="min-w-0">
                  <p className="text-sm font-semibold">
                    Linked as <span className="text-primary font-bold">@{linkedUsername}</span>
                  </p>
                  <p className="text-xs text-muted-foreground mt-1">
                    Your solved problems and recommendations are available.
                  </p>
                </div>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => navigate("/progress")}
                  className="rounded-xl border-border/60 shrink-0"
                >
                  <ExternalLink className="h-4 w-4 mr-2" />
                  View progress
                </Button>
              </div>
              <hr className="border-border/30" />
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium text-red-400">Unlink LeetCode account</span>
                <Button
                  variant="destructive"
                  size="sm"
                  onClick={handleUnlink}
                  disabled={unlinking}
                  className="rounded-xl"
                >
                  {unlinking && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
                  Unlink
                </Button>
              </div>
            </div>
          ) : (
            <div className="space-y-4">
              <p className="text-sm text-muted-foreground leading-relaxed">
                Paste your public LeetCode profile link (or username) so the AI
                can analyse your solved problems and recommend what to practise next.
              </p>
              <div className="flex gap-2">
                <Input
                  type="text"
                  value={accountInput}
                  onChange={(e) => setAccountInput(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && handleLink()}
                  placeholder="https://leetcode.com/u/your-username"
                  className="flex-1 rounded-xl glass-input h-11"
                  maxLength={128}
                />
                <Button onClick={handleLink} disabled={linking} className="btn-gradient rounded-xl h-11 px-5">
                  {linking ? (
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  ) : (
                    <Link2 className="h-4 w-4 mr-2" />
                  )}
                  Link Account
                </Button>
              </div>
            </div>
          )}
        </motion.section>

        <motion.section variants={itemVariants} className="glass-card border border-border/50 rounded-xl p-5">
          <h2 className="text-xs font-semibold text-muted-foreground/60 uppercase tracking-wider mb-4">
            Your Data
          </h2>
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium">Download your data</span>
              <Button variant="outline" size="sm" onClick={handleExport} disabled={exporting} className="rounded-xl border-border/60">
                {exporting ? (
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                ) : (
                  <Download className="h-4 w-4 mr-2" />
                )}
                Export JSON
              </Button>
            </div>
            <hr className="border-border/30" />
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium text-red-400">Delete all conversations</span>
              <Button variant="destructive" size="sm" onClick={handleDeleteAll} disabled={deleting} className="rounded-xl">
                {deleting && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
                Delete All
              </Button>
            </div>
          </div>
        </motion.section>
      </motion.div>
    </div>
  );
};

export default Settings;
