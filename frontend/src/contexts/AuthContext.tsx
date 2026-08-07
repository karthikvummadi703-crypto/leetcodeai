/* oxlint-disable react/only-export-components */
import React, { createContext, useContext, useEffect, useState } from "react";
import type { User } from "firebase/auth";
import {
  onAuthStateChanged,
  GoogleAuthProvider,
  signInWithPopup,
  signInWithEmailAndPassword,
  createUserWithEmailAndPassword,
  sendPasswordResetEmail,
  signOut as firebaseSignOut,
} from "firebase/auth";
import { auth } from "../firebase/firebase";

interface AuthContextType {
  user: User | null;
  loading: boolean;
  signInWithGoogle: () => Promise<void>;
  signInWithEmail: (email: string, password: string) => Promise<void>;
  signUpWithEmail: (email: string, password: string) => Promise<void>;
  resetPassword: (email: string) => Promise<void>;
  signOut: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType>({
  user: null,
  loading: true,
  signInWithGoogle: async () => {},
  signInWithEmail: async () => {},
  signUpWithEmail: async () => {},
  resetPassword: async () => {},
  signOut: async () => {},
});

export const useAuth = () => useContext(AuthContext);

/** Map Firebase auth error codes to user-friendly messages. */
export function getAuthErrorMessage(error: unknown): string {
  const code =
    typeof error === "object" && error !== null && "code" in error
      ? String((error as { code: unknown }).code)
      : "";
  switch (code) {
    case "auth/invalid-email":
      return "Please enter a valid email address.";
    case "auth/user-not-found":
    case "auth/wrong-password":
      return "Incorrect email or password.";
    case "auth/email-already-in-use":
      return "An account with this email already exists. Try signing in.";
    case "auth/weak-password":
      return "Password is too weak. Use at least 6 characters.";
    case "auth/too-many-requests":
      return "Too many attempts. Please wait a moment and try again.";
    case "auth/network-request-failed":
      return "Network error. Please check your connection.";
    case "auth/popup-closed-by-user":
      return "Sign-in popup was closed before completing.";
    case "auth/popup-blocked":
      return "Sign-in popup was blocked. Allow popups for this site and try again.";
    case "auth/operation-not-allowed":
      return "This sign-in method is not enabled. Please contact the administrator.";
    default:
      return "Something went wrong. Please try again.";
  }
}

export const AuthProvider = ({ children }: { children: React.ReactNode }) => {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const unsubscribe = onAuthStateChanged(auth, (currentUser) => {
      setUser(currentUser);
      setLoading(false);
    });

    return () => unsubscribe();
  }, []);

  const signInWithGoogle = async () => {
    const provider = new GoogleAuthProvider();
    await signInWithPopup(auth, provider);
  };

  const signInWithEmail = async (email: string, password: string) => {
    await signInWithEmailAndPassword(auth, email.trim(), password);
  };

  const signUpWithEmail = async (email: string, password: string) => {
    await createUserWithEmailAndPassword(auth, email.trim(), password);
  };

  const resetPassword = async (email: string) => {
    await sendPasswordResetEmail(auth, email.trim());
  };

  const signOut = async () => {
    await firebaseSignOut(auth);
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        loading,
        signInWithGoogle,
        signInWithEmail,
        signUpWithEmail,
        resetPassword,
        signOut,
      }}
    >
      {!loading && children}
    </AuthContext.Provider>
  );
};
