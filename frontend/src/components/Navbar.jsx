import { Link, useLocation } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { useTheme } from "../ThemeContext";
import { useCurrency } from "../CurrencyContext";
import Avatar from "./Avatar";
import config from "../config";
import { useUsers } from "../ConfigContext";

const topLinks = [
  { to: "/", label: "Home" },
  { to: "/add", label: "Add New" },
  { to: "/analytics", label: "Analytics" },
  { to: "/calendar", label: "Calendar" },
  { to: "/insights", label: "Insights" },
  { to: "/history", label: "Expenses" },
];

const bottomLinks = [
  { to: "/", label: "Home", icon: "home" },
  { to: "/add", label: "Add New", icon: "add_circle" },
  { to: "/calendar", label: "Calendar", icon: "calendar_month" },
  { to: "/insights", label: "Insights", icon: "lightbulb" },
  { to: "/history", label: "Expenses", icon: "receipt_long" },
];

export default function Navbar() {
  const location = useLocation();
  const { user, logout } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const { currency, setCurrency, currencies } = useCurrency();
  const { mode } = useUsers();
  const modeLabel = mode === "solo" ? "Solo" : mode === "hybrid" ? "Personal + Shared" : "Shared";

  return (
    <>
      {/* Top App Bar */}
      <header className="fixed top-0 w-full z-50 bg-background/90 backdrop-blur-md shadow-sm shadow-on-surface/5">
        <div className="flex justify-between items-center px-6 py-3 w-full">
          <div className="flex items-center gap-2">
            <Link
              to="/"
              className="flex items-center gap-2"
            >
              <span className="text-xl font-bold text-primary italic font-headline">
                {config.appName}
              </span>
              <span className="text-[10px] font-bold uppercase tracking-wider text-on-surface-variant bg-surface-container px-2 py-0.5 rounded-full ml-2">
                {modeLabel}
              </span>
            </Link>
          </div>

          {/* Desktop Nav */}
          <nav className="hidden md:flex items-center gap-8">
            {topLinks.map((link) => {
              const active = location.pathname === link.to;
              return (
                <Link
                  key={link.to}
                  to={link.to}
                  className={`font-headline tracking-tight text-lg px-3 py-1 rounded-lg transition-colors ${
                    active
                      ? "text-primary font-bold"
                      : "text-on-surface-variant font-semibold hover:bg-surface-container"
                  }`}
                >
                  {link.label}
                </Link>
              );
            })}
          </nav>

          <div className="flex items-center gap-3">
            <Link
              to="/settings"
              className="p-2 rounded-full hover:bg-surface-container transition-colors active:scale-95 duration-200"
              aria-label="Settings"
            >
              <span className="material-symbols-outlined text-primary" aria-hidden="true">
                settings
              </span>
            </Link>
            {user && (
              <div className="flex items-center gap-2 px-2 py-1.5 hidden sm:flex">
                <Avatar user={user.displayName} size="sm" />
                <span className="text-sm font-medium text-on-surface-variant">
                  {user.displayName}
                </span>
              </div>
            )}
            <select
              aria-label="Select display currency (symbol only, no conversion)"
              title="Display currency only — no conversion"
              value={currency}
              onChange={(e) => setCurrency(e.target.value)}
              className="bg-surface-container text-on-surface text-sm font-bold rounded-full px-3 py-2 border-none outline-none cursor-pointer hover:bg-surface-container-high transition-colors appearance-none text-center"
              style={{ minWidth: "4.5rem" }}
            >
              {currencies.map((c) => (
                <option key={c.code} value={c.code}>
                  {c.symbol} {c.code}
                </option>
              ))}
            </select>
            <button
              aria-label="Toggle dark mode"
              onClick={toggleTheme}
              className="p-2 rounded-full hover:bg-surface-container transition-colors active:scale-95 duration-200"
            >
              <span className="material-symbols-outlined text-primary" aria-hidden="true">
                {theme === "dark" ? "light_mode" : "dark_mode"}
              </span>
            </button>
            <button
              aria-label="Log out"
              onClick={logout}
              className="p-2 rounded-full hover:bg-surface-container transition-colors active:scale-95 duration-200"
            >
              <span className="material-symbols-outlined text-primary" aria-hidden="true">
                logout
              </span>
            </button>
          </div>
        </div>
        <div className="bg-surface-container h-[1px] opacity-20"></div>
      </header>

      {/* Bottom Nav Bar (Mobile Only) */}
      <nav className="md:hidden fixed bottom-0 left-0 w-full flex justify-around items-center px-4 pb-6 pt-3 bg-background/80 backdrop-blur-xl z-50 rounded-t-3xl shadow-[0_-4px_24px_rgba(47,51,52,0.06)]">
        {bottomLinks.map((link) => {
          const active = location.pathname === link.to;
          return (
            <Link
              key={link.to}
              to={link.to}
              className={`flex flex-col items-center justify-center px-5 py-2 active:scale-90 transition-transform duration-150 ${
                active
                  ? "bg-primary-container text-primary rounded-2xl"
                  : "text-on-surface-variant hover:text-primary"
              }`}
            >
              <span
                className="material-symbols-outlined"
                style={
                  active
                    ? { fontVariationSettings: "'FILL' 1" }
                    : undefined
                }
              >
                {link.icon}
              </span>
              <span
                className={`font-label text-[11px] tracking-wide uppercase mt-1 ${
                  active ? "font-bold" : "font-medium"
                }`}
              >
                {link.label}
              </span>
            </Link>
          );
        })}
      </nav>
    </>
  );
}
