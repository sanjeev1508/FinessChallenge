import { useCallback, useEffect, useState } from "react";
import { hasAccessToken } from "./api.js";

const KEY = "fitness-challenge:userId";

function read() {
  try {
    if (!hasAccessToken()) {
      localStorage.removeItem(KEY);
      return null;
    }
    return localStorage.getItem(KEY);
  } catch { return null; }
}

// Keep the signed-in user's ID in sync across page reloads and browser tabs.
export function useCurrentUser() {
  const [userId, setUserId] = useState(read);
  useEffect(() => {
    const onStorage = (e) => e.key === KEY && setUserId(e.newValue);
    const onAuthExpired = () => setUserId(null);
    window.addEventListener("storage", onStorage);
    window.addEventListener("fitness-auth-expired", onAuthExpired);
    return () => {
      window.removeEventListener("storage", onStorage);
      window.removeEventListener("fitness-auth-expired", onAuthExpired);
    };
  }, []);
  const set = useCallback((id) => {
    try { id ? localStorage.setItem(KEY, id) : localStorage.removeItem(KEY); } catch { /* private mode */ }
    setUserId(id);
  }, []);
  return [userId, set];
}
