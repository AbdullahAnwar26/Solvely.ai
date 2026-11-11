import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { createMemoryRouter, RouterProvider } from "react-router";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { routes } from "../app/routes";
import { envelope, mockApi, USER } from "../test/mockApi";

const board = vi.hoisted(() => ({
  loaded: false,
  historyClear: vi.fn(),
}));

// The real canvas needs a browser; the module is mocked so laziness and cleanup are observable.
vi.mock("@excalidraw/excalidraw", () => {
  board.loaded = true;
  return {
    Excalidraw: (props: { theme?: string; excalidrawAPI?: (api: unknown) => void }) => {
      props.excalidrawAPI?.({ history: { clear: board.historyClear } });
      return <div data-testid="excalidraw" data-theme={props.theme} />;
    },
  };
});
vi.mock("@excalidraw/excalidraw/index.css", () => ({}));

const LESSON_ID = "7b0b1f0e-8d3c-4a53-9c0a-6f1f6f0a1111";
const LESSON = {
  id: LESSON_ID,
  title: "Untitled lesson",
  current_revision: 0,
  created_at: "2026-10-29T10:00:00Z",
  updated_at: "2026-10-29T10:00:00Z",
};

function renderAt(path = "/") {
  const router = createMemoryRouter(routes, { initialEntries: [path] });
  render(<RouterProvider router={router} />);
  return router;
}

beforeEach(() => {
  board.historyClear.mockClear();
});

afterEach(() => {
  vi.unstubAllGlobals();
});

// Must stay first: the mock factory runs on the first import of Excalidraw.
describe("Lazy loading", () => {
  it("does not load Excalidraw until a Lesson is opened", async () => {
    mockApi({ "GET /api/v1/auth/me/": { status: 200, body: USER } });
    renderAt("/");
    await screen.findByRole("heading", { level: 1, name: "Whiteboard Tutor" });
    expect(board.loaded).toBe(false);
  });
});

