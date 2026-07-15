// income-mode-enabled is now a per-user server-side preference living on the
// same UserPreference row as date_format and currency — see
// UserPreferencesContext.jsx (whose provider is mounted once, as
// DateFormatProvider, in App.jsx). Re-exported under its original name so
// existing useIncomeMode() consumers don't need to change.
export { useIncomeMode } from "../UserPreferencesContext";
