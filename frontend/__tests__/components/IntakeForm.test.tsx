import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import IntakeForm from "@/components/IntakeForm";
import * as api from "@/lib/api";

jest.mock("@/lib/api");

const mockSubmitLead = jest.mocked(api.submitLead);

const SAMPLE_LEAD = {
  id: "1",
  first_name: "Jane",
  last_name: "Doe",
  email: "jane@example.com",
  status: "PENDING" as const,
  status_updated_at: "2024-01-01T00:00:00Z",
  created_at: "2024-01-01T00:00:00Z",
  resume_filename: null,
  resume_url: null,
};

async function fillAndSubmitForm() {
  const user = userEvent.setup();
  await user.type(screen.getByLabelText(/first name/i), "Jane");
  await user.type(screen.getByLabelText(/last name/i), "Doe");
  await user.type(screen.getByLabelText(/email/i), "jane@example.com");
  const file = new File(["resume"], "resume.pdf", { type: "application/pdf" });
  await user.upload(screen.getByLabelText(/resume/i), file);
  await user.click(screen.getByRole("button", { name: /submit/i }));
}

describe("IntakeForm", () => {
  beforeEach(() => jest.clearAllMocks());

  it("shows a success message after a successful submission", async () => {
    mockSubmitLead.mockResolvedValue(SAMPLE_LEAD);
    render(<IntakeForm />);
    await fillAndSubmitForm();
    await waitFor(() =>
      expect(screen.getByText(/application submitted|thank you|success/i)).toBeInTheDocument()
    );
  });

  it("shows a duplicate message when DuplicateLeadError is thrown", async () => {
    mockSubmitLead.mockRejectedValue(new api.DuplicateLeadError("dup"));
    render(<IntakeForm />);
    await fillAndSubmitForm();
    await waitFor(() =>
      expect(screen.getByText(/already.*exists|duplicate/i)).toBeInTheDocument()
    );
  });

  it("shows an error message on a generic API error", async () => {
    mockSubmitLead.mockRejectedValue(new Error("Server error"));
    render(<IntakeForm />);
    await fillAndSubmitForm();
    await waitFor(() =>
      expect(screen.getByText(/something went wrong|error/i)).toBeInTheDocument()
    );
  });
});
