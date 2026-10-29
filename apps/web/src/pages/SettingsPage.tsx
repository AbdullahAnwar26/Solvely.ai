import { useState } from "react";
import { useSession } from "../auth/SessionContext";
import { commonErrorMessage } from "../auth/authApi";
import { useTheme } from "../theme/ThemeContext";
import { THEME_OPTIONS, type ThemePreference } from "../theme/themeStorage";
import { DeleteAccountDialog } from "./DeleteAccountDialog";
import "./settings.css";

const THEME_LABELS: Record<ThemePreference, { label: string; hint: string }> = {
  system: { label: "System", hint: "Follow this device" },
  light: { label: "Light", hint: "Warm paper" },
  dark: { label: "Dark", hint: "Deep ink" },
};

export default function SettingsPage() {
  const { state, signOut } = useSession();
  const { preference, setPreference } = useTheme();
  const email = state.status === "signedIn" ? state.user.email : null;
  const [themeError, setThemeError] = useState<string | null>(null);
  const [signOutPending, setSignOutPending] = useState(false);
  const [signOutError, setSignOutError] = useState<string | null>(null);
  const [deleteOpen, setDeleteOpen] = useState(false);

  const onTheme = async (next: ThemePreference) => {
    setThemeError(null);
    try {
      await setPreference(next);
    } catch (error) {
      setThemeError(`Your theme could not be saved, so it was changed back. ${commonErrorMessage(error)}`);
    }
  };

  const onSignOut = async () => {
    if (signOutPending) return;
    setSignOutPending(true);
    setSignOutError(null);
    try {
      await signOut();
    } catch {
      setSignOutError("Could not sign out. Check your connection and try again.");
      setSignOutPending(false);
    }
  };

  return (
    <div className="page settings">
      <title>Settings · Whiteboard Tutor</title>
      <h1>Settings</h1>

      <section className="settings-section" aria-labelledby="settings-appearance">
        <h2 id="settings-appearance">Appearance</h2>
        <fieldset className="theme-group">
          <legend>Theme</legend>
          <div className="theme-options">
            {THEME_OPTIONS.map((option) => (
              <label key={option} className="theme-option">
                <input
                  type="radio"
                  name="theme"
                  value={option}
                  checked={preference === option}
                  onChange={() => void onTheme(option)}
                />
                <span className="theme-option-text">
                  <span className="theme-option-label">{THEME_LABELS[option].label}</span>
                  <span className="field-hint">{THEME_LABELS[option].hint}</span>
                </span>
              </label>
            ))}
          </div>
        </fieldset>
        {themeError && (
          <p role="alert" className="field-error">
            {themeError}
          </p>
        )}
      </section>

      <section className="settings-section" aria-labelledby="settings-account">
        <h2 id="settings-account">Account</h2>
        {email && <p className="settings-email">Signed in as {email}</p>}
        <div>
          <button
            type="button"
            className="button button-secondary"
            disabled={signOutPending}
            aria-busy={signOutPending}
            onClick={onSignOut}
          >
            {signOutPending ? "Signing out…" : "Sign out"}
          </button>
        </div>
        {signOutError && (
          <p role="alert" className="field-error">
            {signOutError}
          </p>
        )}
      </section>

      <section className="settings-section settings-danger" aria-labelledby="settings-delete">
        <h2 id="settings-delete">Delete account</h2>
        <p>
          Permanently remove your account and all of your data. This can&apos;t be undone.
        </p>
        <div>
          <button type="button" className="button button-danger" onClick={() => setDeleteOpen(true)}>
            Delete account…
          </button>
        </div>
      </section>

      {deleteOpen && <DeleteAccountDialog onClose={() => setDeleteOpen(false)} />}
    </div>
  );
}
