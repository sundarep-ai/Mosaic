import { useState, useRef, useEffect } from "react";
import { useDateFormat } from "../DateFormatContext";

/**
 * Format-aware date input that replaces <input type="date">.
 *
 * Props:
 *   value     — ISO date string (YYYY-MM-DD), the source of truth
 *   onChange  — called with ISO date string when valid, or "" when cleared
 *   max       — optional max ISO date (e.g. today)
 *   name      — form field name
 *   required  — HTML required
 *   className — passed to the text <input>
 */
export default function DateInput({ value, onChange, max, name, required, className }) {
  const { dateFormat, formatDate, parseInputToISO, placeholder, separatorPositions } = useDateFormat();
  const [display, setDisplay] = useState(() => (value ? formatDate(value) : ""));
  const [error, setError] = useState("");
  const inputRef = useRef(null);
  const hiddenDateRef = useRef(null);

  // Sync display when value or format changes from outside
  useEffect(() => {
    setDisplay(value ? formatDate(value) : "");
    setError("");
  }, [value, dateFormat, formatDate]);

  const handleChange = (e) => {
    let raw = e.target.value;

    // Strip non-digit, non-slash characters
    raw = raw.replace(/[^0-9/]/g, "");

    // Auto-insert slashes at separator positions
    const digits = raw.replace(/\//g, "");
    let built = "";
    let di = 0;
    const maxLen = 10; // dd/mm/yyyy = 10 chars
    for (let i = 0; i < maxLen && di < digits.length; i++) {
      if (separatorPositions.includes(i)) {
        built += "/";
      } else {
        built += digits[di];
        di++;
      }
    }

    setDisplay(built);
    setError("");

    // If we have a complete date string, try to parse it
    if (built.length === 10) {
      const iso = parseInputToISO(built);
      if (iso) {
        // Validate the parsed date is real (e.g. not 31/02)
        const [y, m, d] = iso.split("-").map(Number);
        const dateObj = new Date(y, m - 1, d);
        if (dateObj.getFullYear() !== y || dateObj.getMonth() !== m - 1 || dateObj.getDate() !== d) {
          setError("Invalid date");
          return;
        }
        if (max && iso > max) {
          setError("Date cannot be in the future");
          return;
        }
        onChange(iso);
      } else {
        setError("Invalid date");
      }
    } else if (built.length === 0) {
      onChange("");
    }
  };

  const handleBlur = () => {
    // On blur, if incomplete, show error
    if (display && display.length < 10) {
      setError("Incomplete date");
    }
  };

  const handleCalendarChange = (e) => {
    const iso = e.target.value; // native date input always gives YYYY-MM-DD
    if (!iso) return;
    if (max && iso > max) {
      setError("Date cannot be in the future");
      return;
    }
    setError("");
    onChange(iso);
  };

  const openCalendar = () => {
    try {
      hiddenDateRef.current?.showPicker();
    } catch {
      hiddenDateRef.current?.click();
    }
  };

  return (
    <div className="flex-1">
      <div className="flex items-center gap-1">
        <input
          ref={inputRef}
          type="text"
          inputMode="numeric"
          name={name}
          value={display}
          onChange={handleChange}
          onBlur={handleBlur}
          placeholder={placeholder}
          required={required}
          className={className}
          autoComplete="off"
        />
        <button
          type="button"
          onClick={openCalendar}
          className="flex-shrink-0 text-on-surface-variant/60 hover:text-primary transition-colors p-0.5"
          tabIndex={-1}
          aria-label="Open calendar"
        >
          <span className="material-symbols-outlined text-[20px]">calendar_month</span>
        </button>
        <input
          ref={hiddenDateRef}
          type="date"
          value={value || ""}
          max={max}
          onChange={handleCalendarChange}
          className="sr-only"
          tabIndex={-1}
          aria-hidden="true"
        />
      </div>
      {error && (
        <p className="text-error text-xs mt-1 ml-1">{error}</p>
      )}
    </div>
  );
}
