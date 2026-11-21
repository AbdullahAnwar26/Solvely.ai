import { useEffect, useId, useRef, useState, type KeyboardEvent } from "react";
import type { SaveStatus as Status } from "./useAutosave";

const LABEL: Record<Status, string> = {
  saved: "Saved",
  saving: "Saving…",
  error: "Not saved",
  conflict: "Conflict",
};

/**
 * Save status for the Board header (EXPERIENCE.md save states). The visible text follows the
 * state; a separate polite live region announces only failures and recovery, never every save.
 */
export function SaveStatus({ status, retrying, onRetry }: { status: Status; retrying: boolean; onRetry: () => void }) {
  // Derived on status change during render (no effect): what to announce, and whether a
  // failure happened since the last confirmed save (so recovery can be announced).
  const [previous, setPrevious] = useState<Status>(status);
  const [failedBefore, setFailedBefore] = useState(false);
  const [announcement, setAnnouncement] = useState("");
  if (status !== previous) {
    setPrevious(status);
    if (status === "error" && !failedBefore) {
      setFailedBefore(true);
      setAnnouncement("Not saved. Your changes are still on this page.");
    } else if (status === "conflict") {
      setAnnouncement("Not saved: this lesson was changed somewhere else.");
    } else if (status === "saved" && failedBefore) {
      setFailedBefore(false);
      setAnnouncement("Saved again.");
    }
  }

  return (
    <div className="save-status" data-status={status}>
      <span className="save-status-label">{LABEL[status]}</span>
      {status === "error" && (
        <button type="button" className="save-status-retry" onClick={onRetry}>
          Retry
        </button>
      )}
      {status === "error" && retrying && <span className="visually-hidden">Trying again shortly.</span>}
      <span className="visually-hidden" role="status" aria-live="polite">
        {announcement}
      </span>
    </div>
  );
}

const FOCUSABLE = "button:not([disabled])";

/**
 * Inline conflict alert: another tab or device saved this Board. Autosave has stopped; the only
 * way forward offered here is loading the newer version, which discards local changes, so it
 * asks first.
 */
export function ConflictAlert({ onReload }: { onReload: () => Promise<boolean> }) {
  const [confirming, setConfirming] = useState(false);
  const [loading, setLoading] = useState(false);
  const [failed, setFailed] = useState(false);

  const confirm = async () => {
    setLoading(true);
    setFailed(false);
    const ok = await onReload();
    setLoading(false);
    if (ok) setConfirming(false);
    else setFailed(true);
  };

  return (
    <div className="board-conflict" role="alert">
      <p className="board-conflict-text">
        This lesson was changed in another tab or device, so your latest changes here were not saved. Nothing was
        overwritten.
      </p>
      <button type="button" className="board-action board-action-primary" onClick={() => setConfirming(true)}>
        Reload latest
      </button>
      {confirming && (
        <ReloadDialog
          loading={loading}
          failed={failed}
          onConfirm={confirm}
          onCancel={() => {
            if (!loading) {
              setConfirming(false);
              setFailed(false);
            }
          }}
        />
      )}
    </div>
  );
}

function ReloadDialog({
  loading,
  failed,
  onConfirm,
  onCancel,
}: {
  loading: boolean;
  failed: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}) {
  const baseId = useId();
  const dialogRef = useRef<HTMLDialogElement>(null);
  const cancelRef = useRef<HTMLButtonElement>(null);

  // Mounted only while open: focus the safe action, return focus to the opener on close.
  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return;
    const opener = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    if (!dialog.open) dialog.showModal();
    cancelRef.current?.focus();
    return () => {
      if (dialog.open) dialog.close();
      opener?.focus();
    };
  }, []);

  const onKeyDown = (event: KeyboardEvent<HTMLDialogElement>) => {
    if (event.key === "Escape") {
      event.preventDefault();
      onCancel();
      return;
    }
    if (event.key !== "Tab") return;
    const items = Array.from(dialogRef.current?.querySelectorAll<HTMLElement>(FOCUSABLE) ?? []);
    const first = items[0];
    const last = items[items.length - 1];
    if (!first || !last) return;
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  };

  return (
    <dialog
      ref={dialogRef}
      className="board-dialog"
      aria-labelledby={`${baseId}-title`}
      aria-describedby={`${baseId}-body`}
      onKeyDown={onKeyDown}
      onCancel={(event) => {
        event.preventDefault();
        onCancel();
      }}
    >
      <h2 id={`${baseId}-title`} className="board-dialog-title">
        Load the latest version?
      </h2>
      <p id={`${baseId}-body`}>
        The changes you made here since the last save will be discarded and replaced by the version saved elsewhere.
      </p>
      {failed && (
        <p role="alert" className="board-dialog-error">
          We couldn&apos;t load the latest version. Check your connection and try again.
        </p>
      )}
      <div className="board-dialog-actions">
        <button ref={cancelRef} type="button" className="board-action" disabled={loading} onClick={onCancel}>
          Keep editing
        </button>
        <button
          type="button"
          className="board-action board-action-primary"
          disabled={loading}
          aria-busy={loading}
          onClick={onConfirm}
        >
          {loading ? "Loading…" : "Discard my changes and reload"}
        </button>
      </div>
    </dialog>
  );
}
