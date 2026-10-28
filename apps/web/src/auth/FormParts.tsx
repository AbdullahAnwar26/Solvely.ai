import { useEffect, useRef, type InputHTMLAttributes, type ReactNode } from "react";
import type { FormErrors } from "./formErrors";

/** Error summary: takes focus whenever `focusSignal` changes (each failed submit). */
export function FormSummary({
  errors,
  fieldIds,
  labels,
  focusSignal,
}: {
  errors: FormErrors;
  fieldIds: Record<string, string>;
  labels: Record<string, string>;
  focusSignal: number;
}) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (focusSignal > 0) ref.current?.focus();
  }, [focusSignal]);

  const fieldNames = Object.keys(errors.fields);
  if (fieldNames.length === 0 && errors.form.length === 0) return null;

  return (
    <div ref={ref} className="form-summary" role="alert" tabIndex={-1}>
      <p className="form-summary-title">There is a problem</p>
      <ul>
        {errors.form.map((message) => (
          <li key={message}>{message}</li>
        ))}
        {fieldNames.map((name) => (
          <li key={name}>
            <a
              href={`#${fieldIds[name] ?? ""}`}
              onClick={(event) => {
                event.preventDefault();
                document.getElementById(fieldIds[name] ?? "")?.focus();
              }}
            >
              {labels[name] ?? name}: {errors.fields[name]}
            </a>
          </li>
        ))}
      </ul>
    </div>
  );
}

type TextFieldProps = Omit<InputHTMLAttributes<HTMLInputElement>, "id" | "aria-invalid" | "aria-describedby"> & {
  id: string;
  label: string;
  error?: string | undefined;
  hint?: ReactNode;
};

/** Visible label, optional hint, inline error linked with aria-describedby. */
export function TextField({ id, label, error, hint, ...input }: TextFieldProps) {
  const hintId = hint ? `${id}-hint` : undefined;
  const errorId = error ? `${id}-error` : undefined;
  const describedBy = [hintId, errorId].filter(Boolean).join(" ") || undefined;
  return (
    <div className="field">
      <label htmlFor={id}>{label}</label>
      {hint && (
        <p id={hintId} className="field-hint">
          {hint}
        </p>
      )}
      <input
        {...input}
        id={id}
        className="input"
        aria-invalid={error ? true : undefined}
        aria-describedby={describedBy}
      />
      {error && (
        <p id={errorId} className="field-error">
          {error}
        </p>
      )}
    </div>
  );
}

export function SubmitButton({
  pending,
  idle,
  busy,
}: {
  pending: boolean;
  idle: string;
  busy: string;
}) {
  return (
    <button type="submit" className="button button-primary" disabled={pending} aria-busy={pending}>
      {pending ? busy : idle}
    </button>
  );
}
