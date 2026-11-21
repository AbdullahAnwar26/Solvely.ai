import { describe, expect, it } from "vitest";
import { initialAppState, sceneFingerprint, serializeBoard, type SceneElement } from "./boardSerialize";

const el = (id: string, over: Partial<SceneElement> & Record<string, unknown> = {}) => ({
  id,
  type: "rectangle",
  version: 1,
  isDeleted: false,
  ...over,
});

describe("serializeBoard", () => {
  it("keeps live savable elements with their customData and only the minimal appState", () => {
    const elements = [
      el("a", { customData: { origin: "learner" } }),
      el("b", { isDeleted: true }),
      el("c", { type: "image", fileId: "f" }),
      el("d", { type: "embeddable" }),
      el("e", { type: "text", text: "hi", customData: { origin: "ai", stepId: "s1" } }),
    ];
    const appState = {
      viewBackgroundColor: "transparent",
      scrollX: 10,
      scrollY: -5,
      zoom: { value: 1.5 },
      theme: "dark",
      selectedElementIds: { a: true },
      files: {},
    };
    const board = serializeBoard(elements, appState);
    expect(board).toEqual({
      schema_version: 1,
      elements: [elements[0], elements[4]],
      app_state: { viewBackgroundColor: "transparent", scrollX: 10, scrollY: -5, zoom: { value: 1.5 } },
    });
    expect(board).not.toHaveProperty("files");
  });

  it("drops non-finite viewport numbers", () => {
    const board = serializeBoard([], { scrollX: Number.NaN, scrollY: Infinity, zoom: { value: Number.NaN } });
    expect(board.app_state).toEqual({});
  });
});

describe("sceneFingerprint", () => {
  it("changes when an element version changes, is added or deleted", () => {
    const base = sceneFingerprint([el("a"), el("b")]);
    expect(sceneFingerprint([el("a"), el("b")])).toBe(base);
    expect(sceneFingerprint([el("a", { version: 2 }), el("b")])).not.toBe(base);
    expect(sceneFingerprint([el("a")])).not.toBe(base);
    expect(sceneFingerprint([el("a"), el("b", { isDeleted: true })])).toBe(sceneFingerprint([el("a")]));
  });

  it("ignores element types that are never saved", () => {
    expect(sceneFingerprint([el("a"), el("i", { type: "image" })])).toBe(sceneFingerprint([el("a")]));
  });
});

describe("initialAppState", () => {
  it("restores the saved viewport and defaults the background to transparent", () => {
    expect(initialAppState({ schema_version: 1, elements: [] })).toEqual({ viewBackgroundColor: "transparent" });
    expect(
      initialAppState({
        schema_version: 1,
        elements: [],
        app_state: { scrollX: 3, scrollY: 4, zoom: { value: 2 }, viewBackgroundColor: "white" },
      }),
    ).toEqual({ viewBackgroundColor: "white", scrollX: 3, scrollY: 4, zoom: { value: 2 } });
  });
});
