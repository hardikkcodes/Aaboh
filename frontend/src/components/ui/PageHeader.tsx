import type { ReactNode } from "react";

import { cn } from "../../lib/format";
import { NAV_GROUPS } from "../layout/Navigation";
import { iconFor } from "../../lib/topics";

interface PageHeaderProps {
  eyebrow?: string;
  title: string;
  description?: string;
  aside?: ReactNode;
  className?: string;
}

export function PageHeader({ title, description, aside, className }: PageHeaderProps) {
  const route = NAV_GROUPS.flatMap((group) => [...group.items]).find((item) => item.to === window.location.pathname);
  const Icon = route?.icon ?? iconFor(title);
  return (
    <header className={cn("flex flex-wrap items-start justify-between gap-3", className)}>
      <div className="flex max-w-2xl items-start gap-3">
        {Icon ? <span className="icon-tile"><Icon className="h-5 w-5" aria-hidden="true" /></span> : null}
        <div>
          <h1 className="display-title">{title}</h1>
          {description ? <p className="mt-1 text-sm leading-6 text-ink-600">{description}</p> : null}
        </div>
      </div>
      {aside ? <div className="shrink-0">{aside}</div> : null}
    </header>
  );
}
