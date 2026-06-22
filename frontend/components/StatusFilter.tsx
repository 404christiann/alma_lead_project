"use client";

import type { LeadStatus } from "@/types/lead";

export interface StatusFilterProps {
  value: "ALL" | LeadStatus;
  onChange: (v: "ALL" | LeadStatus) => void;
}

const OPTIONS: { label: string; value: "ALL" | LeadStatus }[] = [
  { label: "All", value: "ALL" },
  { label: "Pending", value: "PENDING" },
  { label: "Reached Out", value: "REACHED_OUT" },
];

export default function StatusFilter({ value, onChange }: StatusFilterProps) {
  return (
    <div
      className="inline-flex rounded-full border border-zinc-200 bg-zinc-50 p-1 shadow-inner"
      aria-label="Filter leads by status"
    >
      {OPTIONS.map((opt) => (
        <button
          key={opt.value}
          onClick={() => onChange(opt.value)}
          className={`rounded-full px-3 py-1.5 text-sm font-semibold transition sm:px-4 ${
            value === opt.value
              ? "bg-emerald-900 text-white shadow-sm"
              : "text-zinc-600 hover:bg-white hover:text-zinc-950"
          }`}
          aria-pressed={value === opt.value}
        >
          {opt.label}
        </button>
      ))}
    </div>
  );
}
