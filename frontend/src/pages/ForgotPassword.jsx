import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { API_BASE } from "../config";
import config from "../config";

export default function ForgotPassword() {
  const navigate = useNavigate();

  // Step tracking: "username" -> "answer" -> "success"
  const [step, setStep] = useState("username");
  const [username, setUsername] = useState("");
  const [securityQuestion, setSecurityQuestion] = useState("");
  const [securityAnswer, setSecurityAnswer] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const handleGetQuestion = async (e) => {
    e.preventDefault();
    setError("");
    setSubmitting(true);
    try {
      const res = await fetch(`${API_BASE}/auth/forgot-password/question`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || "User not found");
      }
      const data = await res.json();
      setSecurityQuestion(data.security_question);
      setStep("answer");
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  };

  const handleReset = async (e) => {
    e.preventDefault();
    setError("");

    if (newPassword !== confirmPassword) {
      setError("Passwords do not match");
      return;
    }

    setSubmitting(true);
    try {
      const res = await fetch(`${API_BASE}/auth/forgot-password/reset`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          username,
          security_answer: securityAnswer,
          new_password: newPassword,
        }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || "Reset failed");
      }
      setStep("success");
    } catch (err) {
      setError(err.message);
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
              Reset your password
            </p>
          </div>

          {error && (
            <div className="bg-error-container/20 border border-error/20 text-error px-4 py-3 rounded-xl text-sm mb-6 flex items-center gap-2">
              <span className="material-symbols-outlined text-sm">error</span>
              {error}
            </div>
          )}

          {step === "username" && (
            <form onSubmit={handleGetQuestion} className="space-y-5">
              <div className="flex flex-col">
                <label className="font-label text-xs uppercase tracking-widest text-on-surface-variant font-semibold mb-2 ml-1">
                  Username
                </label>
                <div className="bg-surface-container-high rounded-xl px-4 py-3 flex items-center focus-within:bg-surface-container-lowest transition-colors">
                  <span className="material-symbols-outlined text-primary/60 mr-3">
                    person
                  </span>
                  <input
                    type="text"
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                    placeholder="Enter your username"
                    className="bg-transparent border-none focus:ring-0 focus:outline-none w-full font-medium text-on-surface"
                    autoFocus
                    required
                  />
                </div>
              </div>

              <button
                type="submit"
                disabled={submitting}
                className="w-full h-14 rounded-full bg-gradient-to-r from-primary to-primary-dim text-on-primary font-headline font-bold text-lg shadow-lg hover:shadow-primary/20 active:scale-[0.98] transition-all duration-200 flex items-center justify-center gap-2 disabled:opacity-60"
              >
                <span className="material-symbols-outlined">arrow_forward</span>
                {submitting ? "Looking up..." : "Continue"}
              </button>
            </form>
          )}

          {step === "answer" && (
            <form onSubmit={handleReset} className="space-y-5">
              <div className="bg-primary-container/20 border border-primary/10 rounded-xl px-4 py-3 text-sm text-on-surface">
                <p className="font-semibold text-primary mb-1">
                  Security Question
                </p>
                <p>{securityQuestion}</p>
              </div>

              <div className="flex flex-col">
                <label className="font-label text-xs uppercase tracking-widest text-on-surface-variant font-semibold mb-2 ml-1">
                  Your Answer
                </label>
                <div className="bg-surface-container-high rounded-xl px-4 py-3 flex items-center focus-within:bg-surface-container-lowest transition-colors">
                  <span className="material-symbols-outlined text-primary/60 mr-3">
                    key
                  </span>
                  <input
                    type="text"
                    value={securityAnswer}
                    onChange={(e) => setSecurityAnswer(e.target.value)}
                    placeholder="Answer (case-insensitive)"
                    className="bg-transparent border-none focus:ring-0 focus:outline-none w-full font-medium text-on-surface"
                    autoFocus
                    required
                  />
                </div>
              </div>

              <div className="flex flex-col">
                <label className="font-label text-xs uppercase tracking-widest text-on-surface-variant font-semibold mb-2 ml-1">
                  New Password
                </label>
                <div className="bg-surface-container-high rounded-xl px-4 py-3 flex items-center focus-within:bg-surface-container-lowest transition-colors">
                  <span className="material-symbols-outlined text-primary/60 mr-3">
                    lock
                  </span>
                  <input
                    type="password"
                    value={newPassword}
                    onChange={(e) => setNewPassword(e.target.value)}
                    placeholder="At least 6 characters"
                    className="bg-transparent border-none focus:ring-0 focus:outline-none w-full font-medium text-on-surface"
                    required
                    minLength={6}
                  />
                </div>
              </div>

              <div className="flex flex-col">
                <label className="font-label text-xs uppercase tracking-widest text-on-surface-variant font-semibold mb-2 ml-1">
                  Confirm New Password
                </label>
                <div className="bg-surface-container-high rounded-xl px-4 py-3 flex items-center focus-within:bg-surface-container-lowest transition-colors">
                  <span className="material-symbols-outlined text-primary/60 mr-3">
                    lock
                  </span>
                  <input
                    type="password"
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    placeholder="Repeat new password"
                    className="bg-transparent border-none focus:ring-0 focus:outline-none w-full font-medium text-on-surface"
                    required
                    minLength={6}
                  />
                </div>
              </div>

              <button
                type="submit"
                disabled={submitting}
                className="w-full h-14 rounded-full bg-gradient-to-r from-primary to-primary-dim text-on-primary font-headline font-bold text-lg shadow-lg hover:shadow-primary/20 active:scale-[0.98] transition-all duration-200 flex items-center justify-center gap-2 disabled:opacity-60"
              >
                <span className="material-symbols-outlined">
                  lock_reset
                </span>
                {submitting ? "Resetting..." : "Reset Password"}
              </button>
            </form>
          )}

          {step === "success" && (
            <div className="text-center space-y-4">
              <div className="w-16 h-16 rounded-full bg-tertiary-container mx-auto flex items-center justify-center">
                <span
                  className="material-symbols-outlined text-3xl text-tertiary"
                  style={{ fontVariationSettings: "'FILL' 1" }}
                >
                  check_circle
                </span>
              </div>
              <p className="text-on-surface font-medium">
                Password reset successfully!
              </p>
              <button
                onClick={() => navigate("/")}
                className="w-full h-14 rounded-full bg-gradient-to-r from-primary to-primary-dim text-on-primary font-headline font-bold text-lg shadow-lg hover:shadow-primary/20 active:scale-[0.98] transition-all duration-200 flex items-center justify-center gap-2"
              >
                <span className="material-symbols-outlined">login</span>
                Sign In
              </button>
            </div>
          )}

          {step !== "success" && (
            <div className="text-center mt-6">
              <button
                onClick={() => navigate("/")}
                className="text-primary font-bold text-sm hover:underline"
              >
                Back to Sign In
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
