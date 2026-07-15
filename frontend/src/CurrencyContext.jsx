// Currency is now a per-user server-side preference living on the same
// UserPreference row as date_format and income-mode-enabled — see
// UserPreferencesContext.jsx (whose provider is mounted once, as
// DateFormatProvider, in App.jsx). Re-exported under its original name so
// existing useCurrency() consumers don't need to change.
export { useCurrency } from "./UserPreferencesContext";
