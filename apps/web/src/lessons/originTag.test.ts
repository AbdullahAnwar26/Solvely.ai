import type { ExcalidrawElement } from "@excalidraw/excalidraw/element/types";
import { describe, expect, it } from "vitest";
import { tagLearnerElements } from "./originTag";

function el(over: Record<string, unknown> = {}): ExcalidrawElement {
  return {
    id: "a",
    type: "rectangle",
    version: 3,
    versionNonce: 1,
    isDeleted: false,
    ...over,
  } as unknown as ExcalidrawElement;
}

describe("tagLearnerElements", () => {
  it.each(["rectangle", "text", "arrow", "freedraw"])("tags a new %s element as learner", (type) => {
    const [out] = tagLearnerElements([el({ type })]);
    expect(out?.customData).toEqual({ origin: "learner" });
    expect(out?.version).toBe(4);
  });

  it("leaves an existing origin unchanged", () => {
    const input = [el({ customData: { origin: "ai" } })];
    const out = tagLearnerElements(input);
    expect(out).toBe(input);
    expect(out[0]?.customData).toEqual({ origin: "ai" });
  });

  it("preserves other customData keys and adds origin", () => {
    const [out] = tagLearnerElements([el({ customData: { stepId: "s1" } })]);
    expect(out?.customData).toEqual({ stepId: "s1", origin: "learner" });
  });

  it("is idempotent and returns the same array when nothing changes", () => {
    const once = tagLearnerElements([el()]);
    expect(tagLearnerElements(once)).toBe(once);
  });

  it("only changes untagged elements and skips deleted ones", () => {
    const tagged = el({ id: "t", customData: { origin: "learner" } });
    const deleted = el({ id: "d", isDeleted: true });
    const fresh = el({ id: "f" });
    const out = tagLearnerElements([tagged, deleted, fresh]);
    expect(out[0]).toBe(tagged);
    expect(out[1]).toBe(deleted);
    expect(out[2]?.customData).toEqual({ origin: "learner" });
  });
});
