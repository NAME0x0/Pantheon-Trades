"use client";

/**
 * Lightweight EIP-1193 wallet-connect demo for the replay page.
 *
 * Deliberately zero-dep — no viem / wagmi / web3modal. Uses the
 * injected provider (MetaMask / Rabby / Coinbase wallet / etc.) and
 * exercises three flows:
 *
 *   1. Request accounts (eth_requestAccounts).
 *   2. Read + display the current chainId, with a one-click switch
 *      to Arc Testnet (5042002 / 0x4cef52). Add-network fallback if
 *      the wallet rejects with the "chain not added" code 4902.
 *   3. Sign a SIWE-style message (personal_sign). Read-only — we
 *      never submit the signature anywhere; the point is to prove
 *      the message format works in the user's wallet.
 *
 * Nothing here calls the production API or spends gas. It is a
 * front-end demo of the same plumbing the real ``apps/api`` SIWE
 * route uses.
 */

import { useCallback, useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

// Arc Testnet (Pantheon's deploy target). Hex is required by EIP-3326.
const ARC_CHAIN_ID = 5042002;
const ARC_CHAIN_HEX = `0x${ARC_CHAIN_ID.toString(16)}`;
const ARC_RPC = "https://rpc.testnet.arc.network";
const ARC_EXPLORER = "https://testnet.arcscan.app";

interface Eip1193 {
  request: (args: { method: string; params?: unknown[] | object }) => Promise<unknown>;
  on?: (event: string, handler: (...args: unknown[]) => void) => void;
  removeListener?: (event: string, handler: (...args: unknown[]) => void) => void;
}

declare global {
  interface Window {
    ethereum?: Eip1193;
  }
}

function shorten(addr: string): string {
  return addr.length >= 10 ? `${addr.slice(0, 6)}…${addr.slice(-4)}` : addr;
}

export function WalletConnect() {
  const [address, setAddress] = useState<string | null>(null);
  const [chainId, setChainId] = useState<string | null>(null);
  const [signature, setSignature] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const provider = typeof window !== "undefined" ? window.ethereum : undefined;
  const onArc = chainId === ARC_CHAIN_HEX;

  useEffect(() => {
    if (!provider) return;
    const onAccounts = (...args: unknown[]) => {
      const accounts = args[0] as string[] | undefined;
      setAddress(accounts && accounts.length > 0 ? accounts[0] : null);
    };
    const onChain = (...args: unknown[]) => setChainId(args[0] as string);
    provider.on?.("accountsChanged", onAccounts);
    provider.on?.("chainChanged", onChain);
    // Pull current state on mount.
    provider.request({ method: "eth_accounts" })
      .then((accts) => onAccounts(accts))
      .catch(() => undefined);
    provider.request({ method: "eth_chainId" })
      .then((c) => onChain(c))
      .catch(() => undefined);
    return () => {
      provider.removeListener?.("accountsChanged", onAccounts);
      provider.removeListener?.("chainChanged", onChain);
    };
  }, [provider]);

  const connect = useCallback(async () => {
    if (!provider) {
      setErr("No injected wallet detected. Install MetaMask or Rabby and refresh.");
      return;
    }
    setErr(null);
    setBusy(true);
    try {
      const accounts = (await provider.request({
        method: "eth_requestAccounts",
      })) as string[];
      setAddress(accounts[0]);
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : String(e);
      setErr(`Connect rejected: ${msg}`);
    } finally {
      setBusy(false);
    }
  }, [provider]);

  const switchToArc = useCallback(async () => {
    if (!provider) return;
    setErr(null);
    setBusy(true);
    try {
      await provider.request({
        method: "wallet_switchEthereumChain",
        params: [{ chainId: ARC_CHAIN_HEX }],
      });
    } catch (e: unknown) {
      // 4902 = unknown chain → add it then re-switch.
      const code = (e as { code?: number }).code;
      if (code === 4902) {
        try {
          await provider.request({
            method: "wallet_addEthereumChain",
            params: [{
              chainId: ARC_CHAIN_HEX,
              chainName: "Arc Testnet",
              nativeCurrency: { name: "USDC", symbol: "USDC", decimals: 6 },
              rpcUrls: [ARC_RPC],
              blockExplorerUrls: [ARC_EXPLORER],
            }],
          });
        } catch (e2: unknown) {
          const msg = e2 instanceof Error ? e2.message : String(e2);
          setErr(`Add Arc Testnet failed: ${msg}`);
        }
      } else {
        const msg = e instanceof Error ? e.message : String(e);
        setErr(`Switch chain rejected: ${msg}`);
      }
    } finally {
      setBusy(false);
    }
  }, [provider]);

  const sign = useCallback(async () => {
    if (!provider || !address) return;
    setErr(null);
    setSignature(null);
    setBusy(true);
    // Minimal SIWE-style envelope. The real apps/api SIWE route validates
    // domain, nonce, issued-at, and expiration; this demo signs the same
    // human-readable string so users can see the shape in their wallet.
    const nonce = Math.random().toString(36).slice(2, 10);
    const issued = new Date().toISOString();
    const message =
      `pantheon-trades-web.vercel.app wants you to sign in with your Ethereum account:\n` +
      `${address}\n\n` +
      `Confirm wallet connection to the Pantheon demo. This signature is read-only and never sent to any server.\n\n` +
      `URI: https://pantheon-trades-web.vercel.app/demo\n` +
      `Version: 1\n` +
      `Chain ID: ${ARC_CHAIN_ID}\n` +
      `Nonce: ${nonce}\n` +
      `Issued At: ${issued}`;
    try {
      const sig = (await provider.request({
        method: "personal_sign",
        params: [message, address],
      })) as string;
      setSignature(sig);
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : String(e);
      setErr(`Sign rejected: ${msg}`);
    } finally {
      setBusy(false);
    }
  }, [provider, address]);

  return (
    <Card className="border-primary/30">
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm uppercase tracking-wider text-primary">
            Connect a wallet
          </CardTitle>
          {address && (
            <Badge variant={onArc ? "success" : "warning"}>
              {onArc ? "Arc Testnet" : `Wrong network (${chainId ?? "?"})`}
            </Badge>
          )}
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        <p className="text-xs text-muted-foreground">
          Optional — read-only. The demo never transacts. Connect to see the same SIWE
          flow the production API uses, switch to Arc Testnet so the on-chain Proof of
          Restraint records render properly, and sign a verification message in your
          wallet.
        </p>

        {!provider && (
          <p className="text-sm text-rose-300">
            No injected wallet detected. Install MetaMask, Rabby, Coinbase Wallet, or
            similar and reload.
          </p>
        )}

        {provider && !address && (
          <Button onClick={connect} disabled={busy}>
            {busy ? "Connecting…" : "Connect wallet"}
          </Button>
        )}

        {address && (
          <div className="space-y-2">
            <div className="flex flex-wrap items-center gap-2 text-sm">
              <span className="font-mono text-muted-foreground">connected</span>
              <code className="rounded bg-muted/30 px-2 py-0.5 font-mono text-primary">
                {shorten(address)}
              </code>
            </div>
            <div className="flex flex-wrap gap-2">
              {!onArc && (
                <Button variant="outline" onClick={switchToArc} disabled={busy}>
                  Switch to Arc Testnet
                </Button>
              )}
              <Button variant="outline" onClick={sign} disabled={busy}>
                {busy ? "Signing…" : "Sign verification message"}
              </Button>
              <Button
                variant="ghost"
                onClick={() => {
                  setAddress(null);
                  setSignature(null);
                }}
                disabled={busy}
              >
                Forget
              </Button>
            </div>
          </div>
        )}

        {signature && (
          <details className="rounded-md border border-primary/20 bg-card/40 p-3 text-xs">
            <summary className="cursor-pointer font-mono uppercase tracking-wider text-primary">
              Signature (read-only)
            </summary>
            <code className="mt-2 block break-all font-mono text-muted-foreground">
              {signature}
            </code>
          </details>
        )}

        {err && (
          <p className="rounded-md border border-rose-500/40 bg-rose-500/10 p-2 text-xs text-rose-200">
            {err}
          </p>
        )}
      </CardContent>
    </Card>
  );
}
