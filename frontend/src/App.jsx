import { useEffect, useState } from "react";
import { setAuthToken } from "./api.js";
import AuthScreen from "./components/AuthScreen.jsx";
import Shell from "./components/Shell.jsx";

const STORAGE_KEY = "ekip_session";

export default function App() {
  const [session, setSession] = useState(null);
  const [ready, setReady] = useState(false);

  // Restore a previous session from localStorage on load, so refreshing the
  // page doesn't force a re-login.
  useEffect(() => {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) {
      const parsed = JSON.parse(stored);
      setAuthToken(parsed.access_token);
      setSession(parsed);
    }
    setReady(true);
  }, []);

  function handleAuthenticated(result) {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(result));
    setAuthToken(result.access_token);
    setSession(result);
  }

  function handleLogout() {
    localStorage.removeItem(STORAGE_KEY);
    setAuthToken(null);
    setSession(null);
  }

  if (!ready) return null;

  return session ? (
    <Shell session={session} onLogout={handleLogout} />
  ) : (
    <AuthScreen onAuthenticated={handleAuthenticated} />
  );
}
