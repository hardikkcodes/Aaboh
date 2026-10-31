import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type { Insight } from "../api/types";
import { InsightCard } from "../components/insights/InsightCard";
import { DataStateNotice, StateBadge } from "../components/ui/DataState";

const insight: Insight = {
  rule_id: "heat_apparent_temperature",
  kind: "heat",
  title: "Heat stress conditions are elevated",
  body: "Apparent temperature is above the configured threshold in the stored forecast.",
  severity: "caution",
  valid_from: "2026-05-01T06:00:00Z",
  valid_until: "2026-05-01T12:00:00Z",
  evidence: [
    {
      evidence_type: "forecast",
      label: "Apparent temperature 41.2°C",
      source: { slug: "open_meteo", name: "Open-Meteo" },
      observed_at: "2026-05-01T06:00:00Z",
      reference: { temperature_c: 41.2 },
      source_url: "",
      quality_status: "AVAILABLE",
    },
    {
      evidence_type: "community_report",
      label: "Two nearby waterlogging reports",
      source: { slug: "community_reports", name: "Community reports" },
      observed_at: "2026-05-01T05:30:00Z",
      reference: {},
      source_url: "",
      quality_status: "PARTIAL",
    },
  ],
  caveats: ["A forecast is not a medical heat warning."],
};

describe("data-state components", () => {
  it("renders the human-readable state label", () => {
    render(<StateBadge state="PARTIAL" />);
    expect(screen.getByText("Partial")).toBeInTheDocument();
  });

  it("does not render a notice when a layer is available", () => {
    const { container } = render(
      <DataStateNotice state="AVAILABLE" reason="This should not appear." />,
    );
    expect(container).toBeEmptyDOMElement();
  });

  it("shows the reason and explicit gap for an unavailable layer", () => {
    render(
      <DataStateNotice
        state="UNAVAILABLE"
        title="Official alerts unavailable"
        reason="IMD_API_KEY is not configured."
      />,
    );
    expect(screen.getByText("Official alerts unavailable")).toBeInTheDocument();
    expect(screen.getByText("IMD_API_KEY is not configured.")).toBeInTheDocument();
  });
});

describe("InsightCard", () => {
  it("keeps evidence provenance and the unverified community chip visible", () => {
    render(<InsightCard insight={insight} />);
    expect(screen.getByText(insight.title)).toBeInTheDocument();
    expect(screen.getByText("Caution")).toBeInTheDocument();
    expect(screen.getByText("Open-Meteo", { exact: false })).toBeInTheDocument();
    expect(screen.getByText("Unverified community data")).toBeInTheDocument();
    expect(screen.getByText("Caveats (1)")).toBeInTheDocument();
  });
});
