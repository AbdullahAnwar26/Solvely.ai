import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError } from "../api/client";
import type { BoardSaveRequest } from "./boardApi";
import {
  AUTOSAVE_DEBOUNCE_MS,
  AUTOSAVE_MAX_AUTO_RETRIES,
  AUTOSAVE_RETRY_BASE_MS,
  AutosaveController,
  type AutosaveView,
  type Snapshot,
} from "./useAutosave";

type Deferred = { resolve: (revision: number) => void; reject: (error: unknown) => void };

const apiError = (status: number, code: string, retryable: boolean) =>
  new ApiError({ status, code, message: "x", retryable, request_id: null });
const networkError = () => apiError(0, "network_error", true);
const conflict = () => apiError(409, "revision_conflict", false);

function setup(initial = { revision: 0, fingerprint: "" }) {
  let content = "";
  let ready = true;
  let ids = 0;
  const views: AutosaveView[] = [];
  const requests: BoardSaveRequest[] = [];
  const pending: Deferred[] = [];
  const snapshot = vi.fn((): Snapshot | null =>
    ready ? { board: { schema_version: 1, elements: [{ id: content }] }, fingerprint: content } : null,
  );
  const save = vi.fn(
    (body: BoardSaveRequest) =>
      new Promise<{ revision: number }>((resolve, reject) => {
        requests.push(body);
        pending.push({ resolve: (revision) => resolve({ revision }), reject });
      }),
  );
  const controller = new AutosaveController(
    { save, snapshot, newSaveId: () => `id-${++ids}`, onView: (v) => views.push(v) },
    initial,
  );
  return {
    controller,
    save,
    snapshot,
    requests,
    views,
    status: () => controller.currentStatus,
    edit(next: string) {
      content = next;
      controller.notifyChange();
    },
    setReady(value: boolean) {
      ready = value;
    },
    async settle(index: number, outcome: number | Error) {
      const d = pending[index];
      if (!d) throw new Error(`No save #${index}`);
      if (typeof outcome === "number") d.resolve(outcome);
      else d.reject(outcome);
      await vi.advanceTimersByTimeAsync(0);
    },
  };
}

beforeEach(() => {
  vi.useFakeTimers();
});

afterEach(() => {
  vi.useRealTimers();
});

describe("debounce and coalescing", () => {
  it("does no work on a change and sends one PUT after the debounce", async () => {
    const s = setup();
    s.edit("a");
    expect(s.snapshot).not.toHaveBeenCalled();
    await vi.advanceTimersByTimeAsync(AUTOSAVE_DEBOUNCE_MS - 1);
    expect(s.save).not.toHaveBeenCalled();
    await vi.advanceTimersByTimeAsync(1);
    expect(s.save).toHaveBeenCalledTimes(1);
    expect(s.requests[0]).toEqual({ base_revision: 0, save_id: "id-1", board: expect.any(Object) });
  });

  it("coalesces rapid edits into one PUT with the latest content", async () => {
    const s = setup();
    for (const c of ["a", "b", "c", "d"]) {
      s.edit(c);
      await vi.advanceTimersByTimeAsync(500);
    }
    await vi.advanceTimersByTimeAsync(AUTOSAVE_DEBOUNCE_MS);
    expect(s.save).toHaveBeenCalledTimes(1);
    expect(s.requests[0]?.board.elements).toEqual([{ id: "d" }]);
  });

  it("skips a save when the element fingerprint did not change (pan, select)", async () => {
    const s = setup({ revision: 3, fingerprint: "same" });
    s.edit("same");
    await vi.advanceTimersByTimeAsync(AUTOSAVE_DEBOUNCE_MS);
    expect(s.snapshot).toHaveBeenCalledTimes(1);
    expect(s.save).not.toHaveBeenCalled();
    expect(s.status()).toBe("saved");
  });

  it("keeps exactly one save in flight and sends changes made meanwhile afterwards", async () => {
    const s = setup();
    s.edit("a");
    await vi.advanceTimersByTimeAsync(AUTOSAVE_DEBOUNCE_MS);
    s.edit("b");
    await vi.advanceTimersByTimeAsync(AUTOSAVE_DEBOUNCE_MS);
    s.edit("c");
    await vi.advanceTimersByTimeAsync(AUTOSAVE_DEBOUNCE_MS);
    expect(s.save).toHaveBeenCalledTimes(1);

    await s.settle(0, 1);
    expect(s.save).toHaveBeenCalledTimes(2);
    expect(s.requests[1]).toMatchObject({ base_revision: 1, save_id: "id-2", board: { elements: [{ id: "c" }] } });
    await s.settle(1, 2);
    expect(s.status()).toBe("saved");
    expect(s.controller.currentRevision).toBe(2);
  });
});

