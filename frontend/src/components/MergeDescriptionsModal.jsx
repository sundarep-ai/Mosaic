import { useState, useEffect } from "react";
import {
  getSimilarDescriptions,
  mergeDescriptions,
  dismissMergeSuggestions,
  getDismissedMerges,
  undismissMerges,
  getUniqueDescriptions,
} from "../api/expenses";
import { CATEGORIES } from "../constants/categories";

const TABS = [
  { id: "suggestions", label: "Suggestions", icon: "auto_awesome" },
  { id: "custom", label: "Custom Merge", icon: "edit" },
  { id: "dismissed", label: "Dismissed", icon: "visibility_off" },
];

function SuggestionsTab({ results, onAccept, onReject, processing }) {
  const [selections, setSelections] = useState({});

  useEffect(() => {
    const sel = {};
    results.forEach((catGroup, ci) => {
      catGroup.groups.forEach((group, gi) => {
        const key = `${ci}-${gi}`;
        sel[key] = { target: group.canonical, customTarget: "" };
      });
    });
    setSelections(sel);
  }, [results]);

  const totalGroups = results.reduce((sum, c) => sum + c.groups.length, 0);

  if (totalGroups === 0) {
    return (
      <div className="text-center py-16 text-on-surface-variant">
        <span className="material-symbols-outlined text-4xl mb-2 block opacity-40">
          check_circle
        </span>
        <p className="font-medium">All clean! No similar descriptions found.</p>
        <p className="text-xs mt-1 opacity-70">
          Check the Dismissed tab if you previously rejected suggestions.
        </p>
      </div>
    );
  }

  const setTarget = (key, target) => {
    setSelections((prev) => ({
      ...prev,
      [key]: { ...prev[key], target, customTarget: "" },
    }));
  };

  const setCustomTarget = (key, value) => {
    setSelections((prev) => ({
      ...prev,
      [key]: { ...prev[key], target: "__custom__", customTarget: value },
    }));
  };

  const handleAccept = (ci, gi, catGroup, group) => {
    const key = `${ci}-${gi}`;
    const sel = selections[key];
    const target =
      sel?.target === "__custom__" ? sel?.customTarget?.trim() : sel?.target;
    if (!target) return;

    const allDescs = [group.canonical, ...group.variants];
    const sources = allDescs.filter((d) => d !== target);
    if (sources.length === 0) return;

    onAccept({
      target,
      sources,
      category: catGroup.category,
    });
  };

  const handleReject = (catGroup, group) => {
    onReject({
      category: catGroup.category,
      canonical: group.canonical,
      variants: group.variants,
    });
  };

  return (
    <div className="space-y-6">
      <p className="text-xs text-on-surface-variant">
        Found {totalGroups} group{totalGroups !== 1 ? "s" : ""} of similar descriptions.
        Choose an action for each.
      </p>
      {results.map((catGroup, ci) => (
        <div key={catGroup.category}>
          <h3 className="font-label text-xs uppercase tracking-widest text-on-surface-variant font-semibold mb-3">
            {catGroup.category}
          </h3>
          <div className="space-y-3">
            {catGroup.groups.map((group, gi) => {
              const key = `${ci}-${gi}`;
              const sel = selections[key];
              const allDescs = [group.canonical, ...group.variants];

              return (
                <div
                  key={key}
                  className="rounded-2xl border-2 border-outline-variant/10 bg-surface-container p-4"
                >
                  <div className="flex items-center gap-2 mb-3">
                    <span className="material-symbols-outlined text-primary text-sm">merge</span>
                    <span className="text-sm text-on-surface-variant">
                      {group.total_count} expense{group.total_count !== 1 ? "s" : ""} across{" "}
                      {allDescs.length} variants
                    </span>
                  </div>

                  {/* Target selection */}
                  <div className="ml-6 space-y-1.5 mb-4">
                    {allDescs.map((desc) => (
                      <label key={desc} className="flex items-center gap-2 cursor-pointer">
                        <input
                          type="radio"
                          name={`target-${key}`}
                          checked={sel?.target === desc}
                          onChange={() => setTarget(key, desc)}
                          className="text-primary focus:ring-primary"
                        />
                        <span
                          className={`text-sm ${
                            sel?.target === desc
                              ? "font-bold text-primary"
                              : "text-on-surface"
                          }`}
                        >
                          {desc}
                        </span>
                        {desc === group.canonical && (
                          <span className="text-[10px] bg-primary-container text-on-primary-container px-2 py-0.5 rounded-full font-bold uppercase tracking-wider">
                            Most used
                          </span>
                        )}
                      </label>
                    ))}
                    <label className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="radio"
                        name={`target-${key}`}
                        checked={sel?.target === "__custom__"}
                        onChange={() => setCustomTarget(key, "")}
                        className="text-primary focus:ring-primary"
                      />
                      <span
                        className={`text-sm ${
                          sel?.target === "__custom__"
                            ? "font-bold text-primary"
                            : "text-on-surface-variant"
                        }`}
                      >
                        Custom:
                      </span>
                      {sel?.target === "__custom__" && (
                        <input
                          type="text"
                          value={sel.customTarget}
                          onChange={(e) => setCustomTarget(key, e.target.value)}
                          placeholder="Enter custom name"
                          className="bg-surface-container-high rounded-lg px-3 py-1 text-sm border-none focus:ring-1 focus:ring-primary"
                          autoFocus
                        />
                      )}
                    </label>
                  </div>

                  {/* Action buttons */}
                  <div className="flex gap-2 ml-6">
                    <button
                      onClick={() => handleAccept(ci, gi, catGroup, group)}
                      disabled={processing}
                      className="flex items-center gap-1.5 px-4 py-2 rounded-full text-xs font-bold bg-primary text-on-primary hover:bg-primary/90 transition-colors disabled:opacity-50"
                    >
                      <span className="material-symbols-outlined text-sm">check</span>
                      Accept
                    </button>
                    <button
                      onClick={() => handleReject(catGroup, group)}
                      disabled={processing}
                      className="flex items-center gap-1.5 px-4 py-2 rounded-full text-xs font-bold bg-error-container text-on-error-container hover:bg-error-container/80 transition-colors disabled:opacity-50"
                    >
                      <span className="material-symbols-outlined text-sm">block</span>
                      Reject
                    </button>
                    <span className="flex items-center text-[11px] text-on-surface-variant/60 ml-2">
                      or skip to review later
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      ))}
    </div>
  );
}

function CustomMergeTab({ onMerge, processing }) {
  const [category, setCategory] = useState("");
  const [target, setTarget] = useState("");
  const [sourceInput, setSourceInput] = useState("");
  const [sources, setSources] = useState([]);
  const [allDescriptions, setAllDescriptions] = useState([]);
  const [suggestions, setSuggestions] = useState([]);
  const [focusedField, setFocusedField] = useState(null);

  useEffect(() => {
    (async () => {
      try {
        const data = await getUniqueDescriptions();
        setAllDescriptions(data);
      } catch {
        // Non-critical — autocomplete just won't work
      }
    })();
  }, []);

  const getFilteredSuggestions = (input) => {
    if (!input || input.length < 2) return [];
    const lower = input.toLowerCase();
    return allDescriptions
      .filter(
        (d) =>
          d.description.toLowerCase().includes(lower) &&
          (!category || d.category === category)
      )
      .slice(0, 6);
  };

  const handleSourceInputChange = (val) => {
    setSourceInput(val);
    setSuggestions(getFilteredSuggestions(val, "source"));
  };

  const handleTargetChange = (val) => {
    setTarget(val);
    setSuggestions(getFilteredSuggestions(val, "target"));
  };

  const addSource = (desc) => {
    const trimmed = (desc || sourceInput).trim();
    if (trimmed && !sources.includes(trimmed) && trimmed !== target) {
      setSources((prev) => [...prev, trimmed]);
    }
    setSourceInput("");
    setSuggestions([]);
  };

  const removeSource = (idx) => {
    setSources((prev) => prev.filter((_, i) => i !== idx));
  };

  const handleSubmit = () => {
    if (!target.trim() || sources.length === 0 || !category) return;
    onMerge({
      target: target.trim(),
      sources,
      category,
    });
    setTarget("");
    setSources([]);
    setSourceInput("");
  };

  return (
    <div className="space-y-6">
      <p className="text-xs text-on-surface-variant">
        Manually merge descriptions you've identified as duplicates. Pick a
        category, enter the target name, then add the source descriptions that
        should be renamed.
      </p>

      {/* Category */}
      <div>
        <label className="font-label text-xs uppercase tracking-widest text-on-surface-variant font-semibold block mb-2">
          Category
        </label>
        <select
          value={category}
          onChange={(e) => setCategory(e.target.value)}
          className="w-full bg-surface-container-high rounded-xl px-4 py-3 text-sm text-on-surface border-none focus:ring-1 focus:ring-primary"
        >
          <option value="">Select a category</option>
          {CATEGORIES.map((c) => (
            <option key={c} value={c}>{c}</option>
          ))}
        </select>
      </div>

      {/* Target */}
      <div className="relative">
        <label className="font-label text-xs uppercase tracking-widest text-on-surface-variant font-semibold block mb-2">
          Merge into (target name)
        </label>
        <input
          type="text"
          value={target}
          onChange={(e) => handleTargetChange(e.target.value)}
          onFocus={() => setFocusedField("target")}
          onBlur={() => setTimeout(() => setFocusedField(null), 200)}
          placeholder="e.g. Grocery Store"
          className="w-full bg-surface-container-high rounded-xl px-4 py-3 text-sm text-on-surface border-none focus:ring-1 focus:ring-primary"
        />
        {focusedField === "target" && suggestions.length > 0 && (
          <div className="absolute z-10 mt-1 w-full bg-surface-container-lowest rounded-xl shadow-lg border border-outline-variant/10 max-h-48 overflow-y-auto">
            {suggestions.map((s) => (
              <button
                key={s.description + s.category}
                type="button"
                onMouseDown={() => {
                  setTarget(s.description);
                  if (!category) setCategory(s.category);
                  setSuggestions([]);
                }}
                className="w-full text-left px-4 py-2 text-sm hover:bg-surface-container-high text-on-surface flex justify-between"
              >
                <span>{s.description}</span>
                <span className="text-on-surface-variant text-xs">{s.category} ({s.count})</span>
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Sources */}
      <div className="relative">
        <label className="font-label text-xs uppercase tracking-widest text-on-surface-variant font-semibold block mb-2">
          Source descriptions (to rename)
        </label>
        <div className="flex gap-2">
          <input
            type="text"
            value={sourceInput}
            onChange={(e) => handleSourceInputChange(e.target.value)}
            onFocus={() => setFocusedField("source")}
            onBlur={() => setTimeout(() => setFocusedField(null), 200)}
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                e.preventDefault();
                addSource();
              }
            }}
            placeholder="e.g. Grocry Store"
            className="flex-1 bg-surface-container-high rounded-xl px-4 py-3 text-sm text-on-surface border-none focus:ring-1 focus:ring-primary"
          />
          <button
            onClick={() => addSource()}
            disabled={!sourceInput.trim()}
            className="px-4 py-3 rounded-xl bg-primary text-on-primary font-bold text-sm disabled:opacity-50 transition-colors"
          >
            Add
          </button>
        </div>
        {focusedField === "source" && suggestions.length > 0 && (
          <div className="absolute z-10 mt-1 w-full bg-surface-container-lowest rounded-xl shadow-lg border border-outline-variant/10 max-h-48 overflow-y-auto">
            {suggestions.map((s) => (
              <button
                key={s.description + s.category}
                type="button"
                onMouseDown={() => {
                  addSource(s.description);
                  if (!category) setCategory(s.category);
                }}
                className="w-full text-left px-4 py-2 text-sm hover:bg-surface-container-high text-on-surface flex justify-between"
              >
                <span>{s.description}</span>
                <span className="text-on-surface-variant text-xs">{s.category} ({s.count})</span>
              </button>
            ))}
          </div>
        )}
        {sources.length > 0 && (
          <div className="flex flex-wrap gap-2 mt-3">
            {sources.map((s, i) => (
              <span
                key={i}
                className="inline-flex items-center gap-1.5 bg-error-container/20 text-on-surface px-3 py-1.5 rounded-full text-xs font-medium"
              >
                {s}
                <button
                  onClick={() => removeSource(i)}
                  className="hover:text-error transition-colors"
                >
                  <span className="material-symbols-outlined text-xs">close</span>
                </button>
              </span>
            ))}
          </div>
        )}
      </div>

      {/* Preview & Submit */}
      {target && sources.length > 0 && category && (
        <div className="bg-primary-container/10 rounded-2xl p-4 border border-primary/10">
          <p className="text-xs text-on-surface-variant mb-2 font-semibold uppercase tracking-wider">
            Preview
          </p>
          <p className="text-sm text-on-surface">
            In <span className="font-bold">{category}</span>, rename{" "}
            {sources.map((s, i) => (
              <span key={i}>
                <span className="line-through text-error">{s}</span>
                {i < sources.length - 1 ? ", " : ""}
              </span>
            ))}{" "}
            → <span className="font-bold text-primary">{target}</span>
          </p>
        </div>
      )}

      <button
        onClick={handleSubmit}
        disabled={!target.trim() || sources.length === 0 || !category || processing}
        className="w-full bg-gradient-to-r from-primary to-primary-dim text-on-primary font-bold rounded-full px-4 py-3 transition-all disabled:opacity-50 flex items-center justify-center gap-2"
      >
        <span className="material-symbols-outlined text-sm">merge</span>
        {processing ? "Merging..." : "Merge Descriptions"}
      </button>
    </div>
  );
}

function DismissedTab({ dismissed, onUndismiss, processing }) {
  const totalPairs = dismissed.reduce((sum, c) => sum + c.pairs.length, 0);

  if (totalPairs === 0) {
    return (
      <div className="text-center py-16 text-on-surface-variant">
        <span className="material-symbols-outlined text-4xl mb-2 block opacity-40">
          visibility_off
        </span>
        No dismissed suggestions yet.
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <p className="text-xs text-on-surface-variant">
        These description pairs have been permanently dismissed. Click restore to
        allow them to appear in suggestions again.
      </p>
      {dismissed.map((catGroup) => (
        <div key={catGroup.category}>
          <h3 className="font-label text-xs uppercase tracking-widest text-on-surface-variant font-semibold mb-3">
            {catGroup.category}
          </h3>
          <div className="space-y-2">
            {catGroup.pairs.map((pair) => (
              <div
                key={pair.id}
                className="flex items-center justify-between bg-surface-container rounded-xl px-4 py-3"
              >
                <div className="flex items-center gap-2 text-sm text-on-surface min-w-0">
                  <span className="truncate">{pair.desc_a}</span>
                  <span className="material-symbols-outlined text-on-surface-variant text-sm shrink-0">
                    link
                  </span>
                  <span className="truncate">{pair.desc_b}</span>
                </div>
                <button
                  onClick={() => onUndismiss(pair.id)}
                  disabled={processing}
                  className="flex items-center gap-1 px-3 py-1.5 rounded-full text-xs font-bold bg-primary-container text-on-primary-container hover:bg-primary-container/80 transition-colors disabled:opacity-50 shrink-0 ml-3"
                >
                  <span className="material-symbols-outlined text-sm">undo</span>
                  Restore
                </button>
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

export default function MergeDescriptionsModal({ onClose, onMerged }) {
  const [activeTab, setActiveTab] = useState("suggestions");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [results, setResults] = useState([]);
  const [dismissed, setDismissed] = useState([]);
  const [processing, setProcessing] = useState(false);
  const [toast, setToast] = useState(null);

  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [onClose]);

  const loadData = async () => {
    setLoading(true);
    setError("");
    try {
      const [suggestions, dismissedData] = await Promise.all([
        getSimilarDescriptions(),
        getDismissedMerges(),
      ]);
      setResults(suggestions);
      setDismissed(dismissedData);
    } catch {
      setError("Failed to load data. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadData(); }, []);

  const showToast = (msg) => {
    setToast(msg);
    setTimeout(() => setToast(null), 3000);
  };

  const handleAccept = async (merge) => {
    setProcessing(true);
    try {
      const result = await mergeDescriptions([merge]);
      showToast(`Merged ${result.updated} expense${result.updated !== 1 ? "s" : ""}`);
      onMerged?.();
      await loadData();
    } catch {
      setError("Failed to merge. Please try again.");
    } finally {
      setProcessing(false);
    }
  };

  const handleReject = async (dismissal) => {
    setProcessing(true);
    try {
      await dismissMergeSuggestions([dismissal]);
      showToast("Suggestion dismissed permanently");
      await loadData();
    } catch {
      setError("Failed to dismiss. Please try again.");
    } finally {
      setProcessing(false);
    }
  };

  const handleUndismiss = async (id) => {
    setProcessing(true);
    try {
      await undismissMerges([id]);
      showToast("Suggestion restored");
      await loadData();
    } catch {
      setError("Failed to restore. Please try again.");
    } finally {
      setProcessing(false);
    }
  };

  const handleCustomMerge = async (merge) => {
    setProcessing(true);
    try {
      const result = await mergeDescriptions([merge]);
      showToast(`Merged ${result.updated} expense${result.updated !== 1 ? "s" : ""}`);
      onMerged?.();
      await loadData();
    } catch {
      setError("Failed to merge. Please try again.");
    } finally {
      setProcessing(false);
    }
  };

  const dismissedCount = dismissed.reduce((sum, c) => sum + c.pairs.length, 0);

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
                Clean Up Descriptions
              </h2>
              <p className="text-on-surface-variant text-sm">
                Merge similar descriptions to keep your data tidy.
              </p>
            </div>
            <button
              onClick={onClose}
              className="p-2 rounded-xl hover:bg-surface-container-high transition-colors text-on-surface-variant"
            >
              <span className="material-symbols-outlined">close</span>
            </button>
          </div>

          {/* Tabs */}
          <div className="flex border-b border-outline-variant/10">
            {TABS.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center gap-2 px-5 py-3 text-sm font-bold transition-colors relative ${
                  activeTab === tab.id
                    ? "text-primary"
                    : "text-on-surface-variant hover:text-on-surface"
                }`}
              >
                <span className="material-symbols-outlined text-sm">{tab.icon}</span>
                {tab.label}
                {tab.id === "dismissed" && dismissedCount > 0 && (
                  <span className="bg-surface-container-high text-on-surface-variant text-[10px] font-bold px-1.5 py-0.5 rounded-full">
                    {dismissedCount}
                  </span>
                )}
                {activeTab === tab.id && (
                  <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-primary rounded-full" />
                )}
              </button>
            ))}
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto px-8 py-6">
          {/* Toast */}
          {toast && (
            <div className="mb-4 bg-primary-container text-on-primary-container px-4 py-3 rounded-xl text-sm font-medium flex items-center gap-2 animate-in fade-in">
              <span className="material-symbols-outlined text-sm">check_circle</span>
              {toast}
            </div>
          )}

          {error && (
            <div className="bg-error-container/20 border border-error/20 text-error px-4 py-3 rounded-xl text-sm mb-4 flex items-center gap-2">
              <span className="material-symbols-outlined text-sm">error</span>
              {error}
              <button onClick={() => setError("")} className="ml-auto">
                <span className="material-symbols-outlined text-sm">close</span>
              </button>
            </div>
          )}

          {loading ? (
            <div className="flex flex-col items-center justify-center py-16">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mb-4" />
              <p className="text-on-surface-variant text-sm">
                Running similarity analysis...
              </p>
            </div>
          ) : (
            <>
              {activeTab === "suggestions" && (
                <SuggestionsTab
                  results={results}
                  onAccept={handleAccept}
                  onReject={handleReject}
                  processing={processing}
                />
              )}
              {activeTab === "custom" && (
                <CustomMergeTab
                  onMerge={handleCustomMerge}
                  processing={processing}
                />
              )}
              {activeTab === "dismissed" && (
                <DismissedTab
                  dismissed={dismissed}
                  onUndismiss={handleUndismiss}
                  processing={processing}
                />
              )}
            </>
          )}
        </div>

        {/* Footer */}
        <div className="p-8 pt-4 border-t border-outline-variant/10">
          <button
            onClick={onClose}
            className="w-full bg-surface-container-high hover:bg-surface-container-highest text-on-surface font-bold rounded-full px-4 py-3 transition-colors"
          >
            Done
          </button>
        </div>
      </div>
    </div>
  );
}
