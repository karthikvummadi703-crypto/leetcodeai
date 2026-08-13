import { motion, useScroll, useTransform } from "framer-motion";
import { useRef } from "react";
import { Link } from "react-router-dom";
import { 
  BrainCircuit, 
  Target, 
  Zap, 
  ChevronRight,
  Sparkles,
  BookOpen,
  TrendingUp,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import heroImg from "@/assets/hero_illustration.png";

/* ── Reusable Logo Icon (hexagonal </>) ──────────────────── */
const HexLogo = ({ size = 48 }: { size?: number }) => (
  <svg width={size} height={size} viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
    <defs>
      <linearGradient id="hexBg" x1="0" y1="0" x2="64" y2="64">
        <stop offset="0%" stopColor="#7c3aed"/>
        <stop offset="100%" stopColor="#3b82f6"/>
      </linearGradient>
    </defs>
    <path d="M32 2 L58 17 L58 47 L32 62 L6 47 L6 17 Z" fill="url(#hexBg)" stroke="rgba(255,255,255,0.15)" strokeWidth="1"/>
    <text x="32" y="42" textAnchor="middle" fontFamily="monospace" fontWeight="bold" fontSize="24" fill="white">&lt;/&gt;</text>
  </svg>
);

/* ── Animations Config ───────────────────────────────────── */
const fadeUp = {
  hidden: { opacity: 0, y: 40 },
  visible: { opacity: 1, y: 0 },
};

const fadeIn = {
  hidden: { opacity: 0 },
  visible: { opacity: 1 },
};

const staggerContainer = {
  hidden: {},
  visible: { transition: { staggerChildren: 0.15 } },
};

const scaleIn = {
  hidden: { opacity: 0, scale: 0.85 },
  visible: { opacity: 1, scale: 1 },
};

/* ── Feature Data ────────────────────────────────────────── */
const features = [
  {
    icon: <BrainCircuit className="h-7 w-7" />,
    title: "AI-Powered Explanations",
    description: "Get detailed, step-by-step explanations of complex algorithms tailored to your understanding level.",
    color: "from-violet-500 to-purple-600",
  },
  {
    icon: <Zap className="h-7 w-7" />,
    title: "Complexity Analysis",
    description: "Instantly understand Time and Space complexity for your solutions with visual breakdowns.",
    color: "from-blue-500 to-cyan-500",
  },
  {
    icon: <Target className="h-7 w-7" />,
    title: "Pattern Recognition",
    description: "Learn to identify underlying patterns like Sliding Window or Two Pointers in new problems.",
    color: "from-emerald-500 to-teal-500",
  },
  {
    icon: <Sparkles className="h-7 w-7" />,
    title: "Personalized Hints",
    description: "Receive contextual hints that guide you toward the solution without giving it away.",
    color: "from-amber-500 to-orange-500",
  },
  {
    icon: <BookOpen className="h-7 w-7" />,
    title: "LeetCode Integration",
    description: "Link your LeetCode account to get personalized problem recommendations and track your progress.",
    color: "from-pink-500 to-rose-500",
  },
  {
    icon: <TrendingUp className="h-7 w-7" />,
    title: "Progress Tracking",
    description: "Monitor your growth with detailed analytics across difficulty levels and topic areas.",
    color: "from-indigo-500 to-violet-500",
  },
];

const steps = [
  { step: "01", title: "Paste Your Problem", desc: "Simply paste the LeetCode URL or problem description into the chat." },
  { step: "02", title: "Ask For Hints", desc: "Stuck? Ask the AI for a hint, not the solution. It will guide you towards the right approach." },
  { step: "03", title: "Analyze & Learn", desc: "Get time/space complexity breakdowns, understand patterns, and master concepts." },
];

/* ── Component ───────────────────────────────────────────── */
const Landing = () => {
  const heroRef = useRef<HTMLDivElement>(null);
  const { scrollYProgress } = useScroll({
    target: heroRef,
    offset: ["start start", "end start"],
  });
  const heroY = useTransform(scrollYProgress, [0, 1], ["0%", "30%"]);
  const heroOpacity = useTransform(scrollYProgress, [0, 0.5], [1, 0]);

  return (
    <div className="min-h-screen bg-background text-foreground flex flex-col font-sans selection:bg-primary/30">
      {/* ── Navbar ──────────────────────────────────────────── */}
      <motion.nav
        initial={{ y: -20, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ duration: 0.5 }}
        className="h-16 glass fixed top-0 w-full z-50 flex items-center justify-between px-6 lg:px-12"
      >
        <div className="flex items-center gap-3">
          <HexLogo size={36} />
          <span className="text-lg font-bold tracking-tight">LeetCode <span className="text-gradient">AI</span></span>
        </div>
        <div className="flex items-center gap-4">
          <Link to="/login" className="text-sm font-medium hover:text-primary transition-colors">
            Login
          </Link>
          <Link to="/signup">
            <Button className="btn-gradient rounded-full px-6 text-sm font-semibold">Get Started</Button>
          </Link>
        </div>
      </motion.nav>

      <main className="flex-1 pt-16">
        {/* ── Hero Section ────────────────────────────────────── */}
        <section ref={heroRef} className="relative overflow-hidden pt-20 pb-28 lg:pt-28 lg:pb-36">
          {/* Animated background orbs */}
          <div className="absolute inset-0 bg-gradient-hero pointer-events-none" />
          <div className="absolute top-20 left-1/4 w-72 h-72 bg-primary/10 rounded-full blur-[100px] animate-pulse-glow pointer-events-none" />
          <div className="absolute bottom-20 right-1/4 w-96 h-96 bg-secondary/8 rounded-full blur-[120px] animate-pulse-glow pointer-events-none" style={{ animationDelay: "2s" }} />
          
          <motion.div
            style={{ y: heroY, opacity: heroOpacity }}
            className="container mx-auto px-6 relative z-10"
          >
            <div className="flex flex-col lg:flex-row items-center gap-12 lg:gap-16">
              {/* Left: Text */}
              <motion.div
                className="flex-1 text-center lg:text-left"
                initial="hidden"
                animate="visible"
                variants={staggerContainer}
              >
                <motion.div variants={fadeUp} transition={{ duration: 0.6 }} className="mb-4">
                  <span className="inline-flex items-center gap-2 rounded-full bg-primary/10 border border-primary/20 px-4 py-1.5 text-xs font-medium text-primary">
                    <Sparkles className="h-3.5 w-3.5" />
                    AI-Powered DSA Mentor
                  </span>
                </motion.div>

                <motion.h1 
                  variants={fadeUp} 
                  transition={{ duration: 0.6, delay: 0.1 }}
                  className="text-4xl sm:text-5xl lg:text-6xl xl:text-7xl font-extrabold tracking-tight mb-6 leading-[1.1]"
                >
                  Your Personal{" "}
                  <span className="text-gradient glow-text">DSA Mentor</span>
                  <br />
                  <span className="text-muted-foreground text-3xl sm:text-4xl lg:text-5xl font-semibold">Your Coding Partner.</span>
                </motion.h1>

                <motion.p 
                  variants={fadeUp}
                  transition={{ duration: 0.6, delay: 0.2 }}
                  className="text-base lg:text-lg text-muted-foreground max-w-xl mx-auto lg:mx-0 mb-8 leading-relaxed"
                >
                  Stop memorizing solutions and start understanding patterns.
                  Get contextual hints, complexity analysis, and interactive
                  guidance powered by AI.
                </motion.p>
                
                <motion.div 
                  variants={fadeUp}
                  transition={{ duration: 0.6, delay: 0.3 }}
                  className="flex flex-col sm:flex-row items-center lg:items-start gap-4"
                >
                  <Link to="/signup">
                    <Button className="btn-gradient rounded-full px-8 py-3 text-base font-semibold h-auto">
                      Start Learning For Free
                      <ChevronRight className="ml-2 h-5 w-5" />
                    </Button>
                  </Link>
                  <Link to="/login">
                    <Button variant="outline" className="rounded-full px-8 py-3 text-base font-medium h-auto border-border/50 hover:bg-accent/60">
                      Login with Email
                    </Button>
                  </Link>
                </motion.div>
              </motion.div>

              {/* Right: Hero Image */}
              <motion.div
                className="flex-1 relative max-w-lg"
                initial={{ opacity: 0, x: 40, scale: 0.95 }}
                animate={{ opacity: 1, x: 0, scale: 1 }}
                transition={{ duration: 0.8, delay: 0.3 }}
              >
                <div className="relative">
                  {/* Glow behind image */}
                  <div className="absolute inset-0 bg-gradient-to-tr from-primary/20 to-secondary/15 rounded-3xl blur-3xl scale-110" />
                  
                  <img 
                    src={heroImg}
                    alt="DSA Mentor AI - Hero Illustration" 
                    className="relative w-full rounded-2xl shadow-2xl"
                  />
                  
                  {/* Floating badges */}
                  <motion.div 
                    animate={{ y: [0, -12, 0] }}
                    transition={{ duration: 4, repeat: Infinity, ease: "easeInOut" }}
                    className="absolute -top-4 -left-4 glass px-4 py-2 rounded-xl flex items-center gap-2 shadow-lg"
                  >
                    <span className="text-xl">🧠</span>
                    <span className="font-semibold text-sm">Aha! Moment</span>
                  </motion.div>
                  
                  <motion.div 
                    animate={{ y: [0, 12, 0] }}
                    transition={{ duration: 5, repeat: Infinity, ease: "easeInOut", delay: 1.5 }}
                    className="absolute -bottom-4 -right-4 glass px-4 py-2 rounded-xl flex items-center gap-2 shadow-lg"
                  >
                    <span className="text-xl">⚡</span>
                    <span className="font-semibold text-sm">O(N) Complexity</span>
                  </motion.div>

                  <motion.div 
                    animate={{ y: [0, -8, 0] }}
                    transition={{ duration: 4.5, repeat: Infinity, ease: "easeInOut", delay: 0.8 }}
                    className="absolute top-1/2 -right-8 glass px-3 py-1.5 rounded-lg flex items-center gap-2 shadow-lg"
                  >
                    <span className="text-lg">🎯</span>
                    <span className="font-medium text-xs">Pattern Match</span>
                  </motion.div>
                </div>
              </motion.div>
            </div>
          </motion.div>
        </section>

        {/* ── Features Section ───────────────────────────────── */}
        <section className="py-24 relative">
          <div className="absolute inset-0 bg-card/20 pointer-events-none" />
          
          <div className="container mx-auto px-6 relative z-10">
            <motion.div 
              className="text-center mb-16"
              initial="hidden"
              whileInView="visible"
              viewport={{ once: true, margin: "-100px" }}
              variants={fadeUp}
              transition={{ duration: 0.6 }}
            >
              <h2 className="text-3xl lg:text-5xl font-bold mb-4">
                Master Coding <span className="text-gradient">Interviews</span>
              </h2>
              <p className="text-muted-foreground max-w-2xl mx-auto text-base lg:text-lg">
                Our AI doesn't just give you the answer. It acts as a senior engineer pair-programming with you
                to help you arrive at the solution yourself.
              </p>
            </motion.div>
            
            <motion.div 
              className="grid md:grid-cols-2 lg:grid-cols-3 gap-6 max-w-6xl mx-auto"
              initial="hidden"
              whileInView="visible"
              viewport={{ once: true, margin: "-80px" }}
              variants={staggerContainer}
            >
              {features.map((feature, index) => (
                <motion.div 
                  key={index}
                  variants={scaleIn}
                  transition={{ duration: 0.5 }}
                  whileHover={{ y: -6, transition: { duration: 0.2 } }}
                  className="glass-card p-7 rounded-2xl group cursor-default"
                >
                  <div className={`h-12 w-12 rounded-xl bg-gradient-to-br ${feature.color} flex items-center justify-center mb-5 text-white shadow-lg group-hover:scale-110 transition-transform duration-300`}>
                    {feature.icon}
                  </div>
                  <h3 className="text-lg font-semibold mb-2">{feature.title}</h3>
                  <p className="text-muted-foreground text-sm leading-relaxed">
                    {feature.description}
                  </p>
                </motion.div>
              ))}
            </motion.div>
          </div>
        </section>

        {/* ── How It Works ───────────────────────────────────── */}
        <section className="py-24 relative overflow-hidden">
          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-primary/5 rounded-full blur-[150px] pointer-events-none" />
          
          <div className="container mx-auto px-6 max-w-4xl relative z-10">
            <motion.h2 
              className="text-3xl lg:text-5xl font-bold mb-16 text-center"
              initial="hidden"
              whileInView="visible"
              viewport={{ once: true }}
              variants={fadeUp}
              transition={{ duration: 0.6 }}
            >
              How It <span className="text-gradient">Works</span>
            </motion.h2>
            
            <div className="space-y-8 lg:space-y-12">
              {steps.map((item, i) => (
                <motion.div
                  key={i}
                  initial="hidden"
                  whileInView="visible"
                  viewport={{ once: true, margin: "-50px" }}
                  variants={fadeUp}
                  transition={{ duration: 0.6, delay: i * 0.15 }}
                  className="flex gap-6 items-start group"
                >
                  <div className="flex-shrink-0 w-16 h-16 rounded-2xl bg-gradient-to-br from-primary/20 to-secondary/10 border border-primary/20 flex items-center justify-center text-xl font-bold text-primary group-hover:scale-110 transition-transform duration-300">
                    {item.step}
                  </div>
                  <div className="pt-1">
                    <h3 className="text-xl lg:text-2xl font-semibold mb-2">{item.title}</h3>
                    <p className="text-base text-muted-foreground leading-relaxed">{item.desc}</p>
                  </div>
                </motion.div>
              ))}
            </div>
          </div>
        </section>

        {/* ── CTA Section ────────────────────────────────────── */}
        <section className="py-24">
          <div className="container mx-auto px-6">
            <motion.div 
              className="max-w-3xl mx-auto text-center glass-card rounded-3xl p-12 lg:p-16 relative overflow-hidden"
              initial="hidden"
              whileInView="visible"
              viewport={{ once: true }}
              variants={scaleIn}
              transition={{ duration: 0.6 }}
            >
              <div className="absolute inset-0 bg-gradient-to-br from-primary/5 to-secondary/5 pointer-events-none" />
              <div className="relative z-10">
                <HexLogo size={56} />
                <h2 className="text-3xl lg:text-4xl font-bold mt-6 mb-4">
                  Ready to Level Up?
                </h2>
                <p className="text-muted-foreground text-base lg:text-lg mb-8 max-w-lg mx-auto">
                  Join thousands of developers who are mastering DSA with AI-powered guidance. Start your journey today.
                </p>
                <Link to="/signup">
                  <Button className="btn-gradient rounded-full px-10 py-3 text-base font-semibold h-auto">
                    Get Started — It's Free
                    <ChevronRight className="ml-2 h-5 w-5" />
                  </Button>
                </Link>
              </div>
            </motion.div>
          </div>
        </section>
      </main>

      {/* ── Footer ───────────────────────────────────────────── */}
      <motion.footer
        initial="hidden"
        whileInView="visible"
        viewport={{ once: true }}
        variants={fadeIn}
        transition={{ duration: 0.6 }}
        className="border-t border-border/30 py-12 bg-card/30"
      >
        <div className="container mx-auto px-6 text-center">
          <div className="flex items-center justify-center gap-3 mb-6">
            <HexLogo size={32} />
            <span className="text-lg font-bold tracking-tight">LeetCode <span className="text-gradient">Guidance AI</span></span>
          </div>
          <p className="text-muted-foreground text-sm">
            &copy; {new Date().getFullYear()} LeetCode Guidance AI. All rights reserved.
          </p>
        </div>
      </motion.footer>
    </div>
  );
};

export default Landing;
