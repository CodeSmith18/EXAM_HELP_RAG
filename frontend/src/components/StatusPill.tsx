import { AlertCircle, CheckCircle2, Clock3, Loader2 } from "lucide-react";

interface StatusPillProps {
  status: string;
}

export function StatusPill({ status }: StatusPillProps) {
  const normalized = status.toLowerCase();
  const styles =
    normalized === "ready"
      ? "border-emerald-200 bg-emerald-50 text-emerald-700"
      : normalized === "failed"
        ? "border-red-200 bg-red-50 text-red-700"
        : normalized === "processing"
          ? "border-indigo-200 bg-indigo-50 text-indigo-700"
          : "border-amber-200 bg-amber-50 text-amber-700";
  const Icon =
    normalized === "ready" ? CheckCircle2 : normalized === "failed" ? AlertCircle : normalized === "processing" ? Loader2 : Clock3;

  return (
    <span className={`inline-flex items-center gap-1 rounded-md border px-2 py-1 text-xs font-bold ${styles}`}>
      <Icon size={13} className={normalized === "processing" ? "animate-spin" : ""} aria-hidden="true" />
      {status}
    </span>
  );
}

