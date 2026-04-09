import { useState } from "react";
import { Link } from "react-router-dom";
import { useUsers } from "../ConfigContext";

const DISMISS_KEY = "mode_switch_banner_dismissed";

export default function ModeSwitchBanner() {
  const { mode, userCount } = useUsers();
  const [dismissed, setDismissed] = useState(
    () => sessionStorage.getItem(DISMISS_KEY) === "true"
  );

  if (mode !== "personal" || userCount < 2 || dismissed) return null;

  const handleDismiss = () => {
    sessionStorage.setItem(DISMISS_KEY, "true");
    setDismissed(true);
  };

  return (
    <div className="bg-tertiary-container border border-tertiary/20 rounded-2xl px-4 py-3 mb-6 flex items-center gap-3">
      <span className="material-symbols-outlined text-tertiary">group_add</span>
      <p className="text-sm text-on-tertiary-container flex-1">
        A second user has registered!
        <Link
          to="/settings"
          className="font-bold text-tertiary underline ml-1"
        >
          Switch to Shared or Blended mode
        </Link>{" "}
        to start tracking together.
      </p>
      <button
        onClick={handleDismiss}
        className="text-on-tertiary-container/60 hover:text-on-tertiary-container"
      >
        <span className="material-symbols-outlined text-lg">close</span>
      </button>
    </div>
  );
}
