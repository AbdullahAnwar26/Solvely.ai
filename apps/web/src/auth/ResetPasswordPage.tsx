import { useId, useState, type FormEvent } from "react";
import { Link, useSearchParams } from "react-router";
import { ApiError } from "../api/client";
import { AuthLayout } from "./AuthLayout";
import { confirmPasswordReset } from "./authApi";
import { errorsFromApi, NO_ERRORS, type FormErrors } from "./formErrors";
import { FormSummary, SubmitButton, TextField } from "./FormParts";

function InvalidLink() {
  return (
    <AuthLayout title="This link is invalid or has expired">
      <p role="alert">Password reset links work once and expire after an hour. Request a new one to continue.</p>
      <p className="auth-alt">
        <Link to="/forgot-password">Request a new reset link</Link>
      </p>
    </AuthLayout>
  );
}

export default function ResetPasswordPage() {
  const [params] = useSearchParams();
  const uid = params.get("uid") ?? "";
  const token = params.get("token") ?? "";
  const baseId = useId();
  const ids = { new_password: `${baseId}-password` };
  const [password, setPassword] = useState("");
  const [errors, setErrors] = useState<FormErrors>(NO_ERRORS);
  const [focusSignal, setFocusSignal] = useState(0);
  const [pending, setPending] = useState(false);
  const [done, setDone] = useState(false);
  const [linkInvalid, setLinkInvalid] = useState(false);

  const fail = (next: FormErrors) => {
    setErrors(next);
    setFocusSignal((n) => n + 1);
  };

  const onSubmit = async (event: FormEvent) => {
    event.preventDefault();
    if (pending) return;
    if (!password) return fail({ fields: { new_password: "Enter a new password." }, form: [] });

    setPending(true);
    setErrors(NO_ERRORS);
    try {
      await confirmPasswordReset({ uid, token, new_password: password });
      setPassword("");
      setDone(true);
    } catch (error) {
      if (error instanceof ApiError && error.code === "invalid_reset_token") setLinkInvalid(true);
      else fail(errorsFromApi(error, ["new_password"]));
    } finally {
      setPending(false);
    }
  };

  if (!uid || !token || linkInvalid) return <InvalidLink />;

  if (done) {
    return (
      <AuthLayout title="Password changed">
        <p role="status">Your password has been changed. Sign in with your new password.</p>
        <p className="auth-alt">
          <Link to="/sign-in">Go to sign in</Link>
        </p>
      </AuthLayout>
    );
  }

  return (
    <AuthLayout title="Choose a new password">
      <form onSubmit={onSubmit} noValidate>
        <FormSummary
          errors={errors}
          fieldIds={ids}
          labels={{ new_password: "New password" }}
          focusSignal={focusSignal}
        />
        <TextField
          id={ids.new_password}
          label="New password"
          type="password"
          name="new-password"
          autoComplete="new-password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          error={errors.fields.new_password}
        />
        <SubmitButton pending={pending} idle="Change password" busy="Changing password…" />
      </form>
    </AuthLayout>
  );
}
