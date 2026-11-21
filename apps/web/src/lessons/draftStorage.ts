/**
 * Device-local draft of unsaved Board content (Story 2.4). Pure helpers over `localStorage`.
 *
 * A draft exists only while content is unsaved and is removed once the server confirms it, on
 * Discard or Reload latest, and on sign-out or account deletion. Keys are
 * `wt.draft.<userId>.<lessonId>`; values hold only the board and the metadata below.
 * Every storage call is wrapped: unavailable storage means "no draft", never an error.
 */
import { sceneFingerprint, type BoardPayload, type SceneElement } from "./boardSerialize";

export const DRAFT_PREFIX = "wt.draft.";
/** Drafts larger than this (serialized) are skipped silently. */
export const DRAFT_MAX_CHARS = 1_500_000;
export const DRAFT_THROTTLE_MS = 2000;

export type Draft = {
  lesson_id: string;
  user_id: number | string;
  base_revision: number;
  saved_at: string;
  board: BoardPayload;
};

export const draftKey = (userId: number | string, lessonId: string) => `${DRAFT_PREFIX}${userId}.${lessonId}`;

function storage(): Storage | null {
  try {
    return window.localStorage;
  } catch {
    return null;
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function parseDraft(raw: string): Draft | null {
  let data: unknown;
  try {
    data = JSON.parse(raw);
  } catch {
    return null;
  }
  if (!isRecord(data) || !isRecord(data.board)) return null;
  const { lesson_id, user_id, base_revision, saved_at, board } = data;
  if (typeof lesson_id !== "string") return null;
  if (typeof user_id !== "number" && typeof user_id !== "string") return null;
  if (typeof base_revision !== "number" || !Number.isInteger(base_revision) || base_revision < 0) return null;
  if (typeof saved_at !== "string") return null;
  if (board.schema_version !== 1 || !Array.isArray(board.elements)) return null;
  if (!board.elements.every((el) => isRecord(el) && typeof el.id === "string" && typeof el.type === "string")) {
    return null;
  }
  return { lesson_id, user_id, base_revision, saved_at, board: board as unknown as BoardPayload };
}

/**
 * The valid draft for this user and Lesson, or null. A corrupt draft, or one whose `user_id` or
 * `lesson_id` does not match, is ignored and removed.
 */
export function readDraft(userId: number | string, lessonId: string): Draft | null {
  const store = storage();
  if (!store) return null;
  const key = draftKey(userId, lessonId);
  try {
    const raw = store.getItem(key);
    if (raw === null) return null;
    const draft = parseDraft(raw);
    if (!draft || String(draft.user_id) !== String(userId) || draft.lesson_id !== lessonId) {
      store.removeItem(key);
      return null;
    }
    return draft;
  } catch {
    return null;
  }
}

/** Store a draft; returns the stored text, or null when skipped (storage unavailable, too large, quota). */
function writeDraftRaw(draft: Draft): string | null {
  const store = storage();
  if (!store) return null;
  try {
    const raw = JSON.stringify(draft);
    if (raw.length > DRAFT_MAX_CHARS) return null;
    store.setItem(draftKey(draft.user_id, draft.lesson_id), raw);
    return raw;
  } catch {
    return null;
  }
}

/** Store a draft. Returns false when skipped (storage unavailable, too large, quota). */
export function writeDraft(draft: Draft): boolean {
  return writeDraftRaw(draft) !== null;
}

function readRaw(userId: number | string, lessonId: string): string | null {
  try {
    return storage()?.getItem(draftKey(userId, lessonId)) ?? null;
  } catch {
    return null;
  }
}

/** Remove the draft only if it still holds exactly `raw` (another tab may have replaced it). */
function clearDraftIfUnchanged(userId: number | string, lessonId: string, raw: string) {
  try {
    const store = storage();
    const key = draftKey(userId, lessonId);
    if (store?.getItem(key) === raw) store.removeItem(key);
  } catch {
    // Nothing to do.
  }
}

export function clearDraft(userId: number | string, lessonId: string) {
  try {
    storage()?.removeItem(draftKey(userId, lessonId));
  } catch {
    // Nothing to do.
  }
}

/** Remove every draft key (sign-out, account deletion). */
export function clearAllDrafts() {
  const store = storage();
  if (!store) return;
  try {
    const keys: string[] = [];
    for (let i = 0; i < store.length; i += 1) {
      const key = store.key(i);
      if (key?.startsWith(DRAFT_PREFIX)) keys.push(key);
    }
    for (const key of keys) store.removeItem(key);
  } catch {
    // Nothing to do.
  }
}

export type DraftOffer =
  | { kind: "none"; equal?: boolean }
  | { kind: "restore"; draft: Draft }
  | { kind: "stale"; draft: Draft };

/**
 * What to do with a stored draft once the server Board is known: nothing (`equal` when it matches
 * the server content, so the caller deletes it), offer Restore (same base revision), or tell the
 * Learner it can't be merged (the Lesson changed elsewhere).
 */
export function evaluateDraft(
  draft: Draft | null,
  server: { revision: number; elements: readonly unknown[] },
): DraftOffer {
  if (!draft) return { kind: "none" };
  const same =
    sceneFingerprint(draft.board.elements as unknown as SceneElement[]) ===
    sceneFingerprint(server.elements as SceneElement[]);
  if (same) return { kind: "none", equal: true };
  if (draft.base_revision === server.revision) return { kind: "restore", draft };
  return { kind: "stale", draft };
}

type Timers = {
  setTimeout: (fn: () => void, ms: number) => number;
  clearTimeout: (id: number) => void;
};

const realTimers: Timers = {
  setTimeout: (fn, ms) => window.setTimeout(fn, ms),
  clearTimeout: (id) => window.clearTimeout(id),
};

/**
 * Throttled draft writer for one Lesson. `request()` marks content as unsaved-and-unwritten; the
 * write happens at once if the last one was long enough ago, else on a trailing timer. `flush()`
 * writes any pending content now (pagehide, leaving). `clear()` forgets pending content and
 * deletes the draft this writer stored (never one another tab or an earlier session left), and
 * it never overwrites a draft it did not store itself. While `hold` is on (a recovery banner is showing) nothing is written
 * or deleted, so an offered draft is never silently replaced.
 */
export class DraftWriter {
  private pending = false;
  private held = false;
  private lastWrite = Number.NEGATIVE_INFINITY;
  private timer: number | null = null;
  /** Exact text of the draft this writer last stored; only that text is ever deleted by `clear`. */
  private lastRaw: string | null = null;
  private readonly timers: Timers;

  constructor(
    private readonly opts: {
      userId: number | string;
      lessonId: string;
      /** The content and the revision it is based on, or null when it cannot be read now. */
      read: () => { board: BoardPayload; revision: number } | null;
      throttleMs?: number;
      now?: () => number;
      timers?: Timers;
    },
  ) {
    this.timers = opts.timers ?? realTimers;
  }

  private now() {
    return (this.opts.now ?? Date.now)();
  }

  private get throttle() {
    return this.opts.throttleMs ?? DRAFT_THROTTLE_MS;
  }

  hold(on: boolean) {
    this.held = on;
  }

  /** Take over the stored draft (the Learner restored it), so it is replaced and deleted as ours. */
  adopt() {
    this.lastRaw = readRaw(this.opts.userId, this.opts.lessonId);
  }

  request() {
    if (this.held) return;
    this.pending = true;
    if (this.timer !== null) return;
    const wait = this.throttle - (this.now() - this.lastWrite);
    if (wait <= 0) this.write();
    else this.arm(wait);
  }

  flush() {
    this.cancelTimer();
    if (this.pending) this.write();
  }

  clear() {
    if (this.held) return;
    this.cancelTimer();
    this.pending = false;
    const raw = this.lastRaw;
    this.lastRaw = null;
    if (raw !== null) clearDraftIfUnchanged(this.opts.userId, this.opts.lessonId, raw);
  }

  dispose() {
    this.cancelTimer();
  }

  private arm(ms: number) {
    this.timer = this.timers.setTimeout(() => {
      this.timer = null;
      if (this.pending) this.write();
    }, ms);
  }

  private cancelTimer() {
    if (this.timer !== null) this.timers.clearTimeout(this.timer);
    this.timer = null;
  }

  private write() {
    if (this.held) return;
    const content = this.opts.read();
    if (!content) {
      // Mid-draw or loading: look again shortly.
      this.arm(Math.min(this.throttle, 500));
      return;
    }
    this.pending = false;
    // Another tab (or an earlier session) already keeps a draft for this Lesson: never overwrite it.
    const existing = readRaw(this.opts.userId, this.opts.lessonId);
    if (existing !== null && existing !== this.lastRaw) return;
    this.lastWrite = this.now();
    this.lastRaw = writeDraftRaw({
      lesson_id: this.opts.lessonId,
      user_id: this.opts.userId,
      base_revision: content.revision,
      saved_at: new Date().toISOString(),
      board: content.board,
    });
  }
}
