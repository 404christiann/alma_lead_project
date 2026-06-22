import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import MarkReachedOutButton from "@/components/MarkReachedOutButton";
import * as api from "@/lib/api";

jest.mock("@/lib/api");

const mockMarkReachedOut = jest.mocked(api.markReachedOut);

const UPDATED_LEAD = {
  id: "lead-123",
  first_name: "Jane",
  last_name: "Doe",
  email: "jane@example.com",
  status: "REACHED_OUT" as const,
  status_updated_at: "2024-01-02T00:00:00Z",
  created_at: "2024-01-01T00:00:00Z",
  resume_filename: null,
  resume_url: null,
};

describe("MarkReachedOutButton", () => {
  beforeEach(() => jest.clearAllMocks());

  it("calls markReachedOut with the correct leadId when clicked", async () => {
    mockMarkReachedOut.mockResolvedValue(UPDATED_LEAD);
    const onSuccess = jest.fn();
    render(<MarkReachedOutButton leadId="lead-123" onSuccess={onSuccess} />);

    await userEvent.click(screen.getByRole("button"));

    await waitFor(() =>
      expect(mockMarkReachedOut).toHaveBeenCalledWith("lead-123")
    );
  });

  it("calls onSuccess with the updated lead after API resolves", async () => {
    mockMarkReachedOut.mockResolvedValue(UPDATED_LEAD);
    const onSuccess = jest.fn();
    render(<MarkReachedOutButton leadId="lead-123" onSuccess={onSuccess} />);

    await userEvent.click(screen.getByRole("button"));

    await waitFor(() =>
      expect(onSuccess).toHaveBeenCalledWith(UPDATED_LEAD)
    );
  });
});
