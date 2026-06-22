import {
  DuplicateLeadError,
  UnauthorizedError,
  submitLead,
  listLeads,
  getLead,
  markReachedOut,
} from "@/lib/api";

const mockFetch = jest.fn();
global.fetch = mockFetch;

jest.mock("@/lib/auth", () => ({
  getToken: () => "mock-bearer-token",
  setToken: jest.fn(),
  clearToken: jest.fn(),
}));

const ok = (body: unknown, status = 200) => ({
  status,
  ok: status >= 200 && status < 300,
  json: () => Promise.resolve(body),
});

describe("lib/api", () => {
  beforeEach(() => mockFetch.mockReset());

  // ── submitLead ────────────────────────────────────────────────────────────

  describe("submitLead", () => {
    it("throws DuplicateLeadError on 409", async () => {
      mockFetch.mockResolvedValue(ok({}, 409));
      await expect(submitLead(new FormData())).rejects.toThrow(DuplicateLeadError);
    });

    it("returns the lead on success", async () => {
      const lead = { id: "1", status: "PENDING" };
      mockFetch.mockResolvedValue(ok(lead, 201));
      await expect(submitLead(new FormData())).resolves.toEqual(lead);
    });
  });

  // ── listLeads ─────────────────────────────────────────────────────────────

  describe("listLeads", () => {
    it("throws UnauthorizedError on 401", async () => {
      mockFetch.mockResolvedValue(ok({}, 401));
      await expect(listLeads()).rejects.toThrow(UnauthorizedError);
    });

    it("attaches Authorization: Bearer header", async () => {
      mockFetch.mockResolvedValue(ok([], 200));
      await listLeads();
      const [, init] = mockFetch.mock.calls[0];
      expect((init as RequestInit).headers).toMatchObject({
        Authorization: "Bearer mock-bearer-token",
      });
    });
  });

  // ── getLead ───────────────────────────────────────────────────────────────

  describe("getLead", () => {
    it("throws UnauthorizedError on 401", async () => {
      mockFetch.mockResolvedValue(ok({}, 401));
      await expect(getLead("some-id")).rejects.toThrow(UnauthorizedError);
    });

    it("attaches Authorization: Bearer header", async () => {
      mockFetch.mockResolvedValue(ok({ id: "some-id" }, 200));
      await getLead("some-id");
      const [, init] = mockFetch.mock.calls[0];
      expect((init as RequestInit).headers).toMatchObject({
        Authorization: "Bearer mock-bearer-token",
      });
    });
  });

  // ── markReachedOut ────────────────────────────────────────────────────────

  describe("markReachedOut", () => {
    it("throws UnauthorizedError on 401", async () => {
      mockFetch.mockResolvedValue(ok({}, 401));
      await expect(markReachedOut("some-id")).rejects.toThrow(UnauthorizedError);
    });

    it("attaches Authorization: Bearer header", async () => {
      mockFetch.mockResolvedValue(ok({ id: "some-id", status: "REACHED_OUT" }, 200));
      await markReachedOut("some-id");
      const [, init] = mockFetch.mock.calls[0];
      expect((init as RequestInit).headers).toMatchObject({
        Authorization: "Bearer mock-bearer-token",
      });
    });
  });
});
