import { vi } from "vitest";

/** Fake `window.matchMedia` for a viewport width (min-width / max-width queries only). */
export function setViewportWidth(width: number) {
  const evaluate = (query: string) => {
    const min = /min-width:\s*(\d+)px/.exec(query);
    const max = /max-width:\s*(\d+)px/.exec(query);
    if (min) return width >= Number(min[1]);
    if (max) return width <= Number(max[1]);
    return false;
  };
  vi.stubGlobal(
    "matchMedia",
    vi.fn((query: string) => ({
      matches: evaluate(query),
      media: query,
      onchange: null,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      addListener: vi.fn(),
      removeListener: vi.fn(),
      dispatchEvent: vi.fn(),
    })),
  );
}
