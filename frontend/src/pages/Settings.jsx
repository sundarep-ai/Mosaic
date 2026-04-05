import { useRef, useState } from "react";
import { useAuth } from "../auth/AuthContext";
import { uploadAvatar } from "../api/expenses";
import Avatar from "../components/Avatar";
import { useUsers } from "../ConfigContext";
import { useIncomeMode } from "../hooks/useIncomeMode";

const MODES = [
  {
    value: "solo",
    label: "Solo",
    icon: "person",
    description: "Track your personal expenses",
  },
  {
    value: "duo",
    label: "Shared",
    icon: "group",
    description: "Split expenses with your partner",
  },
  {
    value: "hybrid",
    label: "Personal + Shared",
    icon: "diversity_3",
    description: "Track personal expenses and split shared ones",
  },
];

export default function Settings() {
  const { user } = useAuth();
  const { mode, setMode } = useUsers();
  const fileInputRef = useRef(null);
  const [avatarKey, setAvatarKey] = useState(0);
  const { incomeEnabled, toggleIncome, clearIncome, canUseIncome } = useIncomeMode();

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

  const handleModeChange = async (newMode) => {
    try {
      await setMode(newMode);
      // Income tracking is not available in Shared mode — clear it
      if (newMode === "duo") {
        clearIncome();
      }
    } catch {
      alert("Failed to update mode. Please try again.");
    }
  };

  return (
    <div className="max-w-2xl mx-auto space-y-10">
      <header>
        <h1 className="font-headline text-3xl font-extrabold text-on-surface tracking-tight mb-2">
          Settings
        </h1>
        <p className="text-on-surface-variant font-medium">
          Configure how you use MosaicTally.
        </p>
      </header>

      {/* Profile Picture */}
      {user && (
        <section className="space-y-4">
          <h2 className="font-headline text-xl font-bold text-on-surface">
            Profile Picture
          </h2>
          <div className="flex items-center gap-6 bg-surface-container p-6 rounded-2xl">
            <div className="w-20 h-20 rounded-full overflow-hidden border-4 border-surface-container-high">
              <Avatar user={user.displayName} size="lg" cacheBust={avatarKey} />
            </div>
            <div>
              <p className="font-bold text-on-surface mb-1">{user.displayName}</p>
              <input
                type="file"
                ref={fileInputRef}
                accept="image/*"
                className="hidden"
                onChange={handleAvatarUpload}
              />
              <button
                onClick={() => fileInputRef.current?.click()}
                className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-primary-container text-on-primary-container text-sm font-bold active:scale-95 transition-transform hover:shadow-md"
              >
                <span className="material-symbols-outlined text-[18px]">photo_camera</span>
                Change Photo
              </button>
            </div>
          </div>
        </section>
      )}

      {/* Income Tracking — Solo and Hybrid only */}
      {canUseIncome && (
        <section className="space-y-4">
          <h2 className="font-headline text-xl font-bold text-on-surface">
            Income Tracking
          </h2>
          <div className="bg-surface-container p-6 rounded-2xl flex items-start justify-between gap-6">
            <div className="flex items-start gap-4">
              <div className={`w-12 h-12 rounded-full flex items-center justify-center shrink-0 ${incomeEnabled ? "bg-tertiary-container" : "bg-surface-container-high"}`}>
                <span
                  className={`material-symbols-outlined text-xl ${incomeEnabled ? "text-tertiary" : "text-on-surface-variant"}`}
                  style={incomeEnabled ? { fontVariationSettings: "'FILL' 1" } : undefined}
                >
                  payments
                </span>
              </div>
              <div>
                <p className="font-bold text-on-surface mb-1">Enable Income Tracking</p>
                <p className="text-sm text-on-surface-variant leading-relaxed">
                  Log income you receive and visualise where your money goes with a Sankey chart in Analytics.
                </p>
              </div>
            </div>
            <button
              type="button"
              role="switch"
              aria-checked={incomeEnabled}
              onClick={() => toggleIncome(!incomeEnabled)}
              className={`relative inline-flex h-7 w-12 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 focus:outline-none ${incomeEnabled ? "bg-tertiary" : "bg-surface-container-high"}`}
            >
              <span
                className={`pointer-events-none inline-block h-6 w-6 transform rounded-full bg-white shadow-md ring-0 transition duration-200 ease-in-out ${incomeEnabled ? "translate-x-5" : "translate-x-0"}`}
              />
            </button>
          </div>
        </section>
      )}

      <section className="space-y-4">
        <h2 className="font-headline text-xl font-bold text-on-surface">
          App Mode
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          {MODES.map((m) => {
            const isActive = mode === m.value;
            return (
              <button
                key={m.value}
                onClick={() => handleModeChange(m.value)}
                className={`flex flex-col items-center justify-center p-6 rounded-2xl border-2 transition-all ${
                  isActive
                    ? "bg-primary-container/30 border-primary/30"
                    : "bg-surface-container border-transparent hover:border-outline-variant/20"
                }`}
              >
                <div
                  className={`w-14 h-14 rounded-full flex items-center justify-center mb-3 ${
                    isActive ? "bg-primary-container" : "bg-surface-container-high"
                  }`}
                >
                  <span
                    className={`material-symbols-outlined text-2xl ${
                      isActive ? "text-primary" : "text-on-surface-variant"
                    }`}
                    style={isActive ? { fontVariationSettings: "'FILL' 1" } : undefined}
                  >
                    {m.icon}
                  </span>
                </div>
                <span
                  className={`font-bold text-sm mb-1 ${
                    isActive ? "text-primary" : "text-on-surface"
                  }`}
                >
                  {m.label}
                </span>
                <span className="text-xs text-on-surface-variant text-center">
                  {m.description}
                </span>
              </button>
            );
          })}
        </div>
      </section>
    </div>
  );
}
