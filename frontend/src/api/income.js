import { API_BASE } from "../config";
import { fetchWithAuth } from "./fetchWithAuth";

export async function getIncome(params = {}) {
  const query = new URLSearchParams(params).toString();
  const res = await fetchWithAuth(`${API_BASE}/income?${query}`);
  if (!res.ok) throw new Error("Failed to fetch income");
  return res.json();
}

export async function addIncome(data) {
  const res = await fetchWithAuth(`${API_BASE}/income`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Failed to add income");
  }
  return res.json();
}

export async function updateIncome(id, data) {
  const res = await fetchWithAuth(`${API_BASE}/income/${id}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Failed to update income");
  }
  return res.json();
}

export async function deleteIncome(id) {
  const res = await fetchWithAuth(`${API_BASE}/income/${id}`, {
    method: "DELETE",
  });
  if (!res.ok) throw new Error("Failed to delete income");
}

export async function getMonthlyIncomeSummary() {
  const res = await fetchWithAuth(`${API_BASE}/income/monthly-summary`);
  if (!res.ok) throw new Error("Failed to fetch income summary");
  return res.json();
}

export async function getIncomeSankey(params = {}) {
  const res = await fetchWithAuth(`${API_BASE}/income/sankey`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(params),
  });
  if (!res.ok) throw new Error("Failed to fetch Sankey data");
  return res.json();
}
