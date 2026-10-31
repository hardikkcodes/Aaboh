import { useMemo, useState } from "react";
import { Link } from "react-router-dom";

import { normalizeError } from "../api/client";
import { useGenerateInsights, useInsights } from "../api/queries";
import type { Insight } from "../api/types";
import { useAuth } from "../auth/context";
import { InsightCard } from "../components/insights/InsightCard";
import { DataStateNotice, StateBadge } from "../components/ui/DataState";
import { EmptyState, ErrorState, InlineSpinner, LoadingPanel } from "../components/ui/Feedback";
import { PageHeader } from "../components/ui/PageHeader";
import { SectionHeading } from "../components/ui/SectionHeading";
import { StatCard } from "../components/ui/StatCard";
import { MODULE_LABELS, SEVERITY_META, THRESHOLD_META } from "../lib/constants";
import { formatDateTime, formatNumber, titleCase } from "../lib/format";

const SEVERITIES = ["warning", "caution", "info"] as const;

function isSubstantive(insight: Insight): boolean {
  return insight.kind !== "data_availability";
}

function thresholdMeta(key: string) {
  return THRESHOLD_META[key] ?? { label: titleCase(key), unit: "", digits: 0 };
}

export function InsightsPage() {
  const { isModerator } = useAuth();
  const insights = useInsights();
  const generate = useGenerateInsights();
  const [severity, setSeverity] = useState("");
  const [rule, setRule] = useState("");

  const data = insights.data;
  const substantive = useMemo(
    () => (data?.insights ?? []).filter(isSubstantive),
    [data?.insights],
  );
  const availability = useMemo(
    () => (data?.insights ?? []).filter((insight) => !isSubstantive(insight)),
    [data?.insights],
  );
  const rules = useMemo(
    () => Array.from(new Set(substantive.map((insight) => insight.rule_id))).sort(),
    [substantive],
  );
  const filtered = substantive.filter((insight) => {
    if (severity && insight.severity !== severity) return false;
    if (rule && insight.rule_id !== rule) return false;
    return true;
  });
  const warnings = substantive.filter((insight) => insight.severity === "warning").length;
  const cautions = substantive.filter((insight) => insight.severity === "caution").length;
  const generatorError = generate.isError ? normalizeError(generate.error) : null;

  return (
    <div className="shell space-y-10 py-10 sm:py-14">
      <PageHeader
        eyebrow="Decision support · rule engine"
        title="Today's evidence-backed briefing"
        description="Deterministic rules run over stored observations, forecasts and moderated community reports. Every statement links to its evidence. Missing inputs never produce an estimate."
        aside={data ? <StateBadge state={data.state} /> : null}
      />

      <DataStateNotice
        state={data?.state ?? "UNAVAILABLE"}
        title="This is decision support, not an official warning"
        reason={data?.disclaimer ?? "The briefing is unavailable until the insights endpoint responds."}
      >
        <p>
          Follow instructions from IMD, KMC and emergency services. A rule that does not fire is not a
          guarantee that conditions are safe.
        </p>
      </DataStateNotice>

      {insights.isError ? (
        <ErrorState error={insights.error} onRetry={() => void insights.refetch()} />
      ) : insights.isLoading ? (
        <LoadingPanel label="Evaluating rules against stored evidence" rows={4} />
      ) : data ? (
        <>
          <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <StatCard
              label="Substantive insights"
              value={String(substantive.length)}
              detail="Rule outputs that make a condition statement"
            />
            <StatCard
              label="Warnings"
              value={String(warnings)}
              detail="Highest rule severity for the current data"
              tone={warnings ? "alert" : "default"}
            />
            <StatCard
              label="Cautions"
              value={String(cautions)}
              detail="Elevated but not warning-level thresholds"
              tone={cautions ? "warm" : "default"}
            />
            <StatCard
              label="Ruleset"
              value={data.ruleset_version}
              detail={`Generated ${formatDateTime(data.generated_at)} IST`}
              tone="cool"
            />
          </section>

          <section className="panel p-4 sm:p-5">
            <div className="flex flex-wrap items-end gap-4">
              <div className="min-w-44 flex-1">
                <label className="label" htmlFor="insight-severity">Severity</label>
                <select
                  id="insight-severity"
                  className="field"
                  value={severity}
                  onChange={(event) => setSeverity(event.target.value)}
                >
                  <option value="">All severities</option>
                  {SEVERITIES.map((item) => (
                    <option key={item} value={item}>{SEVERITY_META[item].label}</option>
                  ))}
                </select>
              </div>
              <div className="min-w-56 flex-1">
                <label className="label" htmlFor="insight-rule">Rule</label>
                <select
                  id="insight-rule"
                  className="field"
                  value={rule}
                  onChange={(event) => setRule(event.target.value)}
                >
                  <option value="">All rules</option>
                  {rules.map((item) => (
                    <option key={item} value={item}>{titleCase(item)}</option>
                  ))}
                </select>
              </div>
              <div className="flex flex-wrap gap-2">
                <button
                  type="button"
                  className="btn-secondary text-xs"
                  onClick={() => {
                    setSeverity("");
                    setRule("");
                  }}
                >
                  Clear filters
                </button>
                <button
                  type="button"
                  className="btn-ghost text-xs"
                  onClick={() => void insights.refetch()}
                >
                  Refresh
                </button>
                {isModerator ? (
                  <button
                    type="button"
                    className="btn-primary text-xs"
                    disabled={generate.isPending}
                    onClick={() => void generate.mutateAsync("kolkata")}
                  >
                    {generate.isPending ? <InlineSpinner label="Persisting" /> : "Persist snapshot"}
                  </button>
                ) : null}
              </div>
            </div>
            {generatorError ? (
              <p className="mt-3 text-xs font-medium text-red-700" role="alert">
                {generatorError.message}
              </p>
            ) : null}
            {generate.isSuccess ? (
              <p className="mt-3 text-xs font-medium text-emerald-700" role="status">
                Snapshot persisted with {generate.data.persisted ?? 0} insights.
              </p>
            ) : null}
          </section>

          <section>
            <SectionHeading
              eyebrow="Briefing"
              title={filtered.length ? `${filtered.length} active insight${filtered.length === 1 ? "" : "s"}` : "No matching insights"}
              description="Each card names its evidence, source, observation time and quality. Caveats are part of the output, not an afterthought."
            />
            {filtered.length ? (
              <div className="mt-5 grid gap-4 lg:grid-cols-2">
                {filtered.map((insight) => (
                  <InsightCard key={`${insight.rule_id}-${insight.title}`} insight={insight} />
                ))}
              </div>
            ) : substantive.length ? (
              <EmptyState
                className="mt-5"
                title="No insights match these filters"
                description="Broaden the severity or rule filter. The underlying rule outputs still exist for the current stored data."
                action={
                  <button
                    type="button"
                    className="btn-secondary text-sm"
                    onClick={() => {
                      setSeverity("");
                      setRule("");
                    }}
                  >
                    Clear filters
                  </button>
                }
              />
            ) : (
              <EmptyState
                className="mt-5"
                title="No rule crossed its threshold"
                description="No substantive insight was produced from the currently available evidence. This does not mean conditions are safe; it means the stored data did not meet a deterministic rule threshold."
                action={<Link to="/methodology" className="btn-secondary text-sm">Read the thresholds</Link>}
              />
            )}
          </section>

          <section className="grid gap-6 lg:grid-cols-[1.1fr_0.9fr]">
            <div className="panel p-5 sm:p-6">
              <p className="eyebrow">Rule thresholds</p>
              {data.thresholds ? (
                <dl className="mt-3 grid gap-2 sm:grid-cols-2">
                  {Object.entries(data.thresholds).map(([key, value]) => {
                    const meta = thresholdMeta(key);
                    return (
                      <div key={key} className="rounded-xl border border-ink-100 bg-ink-50 p-3">
                        <dt className="text-[0.65rem] uppercase tracking-wide text-ink-500">{meta.label}</dt>
                        <dd className="mt-1 text-sm font-semibold text-ink-900">
                          {formatNumber(value, meta.digits)} {meta.unit}
                        </dd>
                      </div>
                    );
                  })}
                </dl>
              ) : (
                <p className="prose-civic mt-3">Threshold metadata is not exposed by this ruleset version.</p>
              )}
              <p className="mt-4 text-xs leading-5 text-ink-500">{data.methodology}</p>
            </div>

            <div className="panel p-5 sm:p-6">
              <p className="eyebrow">Input availability</p>
              <ul className="mt-3 space-y-2">
                {data.data_availability.map((item) => (
                  <li key={item.module} className="flex items-start justify-between gap-3 rounded-xl border border-ink-100 p-3">
                    <div>
                      <p className="text-sm font-medium text-ink-900">{MODULE_LABELS[item.module] ?? titleCase(item.module)}</p>
                      {item.reason ? <p className="mt-0.5 text-xs leading-5 text-ink-500">{item.reason}</p> : null}
                    </div>
                    <StateBadge state={item.state} />
                  </li>
                ))}
              </ul>
              <p className="mt-3 text-xs leading-5 text-ink-500">
                A module marked unavailable is excluded from rule evaluation rather than replaced with a
                placeholder value.
              </p>
            </div>
          </section>

          {availability.length ? (
            <section>
              <SectionHeading
                eyebrow="Data-availability caveats"
                title="What the briefing could not use"
                description="These are explicit gaps in the evidence, not recommendations."
              />
              <div className="mt-5 grid gap-4 lg:grid-cols-2">
                {availability.map((insight) => (
                  <InsightCard key={`${insight.rule_id}-availability`} insight={insight} />
                ))}
              </div>
            </section>
          ) : null}

          <p className="text-xs leading-5 text-ink-500">
            Generated {formatDateTime(data.generated_at)} IST for {data.area.name}. Ruleset{" "}
            {data.ruleset_version}. Persisted snapshots are moderator-only and never overwrite past
            briefings. {data.disclaimer}
          </p>
        </>
      ) : null}
    </div>
  );
}
