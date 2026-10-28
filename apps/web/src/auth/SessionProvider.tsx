import { useCallback, useEffect, useMemo, useState, type ReactNode } from "react";
import { ApiError } from "../api/client";
import { fetchCurrentUser, logout, NETWORK_MESSAGE, UNEXPECTED_MESSAGE } from "./authApi";
import { SessionContext, type SessionContextValue, type SessionState, type SessionUser } from "./SessionContext";

/**
 * Session state comes only from `GET /auth/me/` on load (403 means signed out).
 * It is held in memory: no tokens, emails or flags are written to browser storage.
 */
export function SessionProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<SessionState>({ status: "loading" });
  const [signedOutByUser, setSignedOutByUser] = useState(false);
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    fetchCurrentUser(controller.signal).then(
      (user) => {
        if (!controller.signal.aborted) setState({ status: "signedIn", user });
      },
      (error: unknown) => {
        if (controller.signal.aborted) return;
        if (error instanceof ApiError && (error.status === 403 || error.status === 401)) {
          setState({ status: "signedOut" });
        } else if (error instanceof ApiError && error.code === "network_error") {
          setState({ status: "error", message: NETWORK_MESSAGE });
        } else {
          setState({ status: "error", message: UNEXPECTED_MESSAGE });
        }
      },
    );
    return () => controller.abort();
  }, [attempt]);

  const signIn = useCallback((user: SessionUser) => {
    setSignedOutByUser(false);
    setState({ status: "signedIn", user });
  }, []);

  const signOut = useCallback(async () => {
    await logout();
    setSignedOutByUser(true);
    setState({ status: "signedOut" });
  }, []);

  const retry = useCallback(() => {
    setState({ status: "loading" });
    setAttempt((n) => n + 1);
  }, []);

  const value = useMemo<SessionContextValue>(
    () => ({ state, signedOutByUser, signIn, signOut, retry }),
    [state, signedOutByUser, signIn, signOut, retry],
  );

  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>;
}
