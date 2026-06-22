import { getToken, setToken, clearToken } from "@/lib/auth";

describe("lib/auth", () => {
  beforeEach(() => {
    localStorage.clear();
    // Clear alma_token cookie
    document.cookie = "alma_token=; Max-Age=0; path=/";
  });

  describe("setToken", () => {
    it("writes the token to localStorage under alma_token", () => {
      setToken("test-token-123");
      expect(localStorage.getItem("alma_token")).toBe("test-token-123");
    });

    it("writes the token to document.cookie as alma_token", () => {
      setToken("test-token-abc");
      expect(document.cookie).toContain("alma_token=test-token-abc");
    });
  });

  describe("getToken", () => {
    it("returns the token stored in localStorage", () => {
      localStorage.setItem("alma_token", "my-token");
      expect(getToken()).toBe("my-token");
    });

    it("returns null when no token is set", () => {
      expect(getToken()).toBeNull();
    });
  });

  describe("clearToken", () => {
    it("removes the token from localStorage", () => {
      localStorage.setItem("alma_token", "some-token");
      clearToken();
      expect(localStorage.getItem("alma_token")).toBeNull();
    });

    it("clears the alma_token cookie", () => {
      setToken("some-token");
      clearToken();
      expect(document.cookie).not.toContain("alma_token=some-token");
    });
  });
});
