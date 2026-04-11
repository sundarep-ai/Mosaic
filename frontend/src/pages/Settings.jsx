import { useRef, useState, useEffect } from "react";
import { useAuth } from "../auth/AuthContext";
import { uploadAvatar } from "../api/expenses";
import Avatar from "../components/Avatar";
import { useUsers } from "../ConfigContext";
import { useIncomeMode } from "../hooks/useIncomeMode";
import { useDateFormat } from "../DateFormatContext";
import { API_BASE } from "../config";
import { fetchWithAuth } from "../api/fetchWithAuth";

const MODES = [
  {
    value: "personal",
    label: "Personal",
    icon: "person",
    description: "Track your personal expenses",
  },
  {
    value: "shared",
    label: "Shared",
    icon: "group",
    description: "Split expenses with your partner",
  },
  {
    value: "blended",
    label: "Blended",
    icon: "diversity_3",
    description: "Track personal expenses and split shared ones",
  },
];

const DATE_FORMATS = [
  { value: "DD/MM/YYYY", label: "DD/MM/YYYY", example: "25/12/2025" },
  { value: "MM/DD/YYYY", label: "MM/DD/YYYY", example: "12/25/2025" },
  { value: "YYYY/MM/DD", label: "YYYY/MM/DD", example: "2025/12/25" },
  { value: "YYYY/DD/MM", label: "YYYY/DD/MM", example: "2025/25/12" },
];

