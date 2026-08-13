import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import {
  ArrowLeft,
  ExternalLink,
  Loader2,
  Trophy,
  Users,
  Award,
  GraduationCap,
  Target,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/contexts/AuthContext";
import { useToast } from "@/components/Toast";
import {
  getLeetCodeAccount,
  getLeetCodeRecommendations,
  type LeetCodeAccount,
  type LeetCodeRecommendations,
  type RecommendationItem,
  type DifficultyBreakdown,
} from "@/lib/api";

const DIFFICULTY_STYLE: Record<string, string> = {
  Easy: "bg-emerald-500/15 text-emerald-500 border border-emerald-500/30",
  Medium: "bg-amber-500/15 text-amber-500 border border-amber-500/30",
  Hard: "bg-rose-500/15 text-rose-500 border border-rose-500/30",
};

const containerVariants = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: {
      staggerChildren: 0.08,
    },
  },
};

const itemVariants = {
  hidden: { opacity: 0, y: 15 },
  show: { opacity: 1, y: 0, transition: { type: "spring" as const, stiffness: 100 } },
};

const Stat = ({ label, value }: { label: string; value: string | number }) => (
  <div className="rounded-xl border border-border/50 bg-background/40 p-4 text-center shadow-sm">
    <p className="text-2xl font-extrabold text-foreground">{value}</p>
    <p className="text-xs text-muted-foreground mt-1 font-semibold uppercase tracking-wider">{label}</p>
  </div>
);

const DifficultyBar = ({ breakdown }: { breakdown: DifficultyBreakdown }) => {
  const total = breakdown.total || 1;
  const segments = [
    { key: "easy", color: "bg-emerald-500", value: breakdown.easy },
    { key: "medium", color: "bg-amber-500", value: breakdown.medium },
    { key: "hard", color: "bg-rose-500", value: breakdown.hard },
  ];
  return (
    <div>
      <div className="flex h-3 w-full overflow-hidden rounded-full bg-muted shadow-inner">
        {segments.map((s) =>
          s.value > 0 ? (
            <div
              key={s.key}
              className={`${s.color} transition-all duration-500`}
              style={{ width: `${(s.value / total) * 100}%` }}
            />
          ) : null,
        )}
      </div>
      <div className="mt-3 flex justify-between text-xs text-muted-foreground font-semibold">
        <span className="flex items-center gap-1.5"><span className="w-2 h-2 rounded-full bg-emerald-500"></span>Easy {breakdown.easy}</span>
        <span className="flex items-center gap-1.5"><span className="w-2 h-2 rounded-full bg-amber-500"></span>Medium {breakdown.medium}</span>
        <span className="flex items-center gap-1.5"><span className="w-2 h-2 rounded-full bg-rose-500"></span>Hard {breakdown.hard}</span>
      </div>
    </div>
  );
};

const RecommendationRow = ({ item }: { item: RecommendationItem }) => (
  <a
    href={item.url}
    target="_blank"
    rel="noopener noreferrer"
    className="block rounded-xl border border-border/50 bg-background/40 p-3.5 hover:bg-accent/50 transition-colors shadow-sm"
  >
    <div className="flex items-center justify-between gap-3">
      <div className="min-w-0">
        <p className="text-sm font-semibold truncate hover:text-primary transition-colors">
          {item.number}. {item.title}
        </p>
        <p className="text-xs text-muted-foreground truncate mt-1">
          {item.topics.join(" · ") || "—"}
        </p>
      </div>
      <div className="flex items-center gap-2 shrink-0">
        {item.acceptance !== null && (
          <span className="text-xs text-muted-foreground font-medium">
            {(item.acceptance * 100).toFixed(1)}%
          </span>
        )}
        <span
          className={`rounded-full px-2.5 py-0.5 text-[10px] font-bold uppercase tracking-wider ${
            DIFFICULTY_STYLE[item.difficulty] ?? "bg-muted text-muted-foreground"
          }`}
        >
          {item.difficulty}
        </span>
      </div>
    </div>
  </a>
);

