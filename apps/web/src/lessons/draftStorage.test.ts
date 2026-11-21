import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  clearAllDrafts,
  clearDraft,
  DRAFT_MAX_CHARS,
  DraftWriter,
  draftKey,
  evaluateDraft,
  readDraft,
  writeDraft,
  type Draft,
} from "./draftStorage";

const el = (id: string, version = 1) => ({ id, type: "rectangle", version, isDeleted: false });
const draft = (over: Partial<Draft> = {}, elements: unknown[] = [el("a", 2)]): Draft => ({
  lesson_id: "L1",
  user_id: 7,
  base_revision: 3,
  saved_at: "2026-10-29T10:00:00Z",
  board: { schema_version: 1, elements: elements as never, app_state: {} },
  ...over,
});

beforeEach(() => window.localStorage.clear());
afterEach(() => vi.restoreAllMocks());

describe("draft read/write", () => {
  it("round-trips a draft under wt.draft.<user>.<lesson>", () => {
    expect(writeDraft(draft())).toBe(true);
    expect(window.localStorage.getItem("wt.draft.7.L1")).not.toBeNull();
    expect(readDraft(7, "L1")).toEqual(draft());
  });

  it("returns null when there is no draft", () => {
    expect(readDraft(7, "L1")).toBeNull();
  });

  it.each([
    ["invalid JSON", "{nope"],
    ["not an object", "[]"],
    ["missing board", JSON.stringify({ lesson_id: "L1", user_id: 7, base_revision: 3, saved_at: "x" })],
    ["bad schema version", JSON.stringify({ ...draft(), board: { schema_version: 2, elements: [] } })],
    ["elements not an array", JSON.stringify({ ...draft(), board: { schema_version: 1, elements: {} } })],
    ["element without id", JSON.stringify(draft({}, [{ type: "rectangle" }]))],
    ["negative revision", JSON.stringify(draft({ base_revision: -1 }))],
    ["fractional revision", JSON.stringify(draft({ base_revision: 1.5 }))],
    ["missing saved_at", JSON.stringify({ ...draft(), saved_at: undefined })],
  ])("ignores and removes a corrupt draft (%s)", (_name, raw) => {
    window.localStorage.setItem(draftKey(7, "L1"), raw);
    expect(readDraft(7, "L1")).toBeNull();
    expect(window.localStorage.getItem(draftKey(7, "L1"))).toBeNull();
  });

  it("ignores and removes a draft whose user_id or lesson_id differs", () => {
    window.localStorage.setItem(draftKey(7, "L1"), JSON.stringify(draft({ user_id: 8 })));
    expect(readDraft(7, "L1")).toBeNull();
    expect(window.localStorage.getItem(draftKey(7, "L1"))).toBeNull();
    window.localStorage.setItem(draftKey(7, "L1"), JSON.stringify(draft({ lesson_id: "L2" })));
    expect(readDraft(7, "L1")).toBeNull();
  });

  it("skips a draft larger than the limit and keeps the previous one", () => {
    writeDraft(draft());
    const big = draft({}, [{ ...el("a"), text: "x".repeat(DRAFT_MAX_CHARS) }]);
    expect(writeDraft(big)).toBe(false);
    expect(readDraft(7, "L1")).toEqual(draft());
  });

  it("skips silently when storage throws", () => {
    vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
      throw new Error("quota");
    });
    expect(writeDraft(draft())).toBe(false);
    vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => {
      throw new Error("blocked");
    });
    expect(readDraft(7, "L1")).toBeNull();
  });

  it("clears one draft or every wt.draft.* key and nothing else", () => {
    writeDraft(draft());
    writeDraft(draft({ lesson_id: "L2" }));
    window.localStorage.setItem("wt.theme", "dark");
    clearDraft(7, "L1");
    expect(window.localStorage.getItem("wt.draft.7.L1")).toBeNull();
    expect(window.localStorage.getItem("wt.draft.7.L2")).not.toBeNull();
    clearAllDrafts();
    expect(window.localStorage.getItem("wt.draft.7.L2")).toBeNull();
    expect(window.localStorage.getItem("wt.theme")).toBe("dark");
  });
});

