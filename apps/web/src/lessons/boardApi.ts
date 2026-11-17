/** Board endpoint calls (Story 2.3): load the latest revision, save a new one. */
import type { Schema } from "@solvely/shared";
import { api } from "../api/client";
import { ensureCsrfCookie } from "../auth/authApi";
import type { BoardState } from "./boardSerialize";

export type BoardSaveRequest = Schema<"BoardSaveRequest">;
export type BoardSaveResponse = Schema<"BoardSaveResponse">;

/** `ApiError.code` of a 409 save: the Board changed elsewhere and nothing was written. */
export const REVISION_CONFLICT = "revision_conflict";

export function fetchBoard(lessonId: string, signal?: AbortSignal): Promise<BoardState> {
  return api.get("/api/v1/lessons/{id}/board/", { path: { id: lessonId }, signal });
}

export async function saveBoard(lessonId: string, body: BoardSaveRequest): Promise<BoardSaveResponse> {
  await ensureCsrfCookie();
  return api.put("/api/v1/lessons/{id}/board/", { path: { id: lessonId }, body });
}
