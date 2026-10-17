const BASE_URL = "http://localhost:8000/api";

export const getAuthToken = () => localStorage.getItem("bytevox_token");
export const setAuthToken = (token: string) => localStorage.setItem("bytevox_token", token);
export const removeAuthToken = () => localStorage.removeItem("bytevox_token");

export async function apiRequest(endpoint: string, options: RequestInit = {}) {
  const token = getAuthToken();
  const headers: Record<string, string> = {
    ...(options.headers as Record<string, string>),
  };

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  if (!(options.body instanceof FormData)) {
    headers["Content-Type"] = "application/json";
  }

  const res = await fetch(`${BASE_URL}${endpoint}`, {
    ...options,
    headers,
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({ detail: "Request failed" }));
    throw new Error(errorData.detail || "Server error occurred");
  }

  return res.json();
}