describe("New lesson", () => {
  it("shows a busy state, creates the Lesson and opens its Board", async () => {
    const user = userEvent.setup();
    let release: () => void = () => undefined;
    const gate = new Promise<void>((resolve) => (release = resolve));
    const { calls } = mockApi({
      "GET /api/v1/auth/me/": { status: 200, body: USER },
      "POST /api/v1/lessons/": async () => {
        await gate;
        return { status: 201, body: LESSON };
      },
      [`GET /api/v1/lessons/${LESSON_ID}/`]: { status: 200, body: LESSON },
    });
    const router = renderAt("/");

    await user.click(await screen.findByRole("button", { name: "New lesson" }));
    const busy = await screen.findByRole("button", { name: "Starting…" });
    expect(busy).toBeDisabled();
    expect(busy).toHaveAttribute("aria-busy", "true");

    release();
    expect(await screen.findByRole("heading", { level: 1, name: "Untitled lesson" })).toBeInTheDocument();
    expect(router.state.location.pathname).toBe(`/lessons/${LESSON_ID}`);
    expect(await screen.findByTestId("excalidraw")).toBeInTheDocument();

    const create = calls.find((c) => c.method === "POST" && c.path === "/api/v1/lessons/");
    expect(create?.body).toEqual({});
    expect(create?.headers.get("X-CSRFToken")).toBe("test-token");
    expect(screen.getByRole("button", { name: "New lesson" })).toBeEnabled();
  });

  it("shows an inline error and stays put when creating fails", async () => {
    const user = userEvent.setup();
    mockApi({
      "GET /api/v1/auth/me/": { status: 200, body: USER },
      "POST /api/v1/lessons/": envelope("server_error", 500, { retryable: true }),
    });
    const router = renderAt("/");

    await user.click(await screen.findByRole("button", { name: "New lesson" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(/couldn't start a new lesson/i);
    expect(router.state.location.pathname).toBe("/");
    expect(screen.getByRole("button", { name: "New lesson" })).toBeEnabled();
  });

  it("tells the Learner when they are creating lessons too fast", async () => {
    const user = userEvent.setup();
    mockApi({
      "GET /api/v1/auth/me/": { status: 200, body: USER },
      "POST /api/v1/lessons/": envelope("throttled", 429, { retryable: true }),
    });
    renderAt("/");

    await user.click(await screen.findByRole("button", { name: "New lesson" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(/wait a little/i);
  });
});

describe("Lesson page", () => {
  it("shows the title and the Board with no save indicator", async () => {
    mockApi({
      "GET /api/v1/auth/me/": { status: 200, body: USER },
      [`GET /api/v1/lessons/${LESSON_ID}/`]: { status: 200, body: { ...LESSON, title: "Big-O" } },
    });
    renderAt(`/lessons/${LESSON_ID}`);

    expect(await screen.findByRole("heading", { level: 1, name: "Big-O" })).toBeInTheDocument();
    expect(await screen.findByTestId("excalidraw")).toBeInTheDocument();
    expect(board.loaded).toBe(true);
    expect(screen.queryByText(/saved|saving|autosave/i)).not.toBeInTheDocument();
  });

  it.each(["light", "dark"] as const)("gives the Board the %s theme", async (preference) => {
    mockApi({
      "GET /api/v1/auth/me/": { status: 200, body: { ...USER, theme_preference: preference } },
      [`GET /api/v1/lessons/${LESSON_ID}/`]: { status: 200, body: LESSON },
    });
    renderAt(`/lessons/${LESSON_ID}`);
    expect(await screen.findByTestId("excalidraw")).toHaveAttribute("data-theme", preference);
  });

  it("follows the OS theme when the preference is system", async () => {
    vi.stubGlobal(
      "matchMedia",
      vi.fn((query: string) => ({
        matches: query.includes("prefers-color-scheme: dark"),
        media: query,
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
      })),
    );
    mockApi({
      "GET /api/v1/auth/me/": { status: 200, body: USER },
      [`GET /api/v1/lessons/${LESSON_ID}/`]: { status: 200, body: LESSON },
    });
    renderAt(`/lessons/${LESSON_ID}`);
    expect(await screen.findByTestId("excalidraw")).toHaveAttribute("data-theme", "dark");
  });

  it("shows an error state and recovers on retry", async () => {
    const user = userEvent.setup();
    let attempts = 0;
    mockApi({
      "GET /api/v1/auth/me/": { status: 200, body: USER },
      [`GET /api/v1/lessons/${LESSON_ID}/`]: () => {
        attempts += 1;
        return attempts === 1 ? envelope("server_error", 500, { retryable: true }) : { status: 200, body: LESSON };
      },
    });
    renderAt(`/lessons/${LESSON_ID}`);

    expect(await screen.findByRole("alert")).toHaveTextContent(/nothing was changed/i);
    expect(screen.queryByTestId("excalidraw")).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Try again" }));
    expect(await screen.findByTestId("excalidraw")).toBeInTheDocument();
    expect(attempts).toBe(2);
  });

  it("shows the accessible not-found state for a foreign or missing Lesson", async () => {
    mockApi({
      "GET /api/v1/auth/me/": { status: 200, body: USER },
      [`GET /api/v1/lessons/${LESSON_ID}/`]: envelope("not_found", 404),
    });
    renderAt(`/lessons/${LESSON_ID}`);

    expect(
      await screen.findByRole("heading", { level: 1, name: "We couldn't find that lesson." }),
    ).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Go to home" })).toHaveAttribute("href", "/");
    expect(screen.queryByTestId("excalidraw")).not.toBeInTheDocument();
  });

  it("shows the same not-found state for a malformed id without calling the API", async () => {
    const { calls } = mockApi({ "GET /api/v1/auth/me/": { status: 200, body: USER } });
    renderAt("/lessons/not-a-uuid");

    expect(
      await screen.findByRole("heading", { level: 1, name: "We couldn't find that lesson." }),
    ).toBeInTheDocument();
    expect(calls.filter((c) => c.path.startsWith("/api/v1/lessons"))).toHaveLength(0);
  });

  it("unmounts the Board and runs its cleanup when the Learner leaves", async () => {
    const user = userEvent.setup();
    mockApi({
      "GET /api/v1/auth/me/": { status: 200, body: USER },
      [`GET /api/v1/lessons/${LESSON_ID}/`]: { status: 200, body: LESSON },
    });
    renderAt(`/lessons/${LESSON_ID}`);
    await screen.findByTestId("excalidraw");
    expect(board.historyClear).not.toHaveBeenCalled();

    await user.click(screen.getByRole("link", { name: "Home" }));
    await waitFor(() => expect(screen.queryByTestId("excalidraw")).not.toBeInTheDocument());
    expect(board.historyClear).toHaveBeenCalledTimes(1);
  });
});
