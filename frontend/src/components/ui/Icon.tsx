import { cn } from "../../lib/format";
import { iconFor } from "../../lib/topics";

/** A small coloured icon for a topic. Text with no matching topic shows nothing. */
export function TopicIcon({ text, className }: { text: string; className?: string }) {
  const Icon = iconFor(text);
  return Icon ? <Icon className={cn("h-4 w-4 shrink-0 text-brand", className)} aria-hidden="true" /> : null;
}
