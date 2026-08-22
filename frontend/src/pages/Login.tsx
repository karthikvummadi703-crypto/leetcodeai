import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import { useAuth, getAuthErrorMessage } from "@/contexts/AuthContext";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from "@/components/ui/card";
import { Eye, EyeOff, User, Lock, Target } from "lucide-react";
import MagicRings from "@/components/MagicRings";

const HexLogo = ({ size = 48 }: { size?: number }) => (
  <svg width={size} height={size} viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
    <defs>
      <linearGradient id="loginHexGrad" x1="0" y1="0" x2="64" y2="64">
        <stop offset="0%" stopColor="#4D82FF"/>
        <stop offset="100%" stopColor="#9EBCFF"/>
      </linearGradient>
    </defs>
    <path d="M32 2 L58 17 L58 47 L32 62 L6 47 L6 17 Z" fill="url(#loginHexGrad)" stroke="rgba(255,255,255,0.15)" strokeWidth="1"/>
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
      setError("Enter your email address to reset your password.");
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
    <div className="min-h-screen bg-[#05070D] flex items-center justify-center p-6 relative overflow-hidden">
      {/* MagicRings background */}
      <div className="absolute inset-0 pointer-events-none">
        <MagicRings
          color="#4D82FF"
          colorTwo="#7c3aed"
          ringCount={5}
          speed={0.7}
          attenuation={8}
          lineThickness={1.5}
          baseRadius={0.5}
          radiusStep={0.16}
          scaleRate={0.1}
          opacity={0.5}
          noiseAmount={0.05}
          followMouse={true}
          mouseInfluence={0.1}
          parallax={0.03}
        />
      </div>

      {/* Background Orbs */}
      <div className="absolute top-0 right-0 w-[500px] h-[500px] bg-blue-500/10 rounded-full blur-[120px] -mr-64 -mt-64" />
      <div className="absolute bottom-0 left-0 w-[500px] h-[500px] bg-blue-600/5 rounded-full blur-[120px] -ml-64 -mb-64" />

      <motion.div
        initial={{ opacity: 0, scale: 0.95, y: 20 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        transition={{ duration: 0.8, cubicBezier: [0.16, 1, 0.3, 1] }}
        className="w-full max-w-[440px] z-10"
      >
        <Card className="glass-card border-white/5 rounded-[2.5rem] overflow-hidden">
          <CardHeader className="space-y-4 text-center pt-12 pb-6">
            <div className="flex justify-center">
              <motion.div
                whileHover={{ scale: 1.05, rotate: 5 }}
                transition={{ type: "spring", stiffness: 400, damping: 10 }}
              >
                <HexLogo size={64} />
              </motion.div>
            </div>
            <div className="space-y-1">
              <CardTitle className="text-3xl font-bold tracking-tight text-white">Welcome Back</CardTitle>
              <CardDescription className="text-blue-400/60 font-medium">
                Resuming your journey to mastery
              </CardDescription>
            </div>
          </CardHeader>

          <CardContent className="px-10 pb-8">
            <form onSubmit={handleLogin} className="space-y-6">
              <div className="space-y-4">
                {/* Email */}
                <div className="relative group">
                  <User className="absolute left-4 top-1/2 -translate-y-1/2 h-4 w-4 text-white/30 group-focus-within:text-blue-400 transition-colors" />
                  <Input 
                    type="email" 
                    placeholder="Email Address" 
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    required 
                    className="pl-12 h-13 glass-input rounded-2xl bg-white/[0.02] text-white border-white/5 placeholder:text-white/20"
                  />
                </div>

                {/* Password */}
                <div className="relative group">
                  <Lock className="absolute left-4 top-1/2 -translate-y-1/2 h-4 w-4 text-white/30 group-focus-within:text-blue-400 transition-colors" />
                  <Input 
                    type={showPassword ? "text" : "password"}
                    placeholder="Password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    required 
                    className="pl-12 pr-12 h-13 glass-input rounded-2xl bg-white/[0.02] text-white border-white/5 placeholder:text-white/20"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-4 top-1/2 -translate-y-1/2 text-white/20 hover:text-white transition-colors"
                  >
                    {showPassword ? <EyeOff className="h-5 w-5" /> : <Eye className="h-5 w-5" />}
                  </button>
                </div>
              </div>

              <div className="flex items-center justify-between px-1">
                <label className="flex items-center gap-3 cursor-pointer group">
                  <div className="relative flex items-center justify-center">
                    <input
                      type="checkbox"
                      checked={rememberMe}
                      onChange={(e) => setRememberMe(e.target.checked)}
                      className="peer h-5 w-5 rounded-lg border-white/10 bg-white/5 text-blue-500 appearance-none checked:bg-blue-500 checked:border-blue-500 transition-all"
                    />
                    <Target size={12} className="absolute text-white opacity-0 peer-checked:opacity-100 transition-opacity" />
                  </div>
                  <span className="text-sm text-white/40 group-hover:text-white/60 transition-colors">Remember me</span>
                </label>
                <button
                  type="button"
                  onClick={handleForgotPassword}
                  className="text-sm font-bold text-blue-400 hover:text-blue-300 transition-colors"
                >
                  Forgot password?
                </button>
              </div>

              {error && (
                <motion.div 
                  initial={{ opacity: 0, y: -10 }} 
                  animate={{ opacity: 1, y: 0 }}
                  className="p-4 rounded-2xl bg-red-500/10 border border-red-500/20 text-xs font-semibold text-red-400"
                >
                  {error}
                </motion.div>
              )}

              {resetSent && (
                <div className="p-4 rounded-2xl bg-green-500/10 border border-green-500/20 text-xs font-semibold text-green-400">
                  Reset link sent! Check your inbox.
                </div>
              )}

              <Button 
                type="submit" 
                disabled={isLoading}
                className="w-full h-13 btn-gradient rounded-2xl text-base font-bold"
              >
                {isLoading ? "Signing in..." : "Login"}
              </Button>
            </form>

            <div className="relative my-10">
              <div className="absolute inset-0 flex items-center">
                <div className="w-full border-t border-white/5" />
              </div>
              <div className="relative flex justify-center text-[10px] uppercase tracking-[0.2em] font-bold text-white/20">
                <span className="bg-[#0D121E] px-4">Secure Social</span>
              </div>
            </div>

            <Button 
              variant="outline" 
              onClick={handleGoogleLogin} 
              disabled={isLoading}
              className="w-full h-13 rounded-2xl border-white/5 bg-white/[0.02] hover:bg-white/[0.05] text-white font-bold transition-all"
            >
              <svg className="mr-3 h-4 w-4" viewBox="0 0 24 24">
                <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4"/>
                <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
                <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05"/>
                <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/>
              </svg>
              Sign in with Google
            </Button>
          </CardContent>

          <CardFooter className="pb-10 pt-0">
            <p className="text-sm text-center w-full text-white/30 font-medium">
              Don't have an account?{" "}
              <Link to="/signup" className="text-blue-400 hover:text-blue-300 transition-colors font-bold">
                Join now
              </Link>
            </p>
          </CardFooter>
        </Card>
      </motion.div>
    </div>
  );
};

export default Login;
