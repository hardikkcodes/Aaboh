import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { LanguageProvider } from "../components/layout/LanguageProvider";
import { formatNumber } from "../lib/format";
import { useT } from "../lib/i18n";

/** Reads no language value itself, like any page that only formats numbers. */
function Amount() {
  return <p>{formatNumber(25, 0)}</p>;
}

function Toggle() {
  const { lang, setLang } = useT();
  return <button onClick={() => setLang(lang === "bn" ? "en" : "bn")}>switch</button>;
}

describe("language switching", () => {
  it("redraws numbers straight away in both directions", () => {
    render(
      <LanguageProvider>
        <Toggle />
        <Amount />
      </LanguageProvider>,
    );
    expect(screen.getByText("25")).toBeInTheDocument();
    fireEvent.click(screen.getByText("switch"));
    expect(screen.getByText("২৫")).toBeInTheDocument();
    fireEvent.click(screen.getByText("switch"));
    expect(screen.getByText("25")).toBeInTheDocument();
  });
});
