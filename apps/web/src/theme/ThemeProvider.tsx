import { useCallback, useLayoutEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { updateThemePreference } from "../auth/authApi";
import { useSession } from "../auth/SessionContext";
import { ThemeContext, type ThemeContextValue } from "./ThemeContext";
import { applyTheme, readThemeHint, writeThemeHint, type ThemePreference } from "./themeStorage";

/**
 * Starts from the device hint (the same value the inline script applied before first paint),
 * then the server value wins once the session loads. Must sit inside <SessionProvider>.
 */
export function ThemeProvider({ children }: { children: ReactNode }) {
  const { state } = useSession();
  const [preference, setLocal] = useState<ThemePreference>(readThemeHint);
  const latest = useRef(0);

  const serverUserId = state.status === "signedIn" ? state.user.id : null;
  const serverValue = state.status === "signedIn" ? state.user.theme_preference : null;

  // The server value wins whenever a session (or its stored value) arrives: adjust state
  // during render instead of in an effect.
  const serverKey = serverValue === null ? null : `${serverUserId}:${serverValue}`;
  const [syncedKey, setSyncedKey] = useState<string | null>(null);
  if (serverKey !== syncedKey) {
    setSyncedKey(serverKey);
    if (serverValue !== null) setLocal(serverValue);
  }

  useLayoutEffect(() => {
    applyTheme(preference);
    writeThemeHint(preference);
  }, [preference]);

  const setPreference = useCallback(
    async (next: ThemePreference) => {
      const request = ++latest.current;
      const previous = preference;
      setLocal(next);
      try {
        await updateThemePreference(next);
      } catch (error) {
        // Only the newest request may revert, so a late failure cannot undo a later choice.
        if (request === latest.current) setLocal(previous);
        throw error;
      }
    },
    [preference],
  );

  const value = useMemo<ThemeContextValue>(() => ({ preference, setPreference }), [preference, setPreference]);
  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}
