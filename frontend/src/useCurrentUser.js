import { useCallback, useEffect, useState } from "react";

const KEY = "fitness-challenge:userId";

function read() {
  try { return localStorage.getItem(KEY); } catch { return null; }
}

// The "who am I" choice is a per-browser convenience; there is no auth in scope.
export function useCurrentUser() {
  const [userId, setUserId] = useState(read);
  useEffect(() => {
    const onStorage = (e) => e.key === KEY && setUserId(e.newValue);
    window.addEventListener("storage", onStorage);
    return () => window.removeEventListener("storage", onStorage);
  }, []);
  const set = useCallback((id) => {
    try { id ? localStorage.setItem(KEY, id) : localStorage.removeItem(KEY); } catch { /* private mode */ }
    setUserId(id);
  }, []);
  return [userId, set];
}
