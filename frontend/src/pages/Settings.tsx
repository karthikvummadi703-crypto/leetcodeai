import { useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  ArrowLeft,
  Download,
  Moon,
  Sun,
  User as UserIcon,
  Loader2,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/contexts/AuthContext";
import { useChatHistory } from "@/contexts/ChatHistoryContext";
import { useToast } from "@/components/Toast";
import { useTheme } from "@/lib/theme";
import { deleteAllChats, exportData } from "@/lib/api";

const Settings = () => {
  const { user } = useAuth();
  const { refresh } = useChatHistory();
  const { toast } = useToast();
  const { isDark, toggleTheme } = useTheme();
  const navigate = useNavigate();
  const [exporting, setExporting] = useState(false);
  const [deleting, setDeleting] = useState(false);

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
      <div className="max-w-2xl mx-auto px-4 py-8 space-y-6">
        <div className="flex items-center gap-3">
          <Button variant="ghost" size="icon" onClick={() => navigate("/chat")} aria-label="Back">
            <ArrowLeft className="h-5 w-5" />
          </Button>
          <h1 className="text-2xl font-bold">Settings</h1>
        </div>

        <section className="glass-card border border-border/50 rounded-xl p-4 flex items-center gap-4">
          {user?.photoURL ? (
            <img src={user.photoURL} alt="Avatar" className="w-12 h-12 rounded-full" />
          ) : (
            <div className="w-12 h-12 rounded-full bg-primary/10 border border-primary/20 flex items-center justify-center">
              <UserIcon className="h-5 w-5 text-primary" />
            </div>
          )}
          <div className="min-w-0">
            <p className="font-medium truncate">{user?.displayName || "User"}</p>
            <p className="text-sm text-muted-foreground truncate">{user?.email}</p>
          </div>
        </section>

        <section className="glass-card border border-border/50 rounded-xl p-4">
          <h2 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider mb-3">
            Appearance
          </h2>
          <div className="flex items-center justify-between">
            <span className="text-sm">Dark mode</span>
            <Button variant="outline" size="sm" onClick={toggleTheme}>
              {isDark ? <Sun className="h-4 w-4 mr-2" /> : <Moon className="h-4 w-4 mr-2" />}
              {isDark ? "Switch to Light" : "Switch to Dark"}
            </Button>
          </div>
        </section>

        <section className="glass-card border border-border/50 rounded-xl p-4">
          <h2 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider mb-3">
            Your Data
          </h2>
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-sm">Download your data</span>
              <Button variant="outline" size="sm" onClick={handleExport} disabled={exporting}>
                {exporting ? (
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                ) : (
                  <Download className="h-4 w-4 mr-2" />
                )}
                Export JSON
              </Button>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-red-400">Delete all conversations</span>
              <Button variant="destructive" size="sm" onClick={handleDeleteAll} disabled={deleting}>
                {deleting && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
                Delete all
              </Button>
            </div>
          </div>
        </section>
      </div>
    </div>
  );
};

export default Settings;
