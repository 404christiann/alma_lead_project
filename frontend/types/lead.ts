export type LeadStatus = "PENDING" | "REACHED_OUT";

export interface LeadOut {
  id: string;
  first_name: string;
  last_name: string;
  email: string;
  status: LeadStatus;
  status_updated_at: string;
  created_at: string;
  resume_filename: string | null;
  resume_url: string | null;
}

export interface LeadListItem {
  id: string;
  first_name: string;
  last_name: string;
  email: string;
  status: LeadStatus;
  created_at: string;
  status_updated_at: string;
}
