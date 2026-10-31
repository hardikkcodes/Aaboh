import { useEffect, useState, type FormEvent } from "react";
import { Link, useSearchParams } from "react-router-dom";

import { api, fieldErrors, normalizeError } from "../api/client";
import { PageHeader } from "../components/ui/PageHeader";

const MIN_PASSWORD = 10;

function FormError({ error }: { error: unknown }) {
  if (!error) return null;
  const normalized = normalizeError(error);
  return (
    <div className="rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-800" role="alert">
      <p className="font-semibold">{normalized.message}</p>
      {fieldErrors(normalized.details).map((message) => <p key={message} className="mt-1 text-xs">{message}</p>)}
    </div>
  );
}

export function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [sent, setSent] = useState(false);
  const [error, setError] = useState<unknown>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    try {
      await api.post("/auth/password-reset/", { email: email.trim() });
      setSent(true);
    } catch (caught) {
      setError(caught);
    }
  }

  return (
    <div className="shell max-w-lg space-y-6 py-5 sm:py-8">
      <PageHeader title="Reset your password" description="We'll email you a link to choose a new one." />
      {sent ? (
        <p className="panel p-5 text-sm text-ink-700" role="status">
          If an account uses that email, a reset link is on its way.
        </p>
      ) : (
        <form className="panel space-y-4 p-5" onSubmit={(event) => void handleSubmit(event)}>
          <div>
            <label className="label" htmlFor="forgot-email">Email address</label>
            <input id="forgot-email" type="email" autoComplete="email" className="field" required value={email} onChange={(event) => setEmail(event.target.value)} />
          </div>
          <FormError error={error} />
          <button type="submit" className="btn-primary w-full">Send reset link</button>
        </form>
      )}
      <Link to="/login" className="link text-sm">Back to log in</Link>
    </div>
  );
}

export function ResetPasswordPage() {
  const [params] = useSearchParams();
  const [password, setPassword] = useState("");
  const [done, setDone] = useState(false);
  const [error, setError] = useState<unknown>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    try {
      await api.post("/auth/password-reset/confirm/", {
        uid: params.get("uid") ?? "",
        token: params.get("token") ?? "",
        new_password: password,
      });
      setDone(true);
    } catch (caught) {
      setError(caught);
    }
  }

  return (
    <div className="shell max-w-lg space-y-6 py-5 sm:py-8">
      <PageHeader title="Choose a new password" />
      {done ? (
        <p className="panel p-5 text-sm text-ink-700" role="status">
          Your password has changed. <Link to="/login" className="link">Log in</Link>
        </p>
      ) : (
        <form className="panel space-y-4 p-5" onSubmit={(event) => void handleSubmit(event)}>
          <div>
            <label className="label" htmlFor="reset-password">New password</label>
            <input id="reset-password" type="password" autoComplete="new-password" className="field" required minLength={MIN_PASSWORD} value={password} onChange={(event) => setPassword(event.target.value)} />
            <p className="mt-1 text-xs text-ink-500">At least {MIN_PASSWORD} characters.</p>
          </div>
          <FormError error={error} />
          <button type="submit" className="btn-primary w-full">Save password</button>
        </form>
      )}
    </div>
  );
}

export function VerifyEmailPage() {
  const [params] = useSearchParams();
  const token = params.get("token") ?? "";
  const [state, setState] = useState<"checking" | "done" | "failed">("checking");

  useEffect(() => {
    api
      .post("/auth/verify-email/", { token })
      .then(() => setState("done"))
      .catch(() => setState("failed"));
  }, [token]);

  return (
    <div className="shell max-w-lg space-y-6 py-5 sm:py-8">
      <PageHeader title="Confirm your email" />
      <p className="panel p-5 text-sm text-ink-700" role="status">
        {state === "checking"
          ? "Checking your link…"
          : state === "done"
            ? "Your email is confirmed. Thank you."
            : "This link is invalid or has expired. You can send a new one from your account."}
      </p>
      <Link to="/account" className="link text-sm">Go to your account</Link>
    </div>
  );
}
