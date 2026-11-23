import { act, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { createMemoryRouter, RouterProvider } from "react-router";
import { afterEach, beforeEach, describe, expect, it, vi, type Mock } from "vitest";
import { routes } from "../app/routes";
import { envelope, mockApi, USER, type MockHandler, type MockReply, type RecordedCall } from "../test/mockApi";
import { AUTOSAVE_DEBOUNCE_MS } from "./useAutosave";

type El = { id: string; type: string; version: number; isDeleted: boolean; customData?: Record<string, unknown> };

const h = vi.hoisted(() => ({
  props: null as null | {
    onChange?: (els: unknown[], app: Record<string, unknown>) => void;
    initialData?: { elements: unknown[]; appState: Record<string, unknown> };
  },
  elements: [] as unknown[],
  appState: { isLoading: false, zoom: { value: 1 }, scrollX: 0, scrollY: 0, viewBackgroundColor: "transparent" } as Record<
    string,
    unknown
  >,
  updateScene: null as unknown as Mock,
}));

vi.mock("@excalidraw/excalidraw", async () => {
  const { vi: v } = await import("vitest");
  h.updateScene = v.fn((scene: { elements?: unknown[] }) => {
    if (scene.elements) h.elements = scene.elements;
  });
  const api = {
    history: { clear: () => undefined },
    updateScene: (scene: unknown) => h.updateScene(scene),
    scrollToContent: v.fn(),
    getAppState: () => h.appState,
    getSceneElements: () => (h.elements as { isDeleted?: boolean }[]).filter((e) => !e.isDeleted),
  };
  return {
    CaptureUpdateAction: { NEVER: "NEVER" },
    restoreElements: (els: unknown[]) => els.map((e) => ({ ...(e as object) })),
    Excalidraw: (props: NonNullable<typeof h.props> & { excalidrawAPI?: (a: unknown) => void }) => {
      h.props = props;
      if (h.elements.length === 0 && props.initialData) h.elements = props.initialData.elements;
      props.excalidrawAPI?.(api);
      return <div data-testid="excalidraw" tabIndex={-1} className="excalidraw" />;
    },
  };
});
vi.mock("@excalidraw/excalidraw/index.css", () => ({}));

const LESSON_ID = "7b0b1f0e-8d3c-4a53-9c0a-6f1f6f0a3333";
const LESSON = {
  id: LESSON_ID,
  title: "Graphs",
  current_revision: 3,
  created_at: "2026-10-29T10:00:00Z",
  updated_at: "2026-10-29T10:00:00Z",
};
const BOARD = `/api/v1/lessons/${LESSON_ID}/board/`;
const KEY = `wt.draft.${USER.id}.${LESSON_ID}`;
const el = (id: string, version = 1): El => ({
  id,
  type: "rectangle",
  version,
  isDeleted: false,
  customData: { origin: "learner" },
});
const idle = { zoom: { value: 1 }, newElement: null, editingTextElement: null, multiElement: null };

function seedDraft(over: Record<string, unknown> = {}, elements: El[] = [el("a", 5), el("b")]) {
  window.localStorage.setItem(
    KEY,
    JSON.stringify({
      lesson_id: LESSON_ID,
      user_id: USER.id,
      base_revision: 3,
      saved_at: "2026-10-29T10:00:00Z",
      board: { schema_version: 1, elements, app_state: {} },
      ...over,
    }),
  );
}

function open(handlers: Record<string, MockHandler | MockReply> = {}, appState: Record<string, unknown> = { scrollX: 4 }) {
  const api = mockApi({
    "GET /api/v1/auth/me/": { status: 200, body: USER },
    [`GET /api/v1/lessons/${LESSON_ID}/`]: { status: 200, body: LESSON },
    [`GET ${BOARD}`]: {
      status: 200,
      body: { revision: 3, board: { schema_version: 1, elements: [el("a")], app_state: appState } },
    },
    ...handlers,
  });
  const router = createMemoryRouter(routes, { initialEntries: [`/lessons/${LESSON_ID}`] });
  render(<RouterProvider router={router} />);
  return api;
}

function change(elements: El[], app: Record<string, unknown> = {}) {
  h.elements = elements;
  act(() => h.props?.onChange?.(elements, { ...idle, ...app }));
}

const puts = (calls: RecordedCall[]) => calls.filter((c) => c.method === "PUT" && c.path === BOARD);
const label = () => document.querySelector(".save-status-label")?.textContent;
const stored = () => window.localStorage.getItem(KEY);

beforeEach(() => {
  window.localStorage.clear();
  h.props = null;
  h.elements = [];
  h.updateScene?.mockClear();
  h.appState.isLoading = false;
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("Viewport restore", () => {
  it("opens the Board at the saved scroll and zoom", async () => {
    open({}, { scrollX: 40, scrollY: -12, zoom: { value: 2 } });
    await screen.findByTestId("excalidraw");
    expect(h.props?.initialData?.appState).toMatchObject({ scrollX: 40, scrollY: -12, zoom: { value: 2 } });
  });

  it("falls back to the default view for a missing or invalid app_state", async () => {
    open({}, { zoom: { value: -3 }, scrollX: "far" });
    await screen.findByTestId("excalidraw");
    const app = h.props?.initialData?.appState ?? {};
    expect(app).not.toHaveProperty("zoom");
    expect(app).not.toHaveProperty("scrollX");
  });
});

describe("Unsaved state", () => {
  it("flips to Unsaved changes on a real edit, then Saving, then Saved", async () => {
    let release: () => void = () => undefined;
    const gate = new Promise<void>((r) => (release = r));
    const { calls } = open({
      [`PUT ${BOARD}`]: async () => {
        await gate;
        return { status: 200, body: { revision: 4 } };
      },
    });
    await screen.findByTestId("excalidraw");
    expect(label()).toBe("Saved");
    change([el("a"), el("n")]);
    expect(label()).toBe("Unsaved changes");
    await waitFor(() => expect(label()).toBe("Saving…"), { timeout: AUTOSAVE_DEBOUNCE_MS + 2000 });
    release();
    await waitFor(() => expect(label()).toBe("Saved"));
    expect(puts(calls)).toHaveLength(1);
  });

  it("does not flip on a pan, zoom or selection change and sends no save", async () => {
    const { calls } = open({ [`PUT ${BOARD}`]: { status: 200, body: { revision: 4 } } });
    await screen.findByTestId("excalidraw");
    change([el("a")], { scrollX: 99, zoom: { value: 2 } });
    change([el("a")], { selectedElementIds: { a: true } });
    change([el("a")], { selectedElementIds: {} });
    expect(label()).toBe("Saved");
    await new Promise((r) => setTimeout(r, AUTOSAVE_DEBOUNCE_MS + 300));
    expect(label()).toBe("Saved");
    expect(puts(calls)).toHaveLength(0);
    expect(stored()).toBeNull();
  });
});

describe("Draft lifecycle", () => {
  it("writes only board data and metadata while unsaved, and removes it once the save is confirmed", async () => {
    let release: () => void = () => undefined;
    const gate = new Promise<void>((r) => (release = r));
    open({
      [`PUT ${BOARD}`]: async () => {
        await gate;
        return { status: 200, body: { revision: 4 } };
      },
    });
    await screen.findByTestId("excalidraw");
    change([el("a", 2)]);
    const draft = JSON.parse(stored() ?? "null") as Record<string, unknown>;
    expect(Object.keys(draft).sort()).toEqual(["base_revision", "board", "lesson_id", "saved_at", "user_id"]);
    expect(draft).toMatchObject({ lesson_id: LESSON_ID, user_id: USER.id, base_revision: 3 });
    expect(JSON.stringify(draft)).not.toContain(USER.email);
    await waitFor(() => expect(label()).toBe("Saving…"), { timeout: AUTOSAVE_DEBOUNCE_MS + 2000 });
    expect(stored()).not.toBeNull();
    release();
    await waitFor(() => expect(label()).toBe("Saved"));
    expect(stored()).toBeNull();
  });

  it("keeps the draft after a failed save and flushes it on pagehide", async () => {
    open({ [`PUT ${BOARD}`]: envelope("validation_error", 400) });
    await screen.findByTestId("excalidraw");
    change([el("a", 2)]);
    window.localStorage.removeItem(KEY);
    change([el("a", 3)]);
    await waitFor(() => expect(label()).toBe("Not saved"), { timeout: AUTOSAVE_DEBOUNCE_MS + 2000 });
    window.dispatchEvent(new Event("pagehide"));
    const draft = JSON.parse(stored() ?? "null") as { board: { elements: El[] } };
    expect(draft.board.elements[0]?.version).toBe(3);
  });

  it("skips silently when storage throws", async () => {
    vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
      throw new Error("quota");
    });
    open();
    await screen.findByTestId("excalidraw");
    expect(() => change([el("a", 2)])).not.toThrow();
    expect(label()).toBe("Unsaved changes");
    vi.restoreAllMocks();
  });
});

describe("Recovery banner", () => {
  it("offers Restore and Discard without taking focus, announced politely", async () => {
    seedDraft();
    open();
    await screen.findByTestId("excalidraw");
    const region = document.querySelector<HTMLElement>(".board-recovery");
    expect(region).toHaveAttribute("aria-live", "polite");
    expect(region).toHaveTextContent("We found unsaved changes from this device");
    expect(screen.getByRole("button", { name: "Restore" })).toBeVisible();
    expect(screen.getByRole("button", { name: "Discard" })).toBeVisible();
    expect(region?.contains(document.activeElement)).toBe(false);
    expect(label()).toBe("Saved");
  });

  it("Restore (by keyboard) loads the draft, shows Unsaved changes and autosave persists it from the base revision", async () => {
    seedDraft();
    const user = userEvent.setup();
    const { calls } = open({ [`PUT ${BOARD}`]: { status: 200, body: { revision: 4 } } });
    await screen.findByTestId("excalidraw");
    screen.getByRole("button", { name: "Restore" }).focus();
    await user.keyboard("{Enter}");
    expect(h.updateScene).toHaveBeenCalledWith(
      expect.objectContaining({ elements: [el("a", 5), el("b")] }),
    );
    expect(label()).toBe("Unsaved changes");
    expect(document.querySelector(".board-recovery")).toBeNull();
    await waitFor(() => expect(puts(calls)).toHaveLength(1), { timeout: AUTOSAVE_DEBOUNCE_MS + 2000 });
    const body = puts(calls)[0]?.body as { base_revision: number; board: { elements: El[] } };
    expect(body.base_revision).toBe(3);
    expect(body.board.elements).toEqual([el("a", 5), el("b")]);
    await waitFor(() => expect(label()).toBe("Saved"));
    expect(stored()).toBeNull();
  });

  it("Discard removes the draft and leaves the Board unchanged", async () => {
    seedDraft();
    const user = userEvent.setup();
    open();
    await screen.findByTestId("excalidraw");
    await user.click(screen.getByRole("button", { name: "Discard" }));
    expect(stored()).toBeNull();
    expect(document.querySelector(".board-recovery")).toBeNull();
    expect(h.updateScene).not.toHaveBeenCalled();
  });

  it("does not let new edits overwrite an offered draft", async () => {
    seedDraft();
    open();
    await screen.findByTestId("excalidraw");
    const before = stored();
    change([el("a", 2)]);
    expect(stored()).toBe(before);
  });

  it("shows an informational banner for a stale draft: no Restore, kept until Discard", async () => {
    seedDraft({ base_revision: 2 });
    const user = userEvent.setup();
    open();
    await screen.findByTestId("excalidraw");
    const region = document.querySelector(".board-recovery");
    expect(region).toHaveTextContent(
      "Your unsaved changes on this device are based on an older version and can't be merged",
    );
    expect(screen.queryByRole("button", { name: "Restore" })).not.toBeInTheDocument();
    expect(h.updateScene).not.toHaveBeenCalled();
    expect(stored()).not.toBeNull();
    await user.click(screen.getByRole("button", { name: "Discard" }));
    expect(stored()).toBeNull();
  });

  it("removes a draft equal to the server board silently", async () => {
    seedDraft({}, [el("a")]);
    open();
    await screen.findByTestId("excalidraw");
    expect(document.querySelector(".board-recovery")).toBeNull();
    expect(stored()).toBeNull();
  });

  it("ignores and removes another user's draft", async () => {
    seedDraft({ user_id: 99 });
    open();
    await screen.findByTestId("excalidraw");
    expect(document.querySelector(".board-recovery")).toBeNull();
    expect(stored()).toBeNull();
  });

  it("ignores and removes a corrupt draft", async () => {
    window.localStorage.setItem(KEY, "{not json");
    open();
    await screen.findByTestId("excalidraw");
    expect(document.querySelector(".board-recovery")).toBeNull();
    expect(stored()).toBeNull();
  });

  it("falls back to the stale notice when the revision moved on before Restore was pressed", async () => {
    seedDraft();
    const user = userEvent.setup();
    const { calls } = open({ [`PUT ${BOARD}`]: { status: 200, body: { revision: 4 } } });
    await screen.findByTestId("excalidraw");
    // The banner holds the draft, so this edit saves a new revision without touching it.
    change([el("a", 2)]);
    await waitFor(() => expect(puts(calls)).toHaveLength(1), { timeout: AUTOSAVE_DEBOUNCE_MS + 2000 });
    await waitFor(() => expect(label()).toBe("Saved"));
    await user.click(screen.getByRole("button", { name: "Restore" }));
    expect(h.updateScene).not.toHaveBeenCalled();
    expect(screen.queryByRole("button", { name: "Restore" })).not.toBeInTheDocument();
    expect(document.querySelector(".board-recovery")).toHaveTextContent("can't be merged");
    expect(stored()).not.toBeNull();
  });
});
