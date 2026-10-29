/**
 * Auth endpoint calls. Every unsafe request first makes sure the CSRF cookie exists
 * (`GET /auth/csrf/` sets it); the client then echoes it in `X-CSRFToken`.
 * Nothing here touches browser storage: the session lives in an HttpOnly cookie.
 */
import { api, ApiError, CSRF_COOKIE_NAME, readCookie } from "../api/client";
import type { ThemePreference } from "../theme/themeStorage";
import type { SessionUser } from "./SessionContext";

export const NETWORK_MESSAGE = "Could not reach the server. Check your connection and retry.";
export const THROTTLED_MESSAGE = "Too many attempts, try again later.";
export const UNEXPECTED_MESSAGE = "Something went wrong. Please try again.";

async function ensureCsrfCookie(): Promise<void> {
  if (readCookie(CSRF_COOKIE_NAME)) return;
  await api.get("/api/v1/auth/csrf/");
}

export async function fetchCurrentUser(signal?: AbortSignal): Promise<SessionUser> {
  return api.get("/api/v1/auth/me/", { signal });
}

export async function register(input: {
  email: string;
  password: string;
  confirm_adult: boolean;
}): Promise<SessionUser> {
  await ensureCsrfCookie();
  return api.post("/api/v1/auth/register/", { body: input });
}

export async function login(input: { email: string; password: string }): Promise<SessionUser> {
  await ensureCsrfCookie();
  return api.post("/api/v1/auth/login/", { body: input });
}

export async function logout(): Promise<void> {
  await ensureCsrfCookie();
  await api.post("/api/v1/auth/logout/");
}

export async function requestPasswordReset(email: string): Promise<void> {
  await ensureCsrfCookie();
  await api.post("/api/v1/auth/password-reset/", { body: { email } });
}

export async function confirmPasswordReset(input: {
  uid: string;
  token: string;
  new_password: string;
}): Promise<void> {
  await ensureCsrfCookie();
  await api.post("/api/v1/auth/password-reset/confirm/", { body: input });
}

export async function updateThemePreference(theme_preference: ThemePreference): Promise<void> {
  await ensureCsrfCookie();
  await api.patch("/api/v1/auth/preferences/", { body: { theme_preference } });
}

export async function deleteAccount(password: string): Promise<void> {
  await ensureCsrfCookie();
  await api.post("/api/v1/auth/account/delete/", { body: { password } });
}

/** Message for failures that every form handles the same way (network, throttle, unknown). */
export function commonErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.code === "network_error") return NETWORK_MESSAGE;
    if (error.code === "throttled" || error.status === 429) return THROTTLED_MESSAGE;
  }
  return UNEXPECTED_MESSAGE;
}
