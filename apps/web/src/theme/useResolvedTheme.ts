import { useSyncExternalStore } from "react";
import { useTheme } from "./ThemeContext";

const DARK_QUERY = "(prefers-color-scheme: dark)";

function subscribe(onChange: () => void): () => void {
  if (typeof window.matchMedia !== "function") return () => undefined;
  const list = window.matchMedia(DARK_QUERY);
  list.addEventListener("change", onChange);
  return () => list.removeEventListener("change", onChange);
}

function systemPrefersDark(): boolean {
  return typeof window.matchMedia === "function" && window.matchMedia(DARK_QUERY).matches;
}

/** The theme actually in effect: the Learner's choice, or the OS setting for "system". */
export function useResolvedTheme(): "light" | "dark" {
  const { preference } = useTheme();
  const systemDark = useSyncExternalStore(subscribe, systemPrefersDark, () => false);
  if (preference === "system") return systemDark ? "dark" : "light";
  return preference;
}
