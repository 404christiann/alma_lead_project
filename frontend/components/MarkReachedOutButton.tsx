"use client";

import { useState } from "react";
import { markReachedOut } from "@/lib/api";
import type { LeadOut } from "@/types/lead";

export interface MarkReachedOutButtonProps {
  leadId: string;
  onSuccess: (updated: LeadOut) => void;
}

export default function MarkReachedOutButton({
  leadId,
  onSuccess,
}: MarkReachedOutButtonProps) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleClick() {
    setLoading(true);
    setError("");
    try {
      const updated = await markReachedOut(leadId);
      onSuccess(updated);
    } catch {
      setError("Could not update this lead. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div>
      <button
        onClick={handleClick}
        disabled={loading}
        className="inline-flex w-full items-center justify-center gap-2 rounded-xl bg-emerald-900 px-4 py-3 text-sm font-semibold text-white shadow-lg shadow-emerald-950/15 transition hover:-translate-y-0.5 hover:bg-emerald-800 focus:outline-none focus:ring-2 focus:ring-emerald-700 focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-65 disabled:hover:translate-y-0 sm:w-auto"
      >
        {loading && (
          <span className="h-2 w-2 rounded-full bg-white animate-soft-pulse" />
        )}
        {loading ? "Updating..." : "Mark as Reached Out"}
      </button>
      {error && (
        <p className="mt-3 rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-900">
          {error}
        </p>
      )}
    </div>
  );
}
