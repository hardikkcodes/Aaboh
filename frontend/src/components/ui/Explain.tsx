import { Info } from "lucide-react";
import type { ReactNode } from "react";

/** A short plain-language note, closed by default so it never gets in the way. */
export function Explain({ title = "What does this mean?", children }: { title?: string; children: ReactNode }) {
  return (
    <details className="rounded-xl border border-sky-200 bg-sky-50 px-3 py-2 text-sm text-sky-950">
      <summary className="cursor-pointer font-medium"><Info className="mr-1.5 inline h-4 w-4 align-[-2px]" aria-hidden="true" />{title}</summary>
      <div className="mt-1.5 space-y-1.5 leading-6">{children}</div>
    </details>
  );
}
