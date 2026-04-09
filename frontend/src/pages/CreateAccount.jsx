import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { API_BASE } from "../config";
import config from "../config";

const CUSTOM_QUESTION = "__custom__";

export default function CreateAccount() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [presetQuestions, setPresetQuestions] = useState([]);
  const [accountStatus, setAccountStatus] = useState(null);

  const [displayName, setDisplayName] = useState("");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [selectedQuestion, setSelectedQuestion] = useState("");
  const [customQuestion, setCustomQuestion] = useState("");
  const [securityAnswer, setSecurityAnswer] = useState("");
  const [error, setError] = useState("");
  const [successMessage, setSuccessMessage] = useState("");
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    fetch(`${API_BASE}/auth/security-questions`)
      .then((r) => r.json())
      .then((data) => setPresetQuestions(data.questions || []))
      .catch(() => {});

    fetch(`${API_BASE}/auth/account-status`)
      .then((r) => r.json())
      .then((data) => setAccountStatus(data))
      .catch(() => {});
  }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");

    if (password !== confirmPassword) {
      setError("Passwords do not match");
      return;
    }

    const securityQuestion =
      selectedQuestion === CUSTOM_QUESTION ? customQuestion : selectedQuestion;

    if (!securityQuestion) {
      setError("Please select a security question");
      return;
    }
    if (!securityAnswer.trim()) {
      setError("Please provide a security answer");
      return;
    }

    setSubmitting(true);
    try {
      const res = await fetch(`${API_BASE}/auth/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({
          username,
          display_name: displayName,
          password,
          security_question: securityQuestion,
          security_answer: securityAnswer,
        }),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || "Registration failed");
      }

      const data = await res.json();

      if (data.personal_mode_notice) {
        setSuccessMessage(data.message);
        return;
      }

      // Auto-login was done server-side (cookie set). Refresh auth state.
      await login(username, password);
    } catch (err) {
      setError(err.message || "Registration failed");
    } finally {
      setSubmitting(false);
    }
  };

  if (successMessage) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center px-4">
        <div className="w-full max-w-sm bg-surface-container-lowest rounded-[2rem] p-8 shadow-[0_4px_32px_rgba(47,51,52,0.08)] text-center">
          <span className="material-symbols-outlined text-4xl text-tertiary mb-4">
            check_circle
          </span>
          <h2 className="font-headline text-xl font-bold text-on-surface mb-2">
            Account Created
          </h2>
          <p className="text-on-surface-variant text-sm mb-6">
            {successMessage}
          </p>
          <button
            onClick={() => navigate("/")}
            className="text-primary font-bold text-sm hover:underline"
          >
            Back to Sign In
          </button>
        </div>
      </div>
    );
  }

  if (accountStatus && !accountStatus.registration_open) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center px-4">
        <div className="w-full max-w-sm bg-surface-container-lowest rounded-[2rem] p-8 shadow-[0_4px_32px_rgba(47,51,52,0.08)] text-center">
          <h1 className="font-headline text-2xl font-extrabold text-primary tracking-tight mb-4">
            {config.appName}
          </h1>
          <p className="text-on-surface-variant text-sm">
            Maximum accounts reached. Only 2 accounts are allowed.
          </p>
          <button
            onClick={() => navigate("/")}
            className="mt-6 text-primary font-bold text-sm hover:underline"
          >
            Back to Sign In
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background flex items-center justify-center px-4">
      <div className="w-full max-w-md">
        <div className="bg-surface-container-lowest rounded-[2rem] p-8 shadow-[0_4px_32px_rgba(47,51,52,0.08)]">
          <div className="text-center mb-8">
            <h1 className="font-headline text-2xl font-extrabold text-primary tracking-tight">
              {config.appName}
            </h1>
            <p className="text-on-surface-variant text-sm font-medium mt-1">
              {accountStatus?.user_count === 0
                ? "Welcome! Create the first account."
                : "Create the second account."}
            </p>
          </div>

          {error && (
            <div className="bg-error-container/20 border border-error/20 text-error px-4 py-3 rounded-xl text-sm mb-6 flex items-center gap-2">
              <span className="material-symbols-outlined text-sm">error</span>
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-5">
            {/* Display Name */}
            <div className="flex flex-col">
              <label className="font-label text-xs uppercase tracking-widest text-on-surface-variant font-semibold mb-2 ml-1">
                Display Name
              </label>
              <div className="bg-surface-container-high rounded-xl px-4 py-3 flex items-center focus-within:bg-surface-container-lowest transition-colors">
                <span className="material-symbols-outlined text-primary/60 mr-3">
                  badge
                </span>
                <input
                  type="text"
                  value={displayName}
                  onChange={(e) => setDisplayName(e.target.value)}
                  placeholder="How others will see you"
                  className="bg-transparent border-none focus:ring-0 focus:outline-none w-full font-medium text-on-surface"
                  required
                  minLength={2}
                  maxLength={100}
                  autoFocus
                />
              </div>
            </div>

            {/* Username */}
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
                  placeholder="Login username"
                  className="bg-transparent border-none focus:ring-0 focus:outline-none w-full font-medium text-on-surface"
                  required
                  minLength={2}
                  maxLength={50}
                  pattern="[a-zA-Z0-9_-]+"
                  title="Alphanumeric characters, underscores, and hyphens only"
                />
              </div>
            </div>

            {/* Password */}
            <div className="flex flex-col">
              <label className="font-label text-xs uppercase tracking-widest text-on-surface-variant font-semibold mb-2 ml-1">
                Password
              </label>
              <div className="bg-surface-container-high rounded-xl px-4 py-3 flex items-center focus-within:bg-surface-container-lowest transition-colors">
                <span className="material-symbols-outlined text-primary/60 mr-3">
                  lock
                </span>
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="At least 6 characters"
                  className="bg-transparent border-none focus:ring-0 focus:outline-none w-full font-medium text-on-surface"
                  required
                  minLength={6}
                />
              </div>
            </div>

            {/* Confirm Password */}
            <div className="flex flex-col">
              <label className="font-label text-xs uppercase tracking-widest text-on-surface-variant font-semibold mb-2 ml-1">
                Confirm Password
              </label>
              <div className="bg-surface-container-high rounded-xl px-4 py-3 flex items-center focus-within:bg-surface-container-lowest transition-colors">
                <span className="material-symbols-outlined text-primary/60 mr-3">
                  lock
                </span>
                <input
                  type="password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  placeholder="Repeat your password"
                  className="bg-transparent border-none focus:ring-0 focus:outline-none w-full font-medium text-on-surface"
                  required
                  minLength={6}
                />
              </div>
            </div>

            {/* Security Question */}
            <div className="flex flex-col">
              <label className="font-label text-xs uppercase tracking-widest text-on-surface-variant font-semibold mb-2 ml-1">
                Security Question
              </label>
              <div className="bg-surface-container-high rounded-xl px-4 py-3 focus-within:bg-surface-container-lowest transition-colors">
                <select
                  value={selectedQuestion}
                  onChange={(e) => setSelectedQuestion(e.target.value)}
                  className="bg-transparent border-none focus:ring-0 focus:outline-none w-full font-medium text-on-surface"
                  required
                >
                  <option value="">Select a question...</option>
                  {presetQuestions.map((q) => (
                    <option key={q} value={q}>
                      {q}
                    </option>
                  ))}
                  <option value={CUSTOM_QUESTION}>Write your own...</option>
                </select>
              </div>
              {selectedQuestion === CUSTOM_QUESTION && (
                <div className="bg-surface-container-high rounded-xl px-4 py-3 mt-2 focus-within:bg-surface-container-lowest transition-colors">
                  <input
                    type="text"
                    value={customQuestion}
                    onChange={(e) => setCustomQuestion(e.target.value)}
                    placeholder="Type your custom question"
                    className="bg-transparent border-none focus:ring-0 focus:outline-none w-full font-medium text-on-surface"
                    required
                    maxLength={300}
                  />
                </div>
              )}
            </div>

            {/* Security Answer */}
            <div className="flex flex-col">
              <label className="font-label text-xs uppercase tracking-widest text-on-surface-variant font-semibold mb-2 ml-1">
                Security Answer
              </label>
              <div className="bg-surface-container-high rounded-xl px-4 py-3 flex items-center focus-within:bg-surface-container-lowest transition-colors">
                <span className="material-symbols-outlined text-primary/60 mr-3">
                  key
                </span>
                <input
                  type="text"
                  value={securityAnswer}
                  onChange={(e) => setSecurityAnswer(e.target.value)}
                  placeholder="Your answer (case-insensitive)"
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
              <span className="material-symbols-outlined">person_add</span>
              {submitting ? "Creating..." : "Create Account"}
            </button>
          </form>

          <div className="text-center mt-6">
            <button
              onClick={() => navigate("/")}
              className="text-primary font-bold text-sm hover:underline"
            >
              Already have an account? Sign In
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
