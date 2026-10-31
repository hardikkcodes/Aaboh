import type { ReactNode } from "react";

import { cn } from "../../lib/format";

interface PageHeaderProps {
  eyebrow?: string;
  title: string;
  description?: string;
  aside?: ReactNode;
  className?: string;
}

export function PageHeader({ title, description, aside, className }: PageHeaderProps) {
  return (
    <header className={cn("flex flex-wrap items-start justify-between gap-3", className)}>
      <div className="max-w-2xl">
        <h1 className="display-title">{title}</h1>
        {description ? <p className="mt-1 text-sm leading-6 text-ink-600">{description}</p> : null}
      </div>
      {aside ? <div className="shrink-0">{aside}</div> : null}
    </header>
  );
}
