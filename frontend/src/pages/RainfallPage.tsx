import {
  Bar,
  CartesianGrid,
  ComposedChart,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { useRainfallForecast, useRainfallHistory } from "../api/queries";
import { DataStateNotice, StateBadge } from "../components/ui/DataState";
import { ErrorState, LoadingPanel } from "../components/ui/Feedback";
import { LowGroundMap } from "../components/weather/LowGroundMap";
import { RainOutlookPanel } from "../components/weather/RainOutlookPanel";
import { PageHeader } from "../components/ui/PageHeader";
import { SectionHeading } from "../components/ui/SectionHeading";
import { SourcePanel } from "../components/ui/SourcePanel";
import { StatCard } from "../components/ui/StatCard";
import {
  formatDate,
  formatDateTime,
  formatHour,
  formatNumber,
  formatPercent,
  formatWithUnit,
} from "../lib/format";

export function RainfallPage() {
  const forecast = useRainfallForecast();
  const history = useRainfallHistory(undefined, 365);

  const hourlyData = (forecast.data?.hourly ?? []).map((record) => ({
    label: formatHour(record.valid_time),
    time: formatDateTime(record.valid_time),
    rain: record.precipitation_mm,
    probability: record.precipitation_probability,
  }));

  const monthlyData = (history.data?.monthly ?? []).map((item) => ({
    label: item.month,
    rain: item.precipitation_mm,
    days: item.days,
  }));

  return (
    <div className="shell space-y-6 py-5 sm:py-8">
      <PageHeader
        eyebrow="Rainfall"
        title="Rain forecast"
        description="How much rain to expect and where water can gather. A forecast can't tell you if your street will flood, so check live reports too."
        aside={forecast.data ? <StateBadge state={forecast.data.state} /> : null}
      />

      {forecast.isError ? (
        <ErrorState error={forecast.error} onRetry={() => void forecast.refetch()} />
      ) : forecast.isLoading ? (
        <LoadingPanel label="Loading rainfall forecast" />
      ) : (
        <>
          {forecast.data?.outlook ? (
            <RainOutlookPanel outlook={forecast.data.outlook} updatedAt={forecast.data.outlook_retrieved_at} />
          ) : null}

          <LowGroundMap />

          <section className="grid gap-4 sm:grid-cols-3">
            <StatCard
              label="Next 24 hours"
              value={forecast.data ? `${formatNumber(forecast.data.summary.next_24h_total_mm, 1)} mm` : "—"}
              detail="Total rain expected"
              tone="cool"
            />
            <StatCard
              label="Highest hourly chance"
              value={formatPercent(forecast.data?.summary.next_24h_max_probability_pct)}
              detail="Even a brief drizzle counts"
            />
            <StatCard
              label="Wettest hour"
              value={forecast.data?.summary.peak_hour ? formatHour(forecast.data.summary.peak_hour) : "—"}
              detail={forecast.data?.summary.peak_hour_mm !== null && forecast.data?.summary.peak_hour_mm !== undefined
                ? `${formatNumber(forecast.data.summary.peak_hour_mm, 1)} mm in that hour`
                : "No rain expected"}
              tone="warm"
            />
          </section>

          <DataStateNotice
            state={forecast.data?.state ?? "UNAVAILABLE"}
            title="Rainfall forecast is unavailable"
            reason={forecast.data?.state === "AVAILABLE" ? null : "No hourly or daily rainfall forecast rows are stored for Kolkata."}
          >
            <p>{forecast.data?.note}</p>
          </DataStateNotice>

          <section>
            <SectionHeading
              eyebrow="Next 24 hours"
              title="Expected rain each hour"
              description="Bars show how much rain is forecast. The line shows the chance of any rain that hour."
              action={forecast.data ? <StateBadge state={forecast.data.state} /> : null}
            />
            {hourlyData.length ? (
              <div className="panel mt-5 p-4 sm:p-6">
                <div className="h-72 w-full">
                  <ResponsiveContainer width="100%" height="100%">
                    <ComposedChart data={hourlyData} margin={{ top: 8, right: 8, left: -20, bottom: 0 }}>
                      <CartesianGrid stroke="#e3ebe8" strokeDasharray="3 3" vertical={false} />
                      <XAxis dataKey="label" tick={{ fontSize: 10, fill: "#4f7d71" }} interval={2} tickLine={false} axisLine={false} />
                      <YAxis yAxisId="rain" tick={{ fontSize: 11, fill: "#4f7d71" }} tickLine={false} axisLine={false} unit="mm" />
                      <YAxis yAxisId="prob" orientation="right" domain={[0, 100]} tick={{ fontSize: 11, fill: "#6f9a8f" }} tickLine={false} axisLine={false} unit="%" />
                      <Tooltip contentStyle={{ borderRadius: 12, borderColor: "#e3ebe8", fontSize: 12 }} />
                      <Bar yAxisId="rain" dataKey="rain" name="Rain (mm)" fill="#6f9a8f" fillOpacity={0.75} radius={[3, 3, 0, 0]} />
                      <Line yAxisId="prob" type="monotone" dataKey="probability" name="Probability (%)" stroke="#bb621b" strokeWidth={2} dot={false} />
                    </ComposedChart>
                  </ResponsiveContainer>
                </div>
                <div className="mt-3 flex flex-wrap gap-4 text-xs text-ink-500">
                  <span className="inline-flex items-center gap-1.5"><span className="h-2 w-4 rounded-full bg-ink-400" /> Hourly rainfall (mm)</span>
                  <span className="inline-flex items-center gap-1.5"><span className="h-2 w-4 rounded-full bg-ember-600" /> Probability (%)</span>
                </div>
                <p className="mt-3 text-xs text-ink-500">{forecast.data?.note}</p>
              </div>
            ) : (
              <div className="panel-muted mt-5 p-5">
                <p className="text-sm font-medium text-ink-800">No hourly rainfall forecast rows</p>
                <p className="mt-1 text-xs text-ink-500">
                  No substitute rainfall values have been generated. Check the data-status page for ingestion health.
                </p>
              </div>
            )}
          </section>

          <section>
            <div>
              <SectionHeading
                eyebrow="Previous 12 months"
                title="Monthly rainfall"
                description="ERA5-Land reanalysis totals (~9 km), not an individual rain gauge."
                action={history.data ? <StateBadge state={history.data.state} /> : null}
              />
              {history.isError ? (
                <ErrorState className="mt-4" error={history.error} onRetry={() => void history.refetch()} />
              ) : history.isLoading ? (
                <div className="mt-4"><LoadingPanel label="Loading rainfall history" /></div>
              ) : monthlyData.length ? (
                <div className="panel mt-4 p-4 sm:p-6">
                  <div className="h-64 w-full">
                    <ResponsiveContainer width="100%" height="100%">
                      <ComposedChart data={monthlyData} margin={{ top: 8, right: 8, left: -20, bottom: 0 }}>
                        <CartesianGrid stroke="#e3ebe8" strokeDasharray="3 3" vertical={false} />
                        <XAxis dataKey="label" tick={{ fontSize: 10, fill: "#4f7d71" }} tickLine={false} axisLine={false} />
                        <YAxis tick={{ fontSize: 11, fill: "#4f7d71" }} tickLine={false} axisLine={false} unit="mm" />
                        <Tooltip contentStyle={{ borderRadius: 12, borderColor: "#e3ebe8", fontSize: 12 }} />
                        <Bar dataKey="rain" name="Monthly rainfall (mm)" fill="#6f9a8f" fillOpacity={0.8} radius={[4, 4, 0, 0]} />
                      </ComposedChart>
                    </ResponsiveContainer>
                  </div>
                  <div className="mt-3 grid grid-cols-3 gap-3 text-xs">
                    <div className="rounded-lg bg-ink-50 p-2.5">
                      <p className="text-ink-500">Total</p>
                      <p className="mt-1 font-semibold text-ink-900">{formatNumber(history.data?.summary.total_mm, 1)} mm</p>
                    </div>
                    <div className="rounded-lg bg-ink-50 p-2.5">
                      <p className="text-ink-500">Wet days</p>
                      <p className="mt-1 font-semibold text-ink-900">{history.data?.summary.wet_days ?? "—"}</p>
                    </div>
                    <div className="rounded-lg bg-ink-50 p-2.5">
                      <p className="text-ink-500">Max daily</p>
                      <p className="mt-1 font-semibold text-ink-900">{formatWithUnit(history.data?.summary.max_daily_mm, "mm", 1)}</p>
                    </div>
                  </div>
                  <p className="mt-3 text-xs text-ink-500">
                    {formatDate(history.data?.start_date)} to {formatDate(history.data?.end_date)} · {history.data?.note}
                  </p>
                </div>
              ) : (
                <div className="panel-muted mt-4 p-5">
                  <p className="text-sm font-medium text-ink-800">No historical rainfall rows</p>
                  <p className="mt-1 text-xs text-ink-500">No monthly totals have been derived from stored reanalysis.</p>
                </div>
              )}
            </div>
          </section>

          {history.data?.daily.length ? (
            <section>
              <SectionHeading eyebrow="Daily detail" title="Recent daily rainfall" />
              <div className="panel mt-4 overflow-x-auto">
                <table className="table-civic min-w-[520px]">
                  <thead>
                    <tr>
                      <th>Date</th>
                      <th>Rainfall</th>
                    </tr>
                  </thead>
                  <tbody>
                    {history.data.daily.slice(-14).reverse().map((record) => (
                      <tr key={record.id}>
                        <td>{formatDate(record.valid_time)}</td>
                        <td>{formatWithUnit(record.precipitation_mm, "mm", 1)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          ) : null}
        </>
      )}

      <SourcePanel
        source={forecast.data?.source ?? history.data?.source}
        retrievedAt={forecast.data?.retrieved_at ?? history.data?.retrieved_at}
        note="Forecast values are provider estimates. Historical values are ERA5-Land reanalysis (~9 km). Neither is a local rain-gauge observation or a flood forecast."
      />
    </div>
  );
}
