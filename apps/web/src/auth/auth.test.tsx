import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { createMemoryRouter, RouterProvider } from "react-router";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { routes } from "../app/routes";
import { envelope, mockApi, notSignedIn, USER, type MockReply } from "../test/mockApi";
import { setViewportWidth } from "../test/viewport";

function renderAt(path: string) {
  const router = createMemoryRouter(routes, { initialEntries: [path] });
  render(<RouterProvider router={router} />);
  return router;
}

const ME = "GET /api/v1/auth/me/";
const signedOutMe = { [ME]: notSignedIn };
const signedInMe = { [ME]: { status: 200, body: USER } };

beforeEach(() => {
  setViewportWidth(1280);
});

afterEach(() => {
  vi.unstubAllGlobals();
});

async function fillSignIn(user: ReturnType<typeof userEvent.setup>, email = "maya@example.com", password = "correct horse battery") {
  await user.type(await screen.findByLabelText("Email"), email);
  await user.type(screen.getByLabelText("Password"), password);
}

describe("session bootstrap and guards", () => {
  it("treats a 403 from /auth/me/ as signed out without showing an error", async () => {
    mockApi(signedOutMe);
    renderAt("/sign-in");
    expect(await screen.findByRole("heading", { level: 1, name: "Sign in" })).toBeInTheDocument();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("redirects a signed-out visit to / to /sign-in", async () => {
    mockApi(signedOutMe);
    const router = renderAt("/");
    expect(await screen.findByRole("heading", { level: 1, name: "Sign in" })).toBeInTheDocument();
    expect(router.state.location.pathname).toBe("/sign-in");
  });

  it("returns to the remembered route after signing in", async () => {
    mockApi({
      ...signedOutMe,
      "POST /api/v1/auth/login/": { status: 200, body: USER },
    });
    const user = userEvent.setup();
    const router = renderAt("/nope");
    await fillSignIn(user);
    await user.click(screen.getByRole("button", { name: "Sign in" }));

    expect(await screen.findByRole("heading", { level: 1, name: "We couldn't find that page." })).toBeInTheDocument();
    expect(router.state.location.pathname).toBe("/nope");
  });

  it("returns home after signing in when no route was remembered", async () => {
    mockApi({ ...signedOutMe, "POST /api/v1/auth/login/": { status: 200, body: USER } });
    const user = userEvent.setup();
    const router = renderAt("/sign-in");
    await fillSignIn(user);
    await user.keyboard("{Enter}");

    expect(await screen.findByRole("heading", { level: 1, name: "Whiteboard Tutor" })).toBeInTheDocument();
    expect(router.state.location.pathname).toBe("/");
  });

  it.each(["/sign-in", "/sign-up", "/forgot-password"])("redirects a signed-in visit to %s home", async (path) => {
    mockApi(signedInMe);
    const router = renderAt(path);
    expect(await screen.findByRole("heading", { level: 1, name: "Whiteboard Tutor" })).toBeInTheDocument();
    expect(router.state.location.pathname).toBe("/");
  });

  it("shows a retry screen when the session check fails to reach the server", async () => {
    mockApi({ [ME]: new TypeError("offline") });
    renderAt("/");
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Could not reach the server. Check your connection and retry.",
    );
    expect(screen.getByRole("button", { name: "Try again" })).toBeInTheDocument();
  });
});

describe("sign up", () => {
  async function fillSignUp(user: ReturnType<typeof userEvent.setup>, confirm = true) {
    await user.type(await screen.findByLabelText("Email"), "maya@example.com");
    await user.type(screen.getByLabelText("Password"), "a long enough passphrase");
    if (confirm) await user.click(screen.getByRole("checkbox", { name: "I confirm I am 18 or older" }));
  }

  it("signs the Learner in, primes CSRF first, and shows the email in the shell", async () => {
    const { calls } = mockApi({
      ...signedOutMe,
      "POST /api/v1/auth/register/": { status: 201, body: USER },
    });
    const user = userEvent.setup();
    const router = renderAt("/sign-up");
    expect(screen.queryByText(/google|facebook|apple/i)).not.toBeInTheDocument();
    await fillSignUp(user);
    await user.click(screen.getByRole("button", { name: "Create account" }));

    expect(await screen.findByRole("heading", { level: 1, name: "Whiteboard Tutor" })).toBeInTheDocument();
    expect(router.state.location.pathname).toBe("/");
    expect(within(screen.getByRole("navigation", { name: "Main" })).getByText("maya@example.com")).toBeInTheDocument();

    const paths = calls.map((c) => `${c.method} ${c.path}`);
    expect(paths.indexOf("GET /api/v1/auth/csrf/")).toBeGreaterThan(-1);
    expect(paths.indexOf("GET /api/v1/auth/csrf/")).toBeLessThan(paths.indexOf("POST /api/v1/auth/register/"));
    const register = calls.find((c) => c.path === "/api/v1/auth/register/");
    expect(register?.body).toEqual({
      email: "maya@example.com",
      password: "a long enough passphrase",
      confirm_adult: true,
    });
    expect(register?.headers.get("X-CSRFToken")).toBe("test-token");
  });

  it("uses the right autocomplete attributes and an unchecked 18+ box by default", async () => {
    mockApi(signedOutMe);
    renderAt("/sign-up");
    expect(await screen.findByLabelText("Email")).toHaveAttribute("autocomplete", "email");
    expect(screen.getByLabelText("Password")).toHaveAttribute("autocomplete", "new-password");
    expect(screen.getByRole("checkbox", { name: "I confirm I am 18 or older" })).not.toBeChecked();
  });

  it("blocks submit without the 18+ box: field error, no request, summary focused", async () => {
    const { calls } = mockApi(signedOutMe);
    const user = userEvent.setup();
    renderAt("/sign-up");
    await fillSignUp(user, false);
    await user.click(screen.getByRole("button", { name: "Create account" }));

    const box = screen.getByRole("checkbox", { name: "I confirm I am 18 or older" });
    expect(box).toHaveAttribute("aria-invalid", "true");
    expect(box).toHaveAccessibleDescription(/18 or older to create an account/);
    expect(screen.getByRole("alert")).toHaveFocus();
    expect(calls.some((c) => c.method === "POST")).toBe(false);
    expect(calls.some((c) => c.path === "/api/v1/auth/csrf/")).toBe(false);
  });

  it("maps server field errors under the right fields and focuses the summary", async () => {
    mockApi({
      ...signedOutMe,
      "POST /api/v1/auth/register/": envelope("validation_error", 400, {
        fields: {
          email: ["That email already has an account."],
          password: ["This password is too short. It must contain at least 10 characters."],
        },
      }),
    });
    const user = userEvent.setup();
    renderAt("/sign-up");
    await fillSignUp(user);
    await user.click(screen.getByRole("button", { name: "Create account" }));

    const email = await screen.findByLabelText("Email");
    expect(email).toHaveAttribute("aria-invalid", "true");
    expect(email).toHaveAccessibleDescription("That email already has an account.");
    const password = screen.getByLabelText("Password");
    expect(password).toHaveAttribute("aria-invalid", "true");
    expect(password).toHaveAccessibleDescription(/at least 10 characters/);

    const summary = screen.getByRole("alert");
    expect(summary).toHaveFocus();
    expect(within(summary).getByRole("link", { name: /Email: That email already has an account/ })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Create account" })).toBeEnabled();
  });

  it("disables the button with a visible busy state while the request is pending", async () => {
    let release: (reply: MockReply) => void = () => undefined;
    const pending = new Promise<MockReply>((resolve) => {
      release = resolve;
    });
    mockApi({ ...signedOutMe, "POST /api/v1/auth/register/": () => pending });
    const user = userEvent.setup();
    renderAt("/sign-up");
    await fillSignUp(user);
    await user.click(screen.getByRole("button", { name: "Create account" }));

    const busy = await screen.findByRole("button", { name: "Creating account…" });
    expect(busy).toBeDisabled();
    release({ status: 201, body: USER });
    expect(await screen.findByRole("heading", { level: 1, name: "Whiteboard Tutor" })).toBeInTheDocument();
  });
});

describe("sign in", () => {
  it("uses the right autocomplete attributes", async () => {
    mockApi(signedOutMe);
    renderAt("/sign-in");
    expect(await screen.findByLabelText("Email")).toHaveAttribute("autocomplete", "email");
    expect(screen.getByLabelText("Password")).toHaveAttribute("autocomplete", "current-password");
  });

  it("shows one generic message for invalid credentials, clears the password and keeps the email", async () => {
    mockApi({
      ...signedOutMe,
      "POST /api/v1/auth/login/": envelope("invalid_credentials", 400, { message: "server text" }),
    });
    const user = userEvent.setup();
    renderAt("/sign-in");
    await fillSignIn(user);
    await user.click(screen.getByRole("button", { name: "Sign in" }));

    const summary = await screen.findByRole("alert");
    expect(summary).toHaveTextContent("That email and password don't match");
    expect(summary).toHaveFocus();
    expect(screen.getByLabelText("Password")).toHaveValue("");
    expect(screen.getByLabelText("Email")).toHaveValue("maya@example.com");
    expect(screen.getByLabelText("Email")).not.toHaveAttribute("aria-invalid");
    expect(screen.getByLabelText("Password")).not.toHaveAttribute("aria-invalid");
  });

  it("shows a retry-later notice when throttled and re-enables the form", async () => {
    mockApi({
      ...signedOutMe,
      "POST /api/v1/auth/login/": envelope("throttled", 429, { retryable: true }),
    });
    const user = userEvent.setup();
    renderAt("/sign-in");
    await fillSignIn(user);
    await user.click(screen.getByRole("button", { name: "Sign in" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Too many attempts, try again later");
    expect(screen.getByRole("button", { name: "Sign in" })).toBeEnabled();
  });

  it("shows a connection message when the network is down and re-enables the button", async () => {
    mockApi({ ...signedOutMe, "POST /api/v1/auth/login/": new TypeError("Failed to fetch") });
    const user = userEvent.setup();
    renderAt("/sign-in");
    await fillSignIn(user);
    await user.click(screen.getByRole("button", { name: "Sign in" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Could not reach the server. Check your connection and retry.",
    );
    expect(screen.getByRole("button", { name: "Sign in" })).toBeEnabled();
  });

  it("reports empty fields in the focused summary without sending a request", async () => {
    const { calls } = mockApi(signedOutMe);
    const user = userEvent.setup();
    renderAt("/sign-in");
    await user.click(await screen.findByRole("button", { name: "Sign in" }));

    expect(screen.getByRole("alert")).toHaveFocus();
    expect(screen.getByLabelText("Email")).toHaveAttribute("aria-invalid", "true");
    expect(calls.some((c) => c.method === "POST")).toBe(false);
  });
});

describe("forgot password", () => {
  it("shows the same confirmation after a 202 regardless of the email", async () => {
    mockApi({ ...signedOutMe, "POST /api/v1/auth/password-reset/": { status: 202, body: {} } });
    const texts: string[] = [];
    for (const email of ["known@example.com", "nobody@example.com"]) {
      const user = userEvent.setup();
      const { unmount } = render(
        <RouterProvider router={createMemoryRouter(routes, { initialEntries: ["/forgot-password"] })} />,
      );
      await user.type(await screen.findByLabelText("Email"), email);
      await user.click(screen.getByRole("button", { name: "Send reset link" }));
      const status = await screen.findByRole("status");
      texts.push(status.textContent ?? "");
      expect(status).not.toHaveTextContent(email);
      unmount();
    }
    expect(texts[0]).toBe(texts[1]);
    expect(texts[0]).toMatch(/If an account exists/);
  });

  it("shows a field error for an invalid email format", async () => {
    mockApi({
      ...signedOutMe,
      "POST /api/v1/auth/password-reset/": envelope("validation_error", 400, {
        fields: { email: ["Enter a valid email address."] },
      }),
    });
    const user = userEvent.setup();
    renderAt("/forgot-password");
    await user.type(await screen.findByLabelText("Email"), "not-an-email");
    await user.click(screen.getByRole("button", { name: "Send reset link" }));

    expect(await screen.findByLabelText("Email")).toHaveAccessibleDescription("Enter a valid email address.");
    expect(screen.getByRole("alert")).toHaveFocus();
  });
});

describe("reset password", () => {
  const link = "/reset-password?uid=abc&token=tok-123";

  it("changes the password with uid and token from the link and offers sign in", async () => {
    const { calls } = mockApi({
      ...signedOutMe,
      "POST /api/v1/auth/password-reset/confirm/": { status: 200, body: {} },
    });
    const user = userEvent.setup();
    renderAt(link);
    const field = await screen.findByLabelText("New password");
    expect(field).toHaveAttribute("autocomplete", "new-password");
    await user.type(field, "a brand new passphrase");
    await user.click(screen.getByRole("button", { name: "Change password" }));

    expect(await screen.findByRole("status")).toHaveTextContent("Your password has been changed");
    expect(screen.getByRole("link", { name: "Go to sign in" })).toHaveAttribute("href", "/sign-in");
    expect(calls.find((c) => c.path.endsWith("/confirm/"))?.body).toEqual({
      uid: "abc",
      token: "tok-123",
      new_password: "a brand new passphrase",
    });
  });

  it("shows an invalid or expired state with a link to request a new one", async () => {
    mockApi({
      ...signedOutMe,
      "POST /api/v1/auth/password-reset/confirm/": envelope("invalid_reset_token", 400),
    });
    const user = userEvent.setup();
    renderAt(link);
    await user.type(await screen.findByLabelText("New password"), "a brand new passphrase");
    await user.click(screen.getByRole("button", { name: "Change password" }));

    expect(await screen.findByRole("heading", { level: 1, name: /invalid or has expired/ })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Request a new reset link" })).toHaveAttribute("href", "/forgot-password");
  });

  it("shows the invalid state straight away when the link has no uid or token", async () => {
    mockApi(signedOutMe);
    renderAt("/reset-password");
    expect(await screen.findByRole("link", { name: "Request a new reset link" })).toBeInTheDocument();
  });

  it("maps a weak-password error to the field and keeps the form usable", async () => {
    mockApi({
      ...signedOutMe,
      "POST /api/v1/auth/password-reset/confirm/": envelope("validation_error", 400, {
        fields: { new_password: ["This password is too common."] },
      }),
    });
    const user = userEvent.setup();
    renderAt(link);
    await user.type(await screen.findByLabelText("New password"), "password1234");
    await user.click(screen.getByRole("button", { name: "Change password" }));

    expect(await screen.findByLabelText("New password")).toHaveAccessibleDescription("This password is too common.");
    expect(screen.getByRole("alert")).toHaveFocus();
    expect(screen.getByRole("button", { name: "Change password" })).toBeEnabled();
    expect(screen.queryByRole("link", { name: "Request a new reset link" })).not.toBeInTheDocument();
  });

  it("stays reachable for a signed-in Learner", async () => {
    mockApi(signedInMe);
    renderAt(link);
    expect(await screen.findByLabelText("New password")).toBeInTheDocument();
  });
});

describe("sign out", () => {
  it("calls logout with CSRF, clears the session and lands on /sign-in", async () => {
    const { calls } = mockApi({ ...signedInMe, "POST /api/v1/auth/logout/": { status: 204 } });
    const user = userEvent.setup();
    const router = renderAt("/");
    await screen.findByRole("heading", { level: 1, name: "Whiteboard Tutor" });
    await user.click(screen.getByRole("button", { name: "Sign out" }));

    expect(await screen.findByRole("heading", { level: 1, name: "Sign in" })).toBeInTheDocument();
    expect(router.state.location.pathname).toBe("/sign-in");
    expect(router.state.location.state).toBeNull();
    const logout = calls.find((c) => c.path === "/api/v1/auth/logout/");
    expect(logout?.method).toBe("POST");
    expect(logout?.headers.get("X-CSRFToken")).toBe("test-token");
  });

  it("shows a message and stays signed in when logout fails", async () => {
    mockApi({ ...signedInMe, "POST /api/v1/auth/logout/": new TypeError("offline") });
    const user = userEvent.setup();
    renderAt("/");
    await screen.findByRole("heading", { level: 1, name: "Whiteboard Tutor" });
    await user.click(screen.getByRole("button", { name: "Sign out" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Could not sign out");
    expect(screen.getByText("maya@example.com")).toBeInTheDocument();
    await waitFor(() => expect(screen.getByRole("button", { name: "Sign out" })).toBeEnabled());
  });
});

describe("browser storage", () => {
  it("writes nothing auth-related to localStorage or sessionStorage across sign-up, sign-out and sign-in", async () => {
    const setItem = vi.spyOn(Storage.prototype, "setItem");
    mockApi({
      ...signedOutMe,
      "POST /api/v1/auth/register/": { status: 201, body: USER },
      "POST /api/v1/auth/logout/": { status: 204 },
      "POST /api/v1/auth/login/": { status: 200, body: USER },
    });
    const user = userEvent.setup();
    renderAt("/sign-up");
    await user.type(await screen.findByLabelText("Email"), "maya@example.com");
    await user.type(screen.getByLabelText("Password"), "a long enough passphrase");
    await user.click(screen.getByRole("checkbox", { name: "I confirm I am 18 or older" }));
    await user.click(screen.getByRole("button", { name: "Create account" }));
    await screen.findByRole("heading", { level: 1, name: "Whiteboard Tutor" });
    await user.click(screen.getByRole("button", { name: "Sign out" }));
    await fillSignIn(user, "maya@example.com", "a long enough passphrase");
    await user.click(screen.getByRole("button", { name: "Sign in" }));
    await screen.findByRole("heading", { level: 1, name: "Whiteboard Tutor" });

    // The only allowed write is the non-sensitive theme hint: key wt.theme, value light|dark|system.
    for (const [key, value] of setItem.mock.calls) {
      expect(key).toBe("wt.theme");
      expect(["light", "dark", "system"]).toContain(value);
    }
    const keys = Array.from({ length: window.localStorage.length }, (_, i) => window.localStorage.key(i));
    expect(keys.every((k) => k === "wt.theme")).toBe(true);
    expect(["light", "dark", "system", null]).toContain(window.localStorage.getItem("wt.theme"));
    expect(window.sessionStorage).toHaveLength(0);
  });
});
