import { useState, type FormEvent } from "react";

import { api, fieldErrors, normalizeError, TOKEN_KEY } from "../../api/client";
import type { AuthResponse } from "../../api/types";
import { useAuth } from "../../auth/context";

function errorText(error: unknown): string {
  const normalized = normalizeError(error);
  return fieldErrors(normalized.details)[0] ?? normalized.message;
}

export function AccountSecurity() {
  const { user, updateUser, logout } = useAuth();
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [deletePassword, setDeletePassword] = useState("");
  const [message, setMessage] = useState<string | null>(null);

  async function changePassword(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    try {
      const response = await api.post<AuthResponse>("/auth/change-password/", {
        current_password: current,
        new_password: next,
      });
      localStorage.setItem(TOKEN_KEY, response.data.token);
      updateUser(response.data.user);
      setCurrent("");
      setNext("");
      setMessage("Password changed. Other devices have been logged out.");
    } catch (error) {
      setMessage(errorText(error));
    }
  }

  async function resend() {
    try {
      await api.post("/auth/verify-email/resend/");
      setMessage("Confirmation email sent.");
    } catch (error) {
      setMessage(errorText(error));
    }
  }

  async function deleteAccount(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!window.confirm("Delete your account for good? This can't be undone.")) return;
    try {
      await api.delete("/users/me/", { data: { password: deletePassword } });
      await logout();
    } catch (error) {
      setMessage(errorText(error));
    }
  }

  return (
    <section className="panel space-y-5 p-5 sm:p-6">
      <h2 className="section-title">Security</h2>
      {message ? <p className="text-sm text-ink-700" role="status">{message}</p> : null}

      {user && !user.email_verified ? (
        <div className="flex flex-wrap items-center justify-between gap-2 text-sm text-ink-700">
          <span>Your email isn't confirmed yet.</span>
          <button type="button" className="btn-secondary text-xs" onClick={() => void resend()}>Send confirmation email</button>
        </div>
      ) : null}

      <form className="grid gap-3 sm:grid-cols-[1fr_1fr_auto] sm:items-end" onSubmit={(event) => void changePassword(event)}>
        <div>
          <label className="label" htmlFor="current-password">Current password</label>
          <input id="current-password" type="password" autoComplete="current-password" className="field" required value={current} onChange={(event) => setCurrent(event.target.value)} />
        </div>
        <div>
          <label className="label" htmlFor="new-password">New password</label>
          <input id="new-password" type="password" autoComplete="new-password" className="field" required value={next} onChange={(event) => setNext(event.target.value)} />
        </div>
        <button type="submit" className="btn-secondary">Change password</button>
      </form>

      <form className="grid gap-3 border-t border-ink-100 pt-4 sm:grid-cols-[1fr_auto] sm:items-end" onSubmit={(event) => void deleteAccount(event)}>
        <div>
          <label className="label" htmlFor="delete-password">Delete account</label>
          <input id="delete-password" type="password" autoComplete="current-password" placeholder="Your password" className="field" required value={deletePassword} onChange={(event) => setDeletePassword(event.target.value)} />
          <p className="mt-1 text-xs text-ink-500">Your saved places and routes are removed. Public reports stay, without your name.</p>
        </div>
        <button type="submit" className="btn-danger">Delete account</button>
      </form>
    </section>
  );
}