const LeetCode = () => {
  const { user } = useAuth();
  const { toast } = useToast();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [account, setAccount] = useState<LeetCodeAccount | null>(null);
  const [recs, setRecs] = useState<LeetCodeRecommendations | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [accountData, recData] = await Promise.all([
        getLeetCodeAccount(user),
        getLeetCodeRecommendations(user),
      ]);
      setAccount(accountData);
      setRecs(recData);
    } catch {
      toast("Could not load your LeetCode data", "error");
    } finally {
      setLoading(false);
    }
  }, [user, toast]);

  useEffect(() => {
    void load();
  }, [load]);

  const accepted = account?.profile?.accepted;
  const progress = account?.progress;

  return (
    <div className="h-full overflow-y-auto">
      <div className="max-w-3xl mx-auto px-4 py-8 space-y-6">
        <div className="flex items-center gap-3">
          <Button
            variant="ghost"
            size="icon"
            onClick={() => navigate("/settings")}
            aria-label="Back to settings"
          >
            <ArrowLeft className="h-5 w-5" />
          </Button>
          <h1 className="text-2xl font-bold">LeetCode Progress</h1>
        </div>

        {loading ? (
          <div className="flex flex-col items-center justify-center py-24 gap-3 text-muted-foreground">
            <Loader2 className="h-8 w-8 animate-spin text-primary" />
            <p className="text-sm">Fetching your LeetCode data…</p>
          </div>
        ) : !account?.linked ? (
          <motion.div 
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.4 }}
            className="glass-card border border-border/50 rounded-2xl p-8 text-center space-y-4"
          >
            <Target className="h-10 w-10 mx-auto text-primary" />
            <h2 className="text-lg font-bold">
              {account?.error ?? "No LeetCode account linked"}
            </h2>
            <p className="text-sm text-muted-foreground max-w-md mx-auto leading-relaxed">
              Link your public LeetCode profile in Settings to see your
              progress, strengths and recommended problems to solve next.
            </p>
            <Button onClick={() => navigate("/settings")} className="btn-gradient rounded-xl font-semibold">Go to Settings</Button>
          </motion.div>
        ) : (
          <motion.div 
            variants={containerVariants}
            initial="hidden"
            animate="show"
            className="space-y-6"
          >
            {/* Profile */}
            <motion.section variants={itemVariants} className="glass-card border border-border/50 rounded-2xl p-5 flex items-center gap-4">
              {account.profile?.avatar ? (
                <img
                  src={account.profile.avatar}
                  alt="LeetCode avatar"
                  className="w-14 h-14 rounded-full border border-border/50 shadow-sm"
                />
              ) : (
                <div className="w-14 h-14 rounded-full bg-primary/10 border border-primary/20 flex items-center justify-center">
                  <Award className="h-6 w-6 text-primary" />
                </div>
              )}
              <div className="min-w-0 flex-1">
                <p className="font-bold text-lg truncate">
                  {account.profile?.real_name || `@${account.username}`}
                </p>
                <p className="text-sm text-muted-foreground truncate">
                  @{account.username}
                </p>
                <div className="flex flex-wrap gap-x-4 gap-y-1 mt-1 text-xs text-muted-foreground font-semibold">
                  {account.profile?.ranking !== null &&
                    account.profile?.ranking !== undefined && (
                      <span className="inline-flex items-center gap-1.5">
                        <Trophy className="h-3.5 w-3.5 text-amber-500" />
                        #{account.profile.ranking.toLocaleString()}
                      </span>
                    )}
                  {account.profile?.country && (
                    <span className="inline-flex items-center gap-1.5">
                      <Users className="h-3.5 w-3.5" />
                      {account.profile.country}
                    </span>
                  )}
                  {account.profile?.school && (
                    <span className="inline-flex items-center gap-1.5 truncate">
                      <GraduationCap className="h-3.5 w-3.5" />
                      {account.profile.school}
                    </span>
                  )}
                </div>
              </div>
              <a
                href={`https://leetcode.com/${account.username}/`}
                target="_blank"
                rel="noopener noreferrer"
                className="shrink-0"
              >
                <Button variant="outline" size="sm" className="rounded-xl border-border/60">
                  <ExternalLink className="h-4 w-4 mr-2" />
                  Profile
                </Button>
              </a>
            </motion.section>

            {/* Stats */}
            {accepted && (
              <motion.section variants={itemVariants} className="grid grid-cols-2 md:grid-cols-4 gap-3">
                <Stat label="Solved" value={accepted.total} />
                <Stat label="Easy" value={accepted.easy} />
                <Stat label="Medium" value={accepted.medium} />
                <Stat label="Hard" value={accepted.hard} />
              </motion.section>
            )}

            {/* Progress breakdown */}
            {progress && (
              <motion.section variants={itemVariants} className="glass-card border border-border/50 rounded-2xl p-5 space-y-4">
                <h2 className="text-xs font-semibold text-muted-foreground/60 uppercase tracking-wider">
                  Progress by difficulty
                </h2>
                <DifficultyBar breakdown={progress.accepted} />
                <div className="grid grid-cols-3 gap-3 text-xs text-muted-foreground pt-2">
                  <div className="rounded-xl border border-border/50 bg-background/40 p-3 text-center">
                    <p className="text-base font-extrabold text-foreground">
                      {progress.failed.total}
                    </p>
                    <span className="text-[10px] uppercase font-bold text-muted-foreground/60 mt-1 block">Failed</span>
                  </div>
                  <div className="rounded-xl border border-border/50 bg-background/40 p-3 text-center">
                    <p className="text-base font-extrabold text-foreground">
                      {progress.untouched.total}
                    </p>
                    <span className="text-[10px] uppercase font-bold text-muted-foreground/60 mt-1 block">Untouched</span>
                  </div>
                  <div className="rounded-xl border border-border/50 bg-background/40 p-3 text-center">
                    <p className="text-base font-extrabold text-foreground">
                      {account.contest?.rating !== null &&
                      account.contest?.rating !== undefined
                        ? Math.round(account.contest.rating)
                        : "—"}
                    </p>
                    <span className="text-[10px] uppercase font-bold text-muted-foreground/60 mt-1 block">Contest Rating</span>
                  </div>
                </div>
                {account.contest?.top_percentage !== null &&
                  account.contest?.top_percentage !== undefined && (
                    <p className="text-xs text-muted-foreground leading-relaxed pt-1">
                      Top <span className="text-primary font-bold">{account.contest.top_percentage}%</span> of contestants across{" "}
                      {account.contest.contests_attended ?? 0} attended contests.
                    </p>
                  )}
              </motion.section>
            )}

            {/* Recommendations */}
            <motion.section variants={itemVariants} className="glass-card border border-border/50 rounded-2xl p-5 space-y-4">
              <div className="flex items-center justify-between">
                <h2 className="text-xs font-semibold text-muted-foreground/60 uppercase tracking-wider">
                  Recommended next problems
                </h2>
                {recs?.solved_count !== undefined && recs.solved_count > 0 && (
                  <span className="text-xs text-muted-foreground font-medium">
                    {recs.solved_count} recent solved
                  </span>
                )}
              </div>
              {recs && recs.recommendations.length > 0 ? (
                <div className="space-y-2.5">
                  {recs.recommendations.map((item) => (
                    <RecommendationRow key={item.title_slug} item={item} />
                  ))}
                </div>
              ) : (
                <p className="text-sm text-muted-foreground">
                  {recs?.message || "No recommendations available right now."}
                </p>
              )}
              <p className="text-xs text-muted-foreground/60 leading-relaxed pt-1.5 border-t border-border/30">
                The AI mentor also explains these in chat — try{" "}
                <span className="text-primary font-semibold">"what should I solve next?"</span>
              </p>
            </motion.section>

            {/* Recent accepted */}
            {account.recent_ac && account.recent_ac.length > 0 && (
              <motion.section variants={itemVariants} className="glass-card border border-border/50 rounded-2xl p-5 space-y-3">
                <h2 className="text-xs font-semibold text-muted-foreground/60 uppercase tracking-wider">
                  Recently solved
                </h2>
                <div className="flex flex-wrap gap-2">
                  {account.recent_ac.map((s) => (
                    <a
                      key={s.id}
                      href={`https://leetcode.com/problems/${s.title_slug}/`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1.5 rounded-full border border-border/50 bg-background/40 px-3.5 py-1.5 text-xs font-semibold hover:bg-accent/50 transition-colors shadow-sm"
                    >
                      {s.title}
                      <ExternalLink className="h-3 w-3 text-muted-foreground" />
                    </a>
                  ))}
                </div>
              </motion.section>
            )}
          </motion.div>
        )}
      </div>
    </div>
  );
};

export default LeetCode;
