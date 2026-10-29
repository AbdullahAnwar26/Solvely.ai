import { useEffect, useId, useRef, useState, type FormEvent, type KeyboardEvent } from "react";
import { ApiError } from "../api/client";
import { commonErrorMessage, deleteAccount } from "../auth/authApi";
import { TextField } from "../auth/FormParts";
import { useSession } from "../auth/SessionContext";

const FOCUSABLE = "button:not([disabled]), input:not([disabled]), a[href], [tabindex]:not([tabindex='-1'])";

/**
 * Confirmation for permanent account deletion, on a native modal `<dialog>` (no library).
 * Mount it only while open: focus moves in on mount (to the safe action) and returns to the
 * element that opened it when it unmounts. Escape closes it unless a request is running.
 */
export function DeleteAccountDialog({ onClose }: { onClose: () => void }) {
  const { endSessionAfterDeletion } = useSession();
  const baseId = useId();
  const titleId = `${baseId}-title`;
  const bodyId = `${baseId}-body`;
  const passwordId = `${baseId}-password`;

  const dialogRef = useRef<HTMLDialogElement>(null);
  const cancelRef = useRef<HTMLButtonElement>(null);
  const [password, setPassword] = useState("");
  const [pending, setPending] = useState(false);
  const [fieldError, setFieldError] = useState<string | undefined>();
  const [formError, setFormError] = useState<string | null>(null);

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

  const requestClose = () => {
    if (!pending) onClose();
  };

  const onKeyDown = (event: KeyboardEvent<HTMLDialogElement>) => {
    if (event.key === "Escape") {
      event.preventDefault();
      requestClose();
      return;
    }
    if (event.key !== "Tab") return;
    // Keep Tab inside the dialog even where the browser does not make the page inert.
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

  const onSubmit = async (event: FormEvent) => {
    event.preventDefault();
    if (pending) return;
    setFieldError(undefined);
    setFormError(null);
    if (!password) {
      setFieldError("Enter your password to confirm.");
      document.getElementById(passwordId)?.focus();
      return;
    }
    setPending(true);
    try {
      await deleteAccount(password);
      // The route guard now redirects to /sign-in with the "account deleted" notice.
      endSessionAfterDeletion();
    } catch (error) {
      setPending(false);
      if (error instanceof ApiError && error.code === "invalid_credentials") {
        setPassword("");
        setFieldError(error.message);
        document.getElementById(passwordId)?.focus();
      } else if (error instanceof ApiError && error.fields?.password?.[0]) {
        setFieldError(error.fields.password[0]);
        document.getElementById(passwordId)?.focus();
      } else {
        setFormError(commonErrorMessage(error));
      }
    }
  };

  return (
    <dialog
      ref={dialogRef}
      className="dialog"
      aria-labelledby={titleId}
      aria-describedby={bodyId}
      onKeyDown={onKeyDown}
      onCancel={(event) => {
        event.preventDefault();
        requestClose();
      }}
    >
      <form className="dialog-form" onSubmit={onSubmit} noValidate>
        <h2 id={titleId}>Delete your account?</h2>
        <p id={bodyId}>
          This permanently deletes your account and everything in it. It can&apos;t be undone, and
          there is no way to get your data back.
        </p>
        <TextField
          id={passwordId}
          label="Your password"
          type="password"
          name="password"
          autoComplete="current-password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          error={fieldError}
        />
        {formError && (
          <p role="alert" className="field-error">
            {formError}
          </p>
        )}
        <div className="dialog-actions">
          <button
            ref={cancelRef}
            type="button"
            className="button button-ghost"
            disabled={pending}
            onClick={requestClose}
          >
            Keep my account
          </button>
          <button
            type="submit"
            className="button button-danger"
            disabled={pending}
            aria-busy={pending}
          >
            {pending ? "Deleting…" : "Delete account"}
          </button>
        </div>
      </form>
    </dialog>
  );
}
