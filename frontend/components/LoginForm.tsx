"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { login, UnauthorizedError } from "@/lib/api";

export default function LoginForm() {
  const router = useRouter();
  const [error, setError] = useState<string>("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setError("");
    setLoading(true);

    const data = new FormData(e.currentTarget);
    const email = data.get("email") as string;
    const password = data.get("password") as string;

    try {
      await login(email, password);
      router.push("/dashboard");
    } catch (err) {
      if (err instanceof UnauthorizedError) {
        setError("Invalid email or password.");
      } else {
        setError("Something went wrong. Please try again.");
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-5">
      {error && (
        <div
          className="animate-enter-up rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm leading-6 text-rose-900"
          role="alert"
        >
          {error}
        </div>
      )}

      <div>
        <label htmlFor="email" className="block text-sm font-semibold text-zinc-800">
          Email
        </label>
        <input
          id="email"
          name="email"
          type="email"
          required
          autoComplete="email"
          placeholder="attorney@example.com"
          className="mt-2 block w-full rounded-xl border border-zinc-200 bg-white px-4 py-3 text-sm text-zinc-950 shadow-sm transition placeholder:text-zinc-400 hover:border-zinc-300 focus:border-emerald-700 focus:outline-none focus:ring-4 focus:ring-emerald-700/10"
        />
      </div>

      <div>
        <label htmlFor="password" className="block text-sm font-semibold text-zinc-800">
          Password
        </label>
        <input
          id="password"
          name="password"
          type="password"
          required
          autoComplete="current-password"
          placeholder="Enter your password"
          className="mt-2 block w-full rounded-xl border border-zinc-200 bg-white px-4 py-3 text-sm text-zinc-950 shadow-sm transition placeholder:text-zinc-400 hover:border-zinc-300 focus:border-emerald-700 focus:outline-none focus:ring-4 focus:ring-emerald-700/10"
        />
      </div>

      <button
        type="submit"
        disabled={loading}
        className="flex w-full items-center justify-center gap-2 rounded-xl bg-emerald-900 px-4 py-3 text-sm font-semibold text-white shadow-lg shadow-emerald-950/15 transition hover:-translate-y-0.5 hover:bg-emerald-800 focus:outline-none focus:ring-2 focus:ring-emerald-700 focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-65 disabled:hover:translate-y-0"
      >
        {loading && (
          <span className="h-2 w-2 rounded-full bg-white animate-soft-pulse" />
        )}
        {loading ? "Signing in..." : "Sign In"}
      </button>
    </form>
  );
}
