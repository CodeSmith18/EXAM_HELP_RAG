import { FormEvent, useState } from "react";
import { Loader2, LogIn, UserPlus } from "lucide-react";
import { loginAccount, registerAccount } from "../api";
import { UserOut } from "../types";

type AuthMode = "login" | "register";

interface AuthPageProps {
  onAuthenticated: (user: UserOut) => void;
}

export function AuthPage({ onAuthenticated }: AuthPageProps) {
  const [mode, setMode] = useState<AuthMode>("login");
  const [email, setEmail] = useState("");
  const [fullName, setFullName] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setLoading(true);
    setError("");
    try {
      const response =
        mode === "login"
          ? await loginAccount(email.trim(), password)
          : await registerAccount(email.trim(), password, fullName.trim());
      onAuthenticated(response.user);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not authenticate.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center px-4 py-8">
      <section className="card w-full max-w-md p-5">
        <div className="mb-5 flex items-center gap-3">
          <span className="inline-flex h-11 w-11 items-center justify-center rounded-lg bg-teal/10 text-teal">
            {mode === "login" ? <LogIn size={22} aria-hidden="true" /> : <UserPlus size={22} aria-hidden="true" />}
          </span>
          <div>
            <h1 className="text-xl font-bold text-ink">ExamPrep RAG</h1>
            <p className="text-sm text-slate-500">{mode === "login" ? "Sign in" : "Create account"}</p>
          </div>
        </div>

        <div className="segmented mb-5 grid-cols-2">
          <button type="button" className={`segment ${mode === "login" ? "segment-active" : ""}`} onClick={() => setMode("login")}>
            Sign In
          </button>
          <button
            type="button"
            className={`segment ${mode === "register" ? "segment-active" : ""}`}
            onClick={() => setMode("register")}
          >
            Register
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          {mode === "register" ? (
            <div>
              <label htmlFor="fullName" className="label mb-2 block">
                Name
              </label>
              <input
                id="fullName"
                className="input"
                value={fullName}
                onChange={(event) => setFullName(event.target.value)}
                placeholder="Optional"
              />
            </div>
          ) : null}

          <div>
            <label htmlFor="email" className="label mb-2 block">
              Email
            </label>
            <input
              id="email"
              className="input"
              type="email"
              autoComplete="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              placeholder="you@example.com"
              required
            />
          </div>

          <div>
            <label htmlFor="password" className="label mb-2 block">
              Password
            </label>
            <input
              id="password"
              className="input"
              type="password"
              autoComplete={mode === "login" ? "current-password" : "new-password"}
              minLength={mode === "register" ? 8 : 1}
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              required
            />
          </div>

          {error ? <p className="text-sm font-medium text-red-600">{error}</p> : null}

          <button className="btn-primary w-full" disabled={loading}>
            {loading ? <Loader2 size={17} className="animate-spin" aria-hidden="true" /> : <LogIn size={17} aria-hidden="true" />}
            {mode === "login" ? "Sign In" : "Create Account"}
          </button>
        </form>
      </section>
    </main>
  );
}
