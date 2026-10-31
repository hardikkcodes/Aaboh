import type { ReactNode } from "react";

import type { SourceSummary } from "../../api/types";
import { formatDateTime, formatRelative } from "../../lib/format";

interface SourcePanelProps {
  source?: SourceSummary | null;
  observedAt?: string | null;
  retrievedAt?: string | null;
  lastSuccessAt?: string | null;
  note?: string | null;
  dataset?: string | null;
  extra?: ReactNode;
  compact?: boolean;
}

export function SourcePanel({
  source,
  observedAt,
  retrievedAt,
  lastSuccessAt,
  note,
  dataset,
  extra,
  compact = false,
}: SourcePanelProps) {
  const hasSource = Boolean(source?.name || source?.slug);
  return (
    <section className={compact ? "panel-muted p-4" : "panel p-5 sm:p-6"} aria-label="Source and provenance">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-xs font-semibold uppercase tracking-[0.16em] text-ink-500">
          Source &amp; provenance
        </h2>
        {source?.is_official ? (
          <span className="chip border-emerald-200 bg-emerald-50 text-emerald-800">Official source</span>
        ) : hasSource ? (
          <span className="chip border-ink-200 bg-white text-ink-600">Provider data</span>
        ) : null}
      </div>

      {hasSource ? (
        <dl className="mt-4 grid gap-x-6 gap-y-3 text-sm sm:grid-cols-2">
          <div>
            <dt className="text-xs font-semibold uppercase tracking-wide text-ink-500">Source</dt>
            <dd className="mt-1 font-medium text-ink-900">{source?.name ?? source?.slug}</dd>
          </div>
          {dataset || source?.dataset ? (
            <div>
              <dt className="text-xs font-semibold uppercase tracking-wide text-ink-500">Dataset</dt>
              <dd className="mt-1 text-ink-700">{dataset ?? source?.dataset}</dd>
            </div>
          ) : null}
          {source?.provider_type ? (
            <div>
              <dt className="text-xs font-semibold uppercase tracking-wide text-ink-500">Provider type</dt>
              <dd className="mt-1 text-ink-700">{source.provider_type.replaceAll("_", " ")}</dd>
            </div>
          ) : null}
          {source?.spatial_resolution_m ? (
            <div>
              <dt className="text-xs font-semibold uppercase tracking-wide text-ink-500">Spatial resolution</dt>
              <dd className="mt-1 text-ink-700">
                {source.spatial_resolution_m >= 1000
                  ? `~${Math.round(source.spatial_resolution_m / 1000)} km`
                  : `${source.spatial_resolution_m} m`}
              </dd>
            </div>
          ) : null}
          {observedAt ? (
            <div>
              <dt className="text-xs font-semibold uppercase tracking-wide text-ink-500">Observation time</dt>
              <dd className="mt-1 text-ink-700">
                {formatDateTime(observedAt)} <span className="text-ink-400">({formatRelative(observedAt)})</span>
              </dd>
            </div>
          ) : null}
          {retrievedAt ? (
            <div>
              <dt className="text-xs font-semibold uppercase tracking-wide text-ink-500">Retrieved</dt>
              <dd className="mt-1 text-ink-700">
                {formatDateTime(retrievedAt)}{" "}
                <span className="text-ink-400">({formatRelative(retrievedAt)})</span>
              </dd>
            </div>
          ) : null}
          {lastSuccessAt ? (
            <div>
              <dt className="text-xs font-semibold uppercase tracking-wide text-ink-500">Last successful ingestion</dt>
              <dd className="mt-1 text-ink-700">
                {formatDateTime(lastSuccessAt)}{" "}
                <span className="text-ink-400">({formatRelative(lastSuccessAt)})</span>
              </dd>
            </div>
          ) : null}
        </dl>
      ) : (
        <p className="prose-civic mt-3">No source metadata is registered for this layer.</p>
      )}

      {source?.attribution ? (
        <p className="mt-4 border-t border-ink-100 pt-3 text-xs leading-5 text-ink-500">
          {source.attribution}
          {source.license_name ? ` · ${source.license_name}` : ""}
        </p>
      ) : null}
      {note ? <p className="mt-3 text-xs leading-5 text-ink-500">{note}</p> : null}
      {extra ? <div className="mt-3">{extra}</div> : null}
    </section>
  );
}
