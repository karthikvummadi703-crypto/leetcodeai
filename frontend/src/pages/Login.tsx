import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { useAuth, getAuthErrorMessage } from "@/contexts/AuthContext";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from "@/components/ui/card";
import { Eye, EyeOff, User, Lock } from "lucide-react";

/* Reusable hex logo */
const HexLogo = ({ size = 44 }: { size?: number }) => (
  <svg width={size} height={size} viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
    <defs>
      <linearGradient id="hexLogoBg" x1="0" y1="0" x2="64" y2="64">
        <stop offset="0%" stopColor="#7c3aed"/>
        <stop offset="100%" stopColor="#3b82f6"/>
      </linearGradient>
    </defs>
    <path d="M32 2 L58 17 L58 47 L32 62 L6 47 L6 17 Z" fill="url(#hexLogoBg)" stroke="rgba(255,255,255,0.15)" strokeWidth="1"/>
    <text x="32" y="42" textAnchor="middle" fontFamily="monospace" fontWeight="bold" fontSize="24" fill="white">&lt;/&gt;</text>
  </svg>
);

const Login = () => {
  const { signInWithGoogle, signInWithEmail, resetPassword } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [rememberMe, setRememberMe] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");
  const [resetSent, setResetSent] = useState(false);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setIsLoading(true);
    try {
      await signInWithEmail(email, password);
      navigate("/chat");
    } catch (err) {
      setError(getAuthErrorMessage(err));
      setIsLoading(false);
    }
  };

  const handleForgotPassword = async () => {
    if (!email.trim()) {
      setError("Enter your email address above to reset your password.");
      return;
    }
    setError("");
    try {
      await resetPassword(email);
      setResetSent(true);
    } catch (err) {
      setError(getAuthErrorMessage(err));
    }
  };

  const handleGoogleLogin = async () => {
    setError("");
    try {
      setIsLoading(true);
      await signInWithGoogle();
      navigate("/chat");
    } catch (err) {
      setError(getAuthErrorMessage(err));
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-background flex flex-col items-center justify-center p-4 relative overflow-hidden">
      {/* Background orbs */}
      <div className="absolute top-1/4 left-1/4 w-80 h-80 bg-primary/15 rounded-full blur-[120px] pointer-events-none animate-pulse-glow" />
      <div className="absolute bottom-1/4 right-1/4 w-80 h-80 bg-secondary/12 rounded-full blur-[120px] pointer-events-none animate-pulse-glow" style={{ animationDelay: "2s" }} />

      <Link to="/" className="absolute top-8 left-8 flex items-center gap-2.5 hover:opacity-80 transition-opacity">
        <HexLogo size={32} />
        <span className="text-lg font-bold tracking-tight">LeetCode <span className="text-gradient">AI</span></span>
      </Link>

      <motion.div
        initial={{ opacity: 0, y: 20, scale: 0.97 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        transition={{ duration: 0.4, ease: "easeOut" }}
        className="w-full max-w-md z-10"
      >
        <Card className="glass-card border-border/30 rounded-2xl overflow-hidden">
          <CardHeader className="space-y-3 text-center pt-8 pb-2">
            <div className="flex justify-center mb-2">
              <HexLogo size={48} />
            </div>
            <CardTitle className="text-2xl font-bold tracking-tight">Welcome Back!</CardTitle>
            <CardDescription className="text-muted-foreground text-sm">
              Login to continue to LeetCode Guidance AI
            </CardDescription>
          </CardHeader>
          <CardContent className="px-6 pb-2">
            <form onSubmit={handleLogin} className="space-y-4">
              {/* Email field */}
              <div className="relative">
                <User className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input 
                  id="email" 
                  placeholder="Email" 
                  type="email" 
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required 
                  className="pl-10 h-11 glass-input rounded-xl bg-background/30"
                />
              </div>

              {/* Password field */}
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input 
                  id="password" 
                  type={showPassword ? "text" : "password"}
                  placeholder="Password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required 
                  className="pl-10 pr-10 h-11 glass-input rounded-xl bg-background/30"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors"
                  aria-label={showPassword ? "Hide password" : "Show password"}
                >
                  {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>

              {/* Remember + Forgot */}
              <div className="flex items-center justify-between">
                <label className="flex items-center gap-2 cursor-pointer select-none">
                  <input
                    type="checkbox"
                    checked={rememberMe}
                    onChange={(e) => setRememberMe(e.target.checked)}
                    className="w-4 h-4 rounded border-border/50 bg-background/30 text-primary accent-primary"
                  />
                  <span className="text-sm text-muted-foreground">Remember me</span>
                </label>
                <button
                  type="button"
                  onClick={handleForgotPassword}
                  className="text-sm text-primary hover:underline font-medium"
                >
                  Forgot Password?
                </button>
              </div>

              {error && (
                <p role="alert" className="text-sm text-destructive bg-destructive/10 rounded-lg px-3 py-2">{error}</p>
              )}
              {resetSent && (
                <p role="status" className="text-sm text-green-400 bg-green-500/10 rounded-lg px-3 py-2">
                  Password reset link sent. Check your email.
                </p>
              )}

              <Button 
                type="submit" 
                className="w-full h-11 btn-gradient rounded-xl text-base font-semibold"
                disabled={isLoading}
              >
                {isLoading ? "Signing in..." : "Login"}
              </Button>
            </form>

            {/* Divider */}
            <div className="relative my-6">
              <div className="absolute inset-0 flex items-center">
                <span className="w-full border-t border-border/40" />
              </div>
              <div className="relative flex justify-center text-xs">
                <span className="bg-card px-3 text-muted-foreground">
                  or continue with
                </span>
              </div>
            </div>

            {/* Google */}
            <Button 
              variant="outline" 
              type="button" 
              className="w-full h-11 rounded-xl bg-background/30 border-border/40 hover:bg-accent/60 font-medium text-sm" 
              onClick={handleGoogleLogin} 
              disabled={isLoading}
            >
              <svg className="mr-2 h-3.5 w-3.5" viewBox="0 0 24 24">
                <path
                  d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
                  fill="#4285F4"
                />
                <path
                  d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
                  fill="#34A853"
                />
                <path
                  d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
                  fill="#FBBC05"
                />
                <path
                  d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
                  fill="#EA4335"
                />
              </svg>
              Continue with Google
            </Button>
          </CardContent>
          <CardFooter className="pb-6 pt-4">
            <div className="text-sm text-center w-full text-muted-foreground">
              Don't have an account?{" "}
              <Link to="/signup" className="text-primary hover:underline font-semibold">
                Sign up
              </Link>
            </div>
          </CardFooter>
        </Card>
      </motion.div>
    </div>
  );
};

export default Login;
