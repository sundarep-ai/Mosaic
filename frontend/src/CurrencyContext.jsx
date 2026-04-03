import { createContext, useContext, useState } from "react";

const CURRENCIES = [
  { code: "USD", symbol: "$", name: "US Dollar" },
  { code: "EUR", symbol: "\u20AC", name: "Euro" },
  { code: "GBP", symbol: "\u00A3", name: "British Pound" },
  { code: "CAD", symbol: "C$", name: "Canadian Dollar" },
  { code: "AUD", symbol: "A$", name: "Australian Dollar" },
  { code: "INR", symbol: "\u20B9", name: "Indian Rupee" },
  { code: "JPY", symbol: "\u00A5", name: "Japanese Yen" },
  { code: "CNY", symbol: "\u00A5", name: "Chinese Yuan" },
  { code: "CHF", symbol: "CHF", name: "Swiss Franc" },
  { code: "SGD", symbol: "S$", name: "Singapore Dollar" },
];

const DEFAULT_CURRENCY = "CAD";

function getInitialCurrency() {
  const stored = localStorage.getItem("currency");
  if (stored && CURRENCIES.some((c) => c.code === stored)) return stored;
  return DEFAULT_CURRENCY;
}

const CurrencyContext = createContext();

export function CurrencyProvider({ children }) {
  const [currency, setCurrencyState] = useState(getInitialCurrency);

  const current = CURRENCIES.find((c) => c.code === currency) || CURRENCIES[0];

  const setCurrency = (code) => {
    setCurrencyState(code);
    localStorage.setItem("currency", code);
  };

  const fmt = (amount) => `${current.symbol}${amount.toFixed(2)}`;

  return (
    <CurrencyContext.Provider value={{ currency, symbol: current.symbol, setCurrency, fmt, currencies: CURRENCIES }}>
      {children}
    </CurrencyContext.Provider>
  );
}

export function useCurrency() {
  return useContext(CurrencyContext);
}
