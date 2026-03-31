/**
 * Compute a date range by subtracting a number of days from today.
 * @param {number} days – how many days to look back
 * @param {Date}  [now] – reference date (defaults to new Date())
 * @returns {{ start_date: string, end_date: string }} ISO date strings
 */
export function getDateRange(days, now = new Date()) {
  const end = new Date(now);
  const start = new Date(now);
  start.setDate(start.getDate() - days);
  return {
    start_date: start.toISOString().split("T")[0],
    end_date: end.toISOString().split("T")[0],
  };
}

/**
 * Group an array of expenses by description, summing amounts and counting.
 * Returns top N groups sorted by amount descending.
 */
export function groupByDescription(expenses, limit = 7) {
  const grouped = {};
  for (const e of expenses) {
    if (!grouped[e.description]) {
      grouped[e.description] = { description: e.description, amount: 0, count: 0 };
    }
    grouped[e.description].amount += e.amount;
    grouped[e.description].count += 1;
  }
  return Object.values(grouped)
    .sort((a, b) => b.amount - a.amount)
    .slice(0, limit);
}

/**
 * Group an array of expenses by month (YYYY-MM), summing amounts and counting.
 * Returns groups sorted chronologically.
 */
export function groupByMonth(expenses) {
  const byMonth = {};
  for (const e of expenses) {
    const month = e.date.substring(0, 7);
    if (!byMonth[month]) byMonth[month] = { month, amount: 0, count: 0 };
    byMonth[month].amount += e.amount;
    byMonth[month].count += 1;
  }
  return Object.values(byMonth).sort((a, b) => a.month.localeCompare(b.month));
}
