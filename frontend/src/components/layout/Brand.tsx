import { cn } from "../../lib/format";

/** The Aaboh mark: a sun above flowing air and water. Matches public/favicon.svg. */
export function BrandMark({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 64 64" className={cn("h-9 w-9 shrink-0", className)} aria-hidden="true">
      <defs>
        <linearGradient id="aaboh-mark" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="#0d4a48" />
          <stop offset="1" stopColor="#1f8a78" />
        </linearGradient>
      </defs>
      <rect width="64" height="64" rx="16" fill="url(#aaboh-mark)" />
      <circle cx="43" cy="22" r="9" fill="#f6b93b" />
      <path d="M10 37q9-9 18 0t18 0 8-3" fill="none" stroke="#fff" strokeWidth="4.5" strokeLinecap="round" />
      <path d="M10 49q9-9 18 0t18 0 8-3" fill="none" stroke="#bdeadf" strokeWidth="4.5" strokeLinecap="round" />
    </svg>
  );
}

/** The name in its Bangla lettering. It is a logo, so it never gets translated. */
export function Wordmark({ showPlace = false, className }: { showPlace?: boolean; className?: string }) {
  return (
    <span data-original-text className={cn("leading-none", className)}>
      <span lang="bn" className="brand-name block">আবহ</span>
      {showPlace ? <span className="mt-0.5 block text-[0.68rem] font-medium text-ink-500">Aaboh · Kolkata</span> : null}
    </span>
  );
}
