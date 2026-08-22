import { lazy, Suspense, useState } from "react";
import { BrowserRouter as Router, Routes, Route, Navigate, useLocation, useNavigate } from "react-router-dom";
import { AnimatePresence } from "framer-motion";
import { AuthProvider, useAuth } from "./contexts/AuthContext";
import { ChatHistoryProvider } from "./contexts/ChatHistoryContext";
import { ToastProvider } from "./components/Toast";
import MainLayout from "./layout/MainLayout";
import IntroSplash from "./components/IntroSplash";
import PageTransition from "./components/PageTransition";

const Landing = lazy(() => import("./pages/Landing"));
const Login = lazy(() => import("./pages/Login"));
const Signup = lazy(() => import("./pages/Signup"));
const Chat = lazy(() => import("./pages/Chat"));
const Settings = lazy(() => import("./pages/Settings"));
const LeetCode = lazy(() => import("./pages/LeetCode"));

const ProtectedRoute = ({ children }: { children: React.ReactNode }) => {
  const { user, loading } = useAuth();

  if (loading) {
    return <div className="h-screen w-screen flex items-center justify-center bg-[#05070D] text-white">Loading...</div>;
  }

  if (!user) {
    return <Navigate to="/login" />;
  }

  return <>{children}</>;
};

function AnimatedRoutes() {
  const location = useLocation();

  return (
    <AnimatePresence mode="wait">
      <Routes location={location} key={location.pathname}>
        <Route path="/" element={<PageTransition><Landing /></PageTransition>} />
        <Route path="/login" element={<PageTransition><Login /></PageTransition>} />
        <Route path="/signup" element={<PageTransition><Signup /></PageTransition>} />
        <Route
          path="/chat"
          element={
            <ProtectedRoute>
              <ChatHistoryProvider>
                <MainLayout>
                  <PageTransition><Chat /></PageTransition>
                </MainLayout>
              </ChatHistoryProvider>
            </ProtectedRoute>
          }
        />
        <Route
          path="/settings"
          element={
            <ProtectedRoute>
              <ChatHistoryProvider>
                <MainLayout>
                  <PageTransition><Settings /></PageTransition>
                </MainLayout>
              </ChatHistoryProvider>
            </ProtectedRoute>
          }
        />
        <Route
          path="/progress"
          element={
            <ProtectedRoute>
              <ChatHistoryProvider>
                <MainLayout>
                  <PageTransition><LeetCode /></PageTransition>
                </MainLayout>
              </ChatHistoryProvider>
            </ProtectedRoute>
          }
        />
        <Route path="*" element={<Navigate to="/" />} />
      </Routes>
    </AnimatePresence>
  );
}

function AppContent() {
  const [hasEntered, setHasEntered] = useState(() => {
    return sessionStorage.getItem("leetcode-ai-entered") === "true";
  });
  const navigate = useNavigate();

  const handleEnter = () => {
    setHasEntered(true);
    sessionStorage.setItem("leetcode-ai-entered", "true");
    navigate("/login");
  };

  if (!hasEntered) {
    return <IntroSplash onComplete={handleEnter} />;
  }

  return (
    <Suspense
      fallback={
        <div className="h-screen w-screen flex items-center justify-center bg-[#05070D] text-white">
          Loading...
        </div>
      }
    >
      <AnimatedRoutes />
    </Suspense>
  );
}

function App() {
  return (
    <ToastProvider>
      <AuthProvider>
        <Router>
          <AppContent />
        </Router>
      </AuthProvider>
    </ToastProvider>
  );
}

export default App;
