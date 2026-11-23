/**
 * Board autosave (Story 2.3, AD-4): a small state machine plus the React hook that drives it.
 *
 * - A change only (re)arms a debounce timer; nothing is serialized per frame. When the timer
 *   fires, the scene is serialized once and its element fingerprint compared with the last saved
 *   one, so unchanged scenes (pans, selections) are never sent.
 * - Exactly one save is in flight. Changes during a save are coalesced into one follow-up save.
 * - Every save carries the base revision it was built on. A new `save_id` is used for new
 *   content; a retry of the same content reuses its `save_id`, so a retried request that did
 *   reach the server cannot create a second revision.
 * - Retryable failures (network, 5xx, 429) retry with capped exponential backoff, then stay in
 *   "error" until the Learner presses Retry. Other failures go straight to manual retry.
 * - A 409 stops autosaving for good ("conflict"): nothing is retried and nothing overwritten.
 * - "saved" is shown only after the server confirmed the content (or it was just loaded).
 */
import { useCallback, useEffect, useLayoutEffect, useRef, useState } from "react";
import { ApiError } from "../api/client";
import { REVISION_CONFLICT, type BoardSaveRequest, type BoardSaveResponse } from "./boardApi";
import type { BoardPayload } from "./boardSerialize";
import { DraftWriter } from "./draftStorage";

export const AUTOSAVE_DEBOUNCE_MS = 1500;
export const AUTOSAVE_RETRY_BASE_MS = 2000;
export const AUTOSAVE_RETRY_MAX_MS = 16000;
/** Automatic retries after a failed save before the Learner must press Retry. */
export const AUTOSAVE_MAX_AUTO_RETRIES = 3;

/** "unsaved": a real content change happened and no save has started yet (Story 2.4). */
export type SaveStatus = "saved" | "unsaved" | "saving" | "error" | "conflict";

/** `token` is the cheap `contentToken` of the scene (optional: only used for dirty detection). */
export type Snapshot = { board: BoardPayload; fingerprint: string; token?: number };

/** The device-local draft, as seen by the controller (see `DraftWriter`). */
export type DraftSink = { request: () => void; flush: () => void; clear: () => void };

export type AutosaveView = {
  status: SaveStatus;
  /** True while an automatic retry is scheduled (status "error"). */
  retrying: boolean;
};

type Timers = {
  setTimeout: (fn: () => void, ms: number) => number;
  clearTimeout: (id: number) => void;
};

export type AutosaveDeps = {
  save: (body: BoardSaveRequest) => Promise<BoardSaveResponse>;
  /** Current savable scene, or null when it cannot be saved right now (loading, mid-draw). */
  snapshot: () => Snapshot | null;
  newSaveId: () => string;
  onView: (view: AutosaveView) => void;
  draft?: DraftSink;
  timers?: Timers;
};

export type AutosaveOptions = {
  debounceMs?: number;
  retryBaseMs?: number;
  retryMaxMs?: number;
  maxAutoRetries?: number;
};

const defaultTimers: Timers = {
  setTimeout: (fn, ms) => window.setTimeout(fn, ms),
  clearTimeout: (id) => window.clearTimeout(id),
};

function isConflict(error: unknown) {
  return error instanceof ApiError && (error.status === 409 || error.code === REVISION_CONFLICT);
}

/** Network failures, 5xx and 429 are worth retrying automatically; other 4xx are not. */
function isRetryable(error: unknown) {
  if (!(error instanceof ApiError)) return true;
  return error.retryable || error.status === 0 || error.status === 429 || error.status >= 500;
}

export class AutosaveController {
  private readonly deps: AutosaveDeps;
  private readonly timers: Timers;
  private readonly debounceMs: number;
  private readonly retryBaseMs: number;
  private readonly retryMaxMs: number;
  private readonly maxAutoRetries: number;

  private revision: number;
  private savedFingerprint: string;
  private savedToken: number | undefined;
  private status: SaveStatus = "saved";
  private timer: number | null = null;
  private retryScheduled = false;
  private inFlight = false;
  private queued = false;
  private failures = 0;
  private manualOnly = false;
  private paused = false;
  private disposed = false;
  private lastAttempt: { fingerprint: string; saveId: string } | null = null;
  /** Content captured on leave while a save was in flight; sent once that save settles. */
  private finalSnapshot: Snapshot | null = null;

