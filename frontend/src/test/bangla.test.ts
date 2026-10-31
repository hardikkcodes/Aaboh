import { describe, expect, it } from "vitest";

import { bengaliDigits, translateText } from "../lib/banglaDom";

const catalogue = {
  Now: "এখন",
  "Showing {n} of {n}": "{2} এর মধ্যে {1}",
  "Rain next {n} h": "আগামী {n} ঘণ্টায় বৃষ্টি",
  "First line": "প্রথম লাইন",
};

describe("Bangla translation", () => {
  it("translates exact text and keeps surrounding spaces", () => {
    expect(translateText(" Now ", catalogue)).toBe(" এখন ");
  });

  it("fills numbers into templates, in the translated order", () => {
    expect(translateText("Showing 8 of 26", catalogue)).toBe("২৬ এর মধ্যে ৮");
  });

  it("translates a line built from pieces", () => {
    expect(translateText("Rain next 24 h · Now", catalogue)).toBe("আগামী ২৪ ঘণ্টায় বৃষ্টি · এখন");
  });

  it("uses a Bangla full stop when only the phrase is known", () => {
    expect(translateText("First line.", catalogue)).toBe("প্রথম লাইন।");
  });

  it("leaves unknown English readable and only changes its digits", () => {
    expect(translateText("Unknown phrase 12", catalogue)).toBe("Unknown phrase ১২");
  });

  it("does not touch emails or links", () => {
    expect(translateText("someone1@example.com", catalogue)).toBe("someone1@example.com");
  });

  it("converts digits", () => {
    expect(bengaliDigits("2026")).toBe("২০২৬");
  });
});
