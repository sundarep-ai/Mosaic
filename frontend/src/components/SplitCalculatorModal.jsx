import { useState, useEffect, useRef } from "react";
import { useCurrency } from "../CurrencyContext";
import { computeSplit } from "../utils/splitCalc";

const TAX_PCT_KEY = "mosaic_split_calc_tax_pct";
const DEFAULT_TAX_PCT = "13";

function emptyItem(id) {
  return { id, label: "", amount: "", owner: "Shared", taxable: true };
}

export default function SplitCalculatorModal({
  onClose,
  userA,
  userB,
  defaultPayer,
  onUseResult,
}) {
  const { symbol, fmt } = useCurrency();
  const nextId = useRef(1);

  const [payer, setPayer] = useState(defaultPayer || userA);
  const [taxPct, setTaxPct] = useState(() => {
    try {
      return localStorage.getItem(TAX_PCT_KEY) || DEFAULT_TAX_PCT;
    } catch {
      return DEFAULT_TAX_PCT;
    }
  });
  const [items, setItems] = useState(() => [emptyItem(0)]);

  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [onClose]);

  const handleTaxPctChange = (value) => {
    setTaxPct(value);
    try {
      localStorage.setItem(TAX_PCT_KEY, value);
    } catch {
      // localStorage unavailable — the value still works for this session
    }
  };

  const addItem = () => {
    nextId.current += 1;
    setItems((prev) => [...prev, emptyItem(nextId.current)]);
  };

  const removeItem = (id) => {
    setItems((prev) => prev.filter((item) => item.id !== id));
  };

  const updateItem = (id, changes) => {
    setItems((prev) =>
      prev.map((item) => (item.id === id ? { ...item, ...changes } : item))
    );
  };

  const other = payer === userA ? userB : userA;
  const result = computeSplit(items, taxPct, payer, userA, userB);
  const canUseResult = result.netOwed > 0;

  const handleUseResult = () => {
    onUseResult({ amount: result.netOwed, payer, ower: result.ower });
    onClose();
  };

  return (
    <div
      className="fixed inset-0 bg-black/40 backdrop-blur-sm flex items-center justify-center z-50 p-4"
      onClick={onClose}
    >
      <div
        className="bg-surface-container-lowest rounded-[2rem] shadow-xl max-w-2xl w-full max-h-[85vh] flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="p-8 pb-0">
          <div className="flex items-start justify-between mb-6">
            <div>
              <h2 className="font-headline text-2xl font-extrabold text-on-surface mb-1">
                Split Calculator
              </h2>
              <p className="text-on-surface-variant text-sm">
                Add up a mixed receipt and work out who owes what.
              </p>
            </div>
            <button
              type="button"
              onClick={onClose}
              className="text-on-surface-variant hover:text-on-surface"
            >
              <span className="material-symbols-outlined">close</span>
            </button>
          </div>

          {/* Payer + tax controls */}
          <div className="grid grid-cols-2 gap-4 mb-4">
            <div className="flex flex-col">
              <label className="font-label text-[11px] uppercase tracking-widest text-on-surface-variant font-semibold mb-2">
                Who Paid?
              </label>
              <div className="bg-surface-container-high p-1 rounded-xl flex gap-1">
                {[userA, userB].map((u) => (
                  <button
                    key={u}
                    type="button"
                    onClick={() => setPayer(u)}
                    className={`flex-1 rounded-lg py-2 text-sm font-semibold transition-colors ${
                      payer === u
                        ? "bg-surface-container-lowest shadow-sm text-primary"
                        : "text-on-surface-variant hover:bg-surface-container"
                    }`}
                  >
                    {u}
                  </button>
                ))}
              </div>
            </div>
            <div className="flex flex-col">
              <label className="font-label text-[11px] uppercase tracking-widest text-on-surface-variant font-semibold mb-2">
                Tax %
              </label>
              <input
                type="number"
                inputMode="decimal"
                step="0.01"
                min="0"
                value={taxPct}
                onChange={(e) => handleTaxPctChange(e.target.value)}
                onWheel={(e) => e.target.blur()}
                className="bg-surface-container-high rounded-xl px-4 py-2 border-none focus:ring-2 focus:ring-primary/30 font-medium text-on-surface"
              />
            </div>
          </div>
        </div>

        {/* Items */}
        <div className="flex-1 overflow-y-auto px-8 space-y-3">
          {items.map((item) => (
            <div
              key={item.id}
              className="bg-surface-container-high rounded-2xl p-3 flex flex-col gap-2"
            >
              <div className="flex items-center gap-2">
                <input
                  type="text"
                  placeholder="Item (optional)"
                  value={item.label}
                  onChange={(e) => updateItem(item.id, { label: e.target.value })}
                  className="flex-1 bg-transparent border-none focus:ring-0 font-medium text-on-surface text-sm min-w-0"
                />
                <div className="relative flex items-center shrink-0">
                  <span className="text-on-surface-variant text-sm mr-1">{symbol}</span>
                  <input
                    type="number"
                    inputMode="decimal"
                    step="0.01"
                    placeholder="0.00"
                    value={item.amount}
                    onChange={(e) => updateItem(item.id, { amount: e.target.value })}
                    onWheel={(e) => e.target.blur()}
                    className="w-20 bg-surface-container-lowest rounded-lg px-2 py-1 border-none focus:ring-2 focus:ring-primary/30 font-semibold text-on-surface text-sm text-right"
                  />
                </div>
                <button
                  type="button"
                  onClick={() => removeItem(item.id)}
                  disabled={items.length === 1}
                  className="text-on-surface-variant hover:text-error disabled:opacity-30 shrink-0"
                >
                  <span className="material-symbols-outlined text-[18px]">delete</span>
                </button>
              </div>
              <div className="flex items-center justify-between gap-2">
                <div className="bg-surface-container-lowest p-0.5 rounded-lg flex gap-0.5 text-[11px]">
                  {[
                    { value: payer, label: "Mine" },
                    { value: other, label: "Theirs" },
                    { value: "Shared", label: "Shared" },
                  ].map((opt) => (
                    <button
                      key={opt.label}
                      type="button"
                      onClick={() => updateItem(item.id, { owner: opt.value })}
                      className={`px-2.5 py-1 rounded-md font-semibold transition-colors ${
                        item.owner === opt.value
                          ? "bg-secondary-container text-on-secondary-container"
                          : "text-on-surface-variant hover:bg-surface-container"
                      }`}
                    >
                      {opt.label}
                    </button>
                  ))}
                </div>
                <label className="flex items-center gap-1.5 text-[11px] font-semibold text-on-surface-variant">
                  <input
                    type="checkbox"
                    checked={item.taxable}
                    onChange={(e) => updateItem(item.id, { taxable: e.target.checked })}
                    className="rounded"
                  />
                  Taxable
                </label>
              </div>
            </div>
          ))}

          <button
            type="button"
            onClick={addItem}
            className="w-full py-3 rounded-2xl border-2 border-dashed border-outline-variant/30 text-on-surface-variant font-semibold text-sm hover:border-primary/30 hover:text-primary transition-colors flex items-center justify-center gap-1.5"
          >
            <span className="material-symbols-outlined text-[18px]">add</span>
            Add item
          </button>
        </div>

        {/* Preview + actions */}
        <div className="p-8 pt-4 mt-2">
          <div className="bg-primary-container/20 rounded-2xl p-4 mb-4 space-y-1">
            <div className="flex justify-between text-xs text-on-surface-variant">
              <span>Subtotal</span>
              <span>{fmt(result.subtotal)}</span>
            </div>
            <div className="flex justify-between text-xs text-on-surface-variant">
              <span>Tax</span>
              <span>{fmt(result.tax)}</span>
            </div>
            <div className="flex justify-between text-sm font-bold text-on-surface pt-1 border-t border-outline-variant/20 mt-1">
              <span>Total</span>
              <span>{fmt(result.total)}</span>
            </div>
            <p className="text-sm font-bold text-primary text-center pt-2">
              {other} owes {payer} {fmt(result.netOwed)}
            </p>
          </div>
          <button
            type="button"
            onClick={handleUseResult}
            disabled={!canUseResult}
            className="w-full h-14 rounded-full bg-gradient-to-r from-primary to-primary-dim text-on-primary font-headline font-bold shadow-lg active:scale-[0.98] transition-all duration-200 flex items-center justify-center gap-2 disabled:opacity-40"
          >
            <span className="material-symbols-outlined">check_circle</span>
            Use this result
          </button>
          {!canUseResult && (
            <p className="text-xs text-on-surface-variant text-center mt-2">
              Add at least one item owned by {other} or Shared to compute an amount owed.
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
