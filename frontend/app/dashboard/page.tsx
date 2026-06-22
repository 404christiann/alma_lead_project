"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { listLeads, UnauthorizedError } from "@/lib/api";
import type { LeadListItem, LeadStatus } from "@/types/lead";
import LeadTable from "@/components/LeadTable";
import StatusFilter from "@/components/StatusFilter";

export default function DashboardPage() {
  const router = useRouter();
  const [leads, setLeads] = useState<LeadListItem[]>([]);
  const [filter, setFilter] = useState<"ALL" | LeadStatus>("ALL");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    listLeads(filter === "ALL" ? undefined : filter)
      .then(setLeads)
      .catch((err) => {
        if (err instanceof UnauthorizedError) {
          router.push("/login");
        } else {
          setError("Unable to load leads. Please refresh and try again.");
        }
      })
      .finally(() => setLoading(false));
  }, [filter, router]);

  function handleFilterChange(nextFilter: "ALL" | LeadStatus) {
    setFilter(nextFilter);
    setError("");
    setLoading(true);
  }

  const pendingCount = leads.filter((lead) => lead.status === "PENDING").length;
  const reachedOutCount = leads.filter((lead) => lead.status === "REACHED_OUT").length;

  return (
    <main className="min-h-screen bg-[linear-gradient(180deg,_#fbfaf7_0%,_#f5f1e8_100%)] px-4 py-8 sm:px-6 lg:px-8">
      <div className="mx-auto max-w-6xl animate-enter-up">
        <header className="mb-8 flex flex-col gap-5 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <p className="text-sm font-medium text-emerald-700">Attorney dashboard</p>
            <h1 className="mt-2 text-3xl font-semibold tracking-[-0.03em] text-zinc-950">
              Leads
            </h1>
            <p className="mt-2 text-sm leading-6 text-zinc-500">
              Review prospect submissions, inspect resumes, and track outreach.
            </p>
          </div>
          <button
            onClick={() => router.push("/login")}
            className="inline-flex items-center justify-center rounded-full border border-zinc-200 bg-white px-4 py-2 text-sm font-semibold text-zinc-700 shadow-sm transition hover:-translate-y-0.5 hover:border-zinc-300 hover:text-zinc-950 focus:outline-none focus:ring-2 focus:ring-emerald-700 focus:ring-offset-2"
          >
            Sign out
          </button>
        </header>

        <section className="mb-6 grid gap-3 sm:grid-cols-3">
          {[
            ["Visible leads", leads.length.toString(), "Current filter result"],
            ["Pending", pendingCount.toString(), "Awaiting attorney outreach"],
            ["Reached out", reachedOutCount.toString(), "Marked as contacted"],
          ].map(([label, value, helper]) => (
            <div
              key={label}
              className="rounded-2xl border border-white/80 bg-white/85 p-5 shadow-sm shadow-emerald-950/5"
            >
              <p className="text-xs font-semibold uppercase tracking-[0.14em] text-zinc-500">
                {label}
              </p>
              <p className="mt-3 font-mono text-3xl font-semibold tracking-[-0.04em] text-zinc-950">
                {value}
              </p>
              <p className="mt-1 text-sm text-zinc-500">{helper}</p>
            </div>
          ))}
        </section>

        <section className="rounded-[1.5rem] border border-white/80 bg-white/85 p-4 shadow-xl shadow-emerald-950/5 backdrop-blur sm:p-5">
          <div className="mb-5 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <h2 className="text-base font-semibold text-zinc-950">Lead queue</h2>
              <p className="mt-1 text-sm text-zinc-500">
                Sorted by most recent submission.
              </p>
            </div>
            <StatusFilter value={filter} onChange={handleFilterChange} />
          </div>

          {error && (
            <div className="mb-4 rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-900">
              {error}
            </div>
          )}

          {loading ? (
            <div className="space-y-3" aria-label="Loading leads">
              {[0, 1, 2].map((item) => (
                <div
                  key={item}
                  className="h-16 animate-pulse rounded-xl bg-zinc-100"
                />
              ))}
            </div>
          ) : (
            <LeadTable leads={leads} />
          )}
        </section>
      </div>
    </main>
  );
}
