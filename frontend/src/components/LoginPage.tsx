"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { login, registerUser } from "@/lib/auth";

export const LoginPage = () => {
  const router = useRouter();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError(null);
    setIsSubmitting(true);

    const success = await login(username, password);
    if (success) {
      router.push("/");
      return;
    }

    setError("Invalid username or password.");
    setIsSubmitting(false);
  };

  const handleCreateUser = async () => {
    setError(null);
    setIsSubmitting(true);

    const success = await registerUser(username, password);
    if (success) {
      router.push("/");
      return;
    }

    setError("Could not create account. Try another username.");
    setIsSubmitting(false);
  };

  const disableActions = isSubmitting || !username.trim() || !password.trim();

  return (
    <main className="relative min-h-screen overflow-hidden bg-[var(--surface)] px-6 py-12 text-[var(--navy-dark)]">
      <div className="pointer-events-none absolute left-0 top-0 h-[360px] w-[360px] -translate-x-1/3 -translate-y-1/3 rounded-full bg-[radial-gradient(circle,_rgba(32,157,215,0.22)_0%,_rgba(32,157,215,0.04)_55%,_transparent_75%)]" />
      <div className="pointer-events-none absolute right-0 bottom-0 h-[420px] w-[420px] translate-x-1/4 translate-y-1/4 rounded-full bg-[radial-gradient(circle,_rgba(117,57,145,0.18)_0%,_rgba(117,57,145,0.04)_55%,_transparent_80%)]" />

      <div className="relative mx-auto w-full max-w-xl rounded-[40px] border border-[var(--stroke)] bg-white/90 p-10 shadow-[var(--shadow)] backdrop-blur">
        <div className="mb-10">
          <p className="text-xs font-semibold uppercase tracking-[0.35em] text-[var(--gray-text)]">
            Welcome back
          </p>
          <h1 className="mt-4 text-4xl font-semibold leading-tight text-[var(--navy-dark)]">
            Sign in to your Kanban Studio
          </h1>
          <p className="mt-4 text-sm leading-6 text-[var(--gray-text)]">
            Sign in with an existing user or create a new account.
          </p>
        </div>

        <form className="grid gap-6" onSubmit={handleSubmit}>
          <div className="grid gap-4 rounded-[28px] border border-[var(--stroke)] bg-[var(--surface)] p-6">
            <label className="grid gap-2 text-sm font-semibold text-[var(--navy-dark)]">
              Username
              <input
                className="rounded-2xl border border-[var(--stroke)] bg-white px-4 py-3 text-sm text-[var(--navy-dark)] outline-none transition focus:border-[var(--primary-blue)] focus:ring-2 focus:ring-[rgba(32,157,215,0.15)]"
                value={username}
                onChange={(event) => setUsername(event.target.value)}
                placeholder="user"
                aria-label="Username"
                disabled={isSubmitting}
              />
            </label>
            <label className="grid gap-2 text-sm font-semibold text-[var(--navy-dark)]">
              Password
              <input
                type="password"
                className="rounded-2xl border border-[var(--stroke)] bg-white px-4 py-3 text-sm text-[var(--navy-dark)] outline-none transition focus:border-[var(--primary-blue)] focus:ring-2 focus:ring-[rgba(32,157,215,0.15)]"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                placeholder="password"
                aria-label="Password"
                disabled={isSubmitting}
              />
            </label>
          </div>

          {error ? <p className="rounded-2xl bg-red-50 px-4 py-3 text-sm text-red-600">{error}</p> : null}

          <div className="grid gap-3 sm:grid-cols-2">
            <button
              type="submit"
              className="inline-flex justify-center rounded-2xl bg-[var(--primary-blue)] px-6 py-3 text-sm font-semibold text-white shadow-[0_18px_40px_rgba(32,157,215,0.18)] transition hover:bg-[var(--navy-dark)] disabled:cursor-not-allowed disabled:opacity-70"
              disabled={disableActions}
            >
              {isSubmitting ? "Signing in..." : "Sign in"}
            </button>
            <button
              type="button"
              className="inline-flex justify-center rounded-2xl border border-[var(--stroke)] bg-white px-6 py-3 text-sm font-semibold text-[var(--navy-dark)] transition hover:bg-[var(--surface)] disabled:cursor-not-allowed disabled:opacity-70"
              onClick={handleCreateUser}
              disabled={disableActions}
            >
              {isSubmitting ? "Working..." : "Create account"}
            </button>
          </div>
        </form>
      </div>
    </main>
  );
};
