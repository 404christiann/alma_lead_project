import type { LeadStatus } from "@/types/lead";

export interface StatusBadgeProps {
  status: LeadStatus;
}

export default function StatusBadge({ status }: StatusBadgeProps) {
  const isPending = status === "PENDING";
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-semibold ${
        isPending
          ? "border-amber-200 bg-amber-50 text-amber-900"
          : "border-emerald-200 bg-emerald-50 text-emerald-800"
      }`}
    >
      <span
        className={`h-1.5 w-1.5 rounded-full ${
          isPending ? "bg-amber-500" : "bg-emerald-600"
        }`}
      />
      {isPending ? "Pending" : "Reached Out"}
    </span>
  );
}
