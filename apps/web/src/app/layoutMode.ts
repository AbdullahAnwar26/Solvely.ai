import { useSyncExternalStore } from "react";

/** Breakpoints from EXPERIENCE.md "Responsive & Platform". */
export const LAPTOP_QUERY = "(min-width: 1200px)";
export const TABLET_QUERY = "(min-width: 768px)";

/**
 * docked: laptop, sidebar beside content, collapsible to an icon rail (remembered).
 * rail:   tablet, icon rail; the full sidebar opens as a sheet on demand.
 * drawer: phone, top bar with a menu button; the sidebar opens as a drawer.
 */
export type LayoutMode = "docked" | "rail" | "drawer";

function matches(query: string): boolean {
  return typeof window.matchMedia === "function" && window.matchMedia(query).matches;
}

export function getLayoutMode(): LayoutMode {
  // Without matchMedia (very old engines, some test setups) fall back to the laptop layout.
  if (typeof window.matchMedia !== "function") return "docked";
  if (matches(LAPTOP_QUERY)) return "docked";
  if (matches(TABLET_QUERY)) return "rail";
  return "drawer";
}

function subscribe(onChange: () => void): () => void {
  if (typeof window.matchMedia !== "function") return () => undefined;
  const lists = [LAPTOP_QUERY, TABLET_QUERY].map((query) => window.matchMedia(query));
  lists.forEach((list) => list.addEventListener("change", onChange));
  return () => lists.forEach((list) => list.removeEventListener("change", onChange));
}

export function useLayoutMode(): LayoutMode {
  return useSyncExternalStore(subscribe, getLayoutMode, () => "docked");
}
