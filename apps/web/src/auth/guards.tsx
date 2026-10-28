import { Suspense, type ReactNode } from "react";
import { Navigate, Outlet, useLocation } from "react-router";
import { useSession } from "./SessionContext";
import { SessionProvider } from "./SessionProvider";
import "./auth.css";

/** A Learner is only sent back to an in-app path, never to an auth route. */
const AUTH_PATHS = ["/sign-in", "/sign-up", "/forgot-password", "/reset-password"];

type ReturnTo = { pathname: string; search: string; hash: string };

function readReturnTo(state: unknown): ReturnTo | null {
  if (typeof state !== "object" || state === null || !("from" in state)) return null;
  const from = (state as { from: unknown }).from;
  if (typeof from !== "object" || from === null) return null;
  const { pathname, search, hash } = from as Partial<ReturnTo>;
  if (typeof pathname !== "string" || !pathname.startsWith("/") || pathname.startsWith("//")) return null;
  if (AUTH_PATHS.includes(pathname)) return null;
  return {
    pathname,
    search: typeof search === "string" ? search : "",
    hash: typeof hash === "string" ? hash : "",
  };
}

function SessionStatusScreen() {
  const { state, retry } = useSession();
  if (state.status === "error") {
    return (
      <main className="auth-page" id="main">
        <div className="auth-card">
          <h1>We couldn't check your session</h1>
          <p role="alert">{state.message}</p>
          <button type="button" className="button button-primary" onClick={retry}>
            Try again
          </button>
        </div>
      </main>
    );
  }
  return (
    <p role="status" className="visually-hidden">
      Loading
    </p>
  );
}

function SessionGate({ children }: { children: (signedIn: boolean) => ReactNode }) {
  const { state } = useSession();
  if (state.status === "loading" || state.status === "error") return <SessionStatusScreen />;
  return <>{children(state.status === "signedIn")}</>;
}

/** Root route element: provides the session to the whole route tree. */
export function SessionRoot() {
  return (
    <SessionProvider>
      <Suspense
        fallback={
          <p role="status" className="visually-hidden">
            Loading
          </p>
        }
      >
        <Outlet />
      </Suspense>
    </SessionProvider>
  );
}

/** App routes: signed-out visitors go to /sign-in and return to the requested route afterwards. */
export function RequireAuth() {
  const location = useLocation();
  const { signedOutByUser } = useSession();
  const from = { pathname: location.pathname, search: location.search, hash: location.hash };
  return (
    <SessionGate>
      {(signedIn) =>
        signedIn ? (
          <Outlet />
        ) : (
          <Navigate to="/sign-in" replace state={signedOutByUser ? undefined : { from }} />
        )
      }
    </SessionGate>
  );
}

/** Sign-up, sign-in, forgot-password: signed-in Learners go to where they were heading, or home. */
export function RedirectIfSignedIn() {
  const location = useLocation();
  return (
    <SessionGate>
      {(signedIn) =>
        signedIn ? <Navigate to={readReturnTo(location.state) ?? "/"} replace /> : <Outlet />
      }
    </SessionGate>
  );
}

/** Reset-password only waits for the session check: a reset link must work even when signed in. */
export function WaitForSession() {
  return <SessionGate>{() => <Outlet />}</SessionGate>;
}
