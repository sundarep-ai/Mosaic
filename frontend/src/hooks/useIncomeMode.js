import { useState } from "react";
import { useUsers } from "../ConfigContext";

const STORAGE_KEY = "income_mode_enabled";

export function useIncomeMode() {
  const { mode } = useUsers();
  const canUseIncome = mode === "solo" || mode === "hybrid";

  const [enabled, setEnabled] = useState(
    () => canUseIncome && localStorage.getItem(STORAGE_KEY) === "true"
  );

  function toggleIncome(val) {
    if (val) {
      localStorage.setItem(STORAGE_KEY, "true");
    } else {
      localStorage.removeItem(STORAGE_KEY);
    }
    setEnabled(val && canUseIncome);
  }

  function clearIncome() {
    localStorage.removeItem(STORAGE_KEY);
    setEnabled(false);
  }

  return {
    incomeEnabled: enabled && canUseIncome,
    toggleIncome,
    clearIncome,
    canUseIncome,
  };
}
