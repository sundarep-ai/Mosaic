import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { toLocalISODate } from "./dates";
import { getDateRange } from "./analytics";

// These tests pin process.env.TZ to a UTC+ zone (Asia/Kolkata, UTC+5:30) to
// reproduce the bug: toISOString() converts to UTC first, which rolls an
// early-morning local instant back to the *previous* UTC calendar day.
describe("toLocalISODate at a UTC+ offset", () => {
  const originalTZ = process.env.TZ;

  beforeEach(() => {
    process.env.TZ = "Asia/Kolkata";
  });

  afterEach(() => {
    process.env.TZ = originalTZ;
  });

  it("sanity-checks that the bug condition actually exists for this instant", () => {
    // 2026-04-15 02:00 local (Kolkata, UTC+5:30) == 2026-04-14 20:30 UTC
    const localMorning = new Date(2026, 3, 15, 2, 0, 0);
    expect(localMorning.toISOString().startsWith("2026-04-14")).toBe(true);
  });

  it("keeps today's local calendar date instead of rolling back to UTC's previous day", () => {
    const localMorning = new Date(2026, 3, 15, 2, 0, 0);
    expect(toLocalISODate(localMorning)).toBe("2026-04-15");
  });

  it("getDateRange includes today when 'now' is early morning locally", () => {
    const localMorning = new Date(2026, 3, 15, 2, 0, 0);
    const { end_date } = getDateRange(30, localMorning);
    expect(end_date).toBe("2026-04-15");
  });

  it("formats the last day of a month correctly (the Analytics.jsx month drill-down case)", () => {
    // new Date(year, month, 0) gives the last day of the *previous* month at
    // local midnight — July 31 2026 here. The old code converted this local
    // midnight to UTC via toISOString(), which rolled it back to July 30.
    const lastDayOfJuly = new Date(2026, 7, 0);
    expect(toLocalISODate(lastDayOfJuly)).toBe("2026-07-31");
  });

  it("does not depend on the time-of-day for a plain local date", () => {
    const lateEvening = new Date(2026, 3, 15, 23, 45, 0);
    expect(toLocalISODate(lateEvening)).toBe("2026-04-15");
  });
});

describe("toLocalISODate formatting", () => {
  it("zero-pads month and day", () => {
    expect(toLocalISODate(new Date(2026, 0, 5))).toBe("2026-01-05");
  });

  it("defaults to the current date when called with no argument", () => {
    expect(() => toLocalISODate()).not.toThrow();
  });
});
