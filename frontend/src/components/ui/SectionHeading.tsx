import type { ReactNode } from "react";

import { cn } from "../../lib/format";

interface SectionHeadingProps {
  eyebrow?: string;
  title: string;
  description?: string;
  action?: ReactNode;
  className?: string;
}

export function SectionHeading({ eyebrow, title, description, action, className }: SectionHeadingProps) {
  return (
    <div className={cn("flex flex-wrap items-end justify-between gap-4", className)}>
      <div>
        {eyebrow ? <p className="eyebrow">{eyebrow}</p> : null}
        <h2 className="section-title mt-1">{title}</h2>
        {description ? <p className="prose-civic mt-2 max-w-2xl">{description}</p> : null}
      </div>
      {action}
    </div>
  );
}