  constructor(
    deps: AutosaveDeps,
    initial: { revision: number; fingerprint: string; token?: number },
    options: AutosaveOptions = {},
  ) {
    this.deps = deps;
    this.timers = deps.timers ?? defaultTimers;
    this.debounceMs = options.debounceMs ?? AUTOSAVE_DEBOUNCE_MS;
    this.retryBaseMs = options.retryBaseMs ?? AUTOSAVE_RETRY_BASE_MS;
    this.retryMaxMs = options.retryMaxMs ?? AUTOSAVE_RETRY_MAX_MS;
    this.maxAutoRetries = options.maxAutoRetries ?? AUTOSAVE_MAX_AUTO_RETRIES;
    this.revision = initial.revision;
    this.savedFingerprint = initial.fingerprint;
    this.savedToken = initial.token;
  }

  get currentRevision() {
    return this.revision;
  }

  get currentStatus() {
    return this.status;
  }

  /**
   * The scene changed. Cheap: compares the content token and (re)arms the debounce timer. A
   * different token while "saved" flips the label to "unsaved" at once; a pan, zoom or selection
   * (same token) changes nothing and starts no save.
   */
  notifyChange(token?: number) {
    if (this.disposed || this.paused) return;
    if (this.status === "conflict" || this.status === "error") {
      // While failing, the retry schedule (or the manual Retry) decides when to try again, but
      // the content on this device is still unsaved.
      this.deps.draft?.request();
      return;
    }
    if (this.status === "saved" && token !== undefined) {
      if (token === this.savedToken && this.timer === null) return;
      if (token !== this.savedToken) this.setStatus("unsaved");
    }
    if (this.status !== "saved") this.deps.draft?.request();
    this.arm(this.debounceMs);
  }

  /** Content was replaced from outside (draft restored): treat it as an unsaved change. */
  markUnsaved() {
    if (this.disposed || this.paused || this.status === "conflict" || this.status === "error") return;
    if (this.status === "saved") this.setStatus("unsaved");
    this.deps.draft?.request();
    this.arm(this.debounceMs);
  }

  /** Write any pending device draft now (pagehide, beforeunload). */
  flushDraft() {
    this.deps.draft?.flush();
  }

  /** Learner pressed Retry: try now, with a fresh automatic-retry budget. */
  retry() {
    if (this.disposed || this.paused || this.status === "conflict" || this.inFlight) return;
    this.failures = 0;
    this.manualOnly = false;
    this.flush();
  }

  /** Stop saving (for example while the latest revision is being reloaded). */
  pause() {
    this.paused = true;
    this.clearTimer();
  }

  /** A new revision was loaded into the scene: start again from it, clean. */
  reset(revision: number, fingerprint: string, token?: number) {
    this.clearTimer();
    this.revision = revision;
    this.savedFingerprint = fingerprint;
    this.savedToken = token;
    this.lastAttempt = null;
    this.failures = 0;
    this.manualOnly = false;
    this.queued = false;
    this.paused = false;
    this.setStatus("saved");
  }

  /** True when leaving now could lose work (used by the `beforeunload` guard). */
  hasUnsavedChanges() {
    if (this.status !== "saved" || this.inFlight) return true;
    if (this.timer === null) return false;
    const snap = this.deps.snapshot();
    return snap === null || snap.fingerprint !== this.savedFingerprint;
  }

  /**
   * The Board is going away (in-app navigation). Send pending changes once, without retries,
   * then stop. Must run while the scene can still be read.
   */
  leave() {
    if (this.disposed) return;
    const pending = this.timer !== null || this.queued;
    this.clearTimer();
    this.disposed = true;
    if (pending) this.deps.draft?.flush();
    if (!pending || this.paused || this.status === "conflict") return;
    const snap = this.deps.snapshot();
    if (!snap || snap.fingerprint === this.savedFingerprint) return;
    if (this.inFlight) {
      this.finalSnapshot = snap;
      return;
    }
    this.send(snap);
  }

