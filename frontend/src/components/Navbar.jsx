import { useRef, useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { uploadAvatar } from "../api/expenses";
import Avatar from "./Avatar";
import config from "../config";

const topLinks = [
  { to: "/", label: "Dashboard" },
  { to: "/add", label: "Add New" },
  { to: "/analytics", label: "Analytics" },
  { to: "/history", label: "Expenses" },
];

const bottomLinks = [
  { to: "/", label: "Dashboard", icon: "dashboard" },
  { to: "/add", label: "Add New", icon: "add_circle" },
  { to: "/history", label: "Expenses", icon: "receipt_long" },
];

export default function Navbar() {
  const location = useLocation();
  const { user, logout } = useAuth();
  const fileInputRef = useRef(null);
  const [avatarKey, setAvatarKey] = useState(0);

  const handleAvatarUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    try {
      await uploadAvatar(file);
      setAvatarKey((k) => k + 1);
    } catch (err) {
      alert(err.message);
    }
    e.target.value = "";
  };

  return (
    <>
      {/* Top App Bar */}
      <header className="fixed top-0 w-full z-50 bg-[#F9F9F9]/90 backdrop-blur-md shadow-sm shadow-[#2F3334]/5">
        <div className="flex justify-between items-center px-6 py-3 w-full">
          <div className="flex items-center gap-2">
            <Link
              to="/"
              className="flex items-center gap-2"
            >
              <span className="text-xl font-bold text-primary italic font-headline">
                {config.appName}
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
            <input
              type="file"
              ref={fileInputRef}
              accept="image/*"
              className="hidden"
              onChange={handleAvatarUpload}
            />
            {user && (
              <button
                onClick={() => fileInputRef.current?.click()}
                className="flex items-center gap-2 cursor-pointer hover:bg-surface-container px-2 py-1.5 rounded-full transition-colors active:scale-95 duration-200 hidden sm:flex"
                title="Click to change your profile picture"
              >
                <Avatar user={user.displayName} size="sm" cacheBust={avatarKey} />
                <span className="text-sm font-medium text-on-surface-variant">
                  {user.displayName}
                </span>
              </button>
            )}
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
      <nav className="md:hidden fixed bottom-0 left-0 w-full flex justify-around items-center px-4 pb-6 pt-3 bg-[#F9F9F9]/80 backdrop-blur-xl z-50 rounded-t-3xl shadow-[0_-4px_24px_rgba(47,51,52,0.06)]">
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
