"use client";

import { useState } from "react";

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

type Step = "idle" | "nonce" | "signing" | "verifying" | "done" | "error";

export default function SignInPage() {
  const [address, setAddress] = useState("");
  const [step, setStep] = useState<Step>("idle");
  const [error, setError] = useState<string | null>(null);

  async function start() {
    setError(null);
    if (!/^0x[0-9a-fA-F]{40}$/.test(address)) {
      setError("Enter a 42-char 0x address.");
      return;
    }
    setStep("nonce");
    try {
      const nonceRes = await fetch(`${API_BASE}/auth/nonce?address=${address}`);
      if (!nonceRes.ok) throw new Error(`nonce ${nonceRes.status}`);
      const { nonce } = await nonceRes.json();
      const message = buildSiweMessage(address, nonce);

      setStep("signing");
      const eth = (window as any).ethereum;
      if (!eth) throw new Error("no injected wallet found");
      const signature = await eth.request({
        method: "personal_sign",
        params: [message, address],
      });

      setStep("verifying");
      const verifyRes = await fetch(`${API_BASE}/auth/verify`, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ message, signature }),
      });
      if (!verifyRes.ok) throw new Error(`verify ${verifyRes.status}`);
      const { token, address: addr, roles } = await verifyRes.json();
      document.cookie = `pantheon_token=${token}; path=/; samesite=lax`;
      localStorage.setItem("pantheon_address", addr);
      localStorage.setItem("pantheon_roles", JSON.stringify(roles));
      setStep("done");
      window.location.href = "/";
    } catch (e: any) {
      setError(String(e?.message ?? e));
      setStep("error");
    }
  }

  return (
    <section className="mx-auto max-w-md">
      <h1 className="font-mono text-3xl text-pantheon-gold">Sign in</h1>
      <p className="mt-2 text-pantheon-marble">
        Sign-In With Ethereum. Your wallet signs a one-shot nonce; we issue an
        itsdangerous session token. No password, no email.
      </p>
      <div className="mt-6 space-y-3">
        <label className="block text-sm text-pantheon-marble">
          Wallet address
          <input
            value={address}
            onChange={(e) => setAddress(e.target.value)}
            placeholder="0x…"
            className="mt-1 w-full rounded border border-pantheon-gold/30 bg-pantheon-ink p-2 font-mono text-pantheon-parchment"
          />
        </label>
        <button
          onClick={start}
          disabled={step !== "idle" && step !== "error"}
          className="rounded bg-pantheon-gold px-4 py-2 font-mono text-pantheon-ink disabled:opacity-50"
        >
          {step === "idle" || step === "error" ? "Sign in" : step + "…"}
        </button>
        {error && <p className="text-sm text-red-300">{error}</p>}
      </div>
    </section>
  );
}

function buildSiweMessage(address: string, nonce: string): string {
  const host = typeof window !== "undefined" ? window.location.host : "pantheon-trades.local";
  const origin = typeof window !== "undefined" ? window.location.origin : `https://${host}`;
  const issued = new Date().toISOString();
  return [
    `${host} wants you to sign in with your Ethereum account:`,
    address,
    "",
    "Sign in to Pantheon Trades.",
    "",
    `URI: ${origin}`,
    "Version: 1",
    "Chain ID: 5042002",
    `Nonce: ${nonce}`,
    `Issued At: ${issued}`,
  ].join("\n");
}