describe("status honesty", () => {
  it("shows Saving while in flight and Saved only after the server confirms", async () => {
    const s = setup();
    s.edit("a");
    await vi.advanceTimersByTimeAsync(AUTOSAVE_DEBOUNCE_MS);
    expect(s.status()).toBe("saving");
    expect(s.views.map((v) => v.status)).toEqual(["saving"]);
    await vi.advanceTimersByTimeAsync(10_000);
    expect(s.status()).toBe("saving");
    await s.settle(0, 1);
    expect(s.views.map((v) => v.status)).toEqual(["saving", "saved"]);
  });

  it("never saves while the scene is not ready (loading or mid-draw), then saves once it is", async () => {
    const s = setup();
    s.setReady(false);
    s.edit("a");
    await vi.advanceTimersByTimeAsync(AUTOSAVE_DEBOUNCE_MS * 3);
    expect(s.save).not.toHaveBeenCalled();
    s.setReady(true);
    await vi.advanceTimersByTimeAsync(AUTOSAVE_DEBOUNCE_MS);
    expect(s.save).toHaveBeenCalledTimes(1);
  });
});

describe("failures and retries", () => {
  it("retries with exponential backoff, reusing the save_id, then stops for a manual Retry", async () => {
    const s = setup();
    s.edit("a");
    await vi.advanceTimersByTimeAsync(AUTOSAVE_DEBOUNCE_MS);
    await s.settle(0, networkError());
    expect(s.status()).toBe("error");
    expect(s.views.at(-1)).toEqual({ status: "error", retrying: true });

    for (let attempt = 1; attempt <= AUTOSAVE_MAX_AUTO_RETRIES; attempt += 1) {
      const delay = AUTOSAVE_RETRY_BASE_MS * 2 ** (attempt - 1);
      await vi.advanceTimersByTimeAsync(delay - 1);
      expect(s.save).toHaveBeenCalledTimes(attempt);
      await vi.advanceTimersByTimeAsync(1);
      expect(s.save).toHaveBeenCalledTimes(attempt + 1);
      expect(s.requests[attempt]?.save_id).toBe("id-1");
      await s.settle(attempt, apiError(503, "http_error", true));
    }
    expect(s.views.at(-1)).toEqual({ status: "error", retrying: false });
    await vi.advanceTimersByTimeAsync(600_000);
    expect(s.save).toHaveBeenCalledTimes(AUTOSAVE_MAX_AUTO_RETRIES + 1);

    // Edits while failed do not restart automatic saving; the content stays in memory.
    s.edit("b");
    await vi.advanceTimersByTimeAsync(AUTOSAVE_DEBOUNCE_MS * 2);
    expect(s.save).toHaveBeenCalledTimes(AUTOSAVE_MAX_AUTO_RETRIES + 1);

    s.controller.retry();
    expect(s.save).toHaveBeenCalledTimes(AUTOSAVE_MAX_AUTO_RETRIES + 2);
    // New content gets a new save_id.
    expect(s.requests.at(-1)).toMatchObject({ save_id: "id-2", board: { elements: [{ id: "b" }] } });
    await s.settle(AUTOSAVE_MAX_AUTO_RETRIES + 1, 1);
    expect(s.status()).toBe("saved");
  });

  it("a manual retry of unchanged content reuses its save_id", async () => {
    const s = setup();
    s.edit("a");
    await vi.advanceTimersByTimeAsync(AUTOSAVE_DEBOUNCE_MS);
    await s.settle(0, apiError(400, "validation_error", false));
    expect(s.views.at(-1)).toEqual({ status: "error", retrying: false });
    await vi.advanceTimersByTimeAsync(600_000);
    expect(s.save).toHaveBeenCalledTimes(1);
    s.controller.retry();
    expect(s.requests[1]?.save_id).toBe("id-1");
  });

  it("stops autosaving on a 409 conflict and never retries or overwrites", async () => {
    const s = setup({ revision: 4, fingerprint: "" });
    s.edit("a");
    await vi.advanceTimersByTimeAsync(AUTOSAVE_DEBOUNCE_MS);
    await s.settle(0, conflict());
    expect(s.status()).toBe("conflict");
    s.edit("b");
    s.controller.retry();
    await vi.advanceTimersByTimeAsync(600_000);
    expect(s.save).toHaveBeenCalledTimes(1);
    expect(s.controller.hasUnsavedChanges()).toBe(true);
  });

  it("restarts clean from a reloaded revision after a conflict", async () => {
    const s = setup();
    s.edit("a");
    await vi.advanceTimersByTimeAsync(AUTOSAVE_DEBOUNCE_MS);
    await s.settle(0, conflict());
    s.controller.reset(7, "server");
    expect(s.status()).toBe("saved");
    s.edit("next");
    await vi.advanceTimersByTimeAsync(AUTOSAVE_DEBOUNCE_MS);
    expect(s.requests[1]).toMatchObject({ base_revision: 7, save_id: "id-2" });
  });
});

