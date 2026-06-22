"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { supabaseClient } from "@/lib/supabaseClient";

type Stage = "credentials" | "mfa";

export default function LoginPage() {
  const router = useRouter();
  const [stage, setStage] = useState<Stage>("credentials");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [code, setCode] = useState("");
  const [factorId, setFactorId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleCredentialsSubmit(event: React.FormEvent) {
    event.preventDefault();
    setError(null);
    setSubmitting(true);

    const { error: signInError } = await supabaseClient.auth.signInWithPassword({
      email,
      password,
    });

    if (signInError) {
      setError("Invalid email or password.");
      setSubmitting(false);
      return;
    }

    const { data: aalData, error: aalError } =
      await supabaseClient.auth.mfa.getAuthenticatorAssuranceLevel();

    if (aalError) {
      setError(aalError.message);
      setSubmitting(false);
      return;
    }

    if (aalData.nextLevel === "aal2" && aalData.currentLevel !== "aal2") {
      const { data: factorsData, error: factorsError } =
        await supabaseClient.auth.mfa.listFactors();
      if (factorsError || !factorsData?.totp?.[0]) {
        setError("This account requires 2FA but no authenticator is enrolled.");
        setSubmitting(false);
        return;
      }
      setFactorId(factorsData.totp[0].id);
      setStage("mfa");
      setSubmitting(false);
      return;
    }

    router.replace("/dashboard");
  }

  async function handleMfaSubmit(event: React.FormEvent) {
    event.preventDefault();
    if (!factorId) return;
    setError(null);
    setSubmitting(true);

    const { error: verifyError } = await supabaseClient.auth.mfa.challengeAndVerify({
      factorId,
      code,
    });

    if (verifyError) {
      setError("Incorrect code. Try again.");
      setSubmitting(false);
      return;
    }

    router.replace("/dashboard");
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50">
      <div className="w-full max-w-sm rounded-lg border border-gray-200 bg-white p-8 shadow-sm">
        <h1 className="text-lg font-semibold text-gray-900">Personal Finance AI</h1>
        <p className="mt-1 text-xs text-gray-500">Allowlisted accounts only · 2FA required</p>

        {stage === "credentials" && (
          <form onSubmit={handleCredentialsSubmit} className="mt-6 space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700">Email</label>
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700">Password</label>
              <input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
              />
            </div>
            {error && <p className="text-sm text-red-600">{error}</p>}
            <button
              type="submit"
              disabled={submitting}
              className="w-full rounded-md bg-gray-900 px-3 py-2 text-sm font-medium text-white disabled:opacity-50"
            >
              {submitting ? "Signing in…" : "Log in"}
            </button>
          </form>
        )}

        {stage === "mfa" && (
          <form onSubmit={handleMfaSubmit} className="mt-6 space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700">
                Authenticator code
              </label>
              <input
                type="text"
                inputMode="numeric"
                required
                value={code}
                onChange={(e) => setCode(e.target.value)}
                className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
                placeholder="6-digit code"
              />
            </div>
            {error && <p className="text-sm text-red-600">{error}</p>}
            <button
              type="submit"
              disabled={submitting}
              className="w-full rounded-md bg-gray-900 px-3 py-2 text-sm font-medium text-white disabled:opacity-50"
            >
              {submitting ? "Verifying…" : "Verify"}
            </button>
          </form>
        )}
      </div>
    </div>
  );
}
