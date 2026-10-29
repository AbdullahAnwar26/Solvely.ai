import type { Schema } from "@solvely/shared";

export type ThemePreference = Schema<"ThemePreferenceEnum">;

export const THEME_OPTIONS: readonly ThemePreference[] = ["system", "light", "dark"];

/** Non-sensitive device hint, read by the inline script in index.html before first paint. */
export const THEME_HINT_KEY = "wt.theme";

export function isThemePreference(value: unknown): value is ThemePreference {
  return value === "system" || value === "light" || value === "dark";
}

export function readThemeHint(): ThemePreference {
  try {
    const value = window.localStorage.getItem(THEME_HINT_KEY);
    return isThemePreference(value) ? value : "system";
  } catch {
    return "system";
  }
}

export function writeThemeHint(value: ThemePreference): void {
  try {
    window.localStorage.setItem(THEME_HINT_KEY, value);
  } catch {
    // Storage unavailable: the server value is applied after the session loads.
  }
}

/** `data-theme` is set for light/dark only; "system" removes it so the OS setting decides. */
export function applyTheme(value: ThemePreference): void {
  const root = document.documentElement;
  if (value === "system") root.removeAttribute("data-theme");
  else root.setAttribute("data-theme", value);
}