describe("evaluateDraft", () => {
  const server = { revision: 3, elements: [el("a", 1)] };
  it("none without a draft", () => expect(evaluateDraft(null, server)).toEqual({ kind: "none" }));
  it("equal content is dropped silently", () =>
    expect(evaluateDraft(draft({}, [el("a", 1)]), server)).toEqual({ kind: "none", equal: true }));
  it("same base revision offers Restore", () => expect(evaluateDraft(draft(), server).kind).toBe("restore"));
  it("an older base revision is stale", () =>
    expect(evaluateDraft(draft({ base_revision: 2 }), server).kind).toBe("stale"));
  it("equal content wins over an older base", () =>
    expect(evaluateDraft(draft({ base_revision: 1 }, [el("a", 1)]), server)).toEqual({ kind: "none", equal: true }));
});

describe("DraftWriter", () => {
  function setup(read: () => { board: Draft["board"]; revision: number } | null = () => ({ board: draft().board, revision: 3 })) {
    let now = 10_000;
    const timers = new Map<number, () => void>();
    let nextId = 1;
    const writer = new DraftWriter({
      userId: 7,
      lessonId: "L1",
      read,
      now: () => now,
      timers: {
        setTimeout: (fn) => {
          timers.set(nextId, fn);
          return nextId++;
        },
        clearTimeout: (id) => void timers.delete(id),
      },
    });
    return {
      writer,
      timers,
      advance(ms: number) {
        now += ms;
      },
      fire() {
        for (const [id, fn] of [...timers]) {
          timers.delete(id);
          fn();
        }
      },
    };
  }
  const has = () => window.localStorage.getItem("wt.draft.7.L1") !== null;

  it("writes the first request at once and throttles later ones to one per 2 s", () => {
    const s = setup();
    s.writer.request();
    expect(has()).toBe(true);
    window.localStorage.removeItem("wt.draft.7.L1");
    s.advance(500);
    s.writer.request();
    s.writer.request();
    expect(has()).toBe(false);
    expect(s.timers.size).toBe(1);
    s.advance(1500);
    s.fire();
    expect(has()).toBe(true);
  });

  it("flush writes pending content immediately", () => {
    const s = setup();
    s.writer.request();
    window.localStorage.removeItem("wt.draft.7.L1");
    s.advance(100);
    s.writer.request();
    s.writer.flush();
    expect(has()).toBe(true);
  });

  it("clear deletes the draft and drops pending content", () => {
    const s = setup();
    s.writer.request();
    s.advance(100);
    s.writer.request();
    s.writer.clear();
    expect(has()).toBe(false);
    s.writer.flush();
    expect(has()).toBe(false);
  });

  it("never deletes a draft that another tab or an earlier session stored", () => {
    const s = setup();
    window.localStorage.setItem("wt.draft.7.L1", "other");
    s.writer.clear();
    expect(window.localStorage.getItem("wt.draft.7.L1")).toBe("other");
    s.writer.request();
    window.localStorage.setItem("wt.draft.7.L1", "replaced by another tab");
    s.writer.clear();
    expect(window.localStorage.getItem("wt.draft.7.L1")).toBe("replaced by another tab");
  });

  it("does not overwrite a draft stored by another tab", () => {
    const s = setup();
    window.localStorage.setItem("wt.draft.7.L1", "other tab");
    s.writer.request();
    expect(window.localStorage.getItem("wt.draft.7.L1")).toBe("other tab");
  });

  it("does not write or delete while held", () => {
    const s = setup();
    window.localStorage.setItem("wt.draft.7.L1", "keep");
    s.writer.hold(true);
    s.writer.request();
    s.writer.clear();
    expect(window.localStorage.getItem("wt.draft.7.L1")).toBe("keep");
  });

  it("retries later when the content cannot be read right now", () => {
    let ready = false;
    const s = setup(() => (ready ? { board: draft().board, revision: 3 } : null));
    s.writer.request();
    expect(has()).toBe(false);
    ready = true;
    s.advance(2000);
    s.fire();
    expect(has()).toBe(true);
  });
});
