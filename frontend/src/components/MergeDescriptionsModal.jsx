import { useState, useEffect } from "react";
import { getSimilarDescriptions, mergeDescriptions } from "../api/expenses";

export default function MergeDescriptionsModal({ onClose, onMerged }) {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [results, setResults] = useState([]);
  const [selections, setSelections] = useState({});
  const [merging, setMerging] = useState(false);
  const [mergeResult, setMergeResult] = useState(null);

  useEffect(() => {
    (async () => {
      try {
        const data = await getSimilarDescriptions();
        setResults(data);
        // Initialize selections: each group selected by default with canonical as target
        const sel = {};
        data.forEach((catGroup, ci) => {
          catGroup.groups.forEach((group, gi) => {
            const key = `${ci}-${gi}`;
            sel[key] = {
              selected: true,
              target: group.canonical,
              customTarget: "",
            };
          });
        });
        setSelections(sel);
      } catch {
        setError("Failed to analyze descriptions. Please try again.");
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  const toggleGroup = (key) => {
    setSelections((prev) => ({
      ...prev,
      [key]: { ...prev[key], selected: !prev[key].selected },
    }));
  };

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

  const handleMerge = async () => {
    const merges = [];
    results.forEach((catGroup, ci) => {
      catGroup.groups.forEach((group, gi) => {
        const key = `${ci}-${gi}`;
        const sel = selections[key];
        if (!sel?.selected) return;

        const target =
          sel.target === "__custom__" ? sel.customTarget.trim() : sel.target;
        if (!target) return;

        const allDescs = [group.canonical, ...group.variants];
        const sources = allDescs.filter((d) => d !== target);
        if (sources.length === 0) return;

        merges.push({
          target,
          sources,
          category: catGroup.category,
        });
      });
    });

    if (merges.length === 0) return;

    setMerging(true);
    try {
      const result = await mergeDescriptions(merges);
      setMergeResult(result.updated);
      onMerged?.();
    } catch {
      setError("Failed to merge descriptions. Please try again.");
    } finally {
      setMerging(false);
    }
  };

  const selectedCount = Object.values(selections).filter(
    (s) => s.selected,
  ).length;
  const totalGroups = results.reduce((sum, c) => sum + c.groups.length, 0);

  return (
    <div className="fixed inset-0 bg-black/40 backdrop-blur-sm flex items-center justify-center z-50 p-4">
      <div className="bg-surface-container-lowest rounded-[2rem] shadow-xl max-w-2xl w-full max-h-[85vh] flex flex-col">
        {/* Header */}
        <div className="p-8 pb-4">
          <div className="flex items-start justify-between">
            <div>
              <h2 className="font-headline text-2xl font-extrabold text-on-surface mb-1">
                Clean Up Descriptions
              </h2>
              <p className="text-on-surface-variant text-sm">
                {loading
                  ? "Analyzing descriptions for similarities..."
                  : mergeResult !== null
                    ? `Successfully updated ${mergeResult} expense${mergeResult !== 1 ? "s" : ""}!`
                    : totalGroups === 0
                      ? "No similar descriptions found. Everything looks clean!"
                      : `Found ${totalGroups} group${totalGroups !== 1 ? "s" : ""} of similar descriptions.`}
              </p>
            </div>
            <button
              onClick={onClose}
              className="p-2 rounded-xl hover:bg-surface-container-high transition-colors text-on-surface-variant"
            >
              <span className="material-symbols-outlined">close</span>
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto px-8 pb-4">
          {loading && (
            <div className="flex flex-col items-center justify-center py-16">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mb-4" />
              <p className="text-on-surface-variant text-sm">
                Running similarity analysis...
              </p>
            </div>
          )}

          {error && (
            <div className="bg-error-container/20 border border-error/20 text-error px-4 py-3 rounded-xl text-sm mb-4 flex items-center gap-2">
              <span className="material-symbols-outlined text-sm">error</span>
              {error}
            </div>
          )}

          {!loading && mergeResult === null && results.length === 0 && !error && (
            <div className="text-center py-16 text-on-surface-variant">
              <span className="material-symbols-outlined text-4xl mb-2 block opacity-40">
                check_circle
              </span>
              All descriptions are unique. Nothing to merge.
            </div>
          )}

          {!loading &&
            mergeResult === null &&
            results.map((catGroup, ci) => (
              <div key={catGroup.category} className="mb-6">
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
                        className={`rounded-2xl border-2 p-4 transition-colors ${
                          sel?.selected
                            ? "border-primary/20 bg-primary-container/5"
                            : "border-outline-variant/10 bg-surface-container opacity-60"
                        }`}
                      >
                        <div className="flex items-center gap-3 mb-3">
                          <input
                            type="checkbox"
                            checked={sel?.selected || false}
                            onChange={() => toggleGroup(key)}
                            className="w-5 h-5 rounded border-outline-variant text-primary focus:ring-primary"
                          />
                          <span className="text-sm text-on-surface-variant">
                            {group.total_count} expense
                            {group.total_count !== 1 ? "s" : ""} across{" "}
                            {allDescs.length} variants
                          </span>
                        </div>

                        {sel?.selected && (
                          <>
                            <div className="ml-8 space-y-1.5">
                              {allDescs.map((desc) => (
                                <label
                                  key={desc}
                                  className="flex items-center gap-2 cursor-pointer"
                                >
                                  <input
                                    type="radio"
                                    name={`target-${key}`}
                                    checked={sel.target === desc}
                                    onChange={() => setTarget(key, desc)}
                                    className="text-primary focus:ring-primary"
                                  />
                                  <span
                                    className={`text-sm ${
                                      sel.target === desc
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
                                  checked={sel.target === "__custom__"}
                                  onChange={() => setCustomTarget(key, "")}
                                  className="text-primary focus:ring-primary"
                                />
                                <span
                                  className={`text-sm ${
                                    sel.target === "__custom__"
                                      ? "font-bold text-primary"
                                      : "text-on-surface-variant"
                                  }`}
                                >
                                  Custom:
                                </span>
                                {sel.target === "__custom__" && (
                                  <input
                                    type="text"
                                    value={sel.customTarget}
                                    onChange={(e) =>
                                      setCustomTarget(key, e.target.value)
                                    }
                                    placeholder="Enter custom name"
                                    className="bg-surface-container-high rounded-lg px-3 py-1 text-sm border-none focus:ring-1 focus:ring-primary"
                                    autoFocus
                                  />
                                )}
                              </label>
                            </div>
                          </>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            ))}

          {mergeResult !== null && (
            <div className="text-center py-12">
              <div className="w-16 h-16 rounded-full bg-primary-container/20 flex items-center justify-center mx-auto mb-4">
                <span className="material-symbols-outlined text-primary text-3xl">
                  check_circle
                </span>
              </div>
              <p className="text-on-surface font-bold text-lg">
                {mergeResult} expense{mergeResult !== 1 ? "s" : ""} updated
              </p>
              <p className="text-on-surface-variant text-sm mt-1">
                Descriptions have been merged successfully.
              </p>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="p-8 pt-4 border-t border-outline-variant/10 flex gap-3">
          <button
            onClick={onClose}
            className="flex-1 bg-surface-container-high hover:bg-surface-container-highest text-on-surface font-bold rounded-full px-4 py-3 transition-colors"
          >
            {mergeResult !== null ? "Done" : "Cancel"}
          </button>
          {mergeResult === null && totalGroups > 0 && (
            <button
              onClick={handleMerge}
              disabled={merging || selectedCount === 0}
              className="flex-1 bg-gradient-to-r from-primary to-primary-dim text-on-primary font-bold rounded-full px-4 py-3 transition-all disabled:opacity-60 flex items-center justify-center gap-2"
            >
              <span className="material-symbols-outlined text-sm">merge</span>
              {merging
                ? "Merging..."
                : `Merge ${selectedCount} Group${selectedCount !== 1 ? "s" : ""}`}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
