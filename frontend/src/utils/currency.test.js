import { describe, it, expect } from "vitest";
import { formatCurrency } from "./currency";

describe("formatCurrency", () => {
  it("adds thousands separators", () => {
    expect(formatCurrency(1234.5, "$")).toBe("$1,234.50");
  });

  it("handles multiple thousands separators", () => {
    expect(formatCurrency(1234567.89, "$")).toBe("$1,234,567.89");
  });

  it("puts the negative sign before the symbol, not after", () => {
    expect(formatCurrency(-12, "$")).toBe("-$12.00");
  });

  it("puts the negative sign before multi-character symbols too", () => {
    expect(formatCurrency(-1500, "C$")).toBe("-C$1,500.00");
  });

  it("does not render -0.00 for a value that rounds to zero", () => {
    expect(formatCurrency(-0, "$")).toBe("$0.00");
    expect(formatCurrency(0, "$")).toBe("$0.00");
  });

  it("always shows exactly two decimal places", () => {
    expect(formatCurrency(5, "$")).toBe("$5.00");
    expect(formatCurrency(5.1, "$")).toBe("$5.10");
  });

  it("coerces string amounts (e.g. straight from a form input)", () => {
    expect(formatCurrency("42.5", "$")).toBe("$42.50");
  });

  it("falls back to zero for non-numeric input", () => {
    expect(formatCurrency(undefined, "$")).toBe("$0.00");
    expect(formatCurrency(null, "$")).toBe("$0.00");
  });
});
