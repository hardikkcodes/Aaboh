import type { ReactNode } from "react";

import { cn } from "../../lib/format";

interface PageHeaderProps {
  eyebrow: string;
  title: string;
  description: string;
  aside?: ReactNode;
  className?: string;
}

export function PageHeader({ eyebrow, title, description, aside, className }: PageHeaderProps) {
  return (
    <header className={cn("flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between", className)}>
      <div className="max-w-3xl">
        <p className="eyebrow">{eyebrow}</p>
        <h1 className="display-title mt-2">{title}</h1>
        <p className="prose-civic mt-3 max-w-2xl text-base">{description}</p>
      </div>
      {aside ? <div className="shrink-0">{aside}</div> : null}
    </header>
  );
}
