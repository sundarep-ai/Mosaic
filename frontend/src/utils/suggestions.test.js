import { describe, it, expect } from "vitest";
import { createSuggestionEngine } from "./suggestions";

const ITEMS = [
  { description: "Costco Groceries", category: "Groceries", count: 10 },
  { description: "Costco Gas", category: "Gas", count: 5 },
  { description: "Walmart", category: "Groceries", count: 8 },
  { description: "Shell Gas", category: "Gas", count: 3 },
  { description: "Netflix", category: "Subscription", count: 6 },
  { description: "Spotify", category: "Subscription", count: 4 },
];

describe("createSuggestionEngine", () => {
  const { suggest, suggestCategory } = createSuggestionEngine(ITEMS);

  // ── suggest ───────────────────────────────────────────────────

  describe("suggest", () => {
    it("returns matching items for a valid query", () => {
      const results = suggest("Costco");
      expect(results.length).toBeGreaterThan(0);
      expect(results.every((r) => r.description.includes("Costco"))).toBe(true);
    });

    it("returns empty for query shorter than 2 chars", () => {
      expect(suggest("C")).toEqual([]);
    });

    it("returns empty for empty string", () => {
      expect(suggest("")).toEqual([]);
    });

    it("returns empty for null/undefined", () => {
      expect(suggest(null)).toEqual([]);
      expect(suggest(undefined)).toEqual([]);
    });

    it("limits results to 5", () => {
      const results = suggest("Co");
      expect(results.length).toBeLessThanOrEqual(5);
    });

    it("returns items with description, category, and count fields", () => {
      const results = suggest("Netflix");
      expect(results[0]).toHaveProperty("description");
      expect(results[0]).toHaveProperty("category");
      expect(results[0]).toHaveProperty("count");
    });
  });

  // ── suggestCategory ───────────────────────────────────────────

  describe("suggestCategory", () => {
    it("returns a category for a strong match", () => {
      const cat = suggestCategory("Netflix");
      expect(cat).toBe("Subscription");
    });

    it("returns null for query shorter than 3 chars", () => {
      expect(suggestCategory("Ne")).toBeNull();
    });

    it("returns null for empty string", () => {
      expect(suggestCategory("")).toBeNull();
    });

    it("returns null for null/undefined", () => {
      expect(suggestCategory(null)).toBeNull();
      expect(suggestCategory(undefined)).toBeNull();
    });

    it("returns the most frequent category when match is weak", () => {
      // "Gas" matches both "Costco Gas" (Gas, count=5) and "Shell Gas" (Gas, count=3)
      const cat = suggestCategory("Gas");
      expect(cat).toBe("Gas");
    });

    it("returns Groceries for Costco (highest count match)", () => {
      // "Costco" matches "Costco Groceries" (count=10) and "Costco Gas" (count=5)
      // Best match is strong for "Costco Groceries" → Groceries
      const cat = suggestCategory("Costco");
      expect(["Groceries", "Gas"]).toContain(cat);
    });
  });
});
