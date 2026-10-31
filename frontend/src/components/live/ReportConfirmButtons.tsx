import { useState } from "react";
import { Link } from "react-router-dom";

import { normalizeError } from "../../api/client";
import { useConfirmIncident } from "../../api/queries";
import type { ConfirmationKind } from "../../api/types";
import { useAuth } from "../../auth/context";
import { useT } from "../../lib/i18n";

const THANKS: Record<ConfirmationKind, string> = {
  still_there: "Thanks. You confirmed this is still there.",
  cleared: "Thanks. Your update was recorded.",
  wrong: "Thanks. Moderators can review this report.",
};

/** One-tap resident updates. Votes stay separate from moderator verification. */
export function ReportConfirmButtons({ reportId, isOwner = false }: { reportId: string; isOwner?: boolean }) {
  const { t } = useT();
  const { isAuthenticated } = useAuth();
  const confirm = useConfirmIncident();
  const [done, setDone] = useState<ConfirmationKind | null>(null);

  if (!isAuthenticated) {
    return (
      <Link to={`/login?next=/reports/${reportId}`} className="text-xs font-semibold text-ink-700 underline">
        Log in to confirm or clear
      </Link>
    );
  }

  function vote(kind: ConfirmationKind) {
    setDone(null);
    confirm.mutate({ id: reportId, kind }, { onSuccess: () => setDone(kind) });
  }

  const error = confirm.isError ? normalizeError(confirm.error) : null;
  const errorDetail = error && typeof error.details === "object" ? error.details?.kind?.[0] : null;

  return (
    <div>
      <div className="flex flex-wrap gap-1.5">
        {isOwner ? null : (
          <button
            type="button"
            className="btn-secondary !px-2.5 !py-1 text-xs"
            disabled={confirm.isPending}
            onClick={() => vote("still_there")}
          >
            {t("Still there")}
          </button>
        )}
        <button
          type="button"
          className="btn-secondary !px-2.5 !py-1 text-xs"
          disabled={confirm.isPending}
          onClick={() => vote("cleared")}
        >
          {t("Cleared")}
        </button>
        {isOwner ? null : (
          <button
            type="button"
            className="btn-ghost !px-2.5 !py-1 text-xs"
            disabled={confirm.isPending}
            onClick={() => vote("wrong")}
          >
            {t("Looks wrong")}
          </button>
        )}
      </div>
      {done ? (
        <p className="mt-1.5 text-xs text-ink-600" role="status">{THANKS[done]}</p>
      ) : null}
      {error ? (
        <p className="mt-1.5 text-xs text-red-800" role="alert">{errorDetail ?? error.message}</p>
      ) : null}
    </div>
  );
}
