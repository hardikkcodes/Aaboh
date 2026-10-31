import { useModelStatus } from "../api/queries";
import { ErrorState, LoadingPanel } from "../components/ui/Feedback";
import { PageHeader } from "../components/ui/PageHeader";
import { useT } from "../lib/i18n";

function Result({
  name,
  outcome,
  passed,
  detail,
}: {
  name: string;
  outcome: string;
  passed: boolean;
  detail: string;
}) {
  return (
    <article className="panel p-4">
      <div className="flex items-start justify-between gap-2">
        <h3 className="text-sm font-semibold text-ink-900">{name}</h3>
        <span className={`chip ${passed ? "border-emerald-200 bg-emerald-50 text-emerald-800" : "border-red-200 bg-red-50 text-red-800"}`}>
          {passed ? "Passed test" : "Failed test"}
        </span>
      </div>
      <p className="mt-2 text-lg font-semibold text-ink-950">{outcome}</p>
      <p className="mt-1 text-xs leading-5 text-ink-600">{detail}</p>
    </article>
  );
}

export function ModelsPage() {
  const { t } = useT();
  const status = useModelStatus();
  const trained = status.data?.trained;
  const surfaceHeat = status.data?.surface_heat;

  if (status.isError) {
    return <div className="shell py-8"><ErrorState error={status.error} onRetry={() => void status.refetch()} /></div>;
  }
  if (!status.data) {
    return <div className="shell py-8"><LoadingPanel label="Loading model status" rows={3} /></div>;
  }

  return (
    <div className="shell space-y-6 py-5 sm:py-8">
      <PageHeader
        title={t("Model status")}
        description="What has been trained on real data, how it did on days it had never seen, and what is still waiting for data."
      />

      {trained ? (
        <section className="space-y-3">
          <h2 className="section-title">Trained on real history</h2>
          <p className="text-sm text-ink-600">
            {trained.dataset.rows} real days. Tested on {trained.dataset.test_period[0]} to {trained.dataset.test_period[1]}.
            No model on this page changes what residents see yet.
          </p>
          <div className="grid gap-3 md:grid-cols-2">
            <Result
              name="Next-day peak temperature"
              outcome={`${trained.heat.model}°C typical error`}
              passed={trained.heat.promotable}
              detail={`Raw forecast: ${trained.heat.baseline_raw_forecast}°C. ${trained.heat.improvement_pct}% better than a fixed correction. It still needs checking against real thermometers.`}
            />
            <Result
              name="Next-day heavy rain (20 mm or more)"
              outcome={`${trained.rain.improvement_pct}% against baseline`}
              passed={trained.rain.promotable}
              detail={`Score ${trained.rain.model} against ${trained.rain.baseline_calibrated_forecast} for the forecast alone (lower is better), over ${trained.rain.heavy_days_in_test} heavy days. Not used.`}
            />
          </div>
          <ul className="list-disc space-y-1 pl-5 text-xs leading-5 text-ink-500">
            {trained.limitations.map((item) => <li key={item}>{item}</li>)}
          </ul>
        </section>
      ) : null}

      {surfaceHeat ? (
        <section className="space-y-3">
          <h2 className="section-title">Trained on real satellite images</h2>
          <Result
            name="Land-surface heat in Kolkata (1 km)"
            outcome={`${surfaceHeat.mae_c}°C typical error`}
            passed={surfaceHeat.mae_c < surfaceHeat.baseline_cell_month_mae_c}
            detail={`Each place's past average for that month gives ${surfaceHeat.baseline_cell_month_mae_c}°C. Tested on ${surfaceHeat.n_test_dates} later dates after learning from ${surfaceHeat.n_train_dates}. This is ground temperature, not air temperature, and it isn't shown to residents as a prediction.`}
          />
        </section>
      ) : null}

      <section className="space-y-3">
        <h2 className="section-title">Waiting for real data</h2>
        <div className="grid gap-3 md:grid-cols-2">
          {status.data.waiting.map((model) => (
            <article key={model.key} className="panel p-4">
              <h3 className="text-sm font-semibold text-ink-900">{model.name}</h3>
              <div className="mt-3 space-y-2">
                {model.progress.map((item) => (
                  <div key={item.label}>
                    <div className="flex justify-between text-xs text-ink-600">
                      <span>{item.label}</span>
                      <span>{item.value} of {item.target}</span>
                    </div>
                    <div className="mt-1 h-1.5 rounded-full bg-ink-100">
                      <div className="h-1.5 rounded-full bg-ink-700" style={{ width: `${Math.min(100, (item.value / item.target) * 100)}%` }} />
                    </div>
                  </div>
                ))}
              </div>
              <p className="mt-3 text-xs leading-5 text-ink-600">{model.note}</p>
            </article>
          ))}
        </div>
      </section>
    </div>
  );
}
