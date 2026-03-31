import Fuse from "fuse.js";

const FUSE_OPTIONS = {
  keys: ["description"],
  threshold: 0.4,
  distance: 100,
  includeScore: true,
  minMatchCharLength: 2,
};

/**
 * Create a suggestion engine from an array of { description, category, count } items.
 * Returns { suggest, suggestCategory } functions.
 */
export function createSuggestionEngine(items) {
  const fuse = new Fuse(items, FUSE_OPTIONS);

  function suggest(query) {
    if (!query || query.trim().length < 2) return [];
    const results = fuse.search(query.trim(), { limit: 5 });
    return results.map((r) => r.item);
  }

  function suggestCategory(query) {
    if (!query || query.trim().length < 3) return null;
    const results = fuse.search(query.trim(), { limit: 5 });
    if (results.length === 0) return null;
    // Strong match — use directly
    const best = results[0];
    if (best.score < 0.3) return best.item.category;
    // Otherwise, pick most frequent category among top results
    const catCounts = {};
    for (const r of results) {
      const cat = r.item.category;
      catCounts[cat] = (catCounts[cat] || 0) + r.item.count;
    }
    return Object.entries(catCounts).sort((a, b) => b[1] - a[1])[0][0];
  }

  return { suggest, suggestCategory };
}
