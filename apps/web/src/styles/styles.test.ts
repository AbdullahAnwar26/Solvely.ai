import { describe, expect, it } from "vitest";
import baseCss from "./base.css?raw";
import tokensCss from "./tokens.css?raw";

function colorTokens(block: string): Map<string, string> {
  const tokens = new Map<string, string>();
  for (const match of block.matchAll(/(--color-[\w-]+):\s*([^;]+);/g)) {
    tokens.set(match[1] as string, (match[2] as string).trim());
  }
  return tokens;
}

function blockAfter(css: string, selector: string): string {
  const start = css.indexOf(selector);
  expect(start, `missing ${selector}`).toBeGreaterThanOrEqual(0);
  const open = css.indexOf("{", start);
  const close = css.indexOf("}", open);
  return css.slice(open + 1, close);
}

describe("design tokens", () => {
  const light = colorTokens(blockAfter(tokensCss, ":root {"));
  const prefersDark = colorTokens(blockAfter(tokensCss, ':root:not([data-theme="light"])'));
  const forcedDark = colorTokens(blockAfter(tokensCss, ':root[data-theme="dark"]'));

  it("defines every DESIGN.md colour role in the light set", () => {
    expect(light.size).toBe(21);
    expect(light.get("--color-paper")).toBe("#faf7f2");
    expect(light.get("--color-focus")).toBe("#2f6fb0");
  });

  it("swaps to the dark set by prefers-color-scheme and by [data-theme=dark]", () => {
    expect(tokensCss).toContain("@media (prefers-color-scheme: dark)");
    expect([...prefersDark.keys()].sort()).toEqual([...light.keys()].sort());
    expect(forcedDark).toEqual(prefersDark);
    expect(prefersDark.get("--color-paper")).toBe("#171a21");
    expect(prefersDark.get("--color-focus")).toBe("#a8c7fa");
  });

  it("exposes typography and spacing variables", () => {
    expect(tokensCss).toMatch(/--font-serif:\s*"Source Serif 4"/);
    expect(tokensCss).toMatch(/--font-sans:\s*"Source Sans 3"/);
    expect(tokensCss).toMatch(/--font-mono:\s*"JetBrains Mono"/);
    expect(tokensCss).toMatch(/--space-sidebar-width:\s*248px/);
    expect(tokensCss).toMatch(/--space-sidebar-collapsed:\s*56px/);
  });
});

describe("base styles", () => {
  it("removes transitions and animations under prefers-reduced-motion", () => {
    const reduced = baseCss.slice(baseCss.indexOf("@media (prefers-reduced-motion: reduce)"));
    expect(reduced.length).toBeGreaterThan(0);
    expect(reduced).toMatch(/animation:\s*none\s*!important/);
    expect(reduced).toMatch(/transition:\s*none\s*!important/);
  });

  it("draws the focus ring with the focus token", () => {
    expect(baseCss).toMatch(/:focus-visible\s*{\s*outline:\s*2px solid var\(--color-focus\);\s*outline-offset:\s*2px;/);
  });
});
