import type { Insight } from "../../api/types";
import { SEVERITY_META } from "../../lib/constants";
import { formatDateTime, titleCase } from "../../lib/format";

export function InsightCard({ insight, compact = false }: { insight: Insight; compact?: boolean }) {
  const severity = SEVERITY_META[insight.severity] ?? SEVERITY_META.info;
  return (
    <article className="panel flex h-full flex-col p-5 sm:p-6">
      <div className="flex flex-wrap items-center gap-2">
        <span className={`chip ${severity.classes}`}>{severity.label}</span>
        <span className="chip border-ink-200 bg-white text-ink-600">{titleCase(insight.kind)}</span>
        {insight.evidence.some((item) => item.evidence_type === "official_warning") ? (
          <span className="chip border-emerald-200 bg-emerald-50 text-emerald-800">Official warning</span>
        ) : null}
        {insight.evidence.some(
          (item) => item.evidence_type === "community_report" && item.quality_status === "PARTIAL",
        ) ? (
          <span className="chip border-amber-200 bg-amber-50 text-amber-800">Unverified community data</span>
        ) : null}
      </div>

      <h3 className="mt-3 font-display text-xl leading-snug text-ink-950">{insight.title}</h3>
      <p className="prose-civic mt-2">{insight.body}</p>

      {insight.valid_from || insight.valid_until ? (
        <p className="mt-3 text-xs text-ink-500">
          {insight.valid_from ? `From ${formatDateTime(insight.valid_from)}` : null}
          {insight.valid_from && insight.valid_until ? " · " : null}
          {insight.valid_until ? `Until ${formatDateTime(insight.valid_until)}` : null}
        </p>
      ) : null}

      {insight.evidence.length ? (
        <div className="mt-4 border-t border-ink-100 pt-3">
          <p className="text-[0.68rem] font-semibold uppercase tracking-[0.14em] text-ink-500">Evidence</p>
          <ul className="mt-2 space-y-2">
            {insight.evidence.slice(0, compact ? 2 : 6).map((item, index) => (
              <li key={`${item.evidence_type}-${index}`} className="text-xs leading-5 text-ink-600">
                <span className="font-medium text-ink-800">{item.label}</span>
                <span className="text-ink-400"> · {item.source.name ?? "Source unavailable"}</span>
                {item.observed_at ? (
                  <span className="block text-ink-400">{formatDateTime(item.observed_at)}</span>
                ) : null}
                {item.quality_status !== "AVAILABLE" ? (
                  <span className="ml-1 font-semibold text-amber-700">({titleCase(item.quality_status)})</span>
                ) : null}
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      {insight.caveats.length && !compact ? (
        <details className="mt-3 text-xs text-ink-600">
          <summary className="cursor-pointer font-medium text-ink-700">Caveats ({insight.caveats.length})</summary>
          <ul className="mt-2 list-disc space-y-1 pl-4 leading-5">
            {insight.caveats.map((caveat) => (
              <li key={caveat}>{caveat}</li>
            ))}
          </ul>
        </details>
      ) : null}
    </article>
  );
}
