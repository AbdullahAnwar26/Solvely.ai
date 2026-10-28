import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { createMemoryRouter, RouterProvider } from "react-router";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { mockApi, USER } from "../test/mockApi";
import { setViewportWidth } from "../test/viewport";
import { routes } from "./routes";
import { SIDEBAR_STORAGE_KEY } from "./sidebarPreference";

function renderAt(path = "/") {
  const router = createMemoryRouter(routes, { initialEntries: [path] });
  return render(<RouterProvider router={router} />);
}

function shellElement() {
  const shell = document.querySelector<HTMLElement>(".shell");
  if (!shell) throw new Error("shell not rendered");
  return shell;
}

// The shell sits behind the auth guard, so every test starts with a signed-in session.
beforeEach(() => {
  mockApi({ "GET /api/v1/auth/me/": { status: 200, body: USER } });
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("AppShell layout", () => {
  it.each([
    [1280, "docked", "expanded"],
    [820, "rail", "collapsed"],
    [390, "drawer", "hidden"],
  ])("at %ipx renders landmarks with a %s sidebar", async (width, layout, sidebar) => {
    setViewportWidth(width);
    renderAt("/");

    expect(await screen.findByRole("heading", { level: 1, name: "Whiteboard Tutor" })).toBeInTheDocument();
    expect(screen.getByRole("main")).toHaveAttribute("id", "main");
    expect(shellElement()).toHaveAttribute("data-layout", layout);
    expect(shellElement()).toHaveAttribute("data-sidebar", sidebar);
    if (layout === "drawer") {
      // Closed drawer: the nav landmark exists but is inert until the menu opens it.
      expect(screen.getByRole("banner")).toBeInTheDocument();
      const nav = document.getElementById("sidebar");
      expect(nav?.tagName).toBe("NAV");
      expect(nav).toHaveAttribute("inert");
    } else {
      expect(screen.getByRole("navigation", { name: "Main" })).toBeInTheDocument();
      expect(screen.queryByRole("banner")).not.toBeInTheDocument();
    }
  });

  it("opens the phone drawer, closes it with Escape and returns focus to the menu button", async () => {
    setViewportWidth(390);
    const user = userEvent.setup();
    renderAt("/");
    await screen.findByRole("heading", { level: 1 });

    const menu = screen.getByRole("button", { name: "Open menu" });
    expect(menu).toHaveAttribute("aria-expanded", "false");
    await user.click(menu);

    expect(shellElement()).toHaveAttribute("data-sidebar", "expanded");
    expect(screen.getByRole("navigation", { name: "Main" })).not.toHaveAttribute("inert");
    expect(screen.getByRole("button", { name: "Close menu" })).toHaveAttribute("aria-expanded", "true");
    expect(screen.getByRole("link", { name: "Home" })).toHaveFocus();
    expect(document.getElementById("main")).toHaveAttribute("inert");

    await user.keyboard("{Escape}");
    expect(shellElement()).toHaveAttribute("data-sidebar", "hidden");
    expect(screen.getByRole("button", { name: "Open menu" })).toHaveFocus();
  });

  it("opens the tablet sheet from the icon rail without persisting it", async () => {
    setViewportWidth(820);
    const user = userEvent.setup();
    renderAt("/");
    await screen.findByRole("heading", { level: 1 });

    await user.click(screen.getByRole("button", { name: "Open navigation" }));
    expect(shellElement()).toHaveAttribute("data-sidebar", "expanded");
    expect(window.localStorage.getItem(SIDEBAR_STORAGE_KEY)).toBeNull();
  });
});

describe("AppShell keyboard", () => {
  it("tabs from load: skip link, sidebar toggle, nav, then into main", async () => {
    setViewportWidth(1280);
    const user = userEvent.setup();
    renderAt("/nope");
    await screen.findByRole("heading", { level: 1 });

    await user.tab();
    expect(screen.getByRole("link", { name: "Skip to main content" })).toHaveFocus();
    await user.tab();
    expect(screen.getByRole("button", { name: "Collapse sidebar" })).toHaveFocus();
    await user.tab();
    expect(within(screen.getByRole("navigation", { name: "Main" })).getByRole("link", { name: "Home" })).toHaveFocus();
    await user.tab();
    expect(within(screen.getByRole("navigation", { name: "Main" })).getByRole("button", { name: "Sign out" })).toHaveFocus();
    await user.tab();
    expect(within(screen.getByRole("main")).getByRole("link", { name: "Go to home" })).toHaveFocus();
  });

  it("skip link moves focus to the main region", async () => {
    setViewportWidth(1280);
    const user = userEvent.setup();
    renderAt("/");
    await screen.findByRole("heading", { level: 1 });

    await user.tab();
    await user.keyboard("{Enter}");
    expect(screen.getByRole("main")).toHaveFocus();
  });
});

describe("Sidebar collapse persistence", () => {
  it("restores the collapsed state after a reload", async () => {
    setViewportWidth(1280);
    const user = userEvent.setup();
    const first = renderAt("/");
    await screen.findByRole("heading", { level: 1 });

    await user.click(screen.getByRole("button", { name: "Collapse sidebar" }));
    expect(shellElement()).toHaveAttribute("data-sidebar", "collapsed");
    expect(window.localStorage.getItem(SIDEBAR_STORAGE_KEY)).toBe("1");
    first.unmount();

    renderAt("/");
    await screen.findByRole("heading", { level: 1 });
    expect(shellElement()).toHaveAttribute("data-sidebar", "collapsed");
    expect(screen.getByRole("button", { name: "Expand sidebar" })).toHaveAttribute("aria-expanded", "false");
    // Collapsed nav keeps an accessible name.
    expect(screen.getByRole("link", { name: "Home" })).toBeInTheDocument();
  });

  it("falls back to the default and does not crash when storage is unavailable", async () => {
    setViewportWidth(1280);
    vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => {
      throw new DOMException("blocked", "SecurityError");
    });
    vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
      throw new DOMException("blocked", "SecurityError");
    });
    const user = userEvent.setup();
    renderAt("/");
    await screen.findByRole("heading", { level: 1 });

    expect(shellElement()).toHaveAttribute("data-sidebar", "expanded");
    await user.click(screen.getByRole("button", { name: "Collapse sidebar" }));
    expect(shellElement()).toHaveAttribute("data-sidebar", "collapsed");
  });
});

describe("Not found", () => {
  it("shows an accessible not-found page with a link home", async () => {
    setViewportWidth(1280);
    const user = userEvent.setup();
    renderAt("/nope");

    expect(await screen.findByRole("heading", { level: 1, name: "We couldn't find that page." })).toBeInTheDocument();
    await user.click(screen.getByRole("link", { name: "Go to home" }));
    expect(await screen.findByRole("heading", { level: 1, name: "Whiteboard Tutor" })).toBeInTheDocument();
  });
});
