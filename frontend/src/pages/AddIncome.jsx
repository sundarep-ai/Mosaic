import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { addIncome } from "../api/income";
import { INCOME_SOURCES } from "../constants/incomeSources";
import { useIncomeMode } from "../hooks/useIncomeMode";
import DateInput from "../components/DateInput";

export default function AddIncome() {
  const navigate = useNavigate();
  const { incomeEnabled } = useIncomeMode();
  const today = new Date().toISOString().split("T")[0];

  const [form, setForm] = useState({
    date: today,
    amount: "",
    source: INCOME_SOURCES[0],
    notes: "",
  });
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  // Redirect away if income mode is not enabled
  useEffect(() => {
    if (!incomeEnabled) navigate("/", { replace: true });
  }, [incomeEnabled, navigate]);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setForm((prev) => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");

    const amount = parseFloat(form.amount);
    if (!amount || amount <= 0) {
      setError("Amount must be a positive number.");
      return;
    }
    if (form.date > today) {
      setError("Date cannot be in the future.");
      return;
    }

    const payload = {
      date: form.date,
      amount,
      source: form.source,
      notes: form.notes.trim() || null,
    };

    setSubmitting(true);
    try {
      await addIncome(payload);
      navigate("/");
    } catch (err) {
      setError(err.message || "Failed to log income. Please try again.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto px-4">
      <section className="bg-surface-container-lowest rounded-[2rem] p-8 shadow-[0_4px_32px_rgba(47,51,52,0.04)]">
        <header className="mb-10 text-center">
          <h2 className="font-headline text-3xl font-extrabold text-tertiary tracking-tight mb-2">
            Log Income
          </h2>
          <p className="text-on-surface-variant font-medium">
            Record income you&apos;ve received.
          </p>
        </header>

        {error && (
          <div className="bg-error-container/20 border border-error/20 text-error px-4 py-3 rounded-xl text-sm mb-6 flex items-center gap-2">
            <span className="material-symbols-outlined text-sm">error</span>
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-8">
          {/* Amount hero input */}
          <div className="flex flex-col items-center justify-center py-6">
            <label className="font-label text-xs uppercase tracking-widest text-on-surface-variant font-semibold mb-2">
              Amount Received
            </label>
            <div className="relative flex items-center justify-center">
              <span className="text-4xl font-headline font-bold text-tertiary mr-1">
                $
              </span>
              <input
                autoFocus
                type="number"
                name="amount"
                value={form.amount}
                onChange={handleChange}
                step="0.01"
                min="0.01"
                className="w-48 text-5xl font-headline font-extrabold text-tertiary bg-transparent border-none focus:ring-0 text-center placeholder:text-tertiary/20"
                placeholder="0.00"
                required
              />
            </div>
            <div className="h-1 w-24 bg-tertiary-container rounded-full mt-4"></div>
          </div>

          {/* Date & Source */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="flex flex-col">
              <label className="font-label text-xs uppercase tracking-widest text-on-surface-variant font-semibold mb-2 ml-1">
                Date
              </label>
              <div className="bg-surface-container-high rounded-xl px-4 py-3 flex items-center focus-within:bg-surface-container-lowest transition-colors">
                <span className="material-symbols-outlined text-tertiary/60 mr-3">
                  calendar_today
                </span>
                <DateInput
                  name="date"
                  value={form.date}
                  onChange={(iso) => setForm((prev) => ({ ...prev, date: iso }))}
                  max={today}
                  className="bg-transparent border-none focus:ring-0 w-full font-medium text-on-surface"
                  required
                />
              </div>
            </div>

            <div className="flex flex-col">
              <label className="font-label text-xs uppercase tracking-widest text-on-surface-variant font-semibold mb-2 ml-1">
                Source
              </label>
              <div className="bg-surface-container-high rounded-xl px-4 py-1 flex items-center focus-within:bg-surface-container-lowest transition-colors">
                <span className="material-symbols-outlined text-tertiary/60 mr-3">
                  payments
                </span>
                <select
                  name="source"
                  value={form.source}
                  onChange={handleChange}
                  className="bg-transparent border-none focus:ring-0 w-full font-medium text-on-surface py-3"
                  required
                >
                  {INCOME_SOURCES.map((s) => (
                    <option key={s} value={s}>
                      {s}
                    </option>
                  ))}
                </select>
              </div>
            </div>
          </div>

          {/* Notes */}
          <div className="flex flex-col">
            <label className="font-label text-xs uppercase tracking-widest text-on-surface-variant font-semibold mb-2 ml-1">
              Notes <span className="normal-case font-normal">(optional)</span>
            </label>
            <div className="bg-surface-container-high rounded-xl px-4 py-3 flex items-start focus-within:bg-surface-container-lowest transition-colors">
              <span className="material-symbols-outlined text-tertiary/60 mr-3 mt-0.5">
                notes
              </span>
              <textarea
                name="notes"
                value={form.notes}
                onChange={handleChange}
                rows={2}
                placeholder="e.g. March salary, project payment…"
                className="bg-transparent border-none focus:ring-0 w-full font-medium text-on-surface resize-none"
              />
            </div>
          </div>

          {/* Submit */}
          <div className="pt-6">
            <button
              type="submit"
              disabled={submitting}
              className="w-full h-16 rounded-full bg-gradient-to-r from-tertiary to-tertiary/80 text-on-tertiary font-headline font-bold text-lg shadow-lg active:scale-[0.98] transition-all duration-200 flex items-center justify-center gap-2 disabled:opacity-60"
            >
              <span className="material-symbols-outlined">add_circle</span>
              {submitting ? "Logging…" : "Log Income"}
            </button>
          </div>
        </form>
      </section>
    </div>
  );
}
