import { useState, useEffect, useRef, useCallback } from "react";
import Fuse from "fuse.js";
import { getUniqueDescriptions } from "../api/expenses";

const FUSE_OPTIONS = {
  keys: ["description"],
  threshold: 0.4,
  distance: 100,
  includeScore: true,
  minMatchCharLength: 2,
};

export default function useDescriptionSuggestions() {
  const [data, setData] = useState([]);
  const fuseRef = useRef(null);

  const load = useCallback(async () => {
    try {
      const items = await getUniqueDescriptions();
      setData(items);
      fuseRef.current = new Fuse(items, FUSE_OPTIONS);
    } catch {
      // Silently fail — suggestions are non-critical
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const suggest = useCallback(
    (query) => {
      if (!fuseRef.current || !query || query.trim().length < 2) return [];
      const results = fuseRef.current.search(query.trim(), { limit: 5 });
      return results.map((r) => r.item);
    },
    [],
  );

  const suggestCategory = useCallback(
    (query) => {
      if (!fuseRef.current || !query || query.trim().length < 3) return null;
      const results = fuseRef.current.search(query.trim(), { limit: 5 });
      if (results.length === 0) return null;
      // Pick the category from the best match, weighted by count
      // If the top result is a strong match (score < 0.3), use it directly
      const best = results[0];
      if (best.score < 0.3) return best.item.category;
      // Otherwise, pick the most frequent category among top results
      const catCounts = {};
      for (const r of results) {
        const cat = r.item.category;
        catCounts[cat] = (catCounts[cat] || 0) + r.item.count;
      }
      return Object.entries(catCounts).sort((a, b) => b[1] - a[1])[0][0];
    },
    [],
  );

  return { suggest, suggestCategory, refresh: load };
}
