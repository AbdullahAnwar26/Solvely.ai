import type { Schema } from "@solvely/shared";
import { afterEach, describe, expect, expectTypeOf, it, vi } from "vitest";
import { api, ApiError, GENERIC_ERROR_MESSAGE } from "./client";

function mockFetch(response: Response) {
  const fetchMock = vi.fn<typeof fetch>().mockResolvedValue(response);
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

function json(body: unknown, init: ResponseInit = {}) {
  return new Response(JSON.stringify(body), {
    ...init,
    headers: { "Content-Type": "application/json", ...init.headers },
  });
}

function sentHeaders(fetchMock: ReturnType<typeof mockFetch>) {
  const init = fetchMock.mock.calls[0]?.[1];
  return { init, headers: new Headers(init?.headers) };
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("api client: success", () => {
  it("GET /api/v1/health/ returns the typed body", async () => {
    const fetchMock = mockFetch(json({ status: "ok" }));

    const result = await api.get("/api/v1/health/");

    expectTypeOf(result).toEqualTypeOf<Schema<"Health">>();
    expect(result).toEqual({ status: "ok" });
    const [url, init] = fetchMock.mock.calls[0] ?? [];
    expect(url).toBe("/api/v1/health/");
    expect(init?.method).toBe("GET");
    expect(init?.credentials).toBe("include");
    expect(new Headers(init?.headers).has("X-CSRFToken")).toBe(false);
  });

  it("returns undefined for 204 responses", async () => {
    mockFetch(new Response(null, { status: 204 }));
    await expect(api.post("/api/v1/auth/logout/")).resolves.toBeUndefined();
  });
});

describe("api client: errors", () => {
  it("maps the error envelope to ApiError", async () => {
    mockFetch(
      json(
        {
          error: {
            code: "validation_error",
            message: "Please correct the highlighted fields.",
            retryable: false,
            request_id: "req-123",
            fields: { email: ["Enter a valid email address."] },
          },
        },
        { status: 400 },
      ),
    );

    const error = await api
      .post("/api/v1/auth/login/", { body: { email: "x", password: "y" } })
      .catch((e: unknown) => e);

    expect(error).toBeInstanceOf(ApiError);
    expect(error).toMatchObject({
      status: 400,
      code: "validation_error",
      message: "Please correct the highlighted fields.",
      retryable: false,
      request_id: "req-123",
      fields: { email: ["Enter a valid email address."] },
    });
  });

  it("keeps retryable and request_id from a retryable envelope without fields", async () => {
    mockFetch(
      json(
        { error: { code: "throttled", message: "Too many requests.", retryable: true, request_id: "r9" } },
        { status: 429 },
      ),
    );
    const error = (await api.get("/api/v1/auth/me/").catch((e: unknown) => e)) as ApiError;
    expect(error.code).toBe("throttled");
    expect(error.retryable).toBe(true);
    expect(error.request_id).toBe("r9");
    expect(error.fields).toBeUndefined();
  });

  it("turns a non-envelope body into a generic ApiError", async () => {
    mockFetch(
      new Response("<html>Bad gateway</html>", {
        status: 502,
        headers: { "Content-Type": "text/html", "X-Request-ID": "hdr-1" },
      }),
    );
    const error = (await api.get("/api/v1/health/").catch((e: unknown) => e)) as ApiError;
    expect(error).toBeInstanceOf(ApiError);
    expect(error).toMatchObject({
      status: 502,
      code: "http_error",
      message: GENERIC_ERROR_MESSAGE,
      retryable: true,
      request_id: "hdr-1",
    });
  });

  it("turns a network failure into a retryable ApiError", async () => {
    vi.stubGlobal("fetch", vi.fn<typeof fetch>().mockRejectedValue(new TypeError("Failed to fetch")));
    const error = (await api.get("/api/v1/health/").catch((e: unknown) => e)) as ApiError;
    expect(error).toMatchObject({ status: 0, code: "network_error", retryable: true });
  });
});

describe("api client: CSRF", () => {
  it("sends the csrftoken cookie as X-CSRFToken on unsafe requests", async () => {
    document.cookie = "csrftoken=abc123; path=/";
    const fetchMock = mockFetch(new Response(null, { status: 204 }));

    await api.post("/api/v1/auth/logout/");

    const { init, headers } = sentHeaders(fetchMock);
    expect(init?.method).toBe("POST");
    expect(init?.credentials).toBe("include");
    expect(headers.get("X-CSRFToken")).toBe("abc123");
  });

  it("still sends the request without the header when the cookie is missing", async () => {
    const fetchMock = mockFetch(new Response(null, { status: 204 }));

    await api.delete("/api/v1/auth/account/");

    const { init, headers } = sentHeaders(fetchMock);
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(init?.credentials).toBe("include");
    expect(headers.has("X-CSRFToken")).toBe(false);
  });

  it("serialises JSON bodies", async () => {
    document.cookie = "csrftoken=t0k; path=/";
    const fetchMock = mockFetch(json({ id: 1 }));
    await api.post("/api/v1/auth/login/", { body: { email: "a@b.co", password: "pw" } }).catch(() => undefined);
    const { init, headers } = sentHeaders(fetchMock);
    expect(headers.get("Content-Type")).toBe("application/json");
    expect(init?.body).toBe(JSON.stringify({ email: "a@b.co", password: "pw" }));
  });
});
