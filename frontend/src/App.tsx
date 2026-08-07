import { lazy, Suspense } from "react";
import { BrowserRouter as Router, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider, useAuth } from "./contexts/AuthContext";
import { ChatHistoryProvider } from "./contexts/ChatHistoryContext";
import { ToastProvider } from "./components/Toast";
import MainLayout from "./layout/MainLayout";

const Landing = lazy(() => import("./pages/Landing"));
const Login = lazy(() => import("./pages/Login"));
const Signup = lazy(() => import("./pages/Signup"));
const Chat = lazy(() => import("./pages/Chat"));
const Settings = lazy(() => import("./pages/Settings"));

const ProtectedRoute = ({ children }: { children: React.ReactNode }) => {
  const { user, loading } = useAuth();

  if (loading) {
    return <div className="h-screen w-screen flex items-center justify-center bg-background text-foreground">Loading...</div>;
  }

  if (!user) {
    return <Navigate to="/login" />;
  }

  return <>{children}</>;
};

function App() {
  return (
    <ToastProvider>
      <AuthProvider>
        <Router>
          <Suspense
            fallback={
              <div className="h-screen w-screen flex items-center justify-center bg-background text-foreground">
                Loading...
              </div>
            }
          >
            <Routes>
              <Route path="/" element={<Landing />} />
              <Route path="/login" element={<Login />} />
              <Route path="/signup" element={<Signup />} />
              <Route
                path="/chat"
                element={
                  <ProtectedRoute>
                    <ChatHistoryProvider>
                      <MainLayout>
                        <Chat />
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
                        <Settings />
                      </MainLayout>
                    </ChatHistoryProvider>
                  </ProtectedRoute>
                }
              />
              <Route path="*" element={<Navigate to="/" />} />
            </Routes>
          </Suspense>
        </Router>
      </AuthProvider>
    </ToastProvider>
  );
}

export default App;
