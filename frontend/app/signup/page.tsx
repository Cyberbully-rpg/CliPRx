"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";
import { supabase } from "@/lib/supabase";
import Button from "@/components/Button";
import ErrorBanner from "@/components/ErrorBanner";

export default function SignupPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [submitted, setSubmitted] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    const { error } = await supabase.auth.signUp({ email, password });
    setLoading(false);
    if (error) {
      setError(error.message);
      return;
    }
    setSubmitted(true);
  }

  if (submitted) {
    return (
      <div className="auth-shell">
        <div className="auth-card">
          <div className="auth-logo">
            <span style={{ width: 8, height: 8, borderRadius: 2, background: "var(--signal-running)" }} />
            CliPRx
          </div>
          <h1 className="auth-title">Check your email</h1>
          <p className="auth-sub">
            We sent a confirmation link to <strong style={{ color: "var(--ink-700)" }}>{email}</strong>. Confirm
            it, then log in below.
          </p>
          <Button as="a" href="/login" variant="dark" style={{ width: "100%" }}>
            Go to log in
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="auth-shell">
      <div className="auth-card">
        <Link href="/#top" className="auth-logo">
          <span style={{ width: 8, height: 8, borderRadius: 2, background: "var(--signal-running)" }} />
          CliPRx
        </Link>
        <h1 className="auth-title">Create an account</h1>
        <p className="auth-sub">One CSV. A few seconds. A ranked plan.</p>

        <form onSubmit={handleSubmit}>
          <div className="auth-field">
            <label className="field-label" htmlFor="email">Email</label>
            <input
              id="email"
              type="email"
              required
              autoComplete="email"
              className="field-input"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@company.com"
            />
          </div>
          <div className="auth-field">
            <label className="field-label" htmlFor="password">Password</label>
            <input
              id="password"
              type="password"
              required
              minLength={6}
              autoComplete="new-password"
              className="field-input"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="At least 6 characters"
            />
          </div>

          {error && (
            <div style={{ marginBottom: 16 }}>
              <ErrorBanner message={error} />
            </div>
          )}

          <Button type="submit" variant="dark" disabled={loading} style={{ width: "100%" }}>
            {loading ? "Creating account…" : "Sign up"}
          </Button>
        </form>

        <div className="auth-footer">
          Already have an account? <Link href="/login">Log in</Link>
        </div>
      </div>
    </div>
  );
}
