const NUMBER_FORMATTER = new Intl.NumberFormat("en-US", {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

/**
 * Format an amount with a currency symbol: thousands separators, and the
 * sign placed before the symbol for negatives (e.g. "-$12.00", not "$-12.00").
 */
export function formatCurrency(amount, symbol) {
  const num = Number(amount) || 0;
  const sign = num < 0 ? "-" : "";
  return `${sign}${symbol}${NUMBER_FORMATTER.format(Math.abs(num))}`;
}
