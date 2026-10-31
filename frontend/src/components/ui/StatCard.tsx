interface StatCardProps {
  label: string;
  value: string;
  detail?: string;
  tone?: "default" | "warm" | "cool" | "alert";
}

const tones = {
  default: "border-ink-100 bg-white",
  warm: "border-ember-200 bg-ember-50",
  cool: "border-sky-100 bg-sky-50",
  alert: "border-red-200 bg-red-50",
};

export function StatCard({ label, value, detail, tone = "default" }: StatCardProps) {
  return (
    <div className={`rounded-2xl border p-4 shadow-panel sm:p-5 ${tones[tone]}`}>
      <p className="text-[0.68rem] font-semibold uppercase tracking-[0.14em] text-ink-500">{label}</p>
      <p className="mt-2 font-display text-2xl leading-none text-ink-950 sm:text-3xl">{value}</p>
      {detail ? <p className="mt-2 text-xs leading-5 text-ink-500">{detail}</p> : null}
    </div>
  );
}
