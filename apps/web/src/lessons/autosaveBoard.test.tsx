import { act, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { createMemoryRouter, RouterProvider } from "react-router";
import { afterEach, beforeEach, describe, expect, it, vi, type Mock } from "vitest";
import { routes } from "../app/routes";
import { envelope, mockApi, USER, type MockHandler, type MockReply, type RecordedCall } from "../test/mockApi";
import { AUTOSAVE_DEBOUNCE_MS } from "./useAutosave";

type El = { id: string; type: string; version: number; isDeleted: boolean; customData?: Record<string, unknown> };
type Change = (els: El[], app: Record<string, unknown>) => void;

const h = vi.hoisted(() => ({
  props: null as null | {
    onChange?: (els: unknown[], app: Record<string, unknown>) => void;
    initialData?: { elements: unknown[]; appState: Record<string, unknown> };
    UIOptions?: unknown;
  },
  elements: [] as unknown[],
  appState: { isLoading: false, zoom: { value: 1 }, scrollX: 0, scrollY: 0, viewBackgroundColor: "transparent" } as Record<
    string,
    unknown
  >,
  updateScene: null as unknown as Mock,
  historyClear: null as unknown as Mock,
}));

vi.mock("@excalidraw/excalidraw", async () => {
  const { vi: v } = await import("vitest");
  h.updateScene = v.fn((scene: { elements?: unknown[] }) => {
    if (scene.elements) h.elements = scene.elements;
  });
  h.historyClear = v.fn();
  const api = {
    history: { clear: () => h.historyClear() },
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
      return <div data-testid="excalidraw" />;
    },
  };
});
vi.mock("@excalidraw/excalidraw/index.css", () => ({}));

const LESSON_ID = "7b0b1f0e-8d3c-4a53-9c0a-6f1f6f0a2222";
const LESSON = {
  id: LESSON_ID,
  title: "Graphs",
  current_revision: 3,
  created_at: "2026-10-29T10:00:00Z",
  updated_at: "2026-10-29T10:00:00Z",
};
const BOARD = `/api/v1/lessons/${LESSON_ID}/board/`;
const saved = (id: string, version = 1, origin = "learner"): El => ({
  id,
  type: "rectangle",
  version,
  isDeleted: false,
  customData: { origin },
});
const idle = { zoom: { value: 1 }, newElement: null, editingTextElement: null, multiElement: null };

function open(handlers: Record<string, MockHandler | MockReply>, initialElements: El[] = [saved("a")]) {
  const api = mockApi({
    "GET /api/v1/auth/me/": { status: 200, body: USER },
    [`GET /api/v1/lessons/${LESSON_ID}/`]: { status: 200, body: LESSON },
    [`GET ${BOARD}`]: {
      status: 200,
      body: { revision: 3, board: { schema_version: 1, elements: initialElements, app_state: { scrollX: 4 } } },
    },
    ...handlers,
  });
  const router = createMemoryRouter(routes, { initialEntries: [`/lessons/${LESSON_ID}`] });
  render(<RouterProvider router={router} />);
  return api;
}

/** Simulate a Learner edit: the scene changes and Excalidraw calls onChange. */
function edit(elements: El[]) {
  h.elements = elements;
  act(() => (h.props?.onChange as Change | undefined)?.(elements, idle));
}

const puts = (calls: RecordedCall[]) => calls.filter((c) => c.method === "PUT" && c.path === BOARD);

function nth(calls: RecordedCall[], index: number): RecordedCall {
  const call = puts(calls)[index];
  if (!call) throw new Error(`No PUT #${index}`);
  return call;
}

function statusRegion(): HTMLElement {
  const region = document.querySelector<HTMLElement>(".save-status");
  if (!region) throw new Error("No save status rendered");
  return region;
}

