import { useEffect, useState } from "react";
import { motion } from "motion/react";
import { AnimatePresence, motion as fm } from "framer-motion";

const HexLogo = ({ size = 84 }: { size?: number }) => (
  <svg width={size} height={size} viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
    <defs>
      <linearGradient id="splashHexGrad" x1="0" y1="0" x2="64" y2="64">
        <stop offset="0%" stopColor="#7c3aed"/>
        <stop offset="100%" stopColor="#3b82f6"/>
      </linearGradient>
    </defs>
    <path d="M32 2 L58 17 L58 47 L32 62 L6 47 L6 17 Z" fill="url(#splashHexGrad)" stroke="rgba(255,255,255,0.15)" strokeWidth="1"/>
    <text x="32" y="42" textAnchor="middle" fontFamily="monospace" fontWeight="bold" fontSize="24" fill="white">&lt;/&gt;</text>
  </svg>
);

const SplashScreen = ({ duration = 2200 }: { duration?: number }) => {
  const [visible, setVisible] = useState(true);

  useEffect(() => {
    const timer = window.setTimeout(() => setVisible(false), duration);
    return () => window.clearTimeout(timer);
  }, [duration]);

  return (
    <AnimatePresence>
      {visible && (
        <fm.div
          key="splash"
          initial={{ opacity: 1 }}
          exit={{ opacity: 0, scale: 1.06 }}
          transition={{ duration: 0.6, ease: "easeInOut" }}
          className="fixed inset-0 z-[100] flex flex-col items-center justify-center bg-background text-foreground overflow-hidden"
        >
          {/* Background orbs (matches the site's look) */}
          <div className="absolute top-1/4 left-1/4 w-80 h-80 bg-primary/15 rounded-full blur-[120px] pointer-events-none animate-pulse-glow" />
          <div className="absolute bottom-1/4 right-1/4 w-80 h-80 bg-secondary/12 rounded-full blur-[120px] pointer-events-none animate-pulse-glow" style={{ animationDelay: "2s" }} />

          <motion.div
            initial={{ scale: 0.5, opacity: 0, rotate: -8 }}
            animate={{ scale: 1, opacity: 1, rotate: 0 }}
            transition={{ type: "spring", stiffness: 200, damping: 18, delay: 0.1 }}
          >
            <div className="relative">
              <div className="absolute inset-0 scale-125 rounded-3xl bg-gradient-to-tr from-primary/30 to-secondary/20 blur-3xl" />
              <HexLogo size={84} />
            </div>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.35, duration: 0.5, ease: "easeOut" }}
            className="mt-7 text-center"
          >
            <h1 className="text-3xl font-extrabold tracking-tight">
              LeetCode <span className="text-gradient glow-text">AI</span>
            </h1>
            <p className="text-sm text-muted-foreground mt-2">
              Your personal DSA mentor
            </p>
          </motion.div>

          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.5 }}
            className="mt-9 h-1 w-52 overflow-hidden rounded-full bg-muted"
          >
            <motion.div
              className="h-full rounded-full btn-gradient"
              initial={{ width: "0%" }}
              animate={{ width: "100%" }}
              transition={{ duration: Math.max(0.4, duration / 1000 - 0.4), ease: "easeInOut", delay: 0.2 }}
            />
          </motion.div>
        </fm.div>
      )}
    </AnimatePresence>
  );
};

export default SplashScreen;
