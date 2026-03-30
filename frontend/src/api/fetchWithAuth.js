let _onUnauthorized = null;

export function setOnUnauthorized(callback) {
  _onUnauthorized = callback;
}

export async function fetchWithAuth(url, options = {}) {
  const res = await fetch(url, { ...options, credentials: "include" });
  if (res.status === 401 && _onUnauthorized) {
    _onUnauthorized();
    throw new Error("Session expired. Please log in again.");
  }
  return res;
}
