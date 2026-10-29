import { useId, useState, type FormEvent } from "react";
import { Link, useLocation } from "react-router";
import { ApiError } from "../api/client";
import { AuthLayout } from "./AuthLayout";
import { login } from "./authApi";
import { errorsFromApi, hasErrors, NO_ERRORS, type FormErrors } from "./formErrors";
import { FormSummary, SubmitButton, TextField } from "./FormParts";
import { ACCOUNT_DELETED_NOTICE } from "./guards";
import { useSession } from "./SessionContext";

const INVALID_CREDENTIALS_MESSAGE = "That email and password don't match. Check them and try again.";

export default function SignInPage() {
  const baseId = useId();
  const ids = { email: `${baseId}-email`, password: `${baseId}-password` };
  const { signIn } = useSession();
  const location = useLocation();
  const notice =
    typeof location.state === "object" && location.state !== null && "notice" in location.state
      ? (location.state as { notice: unknown }).notice
      : null;
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [errors, setErrors] = useState<FormErrors>(NO_ERRORS);
  const [focusSignal, setFocusSignal] = useState(0);
  const [pending, setPending] = useState(false);

  const fail = (next: FormErrors) => {
    setErrors(next);
    setFocusSignal((n) => n + 1);
  };

  const onSubmit = async (event: FormEvent) => {
    event.preventDefault();
    if (pending) return;
    const local: FormErrors = { fields: {}, form: [] };
    if (!email.trim()) local.fields.email = "Enter your email address.";
    if (!password) local.fields.password = "Enter your password.";
    if (hasErrors(local)) return fail(local);

    setPending(true);
    setErrors(NO_ERRORS);
    try {
      // The route guard sends the Learner to the remembered route (or home) once signed in.
      signIn(await login({ email: email.trim(), password }));
    } catch (error) {
      if (error instanceof ApiError && error.code === "invalid_credentials") {
        // One generic message, no field hints; keep the email, clear the password.
        setPassword("");
        fail({ fields: {}, form: [INVALID_CREDENTIALS_MESSAGE] });
      } else {
        fail(errorsFromApi(error, []));
      }
      setPending(false);
    }
  };

  return (
    <AuthLayout title="Sign in">
      {notice === ACCOUNT_DELETED_NOTICE && (
        <p role="status" className="auth-notice">
          Your account and its data have been deleted.
        </p>
      )}
      <form onSubmit={onSubmit} noValidate>
        <FormSummary
          errors={errors}
          fieldIds={ids}
          labels={{ email: "Email", password: "Password" }}
          focusSignal={focusSignal}
        />
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
        <TextField
          id={ids.password}
          label="Password"
          type="password"
          name="password"
          autoComplete="current-password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          error={errors.fields.password}
        />
        <SubmitButton pending={pending} idle="Sign in" busy="Signing in…" />
      </form>
      <p className="auth-alt">
        <Link to="/forgot-password">Forgot password?</Link>
      </p>
      <p className="auth-alt">
        New here?{" "}
        <Link to="/sign-up" state={location.state}>
          Create an account
        </Link>
      </p>
    </AuthLayout>
  );
}
