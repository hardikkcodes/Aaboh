import type { ReactNode } from "react";

import type { DataState } from "../../api/types";
import { DATA_STATE_META } from "../../lib/constants";
import { cn } from "../../lib/format";

export function StateBadge({ state, className }: { state: DataState; className?: string }) {
  const meta = DATA_STATE_META[state] ?? DATA_STATE_META.UNAVAILABLE;
  return (
    <span className={cn("chip", meta.classes, className)} title={meta.description}>
      <span className={cn("h-1.5 w-1.5 rounded-full", meta.dot)} aria-hidden="true" />
      {meta.label}
    </span>
  );
}

interface DataStateNoticeProps {
  state: DataState;
  title?: string;
  reason?: string | null;
  children?: ReactNode;
  className?: string;
}

export function DataStateNotice({ state, title, reason, children, className }: DataStateNoticeProps) {
  if (state === "AVAILABLE") return null;
  const meta = DATA_STATE_META[state] ?? DATA_STATE_META.UNAVAILABLE;
  const heading =
    title ??
    (state === "STALE"
      ? "This layer may be stale"
      : state === "PARTIAL"
        ? "This layer is only partially available"
        : state === "PROCESSING"
          ? "This layer is being processed"
          : "This layer is unavailable");

  return (
    <div className={cn("rounded-2xl border p-4 sm:p-5", meta.classes, className)} role="status">
      <div className="flex items-start gap-3">
        <span
          className={cn("mt-1.5 h-2.5 w-2.5 shrink-0 rounded-full", meta.dot)}
          aria-hidden="true"
        />
        <div className="min-w-0">
          <p className="text-sm font-semibold">{heading}</p>
          {reason ? <p className="mt-1 text-sm leading-6 opacity-90">{reason}</p> : null}
          {children ? <div className="mt-3 text-sm leading-6">{children}</div> : null}
          <p className="mt-2 text-xs opacity-75">{meta.description}</p>
        </div>
      </div>
    </div>
  );
}
