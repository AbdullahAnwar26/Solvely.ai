import { act, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import Board from "./Board";
import BoardControls from "./BoardControls";
import { nextZoom } from "./viewport";

type Change = (els: unknown[], app: Record<string, unknown>) => void;

const h = vi.hoisted(() => ({
  onChange: null as null | ((els: unknown[], app: Record<string, unknown>) => void),
  updateScene: vi.fn(),
  scrollToContent: vi.fn(),
  historyClear: vi.fn(),
  appState: { zoom: { value: 1 }, scrollX: 0, scrollY: 0, width: 800, height: 600 },
  elements: [] as unknown[],
  api: null as unknown,
}));

vi.mock("@excalidraw/excalidraw", () => ({
  CaptureUpdateAction: { NEVER: "NEVER" },
  Excalidraw: (props: { excalidrawAPI?: (api: unknown) => void; onChange?: Change }) => {
    h.onChange = props.onChange ?? null;
    props.excalidrawAPI?.(h.api);
    return <div data-testid="excalidraw" />;
  },
}));
vi.mock("@excalidraw/excalidraw/index.css", () => ({}));
vi.mock("../theme/useResolvedTheme", () => ({ useResolvedTheme: () => "light" }));

h.api = {
  history: { clear: h.historyClear },
  updateScene: h.updateScene,
  scrollToContent: h.scrollToContent,
  getAppState: () => h.appState,
  getSceneElements: () => h.elements,
};

const idle = { zoom: { value: 1 }, newElement: null, editingTextElement: null, multiElement: null };
const rect = (over: Record<string, unknown> = {}) => ({
  id: "r",
  type: "rectangle",
  version: 1,
  versionNonce: 1,
  isDeleted: false,
  ...over,
});

beforeEach(() => {
  h.updateScene.mockClear();
  h.scrollToContent.mockClear();
  h.historyClear.mockClear();
  h.appState.zoom.value = 1;
  h.elements = [];
});

describe("Board origin tagging", () => {
  it("tags a new element once with no undo capture, and does not loop", () => {
    render(<Board />);
    act(() => h.onChange?.([rect()], idle));
    expect(h.updateScene).toHaveBeenCalledTimes(1);
    const arg = h.updateScene.mock.calls[0]?.[0];
    expect(arg.captureUpdate).toBe("NEVER");
    expect(arg.elements[0].customData).toEqual({ origin: "learner" });

    act(() => h.onChange?.(arg.elements, idle));
    expect(h.updateScene).toHaveBeenCalledTimes(1);
  });

  it("waits while an element is still being drawn or edited", () => {
    render(<Board />);
    act(() => h.onChange?.([rect()], { ...idle, newElement: {} }));
    act(() => h.onChange?.([rect()], { ...idle, editingTextElement: {} }));
    expect(h.updateScene).not.toHaveBeenCalled();
  });

  it("leaves an AI origin alone", () => {
    render(<Board />);
    act(() => h.onChange?.([rect({ customData: { origin: "ai" } })], idle));
    expect(h.updateScene).not.toHaveBeenCalled();
  });

  it("clears history on unmount", () => {
    const { unmount } = render(<Board />);
    unmount();
    expect(h.historyClear).toHaveBeenCalledTimes(1);
  });

  it("enables Fit only once there is content and shows the live zoom", () => {
    render(<Board />);
    const fit = screen.getByRole("button", { name: "Fit to content" });
    expect(fit).toBeDisabled();
    act(() => h.onChange?.([rect({ customData: { origin: "learner" } })], { ...idle, zoom: { value: 2 } }));
    expect(fit).toBeEnabled();
    expect(screen.getByRole("button", { name: "Reset zoom to 100%" })).toHaveTextContent("200%");
  });
});

describe("BoardControls", () => {
  function setup(zoom = 1, hasContent = true) {
    const api = {
      getAppState: () => h.appState,
      getSceneElements: () => h.elements,
      updateScene: h.updateScene,
      scrollToContent: h.scrollToContent,
    };
    h.elements = hasContent ? [rect()] : [];
    h.appState.zoom.value = zoom;
    render(<BoardControls api={api as never} zoom={zoom} hasContent={hasContent} />);
  }

  it("labels every control and exposes a polite live zoom region", () => {
    setup(1.5);
    expect(screen.getByRole("toolbar", { name: "Board view" })).toBeInTheDocument();
    for (const name of ["Zoom out", "Zoom in", "Reset zoom to 100%", "Fit to content"]) {
      expect(screen.getByRole("button", { name })).toBeEnabled();
    }
    expect(screen.getByRole("status")).toHaveAttribute("aria-live", "polite");
  });

  it("zooms in, out and resets through the keyboard", async () => {
    const user = userEvent.setup();
    setup(1);
    await user.tab();
    expect(screen.getByRole("button", { name: "Zoom out" })).toHaveFocus();
    await user.keyboard("{Enter}");
    expect(h.updateScene.mock.calls[0]?.[0].appState.zoom.value).toBeCloseTo(0.8);
    await user.tab();
    await user.tab();
    expect(screen.getByRole("button", { name: "Zoom in" })).toHaveFocus();
    await user.keyboard(" ");
    expect(h.updateScene.mock.calls[1]?.[0].appState.zoom.value).toBeCloseTo(1.25);
    await user.click(screen.getByRole("button", { name: "Reset zoom to 100%" }));
    expect(h.updateScene.mock.calls[2]?.[0].appState.zoom.value).toBe(1);
  });

  it("fits to content", async () => {
    setup(1, true);
    await userEvent.setup().click(screen.getByRole("button", { name: "Fit to content" }));
    expect(h.scrollToContent).toHaveBeenCalledWith(h.elements, expect.objectContaining({ fitToViewport: true }));
  });

  it("disables Fit on an empty Board", () => {
    setup(1, false);
    expect(screen.getByRole("button", { name: "Fit to content" })).toBeDisabled();
  });

  it("disables zoom out at the minimum", () => {
    setup(0.1);
    expect(screen.getByRole("button", { name: "Zoom out" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Zoom in" })).toBeEnabled();
  });

  it("disables zoom in at the maximum", () => {
    setup(30);
    expect(screen.getByRole("button", { name: "Zoom in" })).toBeDisabled();
  });

  it("disables everything until the Board API is ready", () => {
    render(<BoardControls api={null} zoom={1} hasContent />);
    for (const b of screen.getAllByRole("button")) expect(b).toBeDisabled();
  });
});

describe("nextZoom", () => {
  it("steps by a fixed factor, snaps to 100% and clamps", () => {
    expect(nextZoom(1, 1)).toBe(1.25);
    expect(nextZoom(0.9, 1)).toBe(1);
    expect(nextZoom(0.1, -1)).toBe(0.1);
    expect(nextZoom(30, 1)).toBe(30);
  });
});