beforeEach(() => {
  h.props = null;
  h.elements = [];
  h.appState.isLoading = false;
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("Opening a Lesson", () => {
  it("loads the latest revision into the Board (tags intact) before any save, and shows Saved", async () => {
    const { calls } = open({});
    await screen.findByTestId("excalidraw");
    expect(h.props?.initialData?.elements).toEqual([saved("a")]);
    expect(h.props?.initialData?.appState).toMatchObject({ scrollX: 4, viewBackgroundColor: "transparent" });
    expect(h.props?.UIOptions).toEqual({ tools: { image: false } });
    expect(await screen.findByText("Saved")).toBeVisible();
    expect(puts(calls)).toHaveLength(0);
  });

  it("shows the error state and never saves when the Board cannot be loaded", async () => {
    const { calls } = open({ [`GET ${BOARD}`]: envelope("server_error", 500) });
    expect(await screen.findByRole("alert")).toHaveTextContent(/nothing was changed/i);
    expect(screen.queryByTestId("excalidraw")).not.toBeInTheDocument();
    expect(puts(calls)).toHaveLength(0);
  });
});

describe("Autosave on the page", () => {
  it("sends one PUT after the debounce, from the loaded base revision, then shows Saved", async () => {
    let release: () => void = () => undefined;
    const gate = new Promise<void>((r) => (release = r));
    const { calls } = open({
      [`PUT ${BOARD}`]: async () => {
        await gate;
        return { status: 200, body: { revision: 4 } };
      },
    });
    await screen.findByTestId("excalidraw");
    edit([saved("a", 2)]);
    edit([saved("a", 3)]);
    expect(statusRegion()).toHaveTextContent("Saved");

    await waitFor(() => expect(puts(calls)).toHaveLength(1), { timeout: AUTOSAVE_DEBOUNCE_MS + 2000 });
    expect(statusRegion()).toHaveTextContent("Saving…");
    const body = nth(calls, 0).body as { base_revision: number; save_id: string; board: { elements: El[] } };
    expect(body.base_revision).toBe(3);
    expect(body.save_id).toMatch(/^[0-9a-f-]{36}$/);
    expect(body.board.elements).toEqual([saved("a", 3)]);
    expect(body.board).not.toHaveProperty("files");
    expect(nth(calls, 0).headers.get("X-CSRFToken")).toBe("test-token");

    release();
    await waitFor(() => expect(statusRegion()).toHaveTextContent("Saved"));
    expect(puts(calls)).toHaveLength(1);
  });

  it("shows Not saved with Retry on failure and announces recovery", async () => {
    const user = userEvent.setup();
    let attempts = 0;
    const { calls } = open({
      [`PUT ${BOARD}`]: () => {
        attempts += 1;
        return attempts === 1 ? envelope("validation_error", 400) : { status: 200, body: { revision: 4 } };
      },
    });
    await screen.findByTestId("excalidraw");
    edit([saved("a", 2)]);

    const retry = await screen.findByRole("button", { name: "Retry" }, { timeout: AUTOSAVE_DEBOUNCE_MS + 2000 });
    expect(statusRegion()).toHaveTextContent("Not saved");
    const live = within(statusRegion()).getByRole("status");
    expect(live).toHaveAttribute("aria-live", "polite");
    expect(live).toHaveTextContent(/not saved/i);

    await user.click(retry);
    await waitFor(() => expect(statusRegion()).toHaveTextContent("Saved"));
    expect(live).toHaveTextContent("Saved again.");
    const bodies = puts(calls).map((c) => (c.body as { save_id: string }).save_id);
    expect(bodies).toHaveLength(2);
    expect(bodies[0]).toBe(bodies[1]);
  });

  it("on 409 shows Conflict, stops saving, and reloads the latest only after confirmation", async () => {
    const user = userEvent.setup();
    const server = [saved("a", 9, "learner"), saved("z", 1, "ai")];
    let boardGets = 0;
    const { calls } = open({
      [`GET ${BOARD}`]: () => {
        boardGets += 1;
        return boardGets === 1
          ? { status: 200, body: { revision: 3, board: { schema_version: 1, elements: [saved("a")] } } }
          : { status: 200, body: { revision: 8, board: { schema_version: 1, elements: server } } };
      },
      [`PUT ${BOARD}`]: () => ({
        status: 409,
        body: {
          error: {
            code: "revision_conflict",
            message: "changed",
            retryable: false,
            request_id: "r",
            current_revision: 8,
          },
        },
      }),
    });
    await screen.findByTestId("excalidraw");
    edit([saved("a", 2)]);

    const alert = await screen.findByRole("alert", {}, { timeout: AUTOSAVE_DEBOUNCE_MS + 2000 });
    expect(alert).toHaveTextContent(/changed in another tab or device/i);
    expect(statusRegion()).toHaveTextContent("Conflict");

    // Autosave has stopped: more edits send nothing.
    edit([saved("a", 3)]);
    await new Promise((r) => setTimeout(r, AUTOSAVE_DEBOUNCE_MS + 200));
    expect(puts(calls)).toHaveLength(1);

    await user.click(within(alert).getByRole("button", { name: "Reload latest" }));
    const dialog = await screen.findByRole("dialog", { name: "Load the latest version?" });
    // Cancelling keeps the local changes.
    await user.click(within(dialog).getByRole("button", { name: "Keep editing" }));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(boardGets).toBe(1);
    expect(h.elements).toEqual([saved("a", 3)]);

    await user.click(within(screen.getByRole("alert")).getByRole("button", { name: "Reload latest" }));
    await user.click(
      within(await screen.findByRole("dialog")).getByRole("button", { name: "Discard my changes and reload" }),
    );
    await waitFor(() => expect(statusRegion()).toHaveTextContent("Saved"));
    expect(boardGets).toBe(2);
    expect(h.updateScene).toHaveBeenLastCalledWith(expect.objectContaining({ elements: server, captureUpdate: "NEVER" }));
    expect(h.historyClear).toHaveBeenCalled();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();

    // Saving resumes from the reloaded revision.
    edit([...server, saved("n", 1)]);
    await waitFor(() => expect(puts(calls)).toHaveLength(2), { timeout: AUTOSAVE_DEBOUNCE_MS + 2000 });
    expect((nth(calls, 1).body as { base_revision: number }).base_revision).toBe(8);
  }, 15000);

  it("guards unload with beforeunload while changes are unsaved", async () => {
    let release: () => void = () => undefined;
    const gate = new Promise<void>((r) => (release = r));
    open({
      [`PUT ${BOARD}`]: async () => {
        await gate;
        return { status: 200, body: { revision: 4 } };
      },
    });
    await screen.findByTestId("excalidraw");
    await screen.findByText("Saved");

    const fire = () => {
      const event = new Event("beforeunload", { cancelable: true });
      window.dispatchEvent(event);
      return event.defaultPrevented;
    };
    expect(fire()).toBe(false);
    edit([saved("a", 2)]);
    expect(fire()).toBe(true);
    await waitFor(() => expect(statusRegion()).toHaveTextContent("Saving…"), { timeout: AUTOSAVE_DEBOUNCE_MS + 2000 });
    expect(fire()).toBe(true);
    release();
    await waitFor(() => expect(statusRegion()).toHaveTextContent("Saved"));
    expect(fire()).toBe(false);
  });

  it("does not save while the scene is still loading", async () => {
    const { calls } = open({ [`PUT ${BOARD}`]: { status: 200, body: { revision: 4 } } });
    await screen.findByTestId("excalidraw");
    h.appState.isLoading = true;
    edit([]);
    await new Promise((r) => setTimeout(r, AUTOSAVE_DEBOUNCE_MS + 300));
    expect(puts(calls)).toHaveLength(0);
  });
});
