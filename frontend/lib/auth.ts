export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("alma_token");
}

export function setToken(token: string): void {
  localStorage.setItem("alma_token", token);
  document.cookie = `alma_token=${token}; path=/; Max-Age=${8 * 3600}`;
}

export function clearToken(): void {
  localStorage.removeItem("alma_token");
  document.cookie = "alma_token=; Max-Age=0; path=/";
}
