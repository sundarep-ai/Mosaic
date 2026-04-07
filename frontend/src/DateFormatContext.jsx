import { createContext, useContext, useState, useEffect, useCallback } from "react";
import { getUserPreferences, updateUserPreferences } from "./api/expenses";

const DateFormatContext = createContext({
  dateFormat: "DD/MM/YYYY",
  setDateFormat: () => {},
  formatDate: (iso) => iso,
  parseInputToISO: (input) => input,
  toInputValue: (iso) => iso,
});

/**
 * Mapping from format tokens to ISO date part extraction.
 *
 * ISO dates are always YYYY-MM-DD internally.
 * Display formats: MM/DD/YYYY, DD/MM/YYYY, YYYY/MM/DD, YYYY/DD/MM
 */

function isoToDisplay(isoStr, fmt) {
  if (!isoStr || isoStr.length < 10) return isoStr || "";
  const [y, m, d] = isoStr.substring(0, 10).split("-");
  switch (fmt) {
    case "MM/DD/YYYY": return `${m}/${d}/${y}`;
    case "DD/MM/YYYY": return `${d}/${m}/${y}`;
    case "YYYY/MM/DD": return `${y}/${m}/${d}`;
    case "YYYY/DD/MM": return `${y}/${d}/${m}`;
    default:           return `${d}/${m}/${y}`;
  }
}

function displayToISO(displayStr, fmt) {
  if (!displayStr) return "";
  const parts = displayStr.split("/");
  if (parts.length !== 3) return "";
  let y, m, d;
  switch (fmt) {
    case "MM/DD/YYYY": [m, d, y] = parts; break;
    case "DD/MM/YYYY": [d, m, y] = parts; break;
    case "YYYY/MM/DD": [y, m, d] = parts; break;
    case "YYYY/DD/MM": [y, d, m] = parts; break;
    default:           [d, m, y] = parts; break;
  }
  // Validate
  const yi = parseInt(y, 10);
  const mi = parseInt(m, 10);
  const di = parseInt(d, 10);
  if (isNaN(yi) || isNaN(mi) || isNaN(di)) return "";
  if (mi < 1 || mi > 12 || di < 1 || di > 31) return "";
  return `${String(yi).padStart(4, "0")}-${String(mi).padStart(2, "0")}-${String(di).padStart(2, "0")}`;
}

function getPlaceholder(fmt) {
  return fmt.toLowerCase();
}

function getSeparatorPositions(fmt) {
  // Return indices where "/" should be auto-inserted
  switch (fmt) {
    case "MM/DD/YYYY": return [2, 5];
    case "DD/MM/YYYY": return [2, 5];
    case "YYYY/MM/DD": return [4, 7];
    case "YYYY/DD/MM": return [4, 7];
    default:           return [2, 5];
  }
}

export function DateFormatProvider({ children }) {
  const [dateFormat, setDateFormatState] = useState("DD/MM/YYYY");
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    getUserPreferences()
      .then((prefs) => {
        if (prefs.date_format) setDateFormatState(prefs.date_format);
      })
      .catch(() => {})
      .finally(() => setLoaded(true));
  }, []);

  const setDateFormat = useCallback(async (newFormat) => {
    await updateUserPreferences({ date_format: newFormat });
    setDateFormatState(newFormat);
  }, []);

  const formatDate = useCallback(
    (isoStr) => isoToDisplay(isoStr, dateFormat),
    [dateFormat],
  );

  const parseInputToISO = useCallback(
    (displayStr) => displayToISO(displayStr, dateFormat),
    [dateFormat],
  );

  const toInputValue = useCallback(
    (isoStr) => isoToDisplay(isoStr, dateFormat),
    [dateFormat],
  );

  if (!loaded) return null;

  return (
    <DateFormatContext.Provider
      value={{
        dateFormat,
        setDateFormat,
        formatDate,
        parseInputToISO,
        toInputValue,
        placeholder: getPlaceholder(dateFormat),
        separatorPositions: getSeparatorPositions(dateFormat),
      }}
    >
      {children}
    </DateFormatContext.Provider>
  );
}

export function useDateFormat() {
  return useContext(DateFormatContext);
}
