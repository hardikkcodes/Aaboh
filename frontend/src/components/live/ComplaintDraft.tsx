import { useState } from "react";

import type { Incident } from "../../api/types";
import { formatDateTime, formatNumber } from "../../lib/format";

const CIVIC_CATEGORIES = new Set([
  "waterlogging",
  "flooding",
  "blocked_drainage",
  "stagnant_water",
  "fallen_tree",
  "road_disruption",
]);

function draftFor(report: Incident): string {
  const place = report.address_text || report.neighbourhood?.name || "the location below";
  return [
    `Subject: ${report.category_label} at ${place}, Kolkata`,
    "",
    "To the concerned department,",
    "",
    `I would like to report ${report.category_label.toLowerCase()} at ${place}.`,
    report.water_depth_label ? `Water depth: ${report.water_depth_label}.` : "",
    report.passability_label ? `Access: ${report.passability_label}.` : "",
    `First reported: ${formatDateTime(report.occurred_at)}.`,
    `Coordinates: ${formatNumber(report.latitude, 4)}, ${formatNumber(report.longitude, 4)}.`,
    report.description ? `Details: ${report.description}` : "",
    "",
    "Please inspect this and take the necessary action.",
    "",
    "Thank you.",
  ]
    .filter((line, index, lines) => line !== "" || lines[index - 1] !== "")
    .join("\n");
}

/** Turns a report into a letter a resident can send through official channels. */
export function ComplaintDraft({ report }: { report: Incident }) {
  const [open, setOpen] = useState(false);
  const [copied, setCopied] = useState(false);
  if (!CIVIC_CATEGORIES.has(report.category)) return null;
  const draft = draftFor(report);

  async function copy() {
    await navigator.clipboard.writeText(draft);
    setCopied(true);
  }

  return (
    <section className="panel p-5">
      <button type="button" className="text-sm font-semibold text-ink-900 underline" onClick={() => setOpen(!open)}>
        Need the authorities to act? Draft a complaint
      </button>
      {open ? (
        <div className="mt-3 space-y-2">
          <pre className="whitespace-pre-wrap rounded-xl bg-ink-50 p-3 font-sans text-xs leading-5 text-ink-800">{draft}</pre>
          <button type="button" className="btn-secondary text-xs" onClick={() => void copy()}>
            {copied ? "Copied" : "Copy text"}
          </button>
          <p className="text-xs text-ink-500">
            This platform doesn't send it for you. Add your name and submit it through your ward office or KMC's official channels.
          </p>
        </div>
      ) : null}
    </section>
  );
}
