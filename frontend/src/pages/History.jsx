import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import {
  getExpenses,
  updateExpense,
  deleteExpense,
  exportExpenses,
} from "../api/expenses";
import config from "../config";

const CATEGORIES = [
  "Groceries",
  "Rent",
  "Utilities",
  "Dining",
  "Transportation",
  "Entertainment",
  "Healthcare",
  "Shopping",
  "Travel",
  "Other",
];
const SPLIT_METHODS = ["50/50", `100% ${config.users.userA}`, `100% ${config.users.userB}`, "Personal"];

const CATEGORY_ICONS = {
  Groceries: "shopping_cart",
  Rent: "home_work",
  Utilities: "bolt",
  Dining: "restaurant",
  Transportation: "directions_car",
  Entertainment: "subscriptions",
  Healthcare: "health_and_safety",
  Shopping: "shopping_bag",
  Travel: "flight_takeoff",
  Other: "more_horiz",
};

const CATEGORY_BG = {
  Groceries: "bg-primary-container text-on-primary-container",
  Rent: "bg-surface-container-high text-on-surface",
  Utilities: "bg-secondary-container text-on-secondary-container",
  Dining: "bg-tertiary-container text-on-tertiary-container",
  Transportation: "bg-primary-container text-on-primary-container",
  Entertainment: "bg-surface-container-highest text-on-surface-variant",
  Healthcare: "bg-primary-container text-on-primary-container",
  Shopping: "bg-secondary-container text-on-secondary-container",
  Travel: "bg-tertiary-container text-on-tertiary-container",
  Other: "bg-surface-container-highest text-on-surface-variant",
};

function formatDate(dateStr) {
  try {
    const d = new Date(dateStr + "T00:00:00");
    return d.toLocaleDateString("en-US", { month: "short", day: "numeric" });
  } catch {
    return dateStr;
  }
}

function getSplitBadge(method) {
  if (method === "50/50") {
    return (
      <span className="bg-secondary-container text-on-secondary-container px-3 py-1 rounded-full text-[10px] font-bold uppercase tracking-wider border border-secondary/10 flex items-center gap-1">
        <span className="material-symbols-outlined text-xs">group</span>
        Split
      </span>
    );
  }
  if (method === "Personal") {
    return (
      <span className="bg-surface-container-highest text-on-surface-variant px-3 py-1 rounded-full text-[10px] font-bold uppercase tracking-wider flex items-center gap-1">
        <span className="material-symbols-outlined text-xs">person</span>
        Personal
      </span>
    );
  }
  return (
    <span className="bg-surface-container-highest text-on-surface-variant px-3 py-1 rounded-full text-[10px] font-bold uppercase tracking-wider flex items-center gap-1">
      <span className="material-symbols-outlined text-xs">person</span>
      Separate
    </span>
  );
}

