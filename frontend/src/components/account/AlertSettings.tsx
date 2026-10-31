import { useState } from "react";

import { useImpact, useUpdatePreferences } from "../../api/queries";
import type { ImpactResponse, User } from "../../api/types";
import { useAuth } from "../../auth/context";

const LEVELS: Record<ImpactResponse["level"], { label: string; next: string }> = {
  new_neighbour: { label: "New neighbour", next: "Send your first report to become a Reporter." },
  reporter: { label: "Reporter", next: "Reach 5 reports and confirmations to become a Street Watcher." },
  street_watcher: { label: "Street Watcher", next: "Reach 20 to become a Local Guardian." },
  local_guardian: { label: "Local Guardian", next: "Thank you for keeping your area informed." },
};

export function AlertSettings({ user }: { user: User }) {
  const { updateUser } = useAuth();
  const update = useUpdatePreferences();
  const impact = useImpact();
  const [chatId, setChatId] = useState(user.preferences.telegram_chat_id ?? "");
  const [saved, setSaved] = useState(false);
  const level = impact.data ? LEVELS[impact.data.level] : null;

  async function change(payload: Parameters<typeof update.mutateAsync>[0]) {
    setSaved(false);
    updateUser(await update.mutateAsync(payload));
    setSaved(true);
  }

  return (
    <section className="grid gap-6 lg:grid-cols-2">
      <div className="panel space-y-3 p-5">
        <h2 className="section-title">Your alerts</h2>
        <label className="flex items-center gap-2 text-sm text-ink-800">
          <input
            type="checkbox"
            checked={user.preferences.alerts_enabled ?? true}
            onChange={(event) => void change({ alerts_enabled: event.target.checked })}
          />
          Alert me about warnings, heavy rain, heat, and reports on my routes and places
        </label>
        <label className="flex items-center gap-2 text-sm text-ink-800">
          <input
            type="checkbox"
            checked={user.preferences.quiet_hours ?? true}
            onChange={(event) => void change({ quiet_hours: event.target.checked })}
          />
          Quiet hours for Telegram, 10 pm to 6 am (official warnings still arrive)
        </label>
        <div>
          <label className="label" htmlFor="telegram-chat">Telegram chat ID (optional)</label>
          <div className="flex gap-2">
            <input
              id="telegram-chat"
              className="field"
              inputMode="numeric"
              value={chatId}
              onChange={(event) => setChatId(event.target.value.trim())}
            />
            <button
              type="button"
              className="btn-secondary"
              disabled={update.isPending}
              onClick={() => void change({ telegram_chat_id: chatId }).catch(() => undefined)}
            >
              Save
            </button>
          </div>
        </div>
        {update.isError ? <p className="text-sm text-red-800" role="alert">That chat ID doesn't look right.</p> : null}
        {saved ? <p className="text-sm text-emerald-800" role="status">Saved.</p> : null}
      </div>

      <div className="panel p-5">
        <h2 className="section-title">Your impact</h2>
        {impact.data && level ? (
          <>
            <p className="mt-2 font-display text-2xl text-ink-950">{level.label}</p>
            <p className="mt-1 text-sm text-ink-700">{level.next}</p>
            <dl className="mt-3 grid grid-cols-3 gap-2 text-center text-xs text-ink-600">
              <div>
                <dd className="font-display text-xl text-ink-950">{impact.data.reports}</dd>
                <dt>Reports</dt>
              </div>
              <div>
                <dd className="font-display text-xl text-ink-950">{impact.data.reports_confirmed_by_others}</dd>
                <dt>Confirmed by others</dt>
              </div>
              <div>
                <dd className="font-display text-xl text-ink-950">{impact.data.confirmations_given}</dd>
                <dt>Confirmations given</dt>
              </div>
            </dl>
            <p className="mt-3 text-xs text-ink-500">Visible only to you.</p>
          </>
        ) : (
          <p className="mt-2 text-sm text-ink-500">Loading…</p>
        )}
      </div>
    </section>
  );
}