describe("unsaved changes and leaving", () => {
  it("reports unsaved changes while pending, saving or failed, and not when clean", async () => {
    const s = setup();
    expect(s.controller.hasUnsavedChanges()).toBe(false);
    s.edit("a");
    expect(s.controller.hasUnsavedChanges()).toBe(true);
    await vi.advanceTimersByTimeAsync(AUTOSAVE_DEBOUNCE_MS);
    expect(s.controller.hasUnsavedChanges()).toBe(true);
    await s.settle(0, 1);
    expect(s.controller.hasUnsavedChanges()).toBe(false);
    // A pending check whose scene matches the saved one is not unsaved (a pan, for example).
    s.edit("a");
    expect(s.controller.hasUnsavedChanges()).toBe(false);
  });

  it("sends pending changes once when the Board is left", async () => {
    const s = setup();
    s.edit("a");
    s.controller.leave();
    expect(s.save).toHaveBeenCalledTimes(1);
    await s.settle(0, networkError());
    await vi.advanceTimersByTimeAsync(600_000);
    expect(s.save).toHaveBeenCalledTimes(1);
  });

  it("on leave during a save, sends the latest content after that save settles", async () => {
    const s = setup();
    s.edit("a");
    await vi.advanceTimersByTimeAsync(AUTOSAVE_DEBOUNCE_MS);
    s.edit("b");
    s.controller.leave();
    expect(s.save).toHaveBeenCalledTimes(1);
    await s.settle(0, 1);
    expect(s.requests[1]).toMatchObject({ base_revision: 1, board: { elements: [{ id: "b" }] } });
  });
});

