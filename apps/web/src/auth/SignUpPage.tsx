import { useId, useState, type FormEvent } from "react";
import { Link } from "react-router";
import { AuthLayout } from "./AuthLayout";
import { register } from "./authApi";
import { errorsFromApi, hasErrors, NO_ERRORS, type FormErrors } from "./formErrors";
import { FormSummary, SubmitButton, TextField } from "./FormParts";
import { useSession } from "./SessionContext";

const FIELDS = ["email", "password", "confirm_adult"] as const;
const LABELS = { email: "Email", password: "Password", confirm_adult: "18 or older confirmation" };

export default function SignUpPage() {
  const baseId = useId();
  const ids = { email: `${baseId}-email`, password: `${baseId}-password`, confirm_adult: `${baseId}-adult` };
  const { signIn } = useSession();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [adult, setAdult] = useState(false);
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
    if (!password) local.fields.password = "Enter a password.";
    if (!adult) local.fields.confirm_adult = "Confirm that you are 18 or older to create an account.";
    if (hasErrors(local)) return fail(local);

    setPending(true);
    setErrors(NO_ERRORS);
    try {
      // The server validates everything again; on success the Learner is already signed in.
      signIn(await register({ email: email.trim(), password, confirm_adult: adult }));
    } catch (error) {
      fail(errorsFromApi(error, FIELDS));
      setPending(false);
    }
  };

  return (
    <AuthLayout title="Create your account" lead="Sign up to start working through problems with a calm tutor.">
      <form onSubmit={onSubmit} noValidate>
        <FormSummary errors={errors} fieldIds={ids} labels={LABELS} focusSignal={focusSignal} />
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
          name="new-password"
          autoComplete="new-password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          error={errors.fields.password}
          hint="Use at least 10 characters that are not easy to guess."
        />
        <div className="field">
          <div className="checkbox-row">
            <input
              id={ids.confirm_adult}
              type="checkbox"
              name="confirm_adult"
              checked={adult}
              onChange={(e) => setAdult(e.target.checked)}
              aria-invalid={errors.fields.confirm_adult ? true : undefined}
              aria-describedby={errors.fields.confirm_adult ? `${ids.confirm_adult}-error` : undefined}
            />
            <label htmlFor={ids.confirm_adult}>I confirm I am 18 or older</label>
          </div>
          {errors.fields.confirm_adult && (
            <p id={`${ids.confirm_adult}-error`} className="field-error">
              {errors.fields.confirm_adult}
            </p>
          )}
        </div>
        <SubmitButton pending={pending} idle="Create account" busy="Creating account…" />
      </form>
      <p className="auth-alt">
        Already have an account? <Link to="/sign-in">Sign in</Link>
      </p>
    </AuthLayout>
  );
}
