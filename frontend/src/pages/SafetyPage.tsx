import { Phone, ShieldCheck } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router-dom";

import { useAlerts } from "../api/queries";
import { TopicIcon } from "../components/ui/Icon";
import { PageHeader } from "../components/ui/PageHeader";
import { cn, formatDateTime } from "../lib/format";
import { useT } from "../lib/i18n";

const HELPLINES = [
  { number: "112", label: "All emergencies" },
  { number: "100", label: "Police" },
  { number: "101", label: "Fire" },
  { number: "108", label: "Ambulance" },
];

const OFFICIAL_LINKS = [
  { href: "https://mausam.imd.gov.in/", label: "India Meteorological Department" },
  { href: "https://sachet.ndma.gov.in/", label: "SACHET official alerts" },
  { href: "https://ndma.gov.in/", label: "National Disaster Management Authority" },
];

const CHECKLISTS = [
  {
    id: "flood",
    title: "Waterlogging and floods",
    steps: [
      "Never walk or drive through water when you can't see the road.",
      "Keep away from electric poles, wires and open drains.",
      "Move documents, medicines and valuables above floor level.",
      "After contact with floodwater, wash well and treat any cuts.",
      "Clear stagnant water around your home to reduce mosquitoes.",
    ],
  },
  {
    id: "cyclone",
    title: "Cyclones",
    steps: [
      "Follow official instructions, including any order to evacuate.",
      "Keep a bag ready with water, food, medicines, documents and a torch.",
      "Charge phones and power banks early.",
      "Bring in or tie down loose objects on balconies and roofs.",
      "Stay indoors, away from windows, until officials say it is over. The calm eye can pass before the wind returns.",
    ],
  },
  {
    id: "storm",
    title: "Nor'westers and lightning",
    steps: [
      "Go indoors when you hear thunder or see the sky darken quickly.",
      "Stay away from trees, poles, metal fences and open rooftops.",
      "Avoid running water and wired devices during lightning.",
      "If caught outside, leave open ground and water.",
    ],
  },
  {
    id: "heat",
    title: "Extreme heat",
    steps: [
      "Drink water regularly, even if you aren't thirsty.",
      "Avoid strenuous effort in the middle of the day.",
      "Wear light, loose clothing and cover your head outdoors.",
      "Check on older neighbours, young children and people who are unwell.",
      "Confusion, fainting or very hot skin is an emergency: call 112 and cool the person down.",
    ],
  },
  {
    id: "air",
    title: "Poor air quality",
    steps: [
      "Reduce long or hard exercise outdoors.",
      "Keep inhalers and regular medicines close if you have asthma.",
      "Consider a well-fitted N95 mask if you must spend time outdoors.",
    ],
  },
];

export function SafetyPage() {
  const { t } = useT();
  const [open, setOpen] = useState("flood");
  const alerts = useAlerts();
  const cyclones = (alerts.data?.results ?? []).filter((alert) => alert.hazard === "cyclone");

  return (
    <div className="shell space-y-8 py-6 sm:py-10">
      <PageHeader
        eyebrow={t("Safety")}
        title={t("Stay ready")}
        description="General safety guidance. Official instructions always come first."
      />

      {cyclones.length ? (
        <section className="rounded-2xl border border-red-200 bg-red-50 p-4">
          <h2 className="font-display text-xl text-red-950">Cyclone warning</h2>
          {cyclones.map((alert) => (
            <p key={alert.id} className="mt-1 text-sm text-red-900">
              {alert.title}. Until {formatDateTime(alert.expires_at)}.
            </p>
          ))}
          <Link to="/alerts" className="mt-2 inline-block text-sm font-semibold underline">Read the official warning</Link>
        </section>
      ) : null}

      <section>
        <h2 className="section-title flex items-center gap-2"><Phone className="h-5 w-5 text-brand" aria-hidden="true" />{t("Emergency numbers")}</h2>
        <div className="mt-3 grid grid-cols-2 gap-3 lg:grid-cols-4">
          {HELPLINES.map((line) => (
            <a key={line.number} href={`tel:${line.number}`} className="panel p-4 text-center hover:border-ink-300">
              <Phone className="mx-auto mb-1 h-4 w-4 text-brand" aria-hidden="true" />
              <p className="font-display text-3xl text-ink-950">{line.number}</p>
              <p className="text-xs text-ink-600">{line.label}</p>
            </a>
          ))}
        </div>
      </section>

      <section>
        <h2 className="section-title flex items-center gap-2"><ShieldCheck className="h-5 w-5 text-brand" aria-hidden="true" />Prepare and respond</h2>
        <div className="mt-3 space-y-2">
          {CHECKLISTS.map((list) => (
            <div key={list.id} className="panel overflow-hidden">
              <button
                type="button"
                aria-expanded={open === list.id}
                onClick={() => setOpen(open === list.id ? "" : list.id)}
                className={cn("flex w-full items-center justify-between px-4 py-3 text-left text-sm font-semibold text-ink-900")}
              >
                <span className="flex items-center gap-2"><TopicIcon text={list.title} />{list.title}</span>
                <span aria-hidden="true">{open === list.id ? "−" : "+"}</span>
              </button>
              {open === list.id ? (
                <ul className="list-disc space-y-1.5 px-8 pb-4 text-sm leading-6 text-ink-700">
                  {list.steps.map((step) => <li key={step}>{step}</li>)}
                </ul>
              ) : null}
            </div>
          ))}
        </div>
      </section>

      <section>
        <h2 className="section-title">Official sources</h2>
        <ul className="mt-3 space-y-2 text-sm">
          {OFFICIAL_LINKS.map((link) => (
            <li key={link.href}>
              <a className="link" href={link.href} target="_blank" rel="noreferrer">{link.label}</a>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
