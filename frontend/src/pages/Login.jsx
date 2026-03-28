import { useState } from "react";
import { useAuth } from "../auth/AuthContext";
import config from "../config";

export default function Login() {
  const { login } = useAuth();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setSubmitting(true);
    try {
      await login(username, password);
    } catch (err) {
      setError(err.message || "Login failed");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-background flex items-center justify-center px-4">
      <div className="w-full max-w-sm">
        <div className="bg-surface-container-lowest rounded-[2rem] p-8 shadow-[0_4px_32px_rgba(47,51,52,0.08)]">
          <div className="text-center mb-8">
            <h1 className="font-headline text-2xl font-extrabold text-primary tracking-tight">
              {config.appName}
            </h1>
            <p className="text-on-surface-variant text-sm font-medium mt-1">
              Sign in to continue
            </p>
          </div>

          {error && (
            <div className="bg-error-container/20 border border-error/20 text-error px-4 py-3 rounded-xl text-sm mb-6 flex items-center gap-2">
              <span className="material-symbols-outlined text-sm">error</span>
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-5">
            <div className="flex flex-col">
              <label className="font-label text-xs uppercase tracking-widest text-on-surface-variant font-semibold mb-2 ml-1">
                Username
              </label>
              <div className="bg-surface-container-high rounded-xl px-4 py-3 flex items-center focus-within:bg-white transition-colors">
                <span className="material-symbols-outlined text-primary/60 mr-3">
                  person
                </span>
                <input
                  type="text"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  placeholder="Enter your name"
                  className="bg-transparent border-none focus:ring-0 focus:outline-none w-full font-medium text-on-surface"
                  autoFocus
                  required
                />
              </div>
            </div>

            <div className="flex flex-col">
              <label className="font-label text-xs uppercase tracking-widest text-on-surface-variant font-semibold mb-2 ml-1">
                Password
              </label>
              <div className="bg-surface-container-high rounded-xl px-4 py-3 flex items-center focus-within:bg-white transition-colors">
                <span className="material-symbols-outlined text-primary/60 mr-3">
                  lock
                </span>
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Enter your password"
                  className="bg-transparent border-none focus:ring-0 focus:outline-none w-full font-medium text-on-surface"
                  required
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={submitting}
              className="w-full h-14 rounded-full bg-gradient-to-r from-primary to-primary-dim text-on-primary font-headline font-bold text-lg shadow-lg hover:shadow-primary/20 active:scale-[0.98] transition-all duration-200 flex items-center justify-center gap-2 disabled:opacity-60 mt-2"
            >
              <span className="material-symbols-outlined">login</span>
              {submitting ? "Signing in..." : "Sign In"}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
