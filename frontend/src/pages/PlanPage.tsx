import { useWeekPlan } from "../api/queries";
import type { WeekPlanDay } from "../api/types";
import { useTemperatureUnit } from "../auth/context";
import { StateBadge } from "../components/ui/DataState";
import { AgreementChip } from "../components/weather/ForecastConfidence";
import { ErrorState, EmptyState, LoadingPanel } from "../components/ui/Feedback";
import { PageHeader } from "../components/ui/PageHeader";
import { ShareButton } from "../components/ui/ShareButton";
import { cn, formatDay, formatTemperature, formatTime, formatWithUnit } from "../lib/format";
import { useT } from "../lib/i18n";

const RATING = {
  good: { label: "Good", classes: "border-emerald-200 bg-emerald-50 text-emerald-800" },
  fair: { label: "Fair", classes: "border-amber-200 bg-amber-50 text-amber-800" },
  poor: { label: "Poor", classes: "border-red-200 bg-red-50 text-red-800" },
} as const;

function DayCard({ day }: { day: WeekPlanDay }) {
  const { t } = useT();
  const unit = useTemperatureUnit();
  const rating = RATING[day.rating];
  return (
    <article className="panel p-4">
      <div className="flex items-center justify-between gap-2">
        <h2 className="font-display text-lg text-ink-950">{formatDay(day.date)}</h2>
        <span className="flex flex-wrap justify-end gap-1">
          <AgreementChip agreement={day.agreement} />
          <span className={cn("chip", rating.classes)}>{t(rating.label)}</span>
        </span>
      </div>
      <p className="mt-1 text-sm text-ink-700">{day.condition.label}</p>
      <dl className="mt-3 grid grid-cols-2 gap-2 text-xs text-ink-600">
        <div>
          <dt>{t("Rainfall")}</dt>
          <dd className="font-semibold text-ink-900">{formatWithUnit(day.rain_mm, "mm")} · {day.max_rain_probability_pct}%</dd>
        </div>
        <div>
          <dt>Feels like</dt>
          <dd className="font-semibold text-ink-900">{formatTemperature(day.peak_heat_index_c, unit)}</dd>
        </div>
      </dl>
      <p className="mt-3 text-xs text-ink-700">
        {day.best_window
          ? t("Best time outdoors: {start} to {end}", {
              start: formatTime(day.best_window.start),
              end: formatTime(day.best_window.end),
            })
          : t("No clear dry, cooler window today")}
      </p>
      {day.hours_covered < 12 ? <p className="mt-1 text-[0.68rem] text-ink-400">Partial day</p> : null}
    </article>
  );
}

export function PlanPage() {
  const { t } = useT();
  const plan = useWeekPlan();
  const days = plan.data?.days ?? [];
  const best = days.filter((day) => day.rating === "good").map((day) => formatDay(day.date));

  return (
    <div className="shell space-y-6 py-6 sm:py-10">
      <PageHeader
        eyebrow="Planner"
        title={t("Your week")}
        description="Choose the best day and hours for outings, pandal visits, matches or errands."
        aside={plan.data ? <StateBadge state={plan.data.state} /> : null}
      />
      {plan.isError ? (
        <ErrorState error={plan.error} onRetry={() => void plan.refetch()} />
      ) : plan.isLoading ? (
        <LoadingPanel label="Loading the week ahead" rows={3} />
      ) : days.length ? (
        <>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {days.map((day) => <DayCard key={day.date} day={day} />)}
          </div>
          <ShareButton
            title="Best days this week"
            text={best.length ? `Best days in Kolkata this week: ${best.join(", ")}` : "No clearly good days in Kolkata this week."}
          />
        </>
      ) : (
        <EmptyState
          title="No forecast is stored yet"
          description="Run fetch_weather to load the forecast. Nothing is estimated in its place."
        />
      )}
      <p className="text-xs leading-5 text-ink-500">{plan.data?.note}</p>
    </div>
  );
}
