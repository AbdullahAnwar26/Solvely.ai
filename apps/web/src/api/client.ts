/**
 * Typed fetch wrapper over the generated OpenAPI types (@solvely/shared).
 *
 * - Same-origin session cookie auth (AD-6): every request sends `credentials: "include"`.
 * - Unsafe methods echo the `csrftoken` cookie in `X-CSRFToken` (sent even if the cookie is missing).
 * - Non-2xx responses throw `ApiError`, built from the error envelope
 *   `{ "error": { code, message, retryable, request_id, fields? } }` when present.
 */
import type { paths } from "@solvely/shared";

export type HttpMethod = "get" | "post" | "put" | "patch" | "delete";

export const CSRF_COOKIE_NAME = "csrftoken";
export const CSRF_HEADER_NAME = "X-CSRFToken";
const UNSAFE_METHODS: ReadonlySet<HttpMethod> = new Set(["post", "put", "patch", "delete"]);

export const GENERIC_ERROR_MESSAGE = "The request could not be completed.";
export const NETWORK_ERROR_MESSAGE = "We couldn't reach the server. Check your connection and try again.";

export type ApiFieldErrors = Record<string, string[]>;

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly retryable: boolean;
  readonly request_id: string | null;
  readonly fields: ApiFieldErrors | undefined;

  constructor(init: {
    status: number;
    code: string;
    message: string;
    retryable: boolean;
    request_id: string | null;
    fields?: ApiFieldErrors;
  }) {
    super(init.message);
    this.name = "ApiError";
    this.status = init.status;
    this.code = init.code;
    this.retryable = init.retryable;
    this.request_id = init.request_id;
    this.fields = init.fields;
  }
}

// ---- Types derived from the OpenAPI paths ----

type Defined<T> = Exclude<T, undefined>;

/** Paths that declare the given method. */
export type PathsWith<M extends HttpMethod> = {
  [P in keyof paths]: [Defined<paths[P][M]>] extends [never] ? never : P;
}[keyof paths];

type Operation<P extends keyof paths, M extends HttpMethod> = Defined<paths[P][M]>;

type JsonContent<T> = T extends { content: { "application/json": infer Body } } ? Body : undefined;

type SuccessStatus = 200 | 201 | 202 | 204;

/** JSON body of the operation's success response (`undefined` for empty responses). */
export type ResponseBody<P extends keyof paths, M extends HttpMethod> =
  Operation<P, M> extends { responses: infer R }
    ? {
        [S in keyof R & SuccessStatus]: JsonContent<R[S]>;
      }[keyof R & SuccessStatus]
    : never;

/** JSON request body of the operation (`undefined` when it takes none). */
export type RequestBody<P extends keyof paths, M extends HttpMethod> =
  Operation<P, M> extends { requestBody?: infer B } ? JsonContent<Defined<B>> : undefined;

type PathParams<P extends keyof paths, M extends HttpMethod> =
  Operation<P, M> extends { parameters: { path?: infer PP } } ? Defined<PP> : never;

type QueryParams = Record<string, string | number | boolean | undefined>;

export type RequestOptions<P extends keyof paths, M extends HttpMethod> = {
  signal?: AbortSignal;
  query?: QueryParams;
} &([RequestBody<P, M>] extends [undefined] ? { body?: undefined } : { body: RequestBody<P, M> }) &
  ([PathParams<P, M>] extends [never] ? { path?: undefined } : { path: PathParams<P, M> });

// ---- Helpers ----

export function readCookie(name: string): string | null {
  if (typeof document === "undefined" || !document.cookie) return null;
  for (const part of document.cookie.split(";")) {
    const [rawKey, ...rest] = part.trim().split("=");
    if (rawKey === name) {
      try {
        return decodeURIComponent(rest.join("="));
      } catch {
        return rest.join("=");
      }
    }
  }
  return null;
}

