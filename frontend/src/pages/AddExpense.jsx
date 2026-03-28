import { useState, useEffect, useRef, useCallback } from "react";
import { useNavigate, useParams, useLocation } from "react-router-dom";
import {
  createExpense,
  updateExpense,
  getExpense,
} from "../api/expenses";
import { CATEGORIES } from "../constants/categories";
import { useUsers } from "../ConfigContext";
import useDescriptionSuggestions from "../hooks/useDescriptionSuggestions";

const CUSTOM_CATEGORY_VALUE = "__custom__";

export default function AddExpense() {
  const navigate = useNavigate();
  const { id } = useParams();
  const location = useLocation();
  const isEdit = Boolean(id);
  const today = new Date().toISOString().split("T")[0];
  const { userA, userB } = useUsers();
  const prefill = location.state || {};

  const [form, setForm] = useState({
    date: today,
    description: prefill.description || "",
    amount: "",
    category: prefill.category || "Groceries",
    paid_by: userA,
    split_method: "50/50",
  });
  const [customCategory, setCustomCategory] = useState("");
  const [isCustomCategory, setIsCustomCategory] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [loading, setLoading] = useState(isEdit);
  const [error, setError] = useState("");
  const [suggested, setSuggested] = useState(false);
  const [descSuggestions, setDescSuggestions] = useState([]);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const suggestionsRef = useRef(null);
  const descInputRef = useRef(null);
  const { suggest, suggestCategory: suggestCategoryLocal, refresh: refreshSuggestions } = useDescriptionSuggestions();

  useEffect(() => {
    if (!isEdit) return;
    let cancelled = false;
    (async () => {
      try {
        const expense = await getExpense(id);
        if (cancelled) return;
        setForm({
          date: expense.date,
          description: expense.description,
          amount: expense.amount,
          category: expense.category,
          paid_by: expense.paid_by,
          split_method: expense.split_method,
        });
        // If the loaded category isn't in the default list, treat it as custom
        if (!CATEGORIES.includes(expense.category)) {
          setIsCustomCategory(true);
          setCustomCategory(expense.category);
        }
      } catch {
        setError("Could not load expense. It may have been deleted.");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, [id, isEdit]);

  const handleDescriptionChange = useCallback((value) => {
    // Show description suggestions (Feature 1A)
    const matches = suggest(value);
    setDescSuggestions(matches);
    setShowSuggestions(matches.length > 0 && value.trim().length >= 2);

    // Auto-suggest category (Feature 2) — instant, no debounce
    setSuggested(false);
    const cat = suggestCategoryLocal(value);
    if (cat) {
      if (CATEGORIES.includes(cat)) {
        setIsCustomCategory(false);
        setCustomCategory("");
      } else {
        setIsCustomCategory(true);
        setCustomCategory(cat);
      }
      setForm((prev) => ({ ...prev, category: cat }));
      setSuggested(true);
    }
  }, [suggest, suggestCategoryLocal]);

  const handleSuggestionClick = useCallback((item) => {
    setForm((prev) => ({ ...prev, description: item.description }));
    setShowSuggestions(false);
    setDescSuggestions([]);
  }, []);

  // Close suggestions on outside click
  useEffect(() => {
    const handleClickOutside = (e) => {
      if (
        suggestionsRef.current &&
        !suggestionsRef.current.contains(e.target) &&
        descInputRef.current &&
        !descInputRef.current.contains(e.target)
      ) {
        setShowSuggestions(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const handleChange = (e) => {
    const { name, value } = e.target;

    if (name === "category") {
      setSuggested(false);
      if (value === CUSTOM_CATEGORY_VALUE) {
        setIsCustomCategory(true);
        setCustomCategory("");
        setForm({ ...form, category: "" });
        return;
      }
      setIsCustomCategory(false);
      setCustomCategory("");
      setForm({ ...form, category: value });
      return;
    }

    setForm({ ...form, [name]: value });
    if (name === "description") handleDescriptionChange(value);
  };

  const handleCustomCategoryChange = (e) => {
    const value = e.target.value;
    setCustomCategory(value);
    setForm((prev) => ({ ...prev, category: value }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");

    if (!form.description.trim()) {
      setError("Description is required.");
      return;
    }
    const effectiveCategory = isCustomCategory
      ? customCategory.trim()
      : form.category;
    if (!effectiveCategory) {
      setError("Category is required.");
      return;
    }

    const amt = parseFloat(form.amount);
    if (!form.amount || amt === 0) {
      setError("Amount cannot be zero.");
      return;
    }
    if (amt < 0 && effectiveCategory !== "Reimbursement") {
      setError("Negative amounts are only allowed for Reimbursement.");
      return;
    }
    if (amt <= 0 && effectiveCategory !== "Reimbursement") {
      setError("Amount must be greater than 0.");
      return;
    }

    if (form.date > today) {
      setError("Date cannot be in the future.");
      return;
    }

    if (form.split_method === `100% ${form.paid_by}`) {
      setError("Split method cannot assign 100% to the person who paid.");
      return;
    }

    const payload = {
      ...form,
      category: effectiveCategory,
      amount: parseFloat(form.amount),
    };

    setSubmitting(true);
    try {
      if (isEdit) {
        await updateExpense(id, payload);
      } else {
        await createExpense(payload);
      }
      refreshSuggestions();
      navigate(isEdit ? "/history" : "/");
    } catch {
      setError(
        isEdit
          ? "Failed to update expense. Please try again."
          : "Failed to log expense. Please try again.",
      );
    } finally {
      setSubmitting(false);
    }
  };

  const splitMethods = [
    {
      value: "50/50",
      label: "Split 50/50",
      icon: "call_split",
      filled: true,
    },
    {
      value:
        form.paid_by === userA
          ? `100% ${userB}`
          : `100% ${userA}`,
      label: (
        <>
          100%
          <br />
          (Other Owes)
        </>
      ),
      icon: "send_to_mobile",
      filled: false,
    },
    {
      value: "Personal",
      label: "Personal",
      icon: "person_off",
      filled: false,
    },
  ];

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
      </div>
    );
  }

  return (
    <div className="max-w-2xl mx-auto px-4">
      <section className="bg-surface-container-lowest rounded-[2rem] p-8 shadow-[0_4px_32px_rgba(47,51,52,0.04)]">
        <header className="mb-10 text-center">
          <h2 className="font-headline text-3xl font-extrabold text-primary tracking-tight mb-2">
            {isEdit ? "Edit Expense" : "New Expense"}
          </h2>
          <p className="text-on-surface-variant font-medium">
            {isEdit
              ? "Update the details below."
              : "Keep your shared balance in harmony."}
          </p>
        </header>

        {error && (
          <div className="bg-error-container/20 border border-error/20 text-error px-4 py-3 rounded-xl text-sm mb-6 flex items-center gap-2">
            <span className="material-symbols-outlined text-sm">error</span>
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-8">
          {/* Amount Section (Hero Input) */}
          <div className="flex flex-col items-center justify-center py-6">
            <label className="font-label text-xs uppercase tracking-widest text-on-surface-variant font-semibold mb-2">
              Total Amount
            </label>
            <div className="relative flex items-center justify-center">
              <span className="text-4xl font-headline font-bold text-primary mr-1">
                $
              </span>
              <input
                autoFocus={!isEdit}
                type="number"
                name="amount"
                value={form.amount}
                onChange={handleChange}
                step="0.01"
                className="w-48 text-5xl font-headline font-extrabold text-primary bg-transparent border-none focus:ring-0 text-center placeholder:text-primary/20"
                placeholder="0.00"
                required
              />
            </div>
            <div className="h-1 w-24 bg-primary-container rounded-full mt-4"></div>
          </div>

          {/* Date & Description Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="flex flex-col">
              <label className="font-label text-xs uppercase tracking-widest text-on-surface-variant font-semibold mb-2 ml-1">
                Date
              </label>
              <div className="bg-surface-container-high rounded-xl px-4 py-3 flex items-center focus-within:bg-white transition-colors">
                <span className="material-symbols-outlined text-primary/60 mr-3">
                  calendar_today
                </span>
                <input
                  type="date"
                  name="date"
                  value={form.date}
                  onChange={handleChange}
                  max={today}
                  className="bg-transparent border-none focus:ring-0 w-full font-medium text-on-surface"
                  required
                />
              </div>
            </div>
            <div className="flex flex-col relative">
              <label className="font-label text-xs uppercase tracking-widest text-on-surface-variant font-semibold mb-2 ml-1">
                Description
                {suggested && (
                  <span className="inline-flex items-center gap-1 ml-2 text-[10px] font-normal text-primary normal-case tracking-normal">
                    <span className="material-symbols-outlined text-[12px]">
                      auto_awesome
                    </span>
                    Auto-suggested category
                  </span>
                )}
              </label>
              <div className="bg-surface-container-high rounded-xl px-4 py-3 flex items-center focus-within:bg-white transition-colors">
                <span className="material-symbols-outlined text-primary/60 mr-3">
                  edit_note
                </span>
                <input
                  ref={descInputRef}
                  type="text"
                  name="description"
                  value={form.description}
                  onChange={handleChange}
                  onKeyDown={(e) => {
                    if (e.key === "Escape") setShowSuggestions(false);
                  }}
                  onFocus={() => {
                    if (descSuggestions.length > 0) setShowSuggestions(true);
                  }}
                  placeholder="What was it for?"
                  className="bg-transparent border-none focus:ring-0 w-full font-medium text-on-surface"
                  required
                />
              </div>
              {showSuggestions && descSuggestions.length > 0 && (
                <div
                  ref={suggestionsRef}
                  className="absolute top-full left-0 right-0 mt-1 bg-surface-container-lowest rounded-xl shadow-lg border border-outline-variant/20 z-50 overflow-hidden"
                >
                  <div className="px-3 py-1.5 text-[10px] uppercase tracking-widest text-on-surface-variant/60 font-semibold">
                    Did you mean?
                  </div>
                  {descSuggestions.map((item) => (
                    <button
                      key={`${item.description}-${item.category}`}
                      type="button"
                      onClick={() => handleSuggestionClick(item)}
                      className="w-full px-3 py-2.5 text-left hover:bg-surface-container-high transition-colors flex items-center justify-between gap-2"
                    >
                      <span className="font-medium text-on-surface text-sm truncate">
                        {item.description}
                      </span>
                      <span className="text-[10px] text-on-surface-variant/60 shrink-0">
                        {item.category} ({item.count})
                      </span>
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Category */}
          <div className="flex flex-col">
            <label className="font-label text-xs uppercase tracking-widest text-on-surface-variant font-semibold mb-2 ml-1">
              Category
            </label>
            <div className="bg-surface-container-high rounded-xl px-4 py-1 flex items-center focus-within:bg-white transition-colors">
              <span className="material-symbols-outlined text-primary/60 mr-3">
                category
              </span>
              <select
                name="category"
                value={
                  isCustomCategory ? CUSTOM_CATEGORY_VALUE : form.category
                }
                onChange={handleChange}
                className="bg-transparent border-none focus:ring-0 w-full font-medium text-on-surface py-3"
              >
                {CATEGORIES.map((c) => (
                  <option key={c} value={c}>
                    {c}
                  </option>
                ))}
                <option value={CUSTOM_CATEGORY_VALUE}>+ New Category</option>
              </select>
            </div>
            {isCustomCategory && (
              <div className="mt-3 bg-surface-container-high rounded-xl px-4 py-3 flex items-center focus-within:bg-white transition-colors">
                <span className="material-symbols-outlined text-primary/60 mr-3">
                  edit
                </span>
                <input
                  type="text"
                  value={customCategory}
                  onChange={handleCustomCategoryChange}
                  placeholder="Enter new category name"
                  className="bg-transparent border-none focus:ring-0 w-full font-medium text-on-surface"
                  autoFocus
                  required
                />
              </div>
            )}
          </div>

          {/* Who Paid */}
          <div className="flex flex-col">
            <label className="font-label text-xs uppercase tracking-widest text-on-surface-variant font-semibold mb-3 ml-1">
              Who Paid?
            </label>
            <div className="bg-surface-container-high p-1.5 rounded-2xl flex gap-1.5 h-16">
              {[userA, userB].map((user) => (
                <button
                  key={user}
                  type="button"
                  onClick={() => {
                    const newForm = { ...form, paid_by: user };
                    if (form.split_method.startsWith("100%")) {
                      const other =
                        user === userA
                          ? userB
                          : userA;
                      newForm.split_method = `100% ${other}`;
                    }
                    setForm(newForm);
                  }}
                  className={`flex-1 rounded-xl flex items-center justify-center gap-2 transition-colors ${
                    form.paid_by === user
                      ? "bg-white shadow-sm font-bold text-primary border-2 border-primary/10"
                      : "font-semibold text-on-surface-variant hover:bg-surface-container"
                  }`}
                >
                  <span
                    className="material-symbols-outlined"
                    style={
                      form.paid_by === user
                        ? { fontVariationSettings: "'FILL' 1" }
                        : undefined
                    }
                  >
                    person
                  </span>
                  {user}
                </button>
              ))}
            </div>
          </div>

          {/* Split Method */}
          <div className="flex flex-col">
            <label className="font-label text-xs uppercase tracking-widest text-on-surface-variant font-semibold mb-3 ml-1">
              Split Method
            </label>
            <div className="grid grid-cols-3 gap-3">
              {splitMethods.map((method) => {
                const isActive = form.split_method === method.value;
                return (
                  <button
                    key={method.value}
                    type="button"
                    onClick={() =>
                      setForm({ ...form, split_method: method.value })
                    }
                    className={`flex flex-col items-center justify-center py-4 px-1 rounded-2xl border-2 transition-colors group ${
                      isActive
                        ? "bg-secondary-container/30 border-secondary/20 hover:bg-secondary-container/50"
                        : "bg-surface-container-high border-transparent hover:border-outline-variant/20"
                    }`}
                  >
                    <div
                      className={`w-10 h-10 rounded-full flex items-center justify-center mb-2 group-active:scale-90 transition-transform ${
                        isActive
                          ? "bg-secondary-container"
                          : "bg-surface-variant"
                      }`}
                    >
                      <span
                        className={`material-symbols-outlined ${isActive ? "text-on-secondary-container" : "text-on-surface-variant"}`}
                        style={
                          isActive
                            ? { fontVariationSettings: "'FILL' 1" }
                            : undefined
                        }
                      >
                        {method.icon}
                      </span>
                    </div>
                    <span
                      className={`text-[11px] text-center leading-tight ${
                        isActive
                          ? "font-bold text-on-secondary-container"
                          : "font-semibold text-on-surface-variant"
                      }`}
                    >
                      {method.label}
                    </span>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Submit */}
          <div className="pt-6">
            <button
              type="submit"
              disabled={submitting}
              className="w-full h-16 rounded-full bg-gradient-to-r from-primary to-primary-dim text-on-primary font-headline font-bold text-lg shadow-lg hover:shadow-primary/20 active:scale-[0.98] transition-all duration-200 flex items-center justify-center gap-2 disabled:opacity-60"
            >
              <span className="material-symbols-outlined">check_circle</span>
              {submitting
                ? isEdit
                  ? "Saving..."
                  : "Logging..."
                : isEdit
                  ? "Save Changes"
                  : "Log Expense"}
            </button>
          </div>
        </form>
      </section>

      {/* Collaborative Tip */}
      {!isEdit && (
        <div className="mt-8 mb-12 bg-secondary-container/20 p-6 rounded-3xl flex items-start gap-4 border border-secondary-container/30">
          <div className="bg-secondary-container p-3 rounded-2xl">
            <span className="material-symbols-outlined text-on-secondary-container">
              info
            </span>
          </div>
          <div>
            <h4 className="font-bold text-on-secondary-container mb-1">
              Collaborative Tip
            </h4>
            <p className="text-sm text-on-secondary-container opacity-80 leading-relaxed">
              Use &quot;Split 50/50&quot; for shared expenses and
              &quot;Personal&quot; for individual ones. The balance will
              automatically update to reflect who owes whom.
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