describe("unsaved state and device draft (Story 2.4)", () => {
  function withDraft(initial: { revision: number; fingerprint: string; token?: number }) {
    const draft = { request: vi.fn(), flush: vi.fn(), clear: vi.fn() };
    let content = "";
    let token = initial.token ?? 0;
    const views: AutosaveView[] = [];
    const save = vi.fn(() => Promise.resolve({ revision: initial.revision + 1 }));
    const controller = new AutosaveController(
      {
        save,
        snapshot: () => ({ board: { schema_version: 1, elements: [{ id: content }] }, fingerprint: content, token }),
        newSaveId: () => "id",
        onView: (v) => views.push(v),
        draft,
      },
      initial,
    );
    return {
      controller,
      draft,
      save,
      views,
      change(nextContent: string, nextToken: number) {
        content = nextContent;
        token = nextToken;
        controller.notifyChange(nextToken);
      },
    };
  }

  it("flips to unsaved at once on a different token, before any save starts", () => {
    const s = withDraft({ revision: 1, fingerprint: "", token: 5 });
    s.change("a", 6);
    expect(s.controller.currentStatus).toBe("unsaved");
    expect(s.save).not.toHaveBeenCalled();
    expect(s.draft.request).toHaveBeenCalled();
    expect(s.controller.hasUnsavedChanges()).toBe(true);
  });

  it("a same-token change (pan, zoom, selection) neither flips the status nor arms a save", async () => {
    const s = withDraft({ revision: 1, fingerprint: "", token: 5 });
    s.change("", 5);
    expect(s.controller.currentStatus).toBe("saved");
    expect(s.draft.request).not.toHaveBeenCalled();
    await vi.advanceTimersByTimeAsync(AUTOSAVE_DEBOUNCE_MS * 2);
    expect(s.save).not.toHaveBeenCalled();
  });

  it("goes unsaved, saving, saved and clears the draft once confirmed", async () => {
    const s = withDraft({ revision: 1, fingerprint: "", token: 5 });
    s.change("a", 6);
    await vi.advanceTimersByTimeAsync(AUTOSAVE_DEBOUNCE_MS);
    await vi.advanceTimersByTimeAsync(0);
    expect(s.views.map((v) => v.status)).toEqual(["unsaved", "saving", "saved"]);
    expect(s.draft.clear).toHaveBeenCalled();
    // The token of the saved content is the new baseline.
    s.change("a", 6);
    expect(s.controller.currentStatus).toBe("saved");
  });

  it("returns to saved (and clears the draft) when the content is undone to the saved state", async () => {
    const s = withDraft({ revision: 1, fingerprint: "", token: 5 });
    s.change("a", 6);
    s.change("", 5);
    await vi.advanceTimersByTimeAsync(AUTOSAVE_DEBOUNCE_MS);
    expect(s.controller.currentStatus).toBe("saved");
    expect(s.save).not.toHaveBeenCalled();
    expect(s.draft.clear).toHaveBeenCalled();
  });

  it("keeps the draft requested through failure and conflict, and does not clear it", async () => {
    const draft = { request: vi.fn(), flush: vi.fn(), clear: vi.fn() };
    const save = vi.fn(() => Promise.reject(conflict()));
    let token = 0;
    const controller = new AutosaveController(
      {
        save,
        snapshot: () => ({ board: { schema_version: 1, elements: [] }, fingerprint: String(token), token }),
        newSaveId: () => "id",
        onView: () => undefined,
        draft,
      },
      { revision: 0, fingerprint: "0", token: 0 },
    );
    token = 1;
    controller.notifyChange(1);
    await vi.advanceTimersByTimeAsync(AUTOSAVE_DEBOUNCE_MS);
    await vi.advanceTimersByTimeAsync(0);
    expect(controller.currentStatus).toBe("conflict");
    draft.request.mockClear();
    token = 2;
    controller.notifyChange(2);
    expect(draft.request).toHaveBeenCalled();
    expect(draft.clear).not.toHaveBeenCalled();
  });

  it("markUnsaved shows unsaved and lets autosave persist replaced content", async () => {
    const s = withDraft({ revision: 1, fingerprint: "", token: 5 });
    s.controller.markUnsaved();
    expect(s.controller.currentStatus).toBe("unsaved");
    expect(s.draft.request).toHaveBeenCalled();
    await vi.advanceTimersByTimeAsync(AUTOSAVE_DEBOUNCE_MS);
    // Same fingerprint as saved: nothing to send, back to saved.
    expect(s.controller.currentStatus).toBe("saved");
  });

  it("flushes the draft when leaving with a pending change and on flushDraft", () => {
    const s = withDraft({ revision: 1, fingerprint: "", token: 5 });
    s.change("a", 6);
    s.controller.flushDraft();
    expect(s.draft.flush).toHaveBeenCalledTimes(1);
    s.controller.leave();
    expect(s.draft.flush).toHaveBeenCalledTimes(2);
  });
});
