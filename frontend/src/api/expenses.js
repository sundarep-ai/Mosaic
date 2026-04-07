import { API_BASE } from "../config";
import { fetchWithAuth } from "./fetchWithAuth";

export async function getExpenses(params = {}) {
  const query = new URLSearchParams(params).toString();
  const res = await fetchWithAuth(`${API_BASE}/expenses?${query}`);
  if (!res.ok) throw new Error("Failed to fetch expenses");
  return res.json();
}

export async function getExpense(id) {
  const res = await fetchWithAuth(`${API_BASE}/expenses/${id}`);
  if (!res.ok) throw new Error("Failed to fetch expense");
  return res.json();
}

export async function createExpense(data) {
  const res = await fetchWithAuth(`${API_BASE}/expenses`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error("Failed to create expense");
  return res.json();
}

export async function updateExpense(id, data) {
  const res = await fetchWithAuth(`${API_BASE}/expenses/${id}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error("Failed to update expense");
  return res.json();
}

export async function deleteExpense(id) {
  const res = await fetchWithAuth(`${API_BASE}/expenses/${id}`, {
    method: "DELETE",
  });
  if (!res.ok) throw new Error("Failed to delete expense");
  return res.json();
}

export async function getBalance() {
  const res = await fetchWithAuth(`${API_BASE}/balance`);
  if (!res.ok) throw new Error("Failed to fetch balance");
  return res.json();
}

export async function getMonthlySummary() {
  const res = await fetchWithAuth(`${API_BASE}/monthly-summary`);
  if (!res.ok) throw new Error("Failed to fetch monthly summary");
  return res.json();
}

export async function suggestCategory(description) {
  const res = await fetchWithAuth(
    `${API_BASE}/suggest-category?description=${encodeURIComponent(description)}`,
  );
  if (!res.ok) return null;
  const data = await res.json();
  return data.category;
}

export async function getUniqueDescriptions() {
  const res = await fetchWithAuth(`${API_BASE}/unique-descriptions`);
  if (!res.ok) throw new Error("Failed to fetch unique descriptions");
  return res.json();
}

export async function getSimilarDescriptions(threshold = 0.85) {
  const res = await fetchWithAuth(
    `${API_BASE}/similar-descriptions?threshold=${threshold}`,
  );
  if (!res.ok) throw new Error("Failed to fetch similar descriptions");
  return res.json();
}

export async function mergeDescriptions(merges) {
  const res = await fetchWithAuth(`${API_BASE}/merge-descriptions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ merges }),
  });
  if (!res.ok) throw new Error("Failed to merge descriptions");
  return res.json();
}

export async function dismissMergeSuggestions(dismissals) {
  const res = await fetchWithAuth(`${API_BASE}/dismiss-merge`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ dismissals }),
  });
  if (!res.ok) throw new Error("Failed to dismiss merge suggestions");
  return res.json();
}

export async function getDismissedMerges() {
  const res = await fetchWithAuth(`${API_BASE}/dismissed-merges`);
  if (!res.ok) throw new Error("Failed to fetch dismissed merges");
  return res.json();
}

export async function undismissMerges(ids) {
  const res = await fetchWithAuth(`${API_BASE}/undismiss-merge`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ ids }),
  });
  if (!res.ok) throw new Error("Failed to undismiss merges");
  return res.json();
}

export async function getInsights() {
  const res = await fetchWithAuth(`${API_BASE}/insights`);
  if (!res.ok) throw new Error("Failed to fetch insights");
  return res.json();
}

export async function getAnalytics(params = {}) {
  const query = new URLSearchParams(params).toString();
  const res = await fetchWithAuth(`${API_BASE}/analytics?${query}`);
  if (!res.ok) throw new Error("Failed to fetch analytics");
  return res.json();
}

export async function uploadAvatar(file) {
  const formData = new FormData();
  formData.append("file", file);
  const res = await fetchWithAuth(`${API_BASE}/auth/avatar`, {
    method: "POST",
    body: formData,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Failed to upload avatar");
  }
  return res.json();
}

export async function getMyExpenseSummary() {
  const res = await fetchWithAuth(`${API_BASE}/my-expense-summary`);
  if (!res.ok) throw new Error("Failed to fetch my expense summary");
  return res.json();
}

export async function getPersonalSummary() {
  const res = await fetchWithAuth(`${API_BASE}/personal-summary`);
  if (!res.ok) throw new Error("Failed to fetch personal summary");
  return res.json();
}

export async function getSettings() {
  const res = await fetchWithAuth(`${API_BASE}/settings`);
  if (!res.ok) throw new Error("Failed to fetch settings");
  return res.json();
}

export async function updateSettings(data) {
  const res = await fetchWithAuth(`${API_BASE}/settings`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error("Failed to update settings");
  return res.json();
}

export async function getUserPreferences() {
  const res = await fetchWithAuth(`${API_BASE}/user-preferences`);
  if (!res.ok) throw new Error("Failed to fetch user preferences");
  return res.json();
}

export async function updateUserPreferences(data) {
  const res = await fetchWithAuth(`${API_BASE}/user-preferences`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error("Failed to update user preferences");
  return res.json();
}

export async function exportExpenses(params = {}) {
  const query = new URLSearchParams(params).toString();
  const res = await fetchWithAuth(`${API_BASE}/export?${query}`);
  if (!res.ok) throw new Error("Failed to export expenses");

  // Extract filename from Content-Disposition header, fallback to default
  let filename = "expenses.xlsx";
  const disposition = res.headers.get("Content-Disposition");
  if (disposition) {
    const match = disposition.match(/filename=([^\s;]+)/);
    if (match) filename = match[1];
  }

  const blob = await res.blob();
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  window.URL.revokeObjectURL(url);
}