export default function Settings() {
  const { user, logout } = useAuth();
  const { mode, setMode, userCount } = useUsers();
  const fileInputRef = useRef(null);
  const [avatarKey, setAvatarKey] = useState(0);
  const { incomeEnabled, toggleIncome, clearIncome, canUseIncome } = useIncomeMode();
  const { dateFormat, setDateFormat } = useDateFormat();

  // Stay signed in
  const [staySignedIn, setStaySignedIn] = useState(false);
  const [staySignedInLoading, setStaySignedInLoading] = useState(true);

  // Change password
  const [showChangePassword, setShowChangePassword] = useState(false);
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmNewPassword, setConfirmNewPassword] = useState("");
  const [passwordMsg, setPasswordMsg] = useState({ type: "", text: "" });
  const [passwordSubmitting, setPasswordSubmitting] = useState(false);

  // Delete account
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [deletePassword, setDeletePassword] = useState("");
  const [dataAction, setDataAction] = useState("anonymize");
  const [deleteError, setDeleteError] = useState("");
  const [deleteSubmitting, setDeleteSubmitting] = useState(false);

  useEffect(() => {
    fetchWithAuth(`${API_BASE}/auth/me`, { credentials: "include" })
      .then((r) => {
        if (r.ok) return r.json();
        throw new Error();
      })
      .then((data) => {
        if (data.stay_signed_in !== undefined) {
          setStaySignedIn(data.stay_signed_in);
        }
      })
      .catch(() => {})
      .finally(() => setStaySignedInLoading(false));
  }, []);

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
      if (newMode === "shared") {
        clearIncome();
      }
    } catch {
      alert("Failed to update mode. Please try again.");
    }
  };

  const handleToggleStaySignedIn = async (enabled) => {
    try {
      const res = await fetchWithAuth(`${API_BASE}/auth/stay-signed-in`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ enabled }),
        credentials: "include",
      });
      if (!res.ok) throw new Error("Failed to update preference");
      setStaySignedIn(enabled);
    } catch {
      alert("Failed to update stay signed in preference.");
    }
  };

  const handleChangePassword = async (e) => {
    e.preventDefault();
    setPasswordMsg({ type: "", text: "" });

    if (newPassword !== confirmNewPassword) {
      setPasswordMsg({ type: "error", text: "New passwords do not match" });
      return;
    }

    setPasswordSubmitting(true);
    try {
      const res = await fetchWithAuth(`${API_BASE}/auth/change-password`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          current_password: currentPassword,
          new_password: newPassword,
        }),
        credentials: "include",
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || "Failed to change password");
      }
      setPasswordMsg({ type: "success", text: "Password changed successfully!" });
      setCurrentPassword("");
      setNewPassword("");
      setConfirmNewPassword("");
      setTimeout(() => setShowChangePassword(false), 1500);
    } catch (err) {
      setPasswordMsg({ type: "error", text: err.message });
    } finally {
      setPasswordSubmitting(false);
    }
  };

  const handleDeleteAccount = async (e) => {
    e.preventDefault();
    setDeleteError("");
    setDeleteSubmitting(true);
    try {
      const res = await fetchWithAuth(`${API_BASE}/auth/account`, {
        method: "DELETE",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          password: deletePassword,
          data_action: dataAction,
        }),
        credentials: "include",
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || "Failed to delete account");
      }
      // Account deleted — log out
      await logout();
    } catch (err) {
      setDeleteError(err.message);
    } finally {
      setDeleteSubmitting(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto space-y-10">
      <header>
        <h1 className="font-headline text-3xl font-extrabold text-on-surface tracking-tight mb-2">
          Settings
        </h1>
        <p className="text-on-surface-variant font-medium">
          Configure how you use Mosaic.
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

      {/* Stay Signed In */}
      <section className="space-y-4">
        <h2 className="font-headline text-xl font-bold text-on-surface">
          Stay Signed In
        </h2>
        <div className="bg-surface-container p-6 rounded-2xl flex items-start justify-between gap-6">
          <div className="flex items-start gap-4">
            <div className={`w-12 h-12 rounded-full flex items-center justify-center shrink-0 ${staySignedIn ? "bg-tertiary-container" : "bg-surface-container-high"}`}>
              <span
                className={`material-symbols-outlined text-xl ${staySignedIn ? "text-tertiary" : "text-on-surface-variant"}`}
                style={staySignedIn ? { fontVariationSettings: "'FILL' 1" } : undefined}
              >
                lock_open
              </span>
            </div>
            <div>
              <p className="font-bold text-on-surface mb-1">Keep me signed in</p>
              <p className="text-sm text-on-surface-variant leading-relaxed">
                Stay logged in for up to a year instead of 8 hours. Convenient for a locally hosted app.
              </p>
            </div>
          </div>
          <button
            type="button"
            role="switch"
            aria-checked={staySignedIn}
            disabled={staySignedInLoading}
            onClick={() => handleToggleStaySignedIn(!staySignedIn)}
            className={`relative inline-flex h-7 w-12 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 focus:outline-none ${staySignedIn ? "bg-tertiary" : "bg-surface-container-high"}`}
          >
            <span
              className={`pointer-events-none inline-block h-6 w-6 transform rounded-full bg-white shadow-md ring-0 transition duration-200 ease-in-out ${staySignedIn ? "translate-x-5" : "translate-x-0"}`}
            />
          </button>
        </div>
      </section>

      {/* Date Format */}
      <section className="space-y-4">
        <h2 className="font-headline text-xl font-bold text-on-surface">
          Date Format
        </h2>
        <div className="bg-surface-container p-6 rounded-2xl space-y-4">
          <p className="text-sm text-on-surface-variant leading-relaxed">
            Choose how dates are displayed and entered throughout the app.
          </p>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            {DATE_FORMATS.map((f) => {
              const isActive = dateFormat === f.value;
              return (
                <button
                  key={f.value}
                  onClick={() => setDateFormat(f.value)}
                  className={`flex flex-col items-center justify-center p-4 rounded-2xl border-2 transition-all ${
                    isActive
                      ? "bg-primary-container/30 border-primary/30"
                      : "bg-surface-container-high border-transparent hover:border-outline-variant/20"
                  }`}
                >
                  <span
                    className={`font-bold text-sm mb-1 ${
                      isActive ? "text-primary" : "text-on-surface"
                    }`}
                  >
                    {f.label}
                  </span>
                  <span className="text-xs text-on-surface-variant">
                    {f.example}
                  </span>
                </button>
              );
            })}
          </div>
        </div>
      </section>

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
        {mode === "personal" && userCount >= 2 && (
          <div className="bg-tertiary-container/30 border border-tertiary/20 rounded-2xl px-4 py-3 flex items-center gap-3">
            <span className="material-symbols-outlined text-tertiary">group_add</span>
            <p className="text-sm text-on-surface">
              A second user has registered. Switch to <strong>Shared</strong> or{" "}
              <strong>Blended</strong> mode to start collaborating.
            </p>
          </div>
        )}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          {MODES.map((m) => {
            const isActive = mode === m.value;
            const needsSecondUser = m.value !== "personal" && userCount < 2;
            return (
              <button
                key={m.value}
                onClick={() => !needsSecondUser && handleModeChange(m.value)}
                disabled={needsSecondUser}
                className={`flex flex-col items-center justify-center p-6 rounded-2xl border-2 transition-all ${
                  needsSecondUser
                    ? "opacity-50 cursor-not-allowed bg-surface-container border-transparent"
                    : isActive
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
        {userCount < 2 && (
          <p className="text-sm text-on-surface-variant flex items-center gap-2">
            <span className="material-symbols-outlined text-base">info</span>
            A second user must create an account before switching to Shared or
            Blended mode.
          </p>
        )}
      </section>

      {/* Security — Change Password */}
      <section className="space-y-4">
        <h2 className="font-headline text-xl font-bold text-on-surface">
          Security
        </h2>
        <div className="bg-surface-container p-6 rounded-2xl space-y-4">
          {!showChangePassword ? (
            <button
              onClick={() => {
                setShowChangePassword(true);
                setPasswordMsg({ type: "", text: "" });
              }}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-primary-container text-on-primary-container text-sm font-bold active:scale-95 transition-transform hover:shadow-md"
            >
              <span className="material-symbols-outlined text-[18px]">lock_reset</span>
              Change Password
            </button>
          ) : (
            <form onSubmit={handleChangePassword} className="space-y-4">
              <div className="flex flex-col">
                <label htmlFor="current-password" className="font-label text-xs uppercase tracking-widest text-on-surface-variant font-semibold mb-2">
                  Current Password
                </label>
                <input
                  id="current-password"
                  type="password"
                  value={currentPassword}
                  onChange={(e) => setCurrentPassword(e.target.value)}
                  className="bg-surface-container-high rounded-xl px-4 py-3 border-none focus:ring-0 focus:outline-none font-medium text-on-surface focus:bg-surface-container-lowest transition-colors"
                  required
                />
              </div>
              <div className="flex flex-col">
                <label htmlFor="new-password" className="font-label text-xs uppercase tracking-widest text-on-surface-variant font-semibold mb-2">
                  New Password
                </label>
                <input
                  id="new-password"
                  type="password"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  className="bg-surface-container-high rounded-xl px-4 py-3 border-none focus:ring-0 focus:outline-none font-medium text-on-surface focus:bg-surface-container-lowest transition-colors"
                  required
                  minLength={6}
                />
              </div>
              <div className="flex flex-col">
                <label htmlFor="confirm-new-password" className="font-label text-xs uppercase tracking-widest text-on-surface-variant font-semibold mb-2">
                  Confirm New Password
                </label>
                <input
                  id="confirm-new-password"
                  type="password"
                  value={confirmNewPassword}
                  onChange={(e) => setConfirmNewPassword(e.target.value)}
                  className="bg-surface-container-high rounded-xl px-4 py-3 border-none focus:ring-0 focus:outline-none font-medium text-on-surface focus:bg-surface-container-lowest transition-colors"
                  required
                  minLength={6}
                />
              </div>
              {passwordMsg.text && (
                <div
                  className={`px-4 py-3 rounded-xl text-sm flex items-center gap-2 ${
                    passwordMsg.type === "error"
                      ? "bg-error-container/20 border border-error/20 text-error"
                      : "bg-tertiary-container/20 border border-tertiary/20 text-tertiary"
                  }`}
                >
                  <span className="material-symbols-outlined text-sm">
                    {passwordMsg.type === "error" ? "error" : "check_circle"}
                  </span>
                  {passwordMsg.text}
                </div>
              )}
              <div className="flex gap-3">
                <button
                  type="submit"
                  disabled={passwordSubmitting}
                  className="inline-flex items-center gap-2 px-5 py-2.5 rounded-full bg-primary text-on-primary text-sm font-bold disabled:opacity-60"
                >
                  {passwordSubmitting ? "Saving..." : "Update Password"}
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setShowChangePassword(false);
                    setCurrentPassword("");
                    setNewPassword("");
                    setConfirmNewPassword("");
                    setPasswordMsg({ type: "", text: "" });
                  }}
                  className="inline-flex items-center gap-2 px-5 py-2.5 rounded-full bg-surface-container-high text-on-surface text-sm font-bold"
                >
                  Cancel
                </button>
              </div>
            </form>
          )}
        </div>
      </section>

      {/* Danger Zone — Delete Account */}
      <section className="space-y-4">
        <h2 className="font-headline text-xl font-bold text-error">
          Danger Zone
        </h2>
        <div className="bg-error-container/10 border border-error/20 p-6 rounded-2xl space-y-4">
          <div className="flex items-start gap-4">
            <div className="w-12 h-12 rounded-full bg-error-container flex items-center justify-center shrink-0">
              <span className="material-symbols-outlined text-xl text-error">
                warning
              </span>
            </div>
            <div>
              <p className="font-bold text-on-surface mb-1">Delete Account</p>
              <p className="text-sm text-on-surface-variant leading-relaxed">
                Permanently delete your account. You can choose to delete or anonymize your expense data.
              </p>
            </div>
          </div>
          <button
            onClick={() => setShowDeleteModal(true)}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-error text-on-error text-sm font-bold active:scale-95 transition-transform"
          >
            <span className="material-symbols-outlined text-[18px]">delete_forever</span>
            Delete My Account
          </button>
        </div>
      </section>

      {/* Delete Account Modal */}
      {showDeleteModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4">
          <div className="bg-surface-container-lowest rounded-[2rem] p-8 w-full max-w-md shadow-2xl">
            <h3 className="font-headline text-xl font-bold text-error mb-4">
              Delete Account
            </h3>
            <p className="text-sm text-on-surface-variant mb-6">
              This action cannot be undone. Enter your password to confirm.
            </p>

            {deleteError && (
              <div className="bg-error-container/20 border border-error/20 text-error px-4 py-3 rounded-xl text-sm mb-4 flex items-center gap-2">
                <span className="material-symbols-outlined text-sm">error</span>
                {deleteError}
              </div>
            )}

            <form onSubmit={handleDeleteAccount} className="space-y-4">
              <div className="flex flex-col">
                <label htmlFor="delete-account-password" className="font-label text-xs uppercase tracking-widest text-on-surface-variant font-semibold mb-2">
                  Password
                </label>
                <input
                  id="delete-account-password"
                  type="password"
                  value={deletePassword}
                  onChange={(e) => setDeletePassword(e.target.value)}
                  className="bg-surface-container-high rounded-xl px-4 py-3 border-none focus:ring-0 focus:outline-none font-medium text-on-surface"
                  required
                  autoFocus
                />
              </div>

              <div className="flex flex-col">
                <label className="font-label text-xs uppercase tracking-widest text-on-surface-variant font-semibold mb-2">
                  What should happen to your data?
                </label>
                <div className="space-y-2">
                  <label className="flex items-center gap-3 bg-surface-container-high rounded-xl px-4 py-3 cursor-pointer">
                    <input
                      type="radio"
                      name="dataAction"
                      value="anonymize"
                      checked={dataAction === "anonymize"}
                      onChange={() => setDataAction("anonymize")}
                      className="text-primary focus:ring-primary"
                    />
                    <div>
                      <p className="font-medium text-on-surface text-sm">Keep data anonymized</p>
                      <p className="text-xs text-on-surface-variant">Your expenses stay but are labeled "Deleted User"</p>
                    </div>
                  </label>
                  <label className="flex items-center gap-3 bg-surface-container-high rounded-xl px-4 py-3 cursor-pointer">
                    <input
                      type="radio"
                      name="dataAction"
                      value="delete"
                      checked={dataAction === "delete"}
                      onChange={() => setDataAction("delete")}
                      className="text-error focus:ring-error"
                    />
                    <div>
                      <p className="font-medium text-on-surface text-sm">Delete all my data</p>
                      <p className="text-xs text-on-surface-variant">Remove all expenses and income permanently</p>
                    </div>
                  </label>
                </div>
              </div>

              <div className="flex gap-3 pt-2">
                <button
                  type="submit"
                  disabled={deleteSubmitting}
                  className="inline-flex items-center gap-2 px-5 py-2.5 rounded-full bg-error text-on-error text-sm font-bold disabled:opacity-60"
                >
                  {deleteSubmitting ? "Deleting..." : "Delete Account"}
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setShowDeleteModal(false);
                    setDeletePassword("");
                    setDeleteError("");
                  }}
                  className="inline-flex items-center gap-2 px-5 py-2.5 rounded-full bg-surface-container-high text-on-surface text-sm font-bold"
                >
                  Cancel
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
