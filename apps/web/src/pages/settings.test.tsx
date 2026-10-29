import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { createMemoryRouter, RouterProvider } from "react-router";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { routes } from "../app/routes";
import { envelope, mockApi, USER } from "../test/mockApi";
import { setViewportWidth } from "../test/viewport";

const ME = "GET /api/v1/auth/me/";
const PREFS = "PATCH /api/v1/auth/preferences/";
const DELETE = "POST /api/v1/auth/account/delete/";

function renderAt(path: string) {
  const router = createMemoryRouter(routes, { initialEntries: [path] });
  render(<RouterProvider router={router} />);
  return router;
}

const root = () => document.documentElement;
const radio = (name: string) => screen.findByRole("radio", { name: new RegExp(`^${name}`) });

beforeEach(() => setViewportWidth(1280));
afterEach(() => vi.unstubAllGlobals());

describe("theme", () => {
  it("applies Dark at once, saves it and stores the hint", async () => {
    const { calls } = mockApi({
      [ME]: { status: 200, body: USER },
      [PREFS]: { status: 200, body: { theme_preference: "dark" } },
    });
    const user = userEvent.setup();
    renderAt("/settings");
    await user.click(await radio("Dark"));
    expect(root()).toHaveAttribute("data-theme", "dark");
    expect(window.localStorage.getItem("wt.theme")).toBe("dark");
    await waitFor(() => expect(calls.some((c) => c.method === "PATCH")).toBe(true));
    expect(calls.find((c) => c.method === "PATCH")?.body).toEqual({ theme_preference: "dark" });
  });

  it("reverts and shows a message when saving fails", async () => {
    mockApi({
      [ME]: { status: 200, body: USER },
      [PREFS]: envelope("server_error", 500),
    });
    const user = userEvent.setup();
    renderAt("/settings");
    await user.click(await radio("Dark"));
    expect(await screen.findByRole("alert")).toHaveTextContent(/changed back/);
    expect(root()).not.toHaveAttribute("data-theme");
    expect(await radio("System")).toBeChecked();
    expect(window.localStorage.getItem("wt.theme")).toBe("system");
  });

  it("System removes data-theme", async () => {
    mockApi({
      [ME]: { status: 200, body: { ...USER, theme_preference: "dark" } },
      [PREFS]: { status: 200, body: { theme_preference: "system" } },
    });
    const user = userEvent.setup();
    renderAt("/settings");
    await waitFor(() => expect(root()).toHaveAttribute("data-theme", "dark"));
    await user.click(await radio("System"));
    expect(root()).not.toHaveAttribute("data-theme");
    expect(window.localStorage.getItem("wt.theme")).toBe("system");
  });

  it("server value wins over a stale device hint after the session loads", async () => {
    window.localStorage.setItem("wt.theme", "light");
    mockApi({ [ME]: { status: 200, body: { ...USER, theme_preference: "dark" } } });
    renderAt("/settings");
    expect(await radio("Dark")).toBeChecked();
    expect(root()).toHaveAttribute("data-theme", "dark");
  });

  it("falls back to the server value when storage is unavailable", async () => {
    vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => {
      throw new Error("blocked");
    });
    vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
      throw new Error("blocked");
    });
    mockApi({ [ME]: { status: 200, body: { ...USER, theme_preference: "dark" } } });
    renderAt("/settings");
    expect(await radio("Dark")).toBeChecked();
    expect(root()).toHaveAttribute("data-theme", "dark");
    vi.restoreAllMocks();
  });
});

describe("shell", () => {
  it("has a Settings link in the nav", async () => {
    mockApi({ [ME]: { status: 200, body: USER } });
    renderAt("/");
    const link = await screen.findByRole("link", { name: "Settings" });
    expect(link).toHaveAttribute("href", "/settings");
  });
});

describe("delete account dialog", () => {
  async function openDialog() {
    const user = userEvent.setup();
    const router = renderAt("/settings");
    const trigger = await screen.findByRole("button", { name: /Delete account…/ });
    await user.click(trigger);
    const dialog = await screen.findByRole("dialog", { name: "Delete your account?" });
    return { user, router, trigger, dialog };
  }

  it("moves focus in, traps Tab, and Escape closes and restores focus", async () => {
    mockApi({ [ME]: { status: 200, body: USER } });
    const { user, trigger } = await openDialog();
    const keep = screen.getByRole("button", { name: "Keep my account" });
    expect(keep).toHaveFocus();
    await user.tab({ shift: true });
    expect(screen.getByLabelText("Your password")).toHaveFocus();
    await user.tab({ shift: true });
    expect(screen.getByRole("button", { name: "Delete account" })).toHaveFocus();
    await user.tab();
    expect(screen.getByLabelText("Your password")).toHaveFocus();
    await user.keyboard("{Escape}");
    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
    expect(trigger).toHaveFocus();
  });

  it("keeps the dialog open and shows the message on a wrong password", async () => {
    mockApi({
      [ME]: { status: 200, body: USER },
      [DELETE]: envelope("invalid_credentials", 400, { message: "The password is incorrect." }),
    });
    const { user } = await openDialog();
    await user.type(screen.getByLabelText("Your password"), "wrong password");
    await user.click(screen.getByRole("button", { name: "Delete account" }));
    expect(await screen.findByText("The password is incorrect.")).toBeInTheDocument();
    expect(screen.getByRole("dialog")).toBeInTheDocument();
  });

  it("redirects to /sign-in with a notice after deleting", async () => {
    const { calls } = mockApi({
      [ME]: { status: 200, body: USER },
      [DELETE]: { status: 204 },
    });
    const { user, router } = await openDialog();
    await user.type(screen.getByLabelText("Your password"), "correct horse battery");
    await user.click(screen.getByRole("button", { name: "Delete account" }));
    expect(await screen.findByRole("heading", { level: 1, name: "Sign in" })).toBeInTheDocument();
    expect(router.state.location.pathname).toBe("/sign-in");
    expect(screen.getByRole("status")).toHaveTextContent(/deleted/);
    expect(calls.find((c) => c.path === "/api/v1/auth/account/delete/")?.body).toEqual({
      password: "correct horse battery",
    });
  });
});
