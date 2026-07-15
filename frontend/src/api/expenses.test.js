import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { createExpense, updateExpense } from "./expenses";

function mockFetchOnce(status, body) {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue({
      ok: status >= 200 && status < 300,
      status,
      json: () => Promise.resolve(body),
    }),
  );
}

describe("expenses API error propagation", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn());
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("surfaces the backend's detail message on createExpense validation failure", async () => {
    mockFetchOnce(422, { detail: "Negative amounts are only allowed for Reimbursement." });
    await expect(createExpense({})).rejects.toThrow(
      "Negative amounts are only allowed for Reimbursement.",
    );
  });

  it("falls back to a generic message when createExpense fails with no detail", async () => {
    mockFetchOnce(500, {});
    await expect(createExpense({})).rejects.toThrow("Failed to create expense");
  });

  it("surfaces the backend's detail message on updateExpense validation failure", async () => {
    mockFetchOnce(422, { detail: "Split method cannot assign 100% to the person who paid." });
    await expect(updateExpense(1, {})).rejects.toThrow(
      "Split method cannot assign 100% to the person who paid.",
    );
  });

  it("falls back to a generic message when updateExpense fails with no detail", async () => {
    mockFetchOnce(500, {});
    await expect(updateExpense(1, {})).rejects.toThrow("Failed to update expense");
  });
});
