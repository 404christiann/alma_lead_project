"use client";

import { use, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { getLead, UnauthorizedError } from "@/lib/api";
import type { LeadOut } from "@/types/lead";
import StatusBadge from "@/components/StatusBadge";
import MarkReachedOutButton from "@/components/MarkReachedOutButton";

export default function LeadDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const router = useRouter();
  const [lead, setLead] = useState<LeadOut | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    getLead(id)
      .then(setLead)
      .catch((err) => {
        if (err instanceof UnauthorizedError) {
          router.push("/login");
        } else {
          setError("Unable to load this lead. Please return to the dashboard.");
        }
      })
      .finally(() => setLoading(false));
  }, [id, router]);

  if (loading) {
    return (
      <main className="min-h-screen bg-[linear-gradient(180deg,_#fbfaf7_0%,_#f5f1e8_100%)] px-4 py-8 sm:px-6 lg:px-8">
        <div className="mx-auto max-w-4xl animate-pulse space-y-4">
          <div className="h-9 w-40 rounded-full bg-zinc-200" />
          <div className="h-72 rounded-[1.5rem] bg-white/80" />
        </div>
      </main>
    );
  }

  if (!lead) {
    return (
      <main className="min-h-screen bg-[linear-gradient(180deg,_#fbfaf7_0%,_#f5f1e8_100%)] px-4 py-8 sm:px-6 lg:px-8">
        <div className="mx-auto max-w-2xl rounded-2xl border border-zinc-200 bg-white p-8 text-center shadow-sm">
          <p className="text-lg font-semibold text-zinc-950">Lead not found.</p>
          <p className="mt-2 text-sm text-zinc-500">
            {error || "This record may have been removed or is unavailable."}
          </p>
          <Link
            href="/dashboard"
            className="mt-6 inline-flex rounded-full bg-emerald-900 px-4 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-emerald-800 focus:outline-none focus:ring-2 focus:ring-emerald-700 focus:ring-offset-2"
          >
            Back to dashboard
          </Link>
        </div>
      </main>
    );
  }

  const fullName = `${lead.first_name} ${lead.last_name}`;

  return (
    <main className="min-h-screen bg-[linear-gradient(180deg,_#fbfaf7_0%,_#f5f1e8_100%)] px-4 py-8 sm:px-6 lg:px-8">
      <div className="mx-auto max-w-5xl animate-enter-up">
        <Link
          href="/dashboard"
          className="mb-6 inline-flex rounded-full border border-zinc-200 bg-white px-4 py-2 text-sm font-semibold text-zinc-700 shadow-sm transition hover:-translate-y-0.5 hover:border-zinc-300 hover:text-zinc-950 focus:outline-none focus:ring-2 focus:ring-emerald-700 focus:ring-offset-2"
        >
          Back to dashboard
        </Link>

        <div className="rounded-[1.5rem] border border-white/80 bg-white/85 p-4 shadow-xl shadow-emerald-950/5 backdrop-blur sm:p-6">
          <header className="mb-6 flex flex-col gap-5 border-b border-zinc-200 pb-6 sm:flex-row sm:items-start sm:justify-between">
            <div>
              <p className="text-sm font-medium text-emerald-700">Lead detail</p>
              <h1 className="mt-2 text-3xl font-semibold tracking-[-0.03em] text-zinc-950">
                {fullName}
              </h1>
              <p className="mt-2 break-all text-sm text-zinc-500">{lead.email}</p>
            </div>
            <StatusBadge status={lead.status} />
          </header>

          <div className="grid gap-4 lg:grid-cols-[1fr_320px]">
            <section className="rounded-2xl border border-zinc-200 bg-white p-5 shadow-sm">
              <h2 className="text-base font-semibold text-zinc-950">
                Contact information
              </h2>
              <dl className="mt-5 grid gap-4 text-sm sm:grid-cols-2">
                <div>
                  <dt className="font-medium text-zinc-500">First name</dt>
                  <dd className="mt-1 font-semibold text-zinc-950">
                    {lead.first_name}
                  </dd>
                </div>
                <div>
                  <dt className="font-medium text-zinc-500">Last name</dt>
                  <dd className="mt-1 font-semibold text-zinc-950">
                    {lead.last_name}
                  </dd>
                </div>
                <div className="sm:col-span-2">
                  <dt className="font-medium text-zinc-500">Email</dt>
                  <dd className="mt-1 break-all font-semibold text-zinc-950">
                    {lead.email}
                  </dd>
                </div>
              </dl>
            </section>

            <section className="rounded-2xl border border-zinc-200 bg-white p-5 shadow-sm">
              <h2 className="text-base font-semibold text-zinc-950">Status</h2>
              <div className="mt-4">
                <StatusBadge status={lead.status} />
              </div>
              <p className="mt-4 text-sm leading-6 text-zinc-500">
                {lead.status === "PENDING"
                  ? "This lead is ready for attorney outreach."
                  : "This lead has been marked as reached out."}
              </p>
              {lead.status === "PENDING" && (
                <div className="mt-5">
                  <MarkReachedOutButton leadId={lead.id} onSuccess={setLead} />
                </div>
              )}
            </section>

            <section className="rounded-2xl border border-zinc-200 bg-white p-5 shadow-sm lg:col-span-2">
              <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <h2 className="text-base font-semibold text-zinc-950">Resume</h2>
                  <p className="mt-1 text-sm text-zinc-500">
                    Download the uploaded resume or CV using the fresh presigned
                    link.
                  </p>
                </div>
                {lead.resume_filename && lead.resume_url ? (
                  <a
                    href={lead.resume_url}
                    target="_blank"
                    rel="noreferrer"
                    className="inline-flex items-center justify-center rounded-xl bg-emerald-900 px-4 py-3 text-sm font-semibold text-white shadow-lg shadow-emerald-950/15 transition hover:-translate-y-0.5 hover:bg-emerald-800 focus:outline-none focus:ring-2 focus:ring-emerald-700 focus:ring-offset-2"
                  >
                    Download resume
                  </a>
                ) : null}
              </div>
              <div className="mt-5 rounded-xl border border-zinc-200 bg-zinc-50 px-4 py-3">
                <p className="break-all font-mono text-sm text-zinc-700">
                  {lead.resume_filename ?? "No resume file attached"}
                </p>
              </div>
            </section>

            <section className="rounded-2xl border border-zinc-200 bg-white p-5 shadow-sm lg:col-span-2">
              <h2 className="text-base font-semibold text-zinc-950">Timeline</h2>
              <dl className="mt-5 grid gap-4 text-sm sm:grid-cols-2">
                <div>
                  <dt className="font-medium text-zinc-500">Submitted</dt>
                  <dd className="mt-1 font-mono text-zinc-950">
                    {new Date(lead.created_at).toLocaleString()}
                  </dd>
                </div>
                <div>
                  <dt className="font-medium text-zinc-500">Status updated</dt>
                  <dd className="mt-1 font-mono text-zinc-950">
                    {new Date(lead.status_updated_at).toLocaleString()}
                  </dd>
                </div>
              </dl>
            </section>
          </div>
        </div>
      </div>
    </main>
  );
}
