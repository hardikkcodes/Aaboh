import { useState, type FormEvent } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";

import { fieldErrors, normalizeError } from "../api/client";
import { useAuth } from "../auth/context";
import { InlineSpinner } from "../components/ui/Feedback";
import { PageHeader } from "../components/ui/PageHeader";

const MIN_PASSWORD = 10;

export function RegisterPage() {
  const { register, isAuthenticated } = useAuth();
  const navigate = useNavigate();
  const [displayName, setDisplayName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [clientError, setClientError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<unknown>(null);

  if (isAuthenticated) {
    return <Navigate to="/account" replace />;
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setClientError(null);
    setError(null);
    if (displayName.trim().length < 2) {
      setClientError("Choose a display name with at least 2 characters.");
      return;
    }
    if (!email.includes("@")) {
      setClientError("Enter a valid email address.");
      return;
    }
    if (password.length < MIN_PASSWORD) {
      setClientError(`Use a password of at least ${MIN_PASSWORD} characters.`);
      return;
    }
    if (password !== confirmPassword) {
      setClientError("The two passwords do not match.");
      return;
    }
    setSubmitting(true);
    try {
      await register(email.trim(), password, displayName.trim());
      navigate("/account", { replace: true });
    } catch (caught) {
      setError(caught);
    } finally {
      setSubmitting(false);
    }
  }

  const normalized = error ? normalizeError(error) : null;

  return (
    <div className="shell max-w-5xl space-y-6 py-5 sm:py-8">
      <PageHeader
        eyebrow="Account"
        title="Sign up"
        description="Registration is for residents who want to submit local observations and manage their own reports. It does not grant moderator status or make a report official."
        aside={<Link to="/login" className="btn-secondary text-sm">I already have an account</Link>}
      />

      <div className="grid gap-6 lg:grid-cols-[1fr_0.9fr]">
        <form className="panel space-y-5 p-5 sm:p-6" onSubmit={(event) => void handleSubmit(event)} noValidate>
          <div>
            <label className="label" htmlFor="register-name">Display name</label>
            <input
              id="register-name"
              type="text"
              autoComplete="nickname"
              className="field"
              maxLength={80}
              value={displayName}
              onChange={(event) => setDisplayName(event.target.value)}
              required
            />
            <p className="mt-1 text-xs text-ink-400">
              Used for your account only. It is not shown on public reports.
            </p>
          </div>
          <div>
            <label className="label" htmlFor="register-email">Email address</label>
            <input
              id="register-email"
              type="email"
              autoComplete="email"
              className="field"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              required
            />
            <p className="mt-1 text-xs text-ink-400">
              Kept private. We'll send a link to confirm it.
            </p>
          </div>
          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <label className="label" htmlFor="register-password">Password</label>
              <input
                id="register-password"
                type="password"
                autoComplete="new-password"
                className="field"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                required
              />
            </div>
            <div>
              <label className="label" htmlFor="register-confirm">Confirm password</label>
              <input
                id="register-confirm"
                type="password"
                autoComplete="new-password"
                className="field"
                value={confirmPassword}
                onChange={(event) => setConfirmPassword(event.target.value)}
                required
              />
            </div>
          </div>
          <p className="text-xs text-ink-400">At least {MIN_PASSWORD} characters. Avoid reusing a password from another service.</p>

          {clientError ? (
            <div className="rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-800" role="alert">
              {clientError}
            </div>
          ) : null}

          {normalized ? (
            <div className="rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-800" role="alert">
              <p className="font-semibold">{normalized.message}</p>
              {fieldErrors(normalized.details).length ? (
                <ul className="mt-2 list-disc space-y-1 pl-4 text-xs">
                  {fieldErrors(normalized.details).map((message) => <li key={message}>{message}</li>)}
                </ul>
              ) : null}
            </div>
          ) : null}

          <button type="submit" className="btn-primary w-full" disabled={submitting}>
            {submitting ? <InlineSpinner label="Creating account" /> : "Create account"}
          </button>
        </form>

        <aside className="space-y-4">
          <div className="panel-muted p-5">
            <p className="eyebrow">Community rules</p>
            <ul className="mt-3 space-y-3 text-sm leading-6 text-ink-600">
              <li>Report only what you personally observed, not forecasts or social-media claims.</li>
              <li>Use a public landmark or intersection, never an exact home address or personal contact.</li>
              <li>Do not upload images of people without consent.</li>
              <li>Expect moderation. New reports are visibly unverified until checked.</li>
              <li>For emergencies call 112. This platform is not an emergency service.</li>
            </ul>
          </div>
          <div className="panel p-5">
            <p className="eyebrow">No official status</p>
            <p className="prose-civic mt-2">
              An account, a report or a moderator verification does not create an official warning.
              Only warnings issued by official sources are labelled official.
            </p>
            <Link to="/methodology" className="link mt-3 inline-block text-xs">Read the methodology</Link>
          </div>
        </aside>
      </div>
    </div>
  );
}
