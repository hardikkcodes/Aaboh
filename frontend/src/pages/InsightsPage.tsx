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
import { SEVERITY_META } from "../lib/constants";
import { formatDateTime, titleCase } from "../lib/format";

const SEVERITIES = ["warning", "caution", "info"] as const;

function isSubstantive(insight: Insight): boolean {
  return insight.kind !== "data_availability";
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
    <div className="shell space-y-6 py-5 sm:py-8">
      <PageHeader
        title="What today's data means for you"
        description="Each card says what is happening, what it means in plain words, what to do, and where the information came from."
        aside={data ? <StateBadge state={data.state} /> : null}
      />

      <DataStateNotice
        state={data?.state ?? "UNAVAILABLE"}
        title="A guide, not an official warning"
        reason={data?.disclaimer ?? "The briefing is unavailable until the insights endpoint responds."}
      >
        <p>
          Always follow IMD, KMC and emergency services.
        </p>
      </DataStateNotice>

      {insights.isError ? (
        <ErrorState error={insights.error} onRetry={() => void insights.refetch()} />
      ) : insights.isLoading ? (
        <LoadingPanel label="Reading today's data" rows={4} />
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
                title="Nothing matches these filters"
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
                title="Nothing unusual right now"
                description="Today's data shows nothing that needs attention. That doesn't guarantee conditions are safe."
                action={<Link to="/methodology" className="btn-secondary text-sm">How this works</Link>}
              />
            )}
          </section>

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
