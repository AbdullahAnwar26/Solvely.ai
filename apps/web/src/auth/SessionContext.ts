import { createContext, useContext } from "react";
import type { Schema } from "@solvely/shared";

export type SessionUser = Schema<"RegisteredUser">;

export type SessionState =
  | { status: "loading" }
  | { status: "signedOut" }
  | { status: "signedIn"; user: SessionUser }
  /** `/auth/me/` could not be reached or failed unexpectedly (not a plain "signed out"). */
  | { status: "error"; message: string };

export type SessionContextValue = {
  state: SessionState;
  /** True after the Learner chose Sign out, so the guard does not remember a return route. */
  signedOutByUser: boolean;
  /** Set after the account was deleted, so the sign-in page can say so. */
  accountDeleted: boolean;
  /** Record a successful sign-up or sign-in. */
  signIn: (user: SessionUser) => void;
  /** Calls the logout endpoint, then clears session state. Rejects (staying signed in) on failure. */
  signOut: () => Promise<void>;
  /** The server ended the session by deleting the account; clears state without a logout call. */
  endSessionAfterDeletion: () => void;
  /** Re-run the session bootstrap after a failure. */
  retry: () => void;
};

export const SessionContext = createContext<SessionContextValue | null>(null);

export function useSession(): SessionContextValue {
  const value = useContext(SessionContext);
  if (!value) throw new Error("useSession must be used inside <SessionProvider>");
  return value;
}
