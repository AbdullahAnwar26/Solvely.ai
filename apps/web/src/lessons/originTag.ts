import type { ExcalidrawElement } from "@excalidraw/excalidraw/element/types";

export const LEARNER_ORIGIN = "learner";

function hasOrigin(element: ExcalidrawElement): boolean {
  const data = element.customData;
  return data !== undefined && data !== null && "origin" in data && data.origin !== undefined;
}

/**
 * Mark every element that has no origin yet as the Learner's own (AD-3). Pure and idempotent:
 * existing origins and every other customData key are kept, deleted elements are left alone,
 * and the same array is returned when nothing needed tagging so callers can skip an update.
 */
export function tagLearnerElements(
  elements: readonly ExcalidrawElement[],
): readonly ExcalidrawElement[] {
  if (!elements.some((el) => !el.isDeleted && !hasOrigin(el))) return elements;
  return elements.map((el) =>
    el.isDeleted || hasOrigin(el)
      ? el
      : {
          ...el,
          customData: { ...el.customData, origin: LEARNER_ORIGIN },
          // Excalidraw reconciles scenes by version; bump so the change is not discarded.
          version: el.version + 1,
          versionNonce: Math.floor(Math.random() * 2 ** 31),
        },
  );
}
