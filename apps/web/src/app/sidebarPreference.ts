// Sidebar collapsed state, remembered per device (EXPERIENCE.md Navigation).
// Storage can be unavailable (private mode, blocked site data): fall back to the default.

export const SIDEBAR_STORAGE_KEY = "wt.sidebar.collapsed";

export function readSidebarCollapsed(): boolean {
  try {
    return window.localStorage.getItem(SIDEBAR_STORAGE_KEY) === "1";
  } catch {
    return false;
  }
}

export function writeSidebarCollapsed(collapsed: boolean): void {
  try {
    window.localStorage.setItem(SIDEBAR_STORAGE_KEY, collapsed ? "1" : "0");
  } catch {
    // Not persisted; the in-memory state still applies for this visit.
  }
}
