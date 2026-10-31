import { useEffect } from "react";
import { Link } from "react-router-dom";

import { useMarkNotificationsRead, useNotifications } from "../api/queries";
import { useAuth } from "../auth/context";
import { ErrorState, EmptyState, LoadingPanel } from "../components/ui/Feedback";
import { PageHeader } from "../components/ui/PageHeader";
import { cn, formatRelative } from "../lib/format";
import { useT } from "../lib/i18n";

export function NotificationsPage() {
  const { t } = useT();
  const { isAuthenticated, isLoading } = useAuth();
  const notifications = useNotifications(isAuthenticated);
  const markRead = useMarkNotificationsRead();
  const unread = notifications.data?.unread ?? 0;
  const { mutate } = markRead;

  useEffect(() => {
    if (unread) mutate();
  }, [mutate, unread]);

  if (isLoading) return <div className="shell py-12"><LoadingPanel label="Checking your session" rows={2} /></div>;
  if (!isAuthenticated) {
    return (
      <div className="shell max-w-xl py-12 text-center">
        <h1 className="display-title">{t("Notifications")}</h1>
        <p className="prose-civic mt-2">Log in to get alerts for your routes and saved places.</p>
        <Link to="/login?next=/notifications" className="btn-primary mt-4">{t("Log in")}</Link>
      </div>
    );
  }

  const items = notifications.data?.results ?? [];
  return (
    <div className="shell max-w-2xl space-y-5 py-6 sm:py-10">
      <PageHeader
        eyebrow="Alerts"
        title={t("Notifications")}
        description="Official warnings, heavy rain, dangerous heat, and reports on your routes and saved places."
      />
      {notifications.isError ? (
        <ErrorState error={notifications.error} onRetry={() => void notifications.refetch()} />
      ) : notifications.isLoading ? (
        <LoadingPanel label="Loading notifications" rows={3} />
      ) : items.length ? (
        <ul className="space-y-2">
          {items.map((item) => (
            <li key={item.id}>
              <Link
                to={item.link || "/"}
                className={cn("panel block p-4 hover:border-ink-300", !item.read_at && "border-sky-200 bg-sky-50/50")}
              >
                <p className="text-sm font-semibold text-ink-900">{item.title}</p>
                {item.body ? <p className="mt-0.5 text-sm text-ink-700">{item.body}</p> : null}
                <p className="mt-1 text-xs text-ink-500">{formatRelative(item.created_at)}</p>
              </Link>
            </li>
          ))}
        </ul>
      ) : (
        <EmptyState
          title="Nothing yet"
          description="Save a route or place and alerts will appear here. Having none does not mean conditions are safe."
          action={<Link to="/routes" className="btn-secondary">{t("My routes")}</Link>}
        />
      )}
    </div>
  );
}
