import { Fragment, useCallback, useEffect, useMemo, useState, type ReactNode } from "react";

import { LanguageContextProvider, type Language } from "../../lib/i18n";

const LANGUAGE_KEY = "climatesense.language";

function storedLanguage(): Language {
  try {
    const stored = localStorage.getItem(LANGUAGE_KEY) === "bn" ? "bn" : "en";
    // Dates and numbers read this while the first page renders.
    document.documentElement.lang = stored;
    return stored;
  } catch {
    return "en";
  }
}

export function LanguageProvider({ children }: { children: ReactNode }) {
  const [lang, setLanguage] = useState<Language>(storedLanguage);

  const setLang = useCallback((next: Language) => {
    // Set before rendering, because number and date formatting reads it.
    document.documentElement.lang = next;
    setLanguage(next);
  }, []);

  useEffect(() => {
    document.documentElement.lang = lang;
    try {
      localStorage.setItem(LANGUAGE_KEY, lang);
    } catch {
      // The choice simply lasts for this visit.
    }
  }, [lang]);

  useEffect(() => {
    if (lang !== "bn") return undefined;
    let stop: (() => void) | undefined;
    let cancelled = false;
    void Promise.all([import("../../lib/banglaDom"), import("../../lib/bnCatalogue")]).then(([dom, catalogue]) => {
      if (!cancelled) stop = dom.startBangla(catalogue.CATALOGUE);
    });
    return () => {
      cancelled = true;
      stop?.();
    };
  }, [lang]);

  const value = useMemo(() => ({ lang, setLang }), [lang, setLang]);
  // The key redraws the whole app, so text outside React's language context changes too.
  return (
    <LanguageContextProvider value={value}>
      <Fragment key={lang}>{children}</Fragment>
    </LanguageContextProvider>
  );
}
