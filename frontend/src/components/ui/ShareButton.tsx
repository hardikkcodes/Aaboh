import { useState } from "react";

import { useT } from "../../lib/i18n";

/** Uses the phone's share sheet where available, otherwise copies the text. */
export function ShareButton({ title, text, label }: { title: string; text: string; label?: string }) {
  const { t } = useT();
  const [copied, setCopied] = useState(false);

  async function share() {
    const url = window.location.origin;
    if (navigator.share) {
      try {
        await navigator.share({ title, text, url });
      } catch {
        // Closing the share sheet is not an error.
      }
      return;
    }
    await navigator.clipboard.writeText(`${text}\n${url}`);
    setCopied(true);
  }

  return (
    <button type="button" className="btn-secondary !px-3 !py-1.5 text-xs" onClick={() => void share()}>
      {copied ? t("Copied") : label ?? t("Share")}
    </button>
  );
}
