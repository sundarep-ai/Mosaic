const API_BASE = "http://localhost:8000/api";

export async function getExpenses(params = {}) {
  const query = new URLSearchParams(params).toString();
  const res = await fetch(`${API_BASE}/expenses?${query}`);
  if (!res.ok) throw new Error("Failed to fetch expenses");
  return res.json();
}

export async function createExpense(data) {
  const res = await fetch(`${API_BASE}/expenses`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error("Failed to create expense");
  return res.json();
}

export async function updateExpense(id, data) {
  const res = await fetch(`${API_BASE}/expenses/${id}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error("Failed to update expense");
  return res.json();
}

export async function deleteExpense(id) {
  const res = await fetch(`${API_BASE}/expenses/${id}`, { method: "DELETE" });
  if (!res.ok) throw new Error("Failed to delete expense");
  return res.json();
}

export async function getBalance() {
  const res = await fetch(`${API_BASE}/balance`);
  if (!res.ok) throw new Error("Failed to fetch balance");
  return res.json();
}

export async function getMonthlySummary() {
  const res = await fetch(`${API_BASE}/monthly-summary`);
  if (!res.ok) throw new Error("Failed to fetch monthly summary");
  return res.json();
}

export async function suggestCategory(description) {
  const res = await fetch(
    `${API_BASE}/suggest-category?description=${encodeURIComponent(description)}`,
  );
  if (!res.ok) return null;
  const data = await res.json();
  return data.category;
}

export async function getAnalytics(params = {}) {
  const query = new URLSearchParams(params).toString();
  const res = await fetch(`${API_BASE}/analytics?${query}`);
  if (!res.ok) throw new Error("Failed to fetch analytics");
  return res.json();
}

export async function exportExpenses(params = {}) {
  const query = new URLSearchParams(params).toString();
  const res = await fetch(`${API_BASE}/export?${query}`);
  if (!res.ok) throw new Error("Failed to export expenses");
  const blob = await res.blob();
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "expenses.xlsx";
  document.body.appendChild(a);
  a.click();
  a.remove();
  window.URL.revokeObjectURL(url);
}
