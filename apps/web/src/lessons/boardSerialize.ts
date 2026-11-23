/**
 * Pure helpers turning the Excalidraw scene into the saved Board payload and back (Story 2.3).
 *
 * The payload mirrors the server's strict validator (`apps/api/lessons/board.py`): only
 * `schema_version`, `elements` and a minimal `app_state` (`viewBackgroundColor`, `scrollX`,
 * `scrollY`, `zoom`). Binary files are never saved, and element types the server does not accept
 * (images, embeds) are dropped here rather than failing every save.
 */
import type { Schema } from "@solvely/shared";

export type BoardPayload = Schema<"BoardPayload">;
export type BoardState = Schema<"BoardState">;
export type BoardAppState = Schema<"BoardAppState">;

export const BOARD_SCHEMA_VERSION = 1;

/** Mirrors `core.limits.BOARD_ELEMENT_TYPES` on the server. */
export const SAVED_ELEMENT_TYPES: ReadonlySet<string> = new Set([
  "rectangle",
  "diamond",
  "ellipse",
  "arrow",
  "line",
  "freedraw",
  "text",
  "frame",
]);

/** The element fields these helpers read; real Excalidraw elements carry many more. */
export type SceneElement = {
  readonly id: string;
  readonly type: string;
  readonly version: number;
  readonly isDeleted?: boolean;
};

/** The appState fields the Board saves. */
export type SceneAppState = {
  readonly viewBackgroundColor?: string;
  readonly scrollX?: number;
  readonly scrollY?: number;
  readonly zoom?: { readonly value: number };
};

/** Live elements of a savable type, in scene order. */
export function savableElements<E extends SceneElement>(elements: readonly E[]): E[] {
  return elements.filter((el) => !el.isDeleted && SAVED_ELEMENT_TYPES.has(el.type));
}

/**
 * Cheap identity of the saved content: ids and versions of the savable elements, in order.
 * Excalidraw bumps `version` on every element change, so equal fingerprints mean nothing to save.
 * Viewport-only changes (pan, zoom) do not change it and so never trigger a save on their own.
 */
export function sceneFingerprint(elements: readonly SceneElement[]): string {
  let out = "";
  for (const el of elements) {
    if (el.isDeleted || !SAVED_ELEMENT_TYPES.has(el.type)) continue;
    out += `${el.id}:${el.version}|`;
  }
  return out;
}

/**
 * Cheap dirty check for `onChange` (Story 2.4): the sum of `version + 1` over live savable
 * elements. O(n), no strings and no allocation per element. Selection and viewport changes never
 * change it; any add, edit or delete does (a delete drops the element's term).
 */
export function contentToken(elements: readonly SceneElement[]): number {
  let sum = 0;
  for (const el of elements) {
    if (el.isDeleted || !SAVED_ELEMENT_TYPES.has(el.type)) continue;
    sum += el.version + 1;
  }
  return sum;
}

function finite(value: unknown): value is number {
  return typeof value === "number" && Number.isFinite(value);
}

/** Build the payload sent to `PUT /lessons/{id}/board/`. */
export function serializeBoard(elements: readonly SceneElement[], appState: SceneAppState): BoardPayload {
  const app_state: BoardAppState = {};
  if (typeof appState.viewBackgroundColor === "string") app_state.viewBackgroundColor = appState.viewBackgroundColor;
  if (finite(appState.scrollX)) app_state.scrollX = appState.scrollX;
  if (finite(appState.scrollY)) app_state.scrollY = appState.scrollY;
  if (appState.zoom && finite(appState.zoom.value)) app_state.zoom = { value: appState.zoom.value };
  return {
    schema_version: BOARD_SCHEMA_VERSION,
    // Excalidraw elements are plain JSON-safe objects; the server validates every field.
    elements: savableElements(elements) as unknown as BoardPayload["elements"],
    app_state,
  };
}

/** The appState to start from (or reset to) for a loaded Board. */
export function initialAppState(board: BoardPayload): SceneAppState & { viewBackgroundColor: string } {
  const saved = board.app_state ?? {};
  return {
    // Transparent by default so the page's `--color-board` token shows in both themes.
    viewBackgroundColor: saved.viewBackgroundColor ?? "transparent",
    ...(finite(saved.scrollX) ? { scrollX: saved.scrollX } : {}),
    ...(finite(saved.scrollY) ? { scrollY: saved.scrollY } : {}),
    // A zoom outside Excalidraw's range is ignored: default view.
    ...(saved.zoom && finite(saved.zoom.value) && saved.zoom.value >= 0.1 && saved.zoom.value <= 30
      ? { zoom: { value: saved.zoom.value } }
      : {}),
  };
}
