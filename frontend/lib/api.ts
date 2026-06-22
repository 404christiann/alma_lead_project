import { getToken, setToken } from "@/lib/auth";
import type { LeadListItem, LeadOut, LeadStatus } from "@/types/lead";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export class DuplicateLeadError extends Error {
  constructor(message = "A lead with this email already exists") {
    super(message);
    this.name = "DuplicateLeadError";
  }
}

export class FileValidationError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "FileValidationError";
  }
}

export class UnauthorizedError extends Error {
  constructor(message = "Unauthorized") {
    super(message);
    this.name = "UnauthorizedError";
  }
}

export async function login(email: string, password: string): Promise<void> {
  const res = await fetch(`${API_URL}/api/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (res.status === 401) throw new UnauthorizedError();
  if (!res.ok) throw new Error("Login failed");
  const data = await res.json();
  setToken(data.access_token);
}

export async function submitLead(form: FormData): Promise<LeadOut> {
  const res = await fetch(`${API_URL}/api/leads`, {
    method: "POST",
    body: form,
  });
  if (res.status === 409) throw new DuplicateLeadError();
  if (res.status === 422) {
    const body = await res.json();
    throw new FileValidationError(body.detail ?? "File validation failed");
  }
  if (!res.ok) throw new Error("Submission failed");
  return res.json();
}

function authHeaders(): Record<string, string> {
  return { Authorization: `Bearer ${getToken()}` };
}

export async function listLeads(status?: LeadStatus): Promise<LeadListItem[]> {
  const url = status
    ? `${API_URL}/api/leads?status=${status}`
    : `${API_URL}/api/leads`;
  const res = await fetch(url, { headers: authHeaders() });
  if (res.status === 401) throw new UnauthorizedError();
  if (!res.ok) throw new Error("Failed to fetch leads");
  return res.json();
}

export async function getLead(id: string): Promise<LeadOut> {
  const res = await fetch(`${API_URL}/api/leads/${id}`, {
    headers: authHeaders(),
  });
  if (res.status === 401) throw new UnauthorizedError();
  if (!res.ok) throw new Error("Failed to fetch lead");
  return res.json();
}

export async function markReachedOut(id: string): Promise<LeadOut> {
  const res = await fetch(`${API_URL}/api/leads/${id}/status`, {
    method: "PATCH",
    headers: {
      ...authHeaders(),
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ status: "REACHED_OUT" }),
  });
  if (res.status === 401) throw new UnauthorizedError();
  if (!res.ok) throw new Error("Failed to update status");
  return res.json();
}
