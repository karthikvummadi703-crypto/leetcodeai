import { motion } from "framer-motion";
import { Link } from "react-router-dom";
import { 
  Code2, 
  BrainCircuit, 
  Target, 
  Zap, 
  ChevronRight
} from "lucide-react";
import { Button } from "@/components/ui/button";

const features = [
  {
    icon: <BrainCircuit className="h-6 w-6 text-primary" />,
    title: "AI-Powered Explanations",
    description: "Get detailed, step-by-step explanations of complex algorithms tailored to your understanding level."
  },
  {
    icon: <Zap className="h-6 w-6 text-primary" />,
    title: "Complexity Analysis",
    description: "Instantly understand Time and Space complexity for your solutions with visual breakdowns."
  },
  {
    icon: <Target className="h-6 w-6 text-primary" />,
    title: "Pattern Recognition",
    description: "Learn to identify underlying patterns like Sliding Window or Two Pointers in new problems."
  }
];

const Landing = () => {
  return (
    <div className="min-h-screen bg-background text-foreground flex flex-col font-sans selection:bg-primary/30">
      {/* Navbar */}
      <nav className="h-20 border-b border-border/50 glass fixed top-0 w-full z-50 flex items-center justify-between px-6 lg:px-12">
        <div className="flex items-center gap-2">
          <Code2 className="h-8 w-8 text-primary" />
          <span className="text-xl font-bold tracking-tight">LeetCode Guidance AI</span>
        </div>
        <div className="flex items-center gap-4">
          <Link to="/login" className="text-sm font-medium hover:text-primary transition-colors">
            Login
          </Link>
          <Link to="/signup">
            <Button variant="premium">Get Started</Button>
          </Link>
        </div>
      </nav>

      <main className="flex-1 pt-20">
        {/* Hero Section */}
        <section className="relative overflow-hidden pt-24 pb-32 lg:pt-36 lg:pb-40">
          <div className="absolute inset-0 bg-gradient-premium opacity-50 pointer-events-none" />
          
          <div className="container mx-auto px-6 relative z-10 text-center">
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5 }}
            >
              <h1 className="text-5xl lg:text-7xl font-extrabold tracking-tight mb-6">
                Your Personal <span className="text-gradient">DSA Mentor</span>
              </h1>
              <p className="text-lg lg:text-xl text-muted-foreground max-w-2xl mx-auto mb-10">
                Master Data Structures and Algorithms with AI. Stop memorizing solutions and start understanding patterns with contextual hints, complexity analysis, and interactive guidance.
              </p>
              
              <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
                <Link to="/signup">
                  <Button variant="premium" size="lg" className="w-full sm:w-auto text-lg px-8">
                    Start Learning For Free
                    <ChevronRight className="ml-2 h-5 w-5" />
                  </Button>
                </Link>
                <Link to="/login">
                  <Button variant="outline" size="lg" className="w-full sm:w-auto text-lg px-8">
                    Login with Email
                  </Button>
                </Link>
              </div>
            </motion.div>

            {/* Floating UI Elements / Hero Image */}
            <motion.div 
              initial={{ opacity: 0, y: 40 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.7, delay: 0.2 }}
              className="mt-16 relative max-w-4xl mx-auto"
            >
              <div className="aspect-video rounded-xl overflow-hidden glass-card p-2">
                <img 
                  src="/src/assets/hero.png" 
                  alt="App Interface" 
                  className="w-full h-full object-cover rounded-lg border border-border/50"
                  onError={(e) => {
                    // Fallback if image doesn't load
                    const target = e.target as HTMLImageElement;
                    target.src = "https://images.unsplash.com/photo-1555066931-4365d14bab8c?auto=format&fit=crop&q=80&w=1200&h=600";
                  }}
                />
              </div>
              
              {/* Floating badges */}
              <motion.div 
                animate={{ y: [0, -10, 0] }}
                transition={{ duration: 4, repeat: Infinity, ease: "easeInOut" }}
                className="absolute -top-6 -left-6 glass px-4 py-2 rounded-lg flex items-center gap-2"
              >
                <span className="text-2xl">🧠</span>
                <span className="font-medium text-sm">Aha! Moment</span>
              </motion.div>
              
              <motion.div 
                animate={{ y: [0, 10, 0] }}
                transition={{ duration: 5, repeat: Infinity, ease: "easeInOut", delay: 1 }}
                className="absolute -bottom-6 -right-6 glass px-4 py-2 rounded-lg flex items-center gap-2"
              >
                <span className="text-2xl">⚡</span>
                <span className="font-medium text-sm">O(N) Complexity</span>
              </motion.div>
            </motion.div>
          </div>
        </section>

        {/* Features Section */}
        <section className="py-24 bg-card/30">
          <div className="container mx-auto px-6">
            <div className="text-center mb-16">
              <h2 className="text-3xl lg:text-4xl font-bold mb-4">Master Coding Interviews</h2>
              <p className="text-muted-foreground max-w-2xl mx-auto">
                Our AI doesn't just give you the answer. It acts as a senior engineer pair-programming with you to help you arrive at the solution yourself.
              </p>
            </div>
            
            <div className="grid md:grid-cols-3 gap-8 max-w-5xl mx-auto">
              {features.map((feature, index) => (
                <motion.div 
                  key={index}
                  initial={{ opacity: 0, y: 20 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true }}
                  transition={{ delay: index * 0.1 }}
                  className="glass-card p-8 rounded-xl"
                >
                  <div className="h-12 w-12 rounded-lg bg-primary/10 flex items-center justify-center mb-6">
                    {feature.icon}
                  </div>
                  <h3 className="text-xl font-semibold mb-3">{feature.title}</h3>
                  <p className="text-muted-foreground leading-relaxed">
                    {feature.description}
                  </p>
                </motion.div>
              ))}
            </div>
          </div>
        </section>

        {/* How It Works */}
        <section className="py-24">
          <div className="container mx-auto px-6 max-w-4xl">
            <h2 className="text-3xl lg:text-4xl font-bold mb-16 text-center">How It Works</h2>
            
            <div className="space-y-12">
              {[
                { step: "01", title: "Paste Your Problem", desc: "Simply paste the LeetCode URL or problem description into the chat." },
                { step: "02", title: "Ask For Hints", desc: "Stuck? Ask the AI for a hint, not the solution. It will guide you towards the right approach." },
                { step: "03", title: "Analyze Complexity", desc: "Once solved, ask for a time and space complexity breakdown to ensure optimality." }
              ].map((item, i) => (
                <div key={i} className="flex gap-6 items-start">
                  <div className="flex-shrink-0 w-16 h-16 rounded-full glass flex items-center justify-center text-xl font-bold text-primary">
                    {item.step}
                  </div>
                  <div>
                    <h3 className="text-2xl font-semibold mb-2">{item.title}</h3>
                    <p className="text-lg text-muted-foreground">{item.desc}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </section>

      </main>

      <footer className="border-t border-border/50 py-12 bg-card/50">
        <div className="container mx-auto px-6 text-center">
          <div className="flex items-center justify-center gap-2 mb-6">
            <Code2 className="h-6 w-6 text-primary" />
            <span className="text-xl font-bold tracking-tight">LeetCode Guidance AI</span>
          </div>
          <p className="text-muted-foreground text-sm">
            &copy; {new Date().getFullYear()} LeetCode Guidance AI. All rights reserved.
          </p>
        </div>
      </footer>
    </div>
  );
};

export default Landing;