  /** Stop everything without saving (tests, teardown). */
  dispose() {
    this.disposed = true;
    this.clearTimer();
  }

  // ---- internals ----

  private arm(ms: number) {
    this.clearTimer();
    this.timer = this.timers.setTimeout(() => {
      this.timer = null;
      this.retryScheduled = false;
      this.flush();
    }, ms);
  }

  private clearTimer() {
    if (this.timer !== null) this.timers.clearTimeout(this.timer);
    this.timer = null;
    this.retryScheduled = false;
  }

  private setStatus(status: SaveStatus) {
    this.status = status;
    // Confirmed and nothing newer waiting: the device draft is no longer needed.
    if (status === "saved" && this.timer === null && !this.queued) this.deps.draft?.clear();
    if (!this.disposed) this.deps.onView({ status, retrying: status === "error" && this.retryScheduled });
  }

  private flush() {
    if (this.disposed || this.paused || this.status === "conflict") return;
    if (this.inFlight) {
      this.queued = true;
      return;
    }
    const snap = this.deps.snapshot();
    if (snap === null) {
      // Loading or mid-draw: look again after another quiet period.
      this.arm(this.debounceMs);
      return;
    }
    if (snap.fingerprint === this.savedFingerprint) {
      this.lastAttempt = null;
      if (snap.token !== undefined) this.savedToken = snap.token;
      if (this.status !== "saved") this.setStatus("saved");
      return;
    }
    this.send(snap);
  }

  private send(snap: Snapshot) {
    const saveId =
      this.lastAttempt && this.lastAttempt.fingerprint === snap.fingerprint
        ? this.lastAttempt.saveId
        : this.deps.newSaveId();
    this.lastAttempt = { fingerprint: snap.fingerprint, saveId };
    this.inFlight = true;
    this.queued = false;
    this.setStatus("saving");
    this.deps
      .save({ base_revision: this.revision, save_id: saveId, board: snap.board })
      .then(
        (response) => this.onSaved(snap, response.revision),
        (error: unknown) => this.onFailed(error),
      );
  }

  private onSaved(snap: Snapshot, revision: number) {
    this.inFlight = false;
    this.revision = revision;
    this.savedFingerprint = snap.fingerprint;
    if (snap.token !== undefined) this.savedToken = snap.token;
    this.lastAttempt = null;
    this.failures = 0;
    this.manualOnly = false;
    if (this.disposed) {
      const last = this.finalSnapshot;
      this.finalSnapshot = null;
      if (last && last.fingerprint !== this.savedFingerprint) this.send(last);
      else this.deps.draft?.clear();
      return;
    }
    this.setStatus("saved");
    if (this.queued) {
      this.queued = false;
      this.flush();
    }
  }

  private onFailed(error: unknown) {
    this.inFlight = false;
    this.finalSnapshot = null;
    if (this.disposed) return;
    this.queued = false;
    if (isConflict(error)) {
      this.clearTimer();
      this.setStatus("conflict");
      return;
    }
    this.failures += 1;
    if (!this.manualOnly && isRetryable(error) && this.failures <= this.maxAutoRetries) {
      const delay = Math.min(this.retryBaseMs * 2 ** (this.failures - 1), this.retryMaxMs);
      this.arm(delay);
      this.retryScheduled = true;
    } else {
      this.manualOnly = true;
      this.clearTimer();
    }
    this.setStatus("error");
  }
}

// ---- React hook ----

export type UseAutosave = AutosaveView & {
  notifyChange: (token?: number) => void;
  retry: () => void;
  /** Content was replaced from outside (draft restored): show it as unsaved and let autosave persist it. */
  markUnsaved: () => void;
  /** The revision the controller currently builds on. */
  currentRevision: () => number;
  /** Pause saving, load new content with `apply`, then restart clean from its revision. */
  reloadWith: (apply: () => { revision: number; fingerprint: string; token?: number }) => void;
  /** Hold or release the device draft (a recovery banner is showing); `adopt` takes over the stored one. */
  holdDraft: (on: boolean, adopt?: boolean) => void;
};

