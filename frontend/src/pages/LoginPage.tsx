import { useState, type FormEvent } from "react";
import { Link, Navigate, useNavigate, useSearchParams } from "react-router-dom";

import { fieldErrors, normalizeError } from "../api/client";
import { useAuth } from "../auth/context";
import { InlineSpinner } from "../components/ui/Feedback";
import { PageHeader } from "../components/ui/PageHeader";

function safeNext(value: string | null): string {
  if (!value) return "/account";
  if (!value.startsWith("/") || value.startsWith("//")) return "/account";
  if (value.startsWith("/login") || value.startsWith("/register") || value.startsWith("/reset-password")) return "/account";
  return value;
}

export function LoginPage() {
  const { login, isAuthenticated } = useAuth();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const next = safeNext(searchParams.get("next"));
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [clientError, setClientError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<unknown>(null);

  if (isAuthenticated) {
    return <Navigate to={next} replace />;
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setClientError(null);
    setError(null);
    if (!email.trim() || !password) {
      setClientError("Enter both your email address and password.");
      return;
    }
    setSubmitting(true);
    try {
      await login(email.trim(), password);
      navigate(next, { replace: true });
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
        title="Log in to report and personalise"
        description="An account is required only to submit community observations, follow your reports and save preferences. Weather, alerts, heat, rainfall, air quality and climate pages are public."
        aside={<Link to="/register" className="btn-secondary text-sm">Sign up</Link>}
      />

      <div className="grid gap-6 lg:grid-cols-[1fr_0.9fr]">
        <form className="panel space-y-5 p-5 sm:p-6" onSubmit={(event) => void handleSubmit(event)} noValidate>
          <div>
            <label className="label" htmlFor="login-email">Email address</label>
            <input
              id="login-email"
              type="email"
              autoComplete="email"
              className="field"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              required
            />
          </div>
          <div>
            <label className="label" htmlFor="login-password">Password</label>
            <input
              id="login-password"
              type="password"
              autoComplete="current-password"
              className="field"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              required
            />
          </div>

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
            {submitting ? <InlineSpinner label="Signing in" /> : "Log in"}
          </button>

          <div className="flex flex-wrap justify-between gap-2 text-sm">
            <Link to="/forgot-password" className="link">Forgot password?</Link>
            <Link to="/register" className="link">Sign up</Link>
          </div>
        </form>

        <aside className="space-y-4">
          <div className="panel-muted p-5">
            <p className="eyebrow">Why an account?</p>
            <ul className="mt-3 space-y-3 text-sm leading-6 text-ink-600">
              <li>Reports are attributed internally so they can be edited safely and moderated.</li>
              <li>Your email is never shown on a public report or in the public API.</li>
              <li>Moderation decisions are recorded in an audit history without exposing moderator identities.</li>
              <li>Preferences and saved locations are private to your account.</li>
            </ul>
          </div>
          <div className="panel p-5">
            <p className="eyebrow">Public without logging in</p>
            <p className="prose-civic mt-2">
              You can read every public data layer and community report without an account. Reporting
              requires sign-in to reduce spam and make corrections possible.
            </p>
            <Link to="/" className="btn-secondary mt-4 text-xs">Browse public data</Link>
          </div>
        </aside>
      </div>
    </div>
  );
}
