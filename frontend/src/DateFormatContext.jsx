// date_format now lives on the same per-user UserPreference row as currency
// and income-mode-enabled — see UserPreferencesContext.jsx. Re-exported under
// its original names so existing call sites (App.jsx, every useDateFormat()
// consumer) don't need to change.
export { UserPreferencesProvider as DateFormatProvider, useDateFormat } from "./UserPreferencesContext";