/**
 * Owns one AutosaveController for the mounted Board. It is created only after the Board's
 * content was loaded (the caller mounts this with the loaded revision), registers the
 * `beforeunload` guard, and on leave sends any pending change once.
 */
export function useAutosave(
  options: {
    initialRevision: number;
    initialFingerprint: string;
    initialToken?: number;
    /** Enables the device-local draft for this user and Lesson. */
    draftScope?: { userId: number | string; lessonId: string };
    save: AutosaveDeps["save"];
    snapshot: AutosaveDeps["snapshot"];
    newSaveId?: () => string;
  } & AutosaveOptions,
): UseAutosave {
  const [view, setView] = useState<AutosaveView>({ status: "saved", retrying: false });
  const controllerRef = useRef<AutosaveController | null>(null);
  const writerRef = useRef<DraftWriter | null>(null);
  // Keep the latest callbacks without recreating the controller.
  const optionsRef = useRef(options);
  useLayoutEffect(() => {
    optionsRef.current = options;
  });

  // Layout effect so `leave()` runs before Excalidraw unmounts and the scene is still readable.
  useLayoutEffect(() => {
    const opts = optionsRef.current;
    let controller: AutosaveController | null = null;
    const scope = opts.draftScope;
    const writer = scope
      ? new DraftWriter({
          ...scope,
          read: () => {
            const snap = optionsRef.current.snapshot();
            return snap && controller ? { board: snap.board, revision: controller.currentRevision } : null;
          },
        })
      : null;
    writerRef.current = writer;
    const created = new AutosaveController(
      {
        save: (body) => optionsRef.current.save(body),
        snapshot: () => optionsRef.current.snapshot(),
        newSaveId: () => (optionsRef.current.newSaveId ?? (() => crypto.randomUUID()))(),
        onView: setView,
        draft: writer
          ? { request: () => writer.request(), flush: () => writer.flush(), clear: () => writer.clear() }
          : undefined,
      },
      { revision: opts.initialRevision, fingerprint: opts.initialFingerprint, token: opts.initialToken },
      opts,
    );
    controller = created;
    controllerRef.current = created;
    return () => {
      created.leave();
      writer?.dispose();
      if (controllerRef.current === created) controllerRef.current = null;
      if (writerRef.current === writer) writerRef.current = null;
    };
    // The controller lives as long as the Board; later option changes go through optionsRef.
  }, []);

  useEffect(() => {
    const onBeforeUnload = (event: BeforeUnloadEvent) => {
      if (!controllerRef.current?.hasUnsavedChanges()) return;
      event.preventDefault();
      // Older browsers need returnValue set to show the prompt.
      event.returnValue = "";
    };
    // The device draft is written before the page can go away.
    const onLeaving = () => controllerRef.current?.flushDraft();
    window.addEventListener("beforeunload", onBeforeUnload);
    window.addEventListener("pagehide", onLeaving);
    window.addEventListener("beforeunload", onLeaving);
    return () => {
      window.removeEventListener("beforeunload", onBeforeUnload);
      window.removeEventListener("pagehide", onLeaving);
      window.removeEventListener("beforeunload", onLeaving);
    };
  }, []);

  const notifyChange = useCallback((token?: number) => controllerRef.current?.notifyChange(token), []);
  const markUnsaved = useCallback(() => controllerRef.current?.markUnsaved(), []);
  const currentRevision = useCallback(() => controllerRef.current?.currentRevision ?? 0, []);
  const holdDraft = useCallback((on: boolean, adopt = false) => {
    writerRef.current?.hold(on);
    if (adopt) writerRef.current?.adopt();
  }, []);
  const retry = useCallback(() => controllerRef.current?.retry(), []);
  const reloadWith = useCallback((apply: () => { revision: number; fingerprint: string; token?: number }) => {
    const c = controllerRef.current;
    if (!c) return;
    c.pause();
    const loaded = apply();
    c.reset(loaded.revision, loaded.fingerprint, loaded.token);
  }, []);

  return { ...view, notifyChange, retry, markUnsaved, currentRevision, reloadWith, holdDraft };
}
