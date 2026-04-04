export const API_BASE = import.meta.env.VITE_API_BASE ?? "/api";

const config = {
  appName: "MosaicTally",
};

export default config;

// Fetches user display names from the backend (single source of truth).
// Returns { userA, userB } or falls back to empty strings on error.
export async function fetchAppConfig() {
  try {
    const res = await fetch(`${API_BASE}/config`);
    if (!res.ok) throw new Error("Failed to fetch config");
    return await res.json();
  } catch {
    return { userA: "", userB: "", mode: "duo" };
  }
}