export default function History() {
  const [expenses, setExpenses] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [filterPaidBy, setFilterPaidBy] = useState("");
  const [filterCategory, setFilterCategory] = useState("");
  const [editTarget, setEditTarget] = useState(null);
  const [deleteTarget, setDeleteTarget] = useState(null);
  const [saving, setSaving] = useState(false);

  const fetchExpenses = async () => {
    setLoading(true);
    try {
      const params = {};
      if (search) params.search = search;
      if (filterPaidBy) params.paid_by = filterPaidBy;
      if (filterCategory) params.category = filterCategory;
      const data = await getExpenses(params);
      setExpenses(data);
    } catch (err) {
      console.error("Failed to fetch expenses:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchExpenses();
  }, [filterPaidBy, filterCategory]);

  const handleSearchSubmit = (e) => {
    e.preventDefault();
    fetchExpenses();
  };

  const handleEditSave = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      await updateExpense(editTarget.id, {
        ...editTarget,
        amount: parseFloat(editTarget.amount),
      });
      setEditTarget(null);
      fetchExpenses();
    } catch (err) {
      console.error("Failed to update expense:", err);
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteConfirm = async () => {
    try {
      await deleteExpense(deleteTarget.id);
      setDeleteTarget(null);
      fetchExpenses();
    } catch (err) {
      console.error("Failed to delete expense:", err);
    }
  };

  const handleExport = async () => {
    const params = {};
    if (search) params.search = search;
    if (filterPaidBy) params.paid_by = filterPaidBy;
    if (filterCategory) params.category = filterCategory;
    await exportExpenses(params);
  };

  const inputClass =
    "block w-full rounded-xl border-none bg-surface-container-high px-4 py-3 text-on-surface font-medium focus:ring-0 focus:bg-white transition-colors";

  return (
    <div className="space-y-8">
      {/* Header */}
      <header className="flex flex-col md:flex-row md:items-end justify-between gap-6">
        <div>
          <h1 className="text-4xl font-headline font-extrabold text-on-surface tracking-tight mb-2">
            Detailed Expenses
          </h1>
          <p className="text-on-surface-variant font-medium">
            Review and manage your shared financial journey.
          </p>
        </div>
        <div className="flex gap-3">
          <button
            onClick={handleExport}
            className="bg-surface-container-high text-on-surface px-6 py-3 rounded-full font-headline font-bold flex items-center gap-2 hover:bg-surface-container-highest transition-colors active:scale-95"
          >
            <span className="material-symbols-outlined">download</span>
            Export
          </button>
          <Link
            to="/add"
            className="bg-gradient-to-br from-primary to-primary-dim text-on-primary px-8 py-3 rounded-full font-headline font-bold flex items-center gap-2 shadow-[0_4px_24px_rgba(16,106,106,0.2)] active:scale-95 transition-transform"
          >
            <span
              className="material-symbols-outlined"
              style={{ fontVariationSettings: "'FILL' 1" }}
            >
              add_circle
            </span>
            Add Expense
          </Link>
        </div>
      </header>

      {/* Search & Filters */}
      <section className="grid grid-cols-1 lg:grid-cols-4 gap-4">
        <form
          onSubmit={handleSearchSubmit}
          className="lg:col-span-2 bg-surface-container-high rounded-3xl p-4 flex items-center gap-3"
        >
          <span className="material-symbols-outlined text-on-surface-variant">
            search
          </span>
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search transactions..."
            className="bg-transparent border-none focus:ring-0 w-full text-on-surface font-medium placeholder:text-outline"
          />
        </form>
        <div className="bg-surface-container rounded-3xl p-2 flex items-center justify-between px-4">
          <span className="text-on-surface-variant font-label font-semibold uppercase tracking-wider text-xs">
            Category
          </span>
          <select
            value={filterCategory}
            onChange={(e) => setFilterCategory(e.target.value)}
            className="bg-transparent border-none focus:ring-0 text-primary font-bold pr-8 cursor-pointer"
          >
            <option value="">All</option>
            {CATEGORIES.map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </select>
        </div>
        <div className="bg-surface-container rounded-3xl p-2 flex items-center justify-between px-4">
          <span className="text-on-surface-variant font-label font-semibold uppercase tracking-wider text-xs">
            Paid By
          </span>
          <select
            value={filterPaidBy}
            onChange={(e) => setFilterPaidBy(e.target.value)}
            className="bg-transparent border-none focus:ring-0 text-primary font-bold pr-8 cursor-pointer"
          >
            <option value="">All</option>
            <option value={config.users.userA}>{config.users.userA}</option>
            <option value={config.users.userB}>{config.users.userB}</option>
          </select>
        </div>
      </section>

      {/* Table */}
      <div className="bg-surface-container-low rounded-3xl overflow-hidden shadow-sm">
        {loading ? (
          <div className="flex items-center justify-center py-16">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
          </div>
        ) : expenses.length === 0 ? (
          <div className="text-center py-16 text-on-surface-variant">
            <span className="material-symbols-outlined text-4xl mb-2 block opacity-40">
              receipt_long
            </span>
            No expenses found.
          </div>
        ) : (
          <>
            {/* Table Header (Desktop) */}
            <div className="hidden md:grid md:grid-cols-12 gap-4 px-8 py-5 bg-surface-container-highest border-b border-outline-variant/10 text-on-surface-variant font-label font-bold uppercase tracking-widest text-[11px]">
              <div className="col-span-1">Date</div>
              <div className="col-span-4">Description</div>
              <div className="col-span-2">Amount</div>
              <div className="col-span-2 text-center">Paid By</div>
              <div className="col-span-2 text-center">Type</div>
              <div className="col-span-1 text-right">Actions</div>
            </div>

            {/* Rows */}
            <div className="flex flex-col gap-3 p-3 md:p-4">
              {expenses.map((expense) => (
                <div
                  key={expense.id}
                  className="bg-surface-container-lowest rounded-2xl md:rounded-none md:bg-transparent md:hover:bg-surface-container transition-colors grid grid-cols-1 md:grid-cols-12 gap-4 items-center px-6 py-6 group"
                >
                  <div className="col-span-1 text-on-surface-variant font-medium md:text-sm">
                    {formatDate(expense.date)}
                  </div>
                  <div className="col-span-4 flex items-center gap-4">
                    <div
                      className={`w-10 h-10 rounded-full flex items-center justify-center ${CATEGORY_BG[expense.category] || CATEGORY_BG.Other}`}
                    >
                      <span className="material-symbols-outlined">
                        {CATEGORY_ICONS[expense.category] || "more_horiz"}
                      </span>
                    </div>
                    <div>
                      <p className="font-bold text-on-surface">
                        {expense.description}
                      </p>
                      <span
                        className={`text-xs px-2 py-0.5 rounded-full font-label font-bold uppercase tracking-tighter ${CATEGORY_BG[expense.category] || CATEGORY_BG.Other}`}
                      >
                        {expense.category}
                      </span>
                    </div>
                  </div>
                  <div className="col-span-2 text-xl font-headline font-bold text-on-surface">
                    ${expense.amount.toFixed(2)}
                  </div>
                  <div className="col-span-2 flex justify-center">
                    <div className="flex items-center gap-2 bg-surface-container px-3 py-1.5 rounded-full">
                      <div className="w-5 h-5 rounded-full bg-primary flex items-center justify-center">
                        <span className="material-symbols-outlined text-on-primary text-[10px]">
                          person
                        </span>
                      </div>
                      <span className="text-xs font-bold text-on-surface">
                        {expense.paid_by}
                      </span>
                    </div>
                  </div>
                  <div className="col-span-2 flex justify-center">
                    {getSplitBadge(expense.split_method)}
                  </div>
                  <div className="col-span-1 flex justify-end gap-2">
                    <button
                      onClick={() => setEditTarget({ ...expense })}
                      className="p-2 rounded-lg hover:bg-surface-container-high text-outline transition-colors"
                      title="Edit"
                    >
                      <span className="material-symbols-outlined">edit</span>
                    </button>
                    <button
                      onClick={() => setDeleteTarget(expense)}
                      className="p-2 rounded-lg hover:bg-error-container/20 text-outline hover:text-error transition-colors"
                      title="Delete"
                    >
                      <span className="material-symbols-outlined">delete</span>
                    </button>
                  </div>
                </div>
              ))}
            </div>

            {/* Footer */}
            <div className="p-6 bg-surface-container border-t border-outline-variant/10 flex items-center justify-between">
              <p className="text-xs font-medium text-on-surface-variant">
                Showing {expenses.length} expense
                {expenses.length !== 1 ? "s" : ""}
              </p>
            </div>
          </>
        )}
      </div>

      {/* Edit Modal */}
      {editTarget && (
        <div className="fixed inset-0 bg-black/40 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-surface-container-lowest rounded-[2rem] shadow-xl max-w-md w-full p-8">
            <div className="flex items-center justify-between mb-6">
              <h2 className="font-headline text-xl font-bold text-on-surface">
                Edit Expense
              </h2>
              <button
                onClick={() => setEditTarget(null)}
                className="p-2 rounded-full hover:bg-surface-container transition-colors"
              >
                <span className="material-symbols-outlined text-on-surface-variant">
                  close
                </span>
              </button>
            </div>
            <form onSubmit={handleEditSave} className="space-y-5">
              <div>
                <label className="font-label text-xs uppercase tracking-widest text-on-surface-variant font-semibold mb-2 block">
                  Date
                </label>
                <input
                  type="date"
                  value={editTarget.date}
                  onChange={(e) =>
                    setEditTarget({ ...editTarget, date: e.target.value })
                  }
                  className={inputClass}
                  required
                />
              </div>
              <div>
                <label className="font-label text-xs uppercase tracking-widest text-on-surface-variant font-semibold mb-2 block">
                  Description
                </label>
                <input
                  type="text"
                  value={editTarget.description}
                  onChange={(e) =>
                    setEditTarget({
                      ...editTarget,
                      description: e.target.value,
                    })
                  }
                  className={inputClass}
                  required
                />
              </div>
              <div>
                <label className="font-label text-xs uppercase tracking-widest text-on-surface-variant font-semibold mb-2 block">
                  Amount ($)
                </label>
                <input
                  type="number"
                  value={editTarget.amount}
                  onChange={(e) =>
                    setEditTarget({ ...editTarget, amount: e.target.value })
                  }
                  step="0.01"
                  min="0.01"
                  className={inputClass}
                  required
                />
              </div>
              <div>
                <label className="font-label text-xs uppercase tracking-widest text-on-surface-variant font-semibold mb-2 block">
                  Category
                </label>
                <select
                  value={editTarget.category}
                  onChange={(e) =>
                    setEditTarget({ ...editTarget, category: e.target.value })
                  }
                  className={inputClass}
                >
                  {CATEGORIES.map((c) => (
                    <option key={c} value={c}>
                      {c}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="font-label text-xs uppercase tracking-widest text-on-surface-variant font-semibold mb-2 block">
                  Paid By
                </label>
                <select
                  value={editTarget.paid_by}
                  onChange={(e) =>
                    setEditTarget({ ...editTarget, paid_by: e.target.value })
                  }
                  className={inputClass}
                >
                  <option value={config.users.userA}>{config.users.userA}</option>
                  <option value={config.users.userB}>{config.users.userB}</option>
                </select>
              </div>
              <div>
                <label className="font-label text-xs uppercase tracking-widest text-on-surface-variant font-semibold mb-2 block">
                  Split Method
                </label>
                <select
                  value={editTarget.split_method}
                  onChange={(e) =>
                    setEditTarget({
                      ...editTarget,
                      split_method: e.target.value,
                    })
                  }
                  className={inputClass}
                >
                  {SPLIT_METHODS.map((s) => (
                    <option key={s} value={s}>
                      {s}
                    </option>
                  ))}
                </select>
              </div>
              <div className="flex gap-3 pt-4">
                <button
                  type="button"
                  onClick={() => setEditTarget(null)}
                  className="flex-1 bg-surface-container-high hover:bg-surface-container-highest text-on-surface font-bold rounded-full px-4 py-3 transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={saving}
                  className="flex-1 bg-gradient-to-r from-primary to-primary-dim text-on-primary font-bold rounded-full px-4 py-3 transition-colors disabled:opacity-60"
                >
                  {saving ? "Saving..." : "Save Changes"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Delete Confirmation */}
      {deleteTarget && (
        <div className="fixed inset-0 bg-black/40 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-surface-container-lowest rounded-[2rem] shadow-xl max-w-sm w-full p-8">
            <div className="flex flex-col items-center text-center mb-6">
              <div className="w-16 h-16 rounded-full bg-error-container/20 flex items-center justify-center mb-4">
                <span className="material-symbols-outlined text-error text-3xl">
                  delete
                </span>
              </div>
              <h2 className="font-headline text-xl font-bold text-on-surface mb-2">
                Delete Expense
              </h2>
              <p className="text-on-surface-variant text-sm">
                Are you sure you want to delete &ldquo;
                <span className="font-medium">{deleteTarget.description}</span>
                &rdquo; (${deleteTarget.amount.toFixed(2)})? This cannot be
                undone.
              </p>
            </div>
            <div className="flex gap-3">
              <button
                onClick={() => setDeleteTarget(null)}
                className="flex-1 bg-surface-container-high hover:bg-surface-container-highest text-on-surface font-bold rounded-full px-4 py-3 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleDeleteConfirm}
                className="flex-1 bg-error hover:bg-error-dim text-on-error font-bold rounded-full px-4 py-3 transition-colors"
              >
                Delete
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
