import { ApiError } from "../api/client";
import { commonErrorMessage } from "./authApi";

/** Per-field messages plus messages that belong to the form as a whole. */
export type FormErrors = {
  fields: Record<string, string>;
  form: string[];
};

export const NO_ERRORS: FormErrors = { fields: {}, form: [] };

export function hasErrors(errors: FormErrors): boolean {
  return errors.form.length > 0 || Object.keys(errors.fields).length > 0;
}

/**
 * Map a failed request to form errors. `validation_error` fields named in `known` land under
 * their input; any other server field message goes to the summary so nothing is dropped.
 */
export function errorsFromApi(error: unknown, known: readonly string[]): FormErrors {
  if (error instanceof ApiError && error.code === "validation_error") {
    const result: FormErrors = { fields: {}, form: [] };
    for (const [name, messages] of Object.entries(error.fields ?? {})) {
      if (messages.length === 0) continue;
      if (known.includes(name)) result.fields[name] = messages.join(" ");
      else result.form.push(...messages);
    }
    if (!hasErrors(result)) result.form.push(error.message);
    return result;
  }
  return { fields: {}, form: [commonErrorMessage(error)] };
}
