import { createContext, useContext } from "react";
import type { ThemePreference } from "./themeStorage";

export type ThemeContextValue = {
  preference: ThemePreference;
  /** Applies the choice at once and saves it; reverts and rejects if saving fails. */
  setPreference: (next: ThemePreference) => Promise<void>;
};

export const ThemeContext = createContext<ThemeContextValue | null>(null);

export function useTheme(): ThemeContextValue {
  const value = useContext(ThemeContext);
  if (!value) throw new Error("useTheme must be used inside <ThemeProvider>");
  return value;
}
