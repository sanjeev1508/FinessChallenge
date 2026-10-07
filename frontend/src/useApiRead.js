import { useEffect, useMemo, useState } from "react";
import { createLatestRequest } from "./latestRequest.js";

export function useApiRead(request, enabled = true) {
  const [state, setState] = useState(null);
  const runner = useMemo(() => createLatestRequest(
    request,
    (data) => setState({ request, data, error: null }),
    (error) => setState((previous) => ({
      request, data: previous?.request === request ? previous.data : null, error,
    })),
  ), [request]);

  useEffect(() => {
    if (enabled) runner.run();
    return () => runner.cancel();
  }, [runner, enabled]);

  // Hide data from another user/window before effect cleanup has run.
  const visible = enabled && state?.request === request ? state : null;
  return { data: visible?.data ?? null, error: visible?.error ?? null, load: runner.run };
}
