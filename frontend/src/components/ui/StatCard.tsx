interface StatCardProps {
  label: string;
  value: string;
  detail?: string;
  tone?: "default" | "warm" | "cool" | "alert";
}

const tones = {
  default: "border-ink-100 bg-white",
  warm: "border-amber-200 bg-amber-50",
  cool: "border-sky-200 bg-sky-50",
  alert: "border-red-200 bg-red-50",
};

export function StatCard({ label, value, detail, tone = "default" }: StatCardProps) {
  return (
    <div className={`rounded-xl border p-4 ${tones[tone]}`}>
      <p className="text-xs font-medium text-ink-600">{label}</p>
      <p className="mt-1 text-2xl font-semibold leading-tight text-ink-950">{value}</p>
      {detail ? <p className="mt-1 text-xs leading-5 text-ink-600">{detail}</p> : null}
    </div>
  );
}
