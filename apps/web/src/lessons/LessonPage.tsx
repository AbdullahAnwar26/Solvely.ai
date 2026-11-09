import { lazy, Suspense, useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router";
import { ApiError } from "../api/client";
import { fetchLesson, type Lesson } from "./lessonsApi";

// Excalidraw is large: it loads only when a Lesson is opened.
const Board = lazy(() => import("./Board"));

export const LESSON_NOT_FOUND = "We couldn't find that lesson.";

const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

type State =
  | { status: "loading" }
  | { status: "ready"; lesson: Lesson }
  | { status: "notFound" }
  | { status: "error" };

export function LessonNotFound() {
  return (
    <div className="page lesson-state">
      <title>Lesson not found · Whiteboard Tutor</title>
      <h1>{LESSON_NOT_FOUND}</h1>
      <p className="page-lead">It may have been mistyped, or it isn't one of your lessons.</p>
      <p>
        <Link to="/">Go to home</Link>
      </p>
    </div>
  );
}

export default function LessonPage() {
  const { lessonId = "" } = useParams();
  // A malformed id can never exist: show the same not-found state without a request.
  if (!UUID.test(lessonId)) return <LessonNotFound />;
  return <LoadedLesson key={lessonId} lessonId={lessonId} />;
}

function LoadedLesson({ lessonId }: { lessonId: string }) {
  const [state, setState] = useState<State>({ status: "loading" });
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    fetchLesson(lessonId, controller.signal).then(
      (lesson) => setState({ status: "ready", lesson }),
      (error: unknown) => {
        if (controller.signal.aborted) return;
        setState({ status: error instanceof ApiError && error.status === 404 ? "notFound" : "error" });
      },
    );
    return () => controller.abort();
  }, [lessonId, attempt]);

  const retry = useCallback(() => {
    setState({ status: "loading" });
    setAttempt((n) => n + 1);
  }, []);

  if (state.status === "notFound") return <LessonNotFound />;

  if (state.status === "error") {
    return (
      <div className="page lesson-state">
        <title>Lesson · Whiteboard Tutor</title>
        <h1>We couldn't open this lesson.</h1>
        <p role="alert" className="page-lead">
          Nothing was changed. Check your connection and try again.
        </p>
        <button type="button" className="lesson-retry" onClick={retry}>
          Try again
        </button>
      </div>
    );
  }

  if (state.status === "loading") {
    return (
      <div className="lesson-workspace" aria-busy="true">
        <title>Lesson · Whiteboard Tutor</title>
        <header className="lesson-header">
          <p role="status" className="visually-hidden">
            Loading lesson
          </p>
        </header>
        <div className="board-region" />
      </div>
    );
  }

  const { lesson } = state;
  return (
    <div className="lesson-workspace">
      <title>{`${lesson.title ?? "Untitled lesson"} · Whiteboard Tutor`}</title>
      <header className="lesson-header">
        <h1 className="lesson-title">{lesson.title}</h1>
      </header>
      <section className="board-region" aria-label="Board">
        <Suspense
          fallback={
            <p role="status" className="board-loading">
              Loading the Board…
            </p>
          }
        >
          <Board />
        </Suspense>
      </section>
    </div>
  );
}
