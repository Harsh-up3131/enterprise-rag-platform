import { useEffect, useState } from "react";
import { setAuthToken } from "./api.js";
import AuthScreen from "./components/AuthScreen.jsx";
import Shell from "./components/Shell.jsx";

const STORAGE_KEY = "ekip_session";

export default function App() {
  const [session, setSession] = useState(null);
  const [ready, setReady] = useState(false);
  const [offline, setOffline] = useState(!navigator.onLine);

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

  useEffect(() => {
    const onOnline = () => setOffline(false);
    const onOffline = () => setOffline(true);

    window.addEventListener("online", onOnline);
    window.addEventListener("offline", onOffline);

    return () => {
      window.removeEventListener("online", onOnline);
      window.removeEventListener("offline", onOffline);
    };
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

  return (
    <>
      {offline && (
        <div className="offline-banner">
          You’re offline. Cached session data is still available, but network-backed actions will be unavailable until you reconnect.
        </div>
      )}
      {session ? (
        <Shell session={session} onLogout={handleLogout} />
      ) : (
        <AuthScreen onAuthenticated={handleAuthenticated} />
      )}
    </>
  );
}
