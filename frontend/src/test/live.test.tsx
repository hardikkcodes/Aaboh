import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import type { LiveReportFeature } from "../api/types";
import { AuthContext, type AuthContextValue } from "../auth/context";
import { ReportConfirmButtons } from "../components/live/ReportConfirmButtons";
import { distanceMeters } from "../lib/place";
import { QuickReportPage } from "../pages/QuickReportPage";

const mutate = vi.fn();
const nearbyReport: LiveReportFeature = {
  type: "Feature",
  geometry: { type: "Point", coordinates: [88.3525, 22.5531] },
  properties: {
    id: "report-1",
    category: "waterlogging",
    category_label: "Waterlogging",
    description: "",
    place: "Park Street",
    water_depth: "knee",
    water_depth_label: "Knee deep",
    passability: "",
    passability_label: "",
    trust: "unconfirmed",
    still_there: 0,
    cleared: 0,
    occurred_at: "2026-10-31T08:00:00Z",
    expires_at: "2026-10-31T14:00:00Z",
  },
};

vi.mock("../api/queries", () => ({
  useArea: vi.fn(() => ({ data: null })),
  useCreateIncident: vi.fn(() => ({ isPending: false, isError: false, mutateAsync: vi.fn() })),
  useConfirmIncident: vi.fn(() => ({ isPending: false, isError: false, mutate })),
  useLiveMap: vi.fn(() => ({ data: { features: [nearbyReport] } })),
}));

vi.mock("../components/map/CivicMap", () => ({
  LocationPicker: ({ onChange }: { onChange: (latitude: number, longitude: number) => void }) => (
    <button type="button" onClick={() => onChange(22.5531, 88.3525)}>Pick point</button>
  ),
}));

function renderWithAuth(ui: React.ReactNode, isAuthenticated = true) {
  const auth = { isAuthenticated, isLoading: false } as AuthContextValue;
  return render(
    <AuthContext.Provider value={auth}>
      <MemoryRouter>{ui}</MemoryRouter>
    </AuthContext.Provider>,
  );
}

describe("confirm buttons", () => {
  it("asks signed-out residents to log in", () => {
    renderWithAuth(<ReportConfirmButtons reportId="report-1" />, false);
    expect(screen.getByRole("link", { name: /log in to confirm/i })).toHaveAttribute(
      "href",
      "/login?next=/reports/report-1",
    );
  });

  it("sends one-tap votes", () => {
    renderWithAuth(<ReportConfirmButtons reportId="report-1" />);
    fireEvent.click(screen.getByRole("button", { name: "Still there" }));
    expect(mutate.mock.calls[0][0]).toEqual({ id: "report-1", kind: "still_there" });
  });

  it("lets a reporter clear but not confirm their own report", () => {
    renderWithAuth(<ReportConfirmButtons reportId="report-1" isOwner />);
    expect(screen.queryByRole("button", { name: "Still there" })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Cleared" })).toBeInTheDocument();
  });
});

describe("quick report", () => {
  it("asks for depth only on waterlogging reports", () => {
    renderWithAuth(<QuickReportPage />);
    expect(screen.getByText("How deep?")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Power cut" }));
    expect(screen.queryByText("How deep?")).not.toBeInTheDocument();
  });

  it("offers an existing nearby report before a new one", () => {
    renderWithAuth(<QuickReportPage />);
    expect(screen.queryByText("Already reported nearby")).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Pick point" }));
    expect(screen.getByText("Already reported nearby")).toBeInTheDocument();
  });

  it("needs a location before sending", () => {
    renderWithAuth(<QuickReportPage />);
    fireEvent.click(screen.getByRole("button", { name: "Send report" }));
    expect(screen.getByRole("alert")).toHaveTextContent("Set the location first");
  });
});

describe("distance", () => {
  it("measures short distances in metres", () => {
    expect(distanceMeters(22.55, 88.35, 22.55, 88.35)).toBe(0);
    expect(distanceMeters(22.55, 88.35, 22.551, 88.35)).toBeCloseTo(111, 0);
  });
});
