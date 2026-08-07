import { initializeApp } from "firebase/app";
import { getAuth } from "firebase/auth";

// Firebase web app configuration.
// All values come from environment variables (see .env.example) so no
// real keys are committed to the repository.
const firebaseConfig = {
  apiKey: import.meta.env.VITE_FIREBASE_API_KEY || "placeholder-api-key",
  authDomain: import.meta.env.VITE_FIREBASE_AUTH_DOMAIN || "placeholder-auth-domain",
  projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID || "placeholder-project-id",
  storageBucket: import.meta.env.VITE_FIREBASE_STORAGE_BUCKET || "placeholder-storage-bucket",
  messagingSenderId: import.meta.env.VITE_FIREBASE_MESSAGING_SENDER_ID || "placeholder-messaging-sender-id",
  appId: import.meta.env.VITE_FIREBASE_APP_ID || "placeholder-app-id"
};

const app = initializeApp(firebaseConfig);

export const auth = getAuth(app);

export default app;
