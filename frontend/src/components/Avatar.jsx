import { useState } from "react";
import { useUsers } from "../ConfigContext";
import { API_BASE } from "../config";

export default function Avatar({ user, size = "md", cacheBust = "" }) {
  const { userA, userB, userALogin, userBLogin } = useUsers();
  const [imgError, setImgError] = useState(false);

  const login = user === userA ? userALogin : user === userB ? userBLogin : null;
  const avatarUrl = login
    ? `${API_BASE}/auth/avatar/${login}${cacheBust ? `?v=${cacheBust}` : ""}`
    : null;

  const sizes = {
    sm: "w-5 h-5 text-[10px]",
    md: "w-10 h-10 text-sm",
  };
  const cls = sizes[size] || sizes.md;

  if (avatarUrl && !imgError) {
    return (
      <img
        src={avatarUrl}
        alt={user}
        className={`${cls} rounded-full object-cover`}
        onError={() => setImgError(true)}
      />
    );
  }

  return (
    <div
      className={`${cls} rounded-full bg-primary-container flex items-center justify-center`}
    >
      <span className="material-symbols-outlined text-on-primary-container text-[inherit]">
        person
      </span>
    </div>
  );
}
