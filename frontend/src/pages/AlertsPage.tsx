import {
  CircleCheck,
  CloudLightning,
  CloudRain,
  CloudFog,
  ExternalLink,
  Phone,
  ShieldAlert,
  Snowflake,
  Thermometer,
  Tornado,
  TriangleAlert,
  Waves,
  type LucideIcon,
} from "lucide-react";
import { Link } from "react-router-dom";

import { useAlerts } from "../api/queries";
import type { Alert } from "../api/types";
import { Explain } from "../components/ui/Explain";
import { ErrorState, LoadingPanel } from "../components/ui/Feedback";
import { PageHeader } from "../components/ui/PageHeader";
import { CycloneWatch } from "../components/weather/CycloneWatch";
import { cn, formatDateTime, formatRelative } from "../lib/format";

const HAZARDS: Record<string, { icon: LucideIcon; advice: string }> = {
  heavy_rain: { icon: CloudRain, advice: "Avoid low roads, and never walk or drive through water you can't judge." },
  thunderstorm: { icon: CloudLightning, advice: "Go indoors. Stay away from trees, poles and open rooftops." },
  heatwave: { icon: Thermometer, advice: "Stay out of the midday sun, drink water and check on older people." },
  cold_wave: { icon: Snowflake, advice: "Keep warm, especially older people and young children." },
  cyclone: { icon: Tornado, advice: "Follow official instructions, including any order to evacuate." },
  fog: { icon: CloudFog, advice: "Drive slowly and allow extra time for trains and flights." },
  flood: { icon: Waves, advice: "Move to higher ground and keep away from flood water." },
  other: { icon: TriangleAlert, advice: "Read the bulletin and follow official instructions." },
};

const SEVERITY: Record<string, { label: string; classes: string }> = {
  extreme: { label: "Extreme: act now", classes: "border-red-300 bg-red-100 text-red-900" },
  severe: { label: "Severe: be ready to act", classes: "border-red-200 bg-red-50 text-red-800" },
  moderate: { label: "Moderate: stay alert", classes: "border-amber-200 bg-amber-50 text-amber-800" },
  minor: { label: "Minor: be aware", classes: "border-sky-200 bg-sky-50 text-sky-800" },
  unknown: { label: "Check the bulletin", classes: "border-ink-200 bg-ink-50 text-ink-700" },
};

function AlertCard({ alert }: { alert: Alert }) {
  const hazard = HAZARDS[alert.hazard] ?? HAZARDS.other;
  const severity = SEVERITY[alert.severity] ?? SEVERITY.unknown;
  const Icon = hazard.icon;
  return (
    <article className="panel p-5 sm:p-6">
      <div className="flex items-start gap-3">
        <span className="icon-tile"><Icon className="h-5 w-5" aria-hidden="true" /></span>
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <span className={cn("chip", severity.classes)}>{severity.label}</span>
            <span className={cn("chip", alert.match === "state" ? "border-amber-200 bg-amber-50 text-amber-800" : "border-red-200 bg-red-50 text-red-800")}>
              {alert.match === "state" ? "May affect your area" : "Affects your area"}
            </span>
          </div>
          <h2 data-original-text className="mt-2 font-display text-xl leading-snug text-ink-950">{alert.title}</h2>
          <p className="mt-1 text-xs text-ink-500">
            Issued {formatRelative(alert.issued_at)}
            {alert.expires_at ? ` · Until ${formatDateTime(alert.expires_at)}` : ""}
          </p>
        </div>
      </div>

      <p className="mt-3 rounded-xl bg-ink-50 p-3 text-sm font-medium text-ink-900">
        <span className="font-semibold">What to do: </span>{hazard.advice}
      </p>
      <p data-original-text className="prose-civic mt-3 whitespace-pre-line">{alert.description}</p>
      {alert.areas_text ? <p data-original-text className="mt-2 text-xs text-ink-600">{alert.areas_text}</p> : null}

      <div className="mt-3 flex flex-wrap items-center justify-between gap-2 border-t border-ink-100 pt-3 text-xs text-ink-500">
        <span>{alert.source.name ?? "Official source"}</span>
        <a href={alert.source_url} target="_blank" rel="noreferrer" className="link inline-flex items-center gap-1">
          Read the original bulletin
          <ExternalLink className="h-3.5 w-3.5" aria-hidden="true" />
        </a>
      </div>
    </article>
  );
}

