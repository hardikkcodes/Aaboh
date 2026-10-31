import type { ReactNode } from "react";

import { fieldErrors, normalizeError } from "../../api/client";
import { cn } from "../../lib/format";

export function LoadingPanel({ label = "Loading data", rows = 3 }: { label?: string; rows?: number }) {
  return (
    <div className="panel p-6" role="status" aria-live="polite">
      <p className="text-sm font-medium text-ink-600">{label}…</p>
      <div className="mt-4 space-y-2.5">
        {Array.from({ length: rows }).map((_, index) => (
          <div
            key={index}
            className="h-4 animate-pulse rounded-full bg-ink-100"
            style={{ width: `${88 - index * 12}%` }}
          />
        ))}
      </div>
    </div>
  );
}

export function ErrorState({
  error,
  onRetry,
  className,
}: {
  error: unknown;
  onRetry?: () => void;
  className?: string;
}) {
  const normalized = normalizeError(error);
  const fields = fieldErrors(normalized.details);
  return (
    <div className={cn("rounded-2xl border border-red-200 bg-red-50 p-5", className)} role="alert">
      <p className="text-sm font-semibold text-red-900">{normalized.message}</p>
      <p className="mt-1 text-xs font-mono uppercase tracking-wide text-red-700">{normalized.code}</p>
      {fields.length ? (
        <ul className="mt-3 list-disc space-y-1 pl-4 text-sm text-red-800">
          {fields.map((message) => (
            <li key={message}>{message}</li>
          ))}
        </ul>
      ) : null}
      {onRetry ? (
        <button type="button" className="btn-secondary mt-4" onClick={onRetry}>
          Try again
        </button>
      ) : null}
    </div>
  );
}

export function EmptyState({
  title,
  description,
  action,
  className,
}: {
  title: string;
  description: string;
  action?: ReactNode;
  className?: string;
}) {
  return (
    <div className={cn("panel-muted p-6 text-center sm:p-10", className)}>
      <p className="font-display text-xl text-ink-900">{title}</p>
      <p className="prose-civic mx-auto mt-2 max-w-xl">{description}</p>
      {action ? <div className="mt-4 flex justify-center">{action}</div> : null}
    </div>
  );
}

export function CaveatList({ caveats, title = "Things to keep in mind" }: { caveats: string[]; title?: string }) {
  if (!caveats.length) return null;
  return (
    <div className="rounded-xl border border-amber-200 bg-amber-50/70 p-4">
      <p className="text-xs font-semibold uppercase tracking-wide text-amber-900">{title}</p>
      <ul className="mt-2 list-disc space-y-1 pl-4 text-xs leading-5 text-amber-900">
        {caveats.map((caveat) => (
          <li key={caveat}>{caveat}</li>
        ))}
      </ul>
    </div>
  );
}

export function InlineSpinner({ label = "Working" }: { label?: string }) {
  return (
    <span className="inline-flex items-center gap-2 text-sm text-ink-600" role="status">
      <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-ink-200 border-t-ink-700" />
      {label}…
    </span>
  );
}
