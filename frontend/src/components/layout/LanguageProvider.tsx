import { useEffect, useMemo, useState, type ReactNode } from "react";

import { LanguageContextProvider, type Language } from "../../lib/i18n";

const LANGUAGE_KEY = "climatesense.language";

function storedLanguage(): Language {
  try {
    return localStorage.getItem(LANGUAGE_KEY) === "bn" ? "bn" : "en";
  } catch {
    return "en";
  }
}

export function LanguageProvider({ children }: { children: ReactNode }) {
  const [lang, setLang] = useState<Language>(storedLanguage);

  useEffect(() => {
    document.documentElement.lang = lang;
    try {
      localStorage.setItem(LANGUAGE_KEY, lang);
    } catch {
      // The choice simply lasts for this visit.
    }
  }, [lang]);

  const value = useMemo(() => ({ lang, setLang }), [lang]);
  return <LanguageContextProvider value={value}>{children}</LanguageContextProvider>;
}