function Status({ count, status, area, checked }: { count: number; status: string; area: string; checked: string | null }) {
  const clear = count === 0 && status === "ok";
  const Icon = count ? ShieldAlert : clear ? CircleCheck : TriangleAlert;
  const tone = count ? "border-red-200 bg-red-50" : clear ? "border-emerald-200 bg-emerald-50" : "border-amber-200 bg-amber-50";
  const title = count
    ? `Official warnings in effect: ${count}`
    : clear
      ? "No official warnings right now"
      : "We couldn't check for warnings";
  return (
    <section className={cn("flex items-start gap-3 rounded-2xl border p-5", tone)}>
      <Icon className="mt-0.5 h-7 w-7 shrink-0 text-ink-900" aria-hidden="true" />
      <div>
        <h2 className="text-xl font-semibold text-ink-950">{title}</h2>
        <p className="mt-0.5 text-sm text-ink-700">
          {clear
            ? "None of the warnings issued now cover your area. Stay alert in bad weather."
            : count
              ? "Read each one below and follow official instructions."
              : "Check SACHET or IMD directly until this comes back."}
        </p>
        <p className="mt-1 text-xs text-ink-600">
          <span>{area}</span>
          {checked ? ` · Checked ${formatRelative(checked)}` : ""}
        </p>
      </div>
    </section>
  );
}

const LINKS = [
  { href: "https://sachet.ndma.gov.in/", label: "SACHET" },
  { href: "https://mausam.imd.gov.in/", label: "IMD" },
];

export function AlertsPage() {
  const alerts = useAlerts();
  const data = alerts.data;
  const results = [...(data?.results ?? [])].sort((a, b) => Number(a.match === "state") - Number(b.match === "state"));

  return (
    <div className="shell space-y-5 py-5 sm:py-8">
      <PageHeader title="Official warnings" description="Warnings from government agencies, shown exactly as issued." />
      {alerts.isError ? (
        <ErrorState error={alerts.error} onRetry={() => void alerts.refetch()} />
      ) : alerts.isLoading || !data ? (
        <LoadingPanel label="Loading the official alert feed" />
      ) : (
        <>
          <Status
            count={results.length}
            status={data.feed_status}
            area={data.area.name}
            checked={data.last_success_at}
          />
          <CycloneWatch />
          {results.map((alert) => <AlertCard key={alert.id} alert={alert} />)}
          <section className="grid gap-3 sm:grid-cols-3">
            <a href="tel:112" className="panel flex items-center gap-3 p-4">
              <Phone className="h-5 w-5 text-brand" aria-hidden="true" />
              <span>
                <span className="block text-sm font-semibold text-ink-900">Emergency: 112</span>
                <span className="text-xs text-ink-500">Tap to call</span>
              </span>
            </a>
            {LINKS.map((link) => (
              <a key={link.label} href={link.href} target="_blank" rel="noreferrer" className="panel flex items-center gap-3 p-4">
                <ExternalLink className="h-5 w-5 text-brand" aria-hidden="true" />
                <span data-original-text className="text-sm font-semibold text-ink-900">{link.label}</span>
              </a>
            ))}
          </section>
          <Link to="/safety" className="link inline-block text-sm">Safety checklists for storms, floods and heat</Link>
          <Explain title="Where do these come from?">
            <p>From the national SACHET service, which carries warnings from IMD, CWC and state disaster agencies. We don't write or change them.</p>
            <p>Some warnings name only the state, so we mark them as "may affect your area". Check the bulletin for your district.</p>
            <p>An empty list doesn't mean you're safe. Trust what you see, and official instructions, first.</p>
          </Explain>
        </>
      )}
    </div>
  );
}
