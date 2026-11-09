/** Lesson endpoint calls (Story 2.1). Lessons are always the signed-in Learner's own. */
import type { Schema } from "@solvely/shared";
import { api } from "../api/client";
import { ensureCsrfCookie } from "../auth/authApi";

export type Lesson = Schema<"Lesson">;

export async function createLesson(): Promise<Lesson> {
  await ensureCsrfCookie();
  return api.post("/api/v1/lessons/", { body: {} });
}

export async function fetchLesson(id: string, signal?: AbortSignal): Promise<Lesson> {
  return api.get("/api/v1/lessons/{id}/", { path: { id }, signal });
}
