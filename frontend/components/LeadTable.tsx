import Link from "next/link";
import type { LeadListItem } from "@/types/lead";
import StatusBadge from "@/components/StatusBadge";

export interface LeadTableProps {
  leads: LeadListItem[];
}

export default function LeadTable({ leads }: LeadTableProps) {
  if (leads.length === 0) {
    return (
      <div className="rounded-2xl border border-dashed border-zinc-300 bg-zinc-50/70 px-6 py-10 text-center">
        <p className="text-base font-semibold text-zinc-900">No leads found.</p>
        <p className="mt-2 text-sm text-zinc-500">
          New prospect submissions will appear here as soon as they arrive.
        </p>
      </div>
    );
  }

  return (
    <>
      <div className="grid gap-3 md:hidden">
        {leads.map((lead) => (
          <Link
            key={lead.id}
            href={`/dashboard/${lead.id}`}
            className="rounded-2xl border border-zinc-200 bg-white p-4 shadow-sm transition hover:-translate-y-0.5 hover:border-emerald-700/30 hover:shadow-md focus:outline-none focus:ring-2 focus:ring-emerald-700 focus:ring-offset-2"
          >
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="font-semibold text-zinc-950">
                  {lead.first_name} {lead.last_name}
                </p>
                <p className="mt-1 break-all text-sm text-zinc-500">
                  {lead.email}
                </p>
              </div>
              <StatusBadge status={lead.status} />
            </div>
            <p className="mt-4 text-xs font-medium uppercase tracking-[0.14em] text-zinc-400">
              Submitted {new Date(lead.created_at).toLocaleDateString()}
            </p>
          </Link>
        ))}
      </div>

      <div className="hidden overflow-hidden rounded-2xl border border-zinc-200 bg-white shadow-sm md:block">
        <table className="min-w-full divide-y divide-zinc-200">
          <thead className="bg-zinc-50/80">
            <tr>
              {["Name", "Email", "Status", "Submitted"].map((h) => (
                <th
                  key={h}
                  className="px-5 py-3.5 text-left text-xs font-semibold uppercase tracking-[0.14em] text-zinc-500"
                >
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-zinc-100 bg-white">
            {leads.map((lead) => (
              <tr key={lead.id} className="transition hover:bg-emerald-50/40">
                <td className="px-5 py-4 text-sm font-semibold text-zinc-950">
                  <Link
                    href={`/dashboard/${lead.id}`}
                    className="rounded-sm hover:text-emerald-800 focus:outline-none focus:ring-2 focus:ring-emerald-700 focus:ring-offset-2"
                  >
                    {lead.first_name} {lead.last_name}
                  </Link>
                </td>
                <td className="px-5 py-4 text-sm text-zinc-600">{lead.email}</td>
                <td className="px-5 py-4">
                  <StatusBadge status={lead.status} />
                </td>
                <td className="px-5 py-4 font-mono text-sm text-zinc-500">
                  {new Date(lead.created_at).toLocaleDateString()}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}