function buildUrl(template: string, path: unknown, query: QueryParams | undefined) {
  let url = template.replace(/\{(\w+)\}/g, (_, key: string) => {
    const value = isRecord(path) ? path[key] : undefined;
    if (value === undefined || value === null) throw new Error(`Missing path parameter "${key}"`);
    return encodeURIComponent(String(value));
  });
  if (query) {
    const params = new URLSearchParams();
    for (const [key, value] of Object.entries(query)) {
      if (value !== undefined) params.append(key, String(value));
    }
    const search = params.toString();
    if (search) url += `?${search}`;
  }
  return url;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function parseFields(value: unknown): ApiFieldErrors | undefined {
  if (!isRecord(value)) return undefined;
  const fields: ApiFieldErrors = {};
  for (const [key, messages] of Object.entries(value)) {
    if (Array.isArray(messages)) fields[key] = messages.map(String);
  }
  return fields;
}

/** Build an ApiError from a non-2xx response, using the envelope when it is well formed. */
export async function toApiError(response: Response): Promise<ApiError> {
  const headerRequestId = response.headers.get("X-Request-ID");
  let body: unknown = undefined;
  try {
    body = await response.json();
  } catch {
    // Not JSON: fall through to the generic error.
  }
  const envelope = isRecord(body) ? body.error : undefined;
  if (isRecord(envelope) && typeof envelope.code === "string" && typeof envelope.message === "string") {
    return new ApiError({
      status: response.status,
      code: envelope.code,
      message: envelope.message,
      retryable: envelope.retryable === true,
      request_id: typeof envelope.request_id === "string" ? envelope.request_id : headerRequestId,
      fields: parseFields(envelope.fields),
    });
  }
  return new ApiError({
    status: response.status,
    code: "http_error",
    message: GENERIC_ERROR_MESSAGE,
    retryable: response.status >= 500 || response.status === 429,
    request_id: headerRequestId,
  });
}

// ---- Request ----

export async function apiRequest<M extends HttpMethod, P extends PathsWith<M>>(
  method: M,
  path: P,
  ...[options]: OptionsArg<P, M>
): Promise<ResponseBody<P, M>> {
  const headers = new Headers({ Accept: "application/json" });
  const body = options?.body;
  if (body !== undefined) headers.set("Content-Type", "application/json");
  if (UNSAFE_METHODS.has(method)) {
    const token = readCookie(CSRF_COOKIE_NAME);
    if (token) headers.set(CSRF_HEADER_NAME, token);
  }

  let response: Response;
  try {
    response = await fetch(buildUrl(path, options?.path, options?.query), {
      method: method.toUpperCase(),
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
      credentials: "include",
      signal: options?.signal,
    });
  } catch (error) {
    // Caller-initiated cancel stays an AbortError; anything else is a network failure.
    if (error instanceof DOMException && error.name === "AbortError") throw error;
    throw new ApiError({
      status: 0,
      code: "network_error",
      message: NETWORK_ERROR_MESSAGE,
      retryable: true,
      request_id: null,
    });
  }

  if (!response.ok) throw await toApiError(response);
  if (response.status === 204) return undefined as ResponseBody<P, M>;
  const text = await response.text();
  return (text ? JSON.parse(text) : undefined) as ResponseBody<P, M>;
}

/** Shorthands: `api.get("/api/v1/health/")`. */
export const api = {
  get: <P extends PathsWith<"get">>(path: P, ...rest: OptionsArg<P, "get">) =>
    apiRequest("get", path, ...rest),
  post: <P extends PathsWith<"post">>(path: P, ...rest: OptionsArg<P, "post">) =>
    apiRequest("post", path, ...rest),
  put: <P extends PathsWith<"put">>(path: P, ...rest: OptionsArg<P, "put">) =>
    apiRequest("put", path, ...rest),
  patch: <P extends PathsWith<"patch">>(path: P, ...rest: OptionsArg<P, "patch">) =>
    apiRequest("patch", path, ...rest),
  delete: <P extends PathsWith<"delete">>(path: P, ...rest: OptionsArg<P, "delete">) =>
    apiRequest("delete", path, ...rest),
};

/** Options are optional only when the operation needs neither a body nor path parameters. */
type OptionsArg<P extends keyof paths, M extends HttpMethod> = [RequestBody<P, M>] extends [undefined]
  ? [PathParams<P, M>] extends [never]
    ? [options?: RequestOptions<P, M>]
    : [options: RequestOptions<P, M>]
  : [options: RequestOptions<P, M>];
