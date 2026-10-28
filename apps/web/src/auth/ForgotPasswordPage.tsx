import { useId, useState, type FormEvent } from "react";
import { Link } from "react-router";
import { AuthLayout } from "./AuthLayout";
import { requestPasswordReset } from "./authApi";
import { errorsFromApi, NO_ERRORS, type FormErrors } from "./formErrors";
import { FormSummary, SubmitButton, TextField } from "./FormParts";

// Identical for every address, so the page never reveals whether an account exists.
const CONFIRMATION =
  "If an account exists for that email, we've sent a link to reset your password. The link expires after an hour.";

export default function ForgotPasswordPage() {
  const baseId = useId();
  const ids = { email: `${baseId}-email` };
  const [email, setEmail] = useState("");
  const [errors, setErrors] = useState<FormErrors>(NO_ERRORS);
  const [focusSignal, setFocusSignal] = useState(0);
  const [pending, setPending] = useState(false);
  const [sent, setSent] = useState(false);

  const fail = (next: FormErrors) => {
    setErrors(next);
    setFocusSignal((n) => n + 1);
  };

  const onSubmit = async (event: FormEvent) => {
    event.preventDefault();
    if (pending) return;
    if (!email.trim()) return fail({ fields: { email: "Enter your email address." }, form: [] });

    setPending(true);
    setErrors(NO_ERRORS);
    try {
      await requestPasswordReset(email.trim());
      setSent(true);
    } catch (error) {
      fail(errorsFromApi(error, ["email"]));
    } finally {
      setPending(false);
    }
  };

  if (sent) {
    return (
      <AuthLayout title="Check your email">
        <p role="status">{CONFIRMATION}</p>
        <p className="auth-alt">
          <Link to="/sign-in">Back to sign in</Link>
        </p>
      </AuthLayout>
    );
  }

  return (
    <AuthLayout
      title="Reset your password"
      lead="Enter your email and we'll send you a link to choose a new password."
    >
      <form onSubmit={onSubmit} noValidate>
        <FormSummary errors={errors} fieldIds={ids} labels={{ email: "Email" }} focusSignal={focusSignal} />
        <TextField
          id={ids.email}
          label="Email"
          type="email"
          name="email"
          autoComplete="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          error={errors.fields.email}
        />
        <SubmitButton pending={pending} idle="Send reset link" busy="Sending…" />
      </form>
      <p className="auth-alt">
        <Link to="/sign-in">Back to sign in</Link>
      </p>
    </AuthLayout>
  );
}
