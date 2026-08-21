import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";

const SnakeTrail = ({ delay = 0, color = "#4D82FF", width = 2, duration = 6 }) => (
  <svg className="absolute inset-0 w-full h-full pointer-events-none" viewBox="0 0 1000 1000">
    <motion.path
      d={`M ${200 + Math.random() * 600} ${200 + Math.random() * 600} 
         Q ${500 + (Math.random() - 0.5) * 400} ${500 + (Math.random() - 0.5) * 400} 
           ${500 + (Math.random() - 0.5) * 300} ${500 + (Math.random() - 0.5) * 300}
         T ${500 + (Math.random() - 0.5) * 500} ${500 + (Math.random() - 0.5) * 500}`}
      fill="none"
      stroke={color}
      strokeWidth={width}
      strokeLinecap="round"
      initial={{ pathLength: 0, pathOffset: 0, opacity: 0 }}
      animate={{ 
        pathLength: [0, 0.4, 0],
        pathOffset: [0, 1.2],
        opacity: [0, 0.6, 0]
      }}
      transition={{ 
        duration, 
        delay, 
        repeat: Infinity, 
        ease: "easeInOut" 
      }}
      style={{ filter: `blur(${width * 2}px)` }}
    />
  </svg>
);

const IntroSplash = ({ onComplete }: { onComplete: () => void }) => {
  const [percent, setPercent] = useState(0);
  const [status, setStatus] = useState("INITIALIZING");
  const [showButton, setShowButton] = useState(false);

  useEffect(() => {
    const sequence = [
      { p: 0, t: 0 },
      { p: 30, t: 800 },
      { p: 58, t: 1500 },
      { p: 78, t: 2200 },
      { p: 100, t: 3000 }
    ];

    sequence.forEach((step, i) => {
      setTimeout(() => {
        setPercent(step.p);
        if (step.p === 100) {
          setStatus("SYSTEM READY");
          setTimeout(() => setShowButton(true), 500);
        }
      }, step.t);
    });
  }, []);

  return (
    <div className="fixed inset-0 z-[200] bg-[#05070D] flex flex-col items-center justify-center overflow-hidden">
      {/* Snake trails */}
      <SnakeTrail delay={0} color="#4D82FF" width={3} duration={7} />
      <SnakeTrail delay={1.5} color="#6F9BFF" width={2} duration={8} />
      <SnakeTrail delay={3} color="#9EBCFF" width={4} duration={6} />
      <SnakeTrail delay={4.5} color="#4D82FF" width={2} duration={9} />

      {/* Main Branding */}
      <div className="relative z-10 flex flex-col items-center">
        <motion.div
          initial={{ opacity: 0, scale: 0.8 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.8, ease: "easeOut" }}
          className="text-5xl font-mono font-bold text-white mb-4 tracking-tighter"
        >
          &lt;/&gt;
        </motion.div>
        
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.5, duration: 1 }}
          className="text-4xl font-extrabold tracking-tight text-white flex gap-3"
        >
          <span>LeetCode</span>
          <span className="text-gradient">AI</span>
        </motion.div>

        {/* Loading Bar Container */}
        <div className="mt-12 w-64 space-y-4">
          <div className="flex justify-between items-end text-[10px] font-bold tracking-[0.2em] text-blue-400/60 uppercase">
            <span>{status}</span>
            <span>{percent}%</span>
          </div>
          <div className="h-[2px] w-full bg-white/5 rounded-full overflow-hidden">
            <motion.div 
              className="h-full bg-blue-500 shadow-[0_0_15px_rgba(77,130,255,0.8)]"
              animate={{ width: `${percent}%` }}
              transition={{ duration: 0.4 }}
            />
          </div>
        </div>
      </div>

      {/* CTA Button at Bottom */}
      <AnimatePresence>
        {showButton && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, ease: "easeOut" }}
            className="absolute bottom-20 z-20"
          >
            <button
              onClick={onComplete}
              className="group relative px-8 py-3 rounded-full bg-white/5 border border-white/10 hover:border-blue-500/50 transition-all duration-500"
            >
              <div className="absolute inset-0 rounded-full bg-blue-500/10 blur-xl opacity-0 group-hover:opacity-100 transition-opacity" />
              <span className="relative text-sm font-bold tracking-widest text-white flex items-center gap-3">
                Enter LeetCode AI
                <span className="text-blue-400 group-hover:translate-x-1 transition-transform">→</span>
              </span>
            </button>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Background radial glow */}
      <div className="absolute inset-0 bg-radial-gradient from-blue-500/5 to-transparent pointer-events-none" />
    </div>
  );
};

export default IntroSplash;
