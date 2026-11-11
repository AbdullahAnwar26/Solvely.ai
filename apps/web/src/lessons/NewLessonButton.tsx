import { useRef, useState } from "react";
import { useNavigate } from "react-router";
import { ApiError } from "../api/client";
import { PlusIcon } from "../app/icons";
import { createLesson } from "./lessonsApi";

export const NEW_LESSON_ERROR = "We couldn't start a new lesson. Check your connection and try again.";
export const NEW_LESSON_THROTTLED = "You've started a lot of lessons. Please wait a little and try again.";

type Props = {
  /** Show the text label (sidebar expanded or drawer); otherwise icon only with an accessible name. */
  expanded: boolean;
  /** Reports a failure message, or null when a new attempt starts or succeeds. */
  onError: (message: string | null) => void;
  /** Called after the Lesson exists, just before navigating to it. */
  onCreated?: () => void;
};

/** Primary sidebar action: creates a Lesson, then opens it. */
export function NewLessonButton({ expanded, onError, onCreated }: Props) {
  const navigate = useNavigate();
  const [busy, setBusy] = useState(false);
  const inFlight = useRef(false);

  const onClick = async () => {
    if (inFlight.current) return;
    inFlight.current = true;
    setBusy(true);
    onError(null);
    try {
      const lesson = await createLesson();
      onCreated?.();
      await navigate(`/lessons/${lesson.id}`);
    } catch (error) {
      onError(error instanceof ApiError && error.status === 429 ? NEW_LESSON_THROTTLED : NEW_LESSON_ERROR);
    } finally {
      inFlight.current = false;
      setBusy(false);
    }
  };

  const label = busy ? "Starting…" : "New lesson";
  return (
    <button
      type="button"
      className="new-lesson-button"
      aria-label={expanded ? undefined : label}
      aria-busy={busy}
      disabled={busy}
      title={expanded ? undefined : label}
      onClick={onClick}
    >
      <PlusIcon />
      <span className={expanded ? "nav-label" : "visually-hidden"}>{label}</span>
    </button>
  );
}
