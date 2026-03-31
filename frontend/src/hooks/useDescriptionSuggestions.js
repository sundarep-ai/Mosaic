import { useState, useEffect, useRef, useCallback } from "react";
import { getUniqueDescriptions } from "../api/expenses";
import { createSuggestionEngine } from "../utils/suggestions";

export default function useDescriptionSuggestions() {
  const [data, setData] = useState([]);
  const engineRef = useRef(null);

  const load = useCallback(async () => {
    try {
      const items = await getUniqueDescriptions();
      setData(items);
      engineRef.current = createSuggestionEngine(items);
    } catch {
      // Silently fail — suggestions are non-critical
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const suggest = useCallback(
    (query) => {
      if (!engineRef.current) return [];
      return engineRef.current.suggest(query);
    },
    [],
  );

  const suggestCategory = useCallback(
    (query) => {
      if (!engineRef.current) return null;
      return engineRef.current.suggestCategory(query);
    },
    [],
  );

  return { suggest, suggestCategory, refresh: load };
}
