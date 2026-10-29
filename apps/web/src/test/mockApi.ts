import { vi } from "vitest";
import type { ThemePreference } from "../theme/themeStorage";

export type MockReply = { status?: number; body?: unknown } | Error;
export type MockHandler = (request: { body: unknown; headers: Headers }) => MockReply | Promise<MockReply>;

export type RecordedCall = { method: string; path: string; body: unknown; headers: Headers };

export const USER = {
  id: 1,
  email: "maya@example.com",
  adult_confirmed_at: "2026-10-29T10:00:00Z",
  theme_preference: "system" as ThemePreference,
};

export function envelope(
  code: string,
  status: number,
  extra: { message?: string; fields?: Record<string, string[]>; retryable?: boolean } = {},
) {
  return {
    status,
    body: {
      error: {
        code,
        message: extra.message ?? "Something is wrong.",
        retryable: extra.retryable ?? false,
        request_id: "req-1",
        ...(extra.fields ? { fields: extra.fields } : {}),
      },
    },
  };
}

/**
 * Stub `fetch` with handlers keyed "METHOD /path" (query string ignored). `GET /api/v1/auth/csrf/`
 * defaults to setting a csrftoken cookie, like the real endpoint. Unknown routes fail the test.
 */
export function mockApi(handlers: Record<string, MockHandler | MockReply>) {
  const calls: RecordedCall[] = [];
  const table: Record<string, MockHandler | MockReply> = {
    "GET /api/v1/auth/csrf/": () => {
      document.cookie = "csrftoken=test-token; path=/";
      return { status: 204 };
    },
    ...handlers,
  };
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = new URL(String(input), "http://localhost");
    const method = (init?.method ?? "GET").toUpperCase();
    const headers = new Headers(init?.headers);
    const body = typeof init?.body === "string" ? (JSON.parse(init.body) as unknown) : undefined;
    calls.push({ method, path: url.pathname, body, headers });
    const entry = table[`${method} ${url.pathname}`];
    if (!entry) throw new Error(`Unmocked request: ${method} ${url.pathname}`);
    const reply = typeof entry === "function" ? await entry({ body, headers }) : entry;
    if (reply instanceof Error) throw reply;
    const status = reply.status ?? 200;
    const text = reply.body === undefined ? null : JSON.stringify(reply.body);
    return new Response(status === 204 ? null : text, {
      status,
      headers: { "Content-Type": "application/json" },
    });
  });
  vi.stubGlobal("fetch", fetchMock);
  return { calls, fetchMock };
}

export const notSignedIn = envelope("not_authenticated", 403);
