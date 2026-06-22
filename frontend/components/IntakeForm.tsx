"use client";

import { useState } from "react";
import { submitLead, DuplicateLeadError, FileValidationError } from "@/lib/api";

type FormState = "idle" | "submitting" | "success" | "error" | "duplicate";

const ALLOWED_EXTENSIONS = [".pdf", ".doc", ".docx", ".png", ".jpg", ".jpeg"];
const MAX_BYTES = 10 * 1024 * 1024;

export default function IntakeForm() {
  const [state, setState] = useState<FormState>("idle");
  const [fieldError, setFieldError] = useState<string>("");
  const [selectedFileName, setSelectedFileName] = useState<string>("");

  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setFieldError("");
    setState("idle");

    const form = e.currentTarget;
    const data = new FormData(form);

    const firstName = (data.get("first_name") as string)?.trim();
    const lastName = (data.get("last_name") as string)?.trim();
    const email = (data.get("email") as string)?.trim();
    const fileInput = form.elements.namedItem("resume") as HTMLInputElement | null;
    const file = fileInput?.files?.[0] ?? null;

    if (!firstName || !lastName || !email) {
      setFieldError("All fields are required.");
      return;
    }

    if (!file || file.size === 0) {
      setFieldError("Please upload a resume.");
      return;
    }

    const ext = "." + file.name.split(".").pop()?.toLowerCase();
    if (!ALLOWED_EXTENSIONS.includes(ext)) {
      setFieldError(`File type not supported. Allowed: ${ALLOWED_EXTENSIONS.join(", ")}`);
      return;
    }

    if (file.size > MAX_BYTES) {
      setFieldError("File must be 10 MB or smaller.");
      return;
    }

    setState("submitting");
    try {
      await submitLead(data);
      setState("success");
      setSelectedFileName("");
      form.reset();
    } catch (err) {
      if (err instanceof DuplicateLeadError) {
        setState("duplicate");
      } else if (err instanceof FileValidationError) {
        setState("idle");
        setFieldError(err.message);
      } else {
        setState("error");
      }
    }
  }

  if (state === "success") {
    return (
      <div
        className="animate-enter-up rounded-2xl border border-emerald-200 bg-emerald-50/80 p-6 text-center shadow-sm"
        role="status"
      >
        <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-emerald-600 text-lg font-semibold text-white">
          OK
        </div>
        <h2 className="text-lg font-semibold text-emerald-950">
          Application Submitted!
        </h2>
        <p className="mt-2 text-sm leading-6 text-emerald-800">
          The attorney team has your information and will be in touch soon.
        </p>
        <button
          onClick={() => setState("idle")}
          className="mt-5 rounded-full border border-emerald-700/20 bg-white px-4 py-2 text-sm font-semibold text-emerald-800 shadow-sm transition hover:-translate-y-0.5 hover:border-emerald-700/30 hover:bg-emerald-50 focus:outline-none focus:ring-2 focus:ring-emerald-700 focus:ring-offset-2"
        >
          Submit another
        </button>
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit} noValidate className="space-y-5">
      {state === "duplicate" && (
        <div
          className="animate-enter-up rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm leading-6 text-amber-900"
          role="alert"
        >
          <span className="font-semibold">Already submitted.</span> A lead with
          this email already exists.
        </div>
      )}
      {state === "error" && (
        <div
          className="animate-enter-up rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm leading-6 text-rose-900"
          role="alert"
        >
          Something went wrong. Please try again.
        </div>
      )}
      {fieldError && (
        <div
          className="animate-enter-up rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm leading-6 text-rose-900"
          role="alert"
        >
          {fieldError}
        </div>
      )}

      <div>
        <label htmlFor="first_name" className="block text-sm font-semibold text-zinc-800">
          First Name
        </label>
        <input
          id="first_name"
          name="first_name"
          type="text"
          required
          autoComplete="given-name"
          placeholder="Jane"
          className="mt-2 block w-full rounded-xl border border-zinc-200 bg-white px-4 py-3 text-sm text-zinc-950 shadow-sm transition placeholder:text-zinc-400 hover:border-zinc-300 focus:border-emerald-700 focus:outline-none focus:ring-4 focus:ring-emerald-700/10"
        />
      </div>

      <div>
        <label htmlFor="last_name" className="block text-sm font-semibold text-zinc-800">
          Last Name
        </label>
        <input
          id="last_name"
          name="last_name"
          type="text"
          required
          autoComplete="family-name"
          placeholder="Doe"
          className="mt-2 block w-full rounded-xl border border-zinc-200 bg-white px-4 py-3 text-sm text-zinc-950 shadow-sm transition placeholder:text-zinc-400 hover:border-zinc-300 focus:border-emerald-700 focus:outline-none focus:ring-4 focus:ring-emerald-700/10"
        />
      </div>

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
          placeholder="jane@example.com"
          className="mt-2 block w-full rounded-xl border border-zinc-200 bg-white px-4 py-3 text-sm text-zinc-950 shadow-sm transition placeholder:text-zinc-400 hover:border-zinc-300 focus:border-emerald-700 focus:outline-none focus:ring-4 focus:ring-emerald-700/10"
        />
      </div>

      <div>
        <label htmlFor="resume" className="block text-sm font-semibold text-zinc-800">
          Resume / CV
        </label>
        <div className="mt-2 rounded-2xl border border-dashed border-zinc-300 bg-zinc-50/70 p-4 transition hover:border-emerald-700/40 hover:bg-emerald-50/30">
          <input
            id="resume"
            name="resume"
            type="file"
            accept=".pdf,.doc,.docx,.png,.jpg,.jpeg"
            required
            onChange={(event) =>
              setSelectedFileName(event.currentTarget.files?.[0]?.name ?? "")
            }
            className="block w-full cursor-pointer text-sm text-zinc-600 file:mr-4 file:rounded-full file:border-0 file:bg-emerald-900 file:px-4 file:py-2.5 file:text-sm file:font-semibold file:text-white file:shadow-sm hover:file:bg-emerald-800 focus:outline-none"
          />
          <p className="mt-3 text-xs leading-5 text-zinc-500">
            PDF, DOC, DOCX, PNG, JPG - max 10 MB.
          </p>
          {selectedFileName && (
            <p className="mt-2 rounded-lg bg-white px-3 py-2 text-xs font-medium text-zinc-700 shadow-sm">
              Selected: {selectedFileName}
            </p>
          )}
        </div>
      </div>

      <button
        type="submit"
        disabled={state === "submitting"}
        className="group flex w-full items-center justify-center gap-2 rounded-xl bg-emerald-900 px-4 py-3 text-sm font-semibold text-white shadow-lg shadow-emerald-950/15 transition hover:-translate-y-0.5 hover:bg-emerald-800 focus:outline-none focus:ring-2 focus:ring-emerald-700 focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-65 disabled:hover:translate-y-0"
      >
        {state === "submitting" && (
          <span className="h-2 w-2 rounded-full bg-white animate-soft-pulse" />
        )}
        {state === "submitting" ? "Submitting..." : "Submit Application"}
      </button>
    </form>
  );
}
