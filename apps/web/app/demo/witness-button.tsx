"use client";

/**
 * WitnessButton — visitor-driven on-chain proof that they ran the demo.
 *
 * Calls `VisitorWitness.witness(bytes32 visitHash, string scenario)` on
 * Arc Testnet via the injected EIP-1193 provider (same plumbing as the
 * neighbouring WalletConnect card — zero deps, no wagmi/viem). The
 * visitHash is a SHA-256 of (address || scenario || now) computed by
 * Web Crypto, so each click is unique without needing a Keccak library.
 *
 * Flow:
 *
 *   idle → connecting → switching → signing → pending → confirmed
 *                                                  └─→ error
 *
 * The contract is permissionless (no role gating) — see contracts/src/
 * VisitorWitness.sol. Gas cost on Arc Testnet is fractions of a cent in
 * USDC (Arc's native gas token). Faucet link below the button.
 */

import { useCallback, useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

const ARC_CHAIN_ID = 5042002;
const ARC_CHAIN_HEX = `0x${ARC_CHAIN_ID.toString(16)}`;
const ARC_RPC = "https://rpc.testnet.arc.network";
const ARC_EXPLORER = "https://testnet.arcscan.app";

const VISITOR_WITNESS_ADDRESS =
  process.env.NEXT_PUBLIC_VISITOR_WITNESS_ADDRESS ??
  "0xF35B1fa5A6026C61C187881eA17d77F97Cd1AFA7";

// keccak("witness(bytes32,string)")[:4] — computed via `cast sig`.
const WITNESS_SELECTOR = "639637ce";
// keccak("visits(address)")[:4] — public mapping getter on VisitorWitness.
const VISITS_SELECTOR = "f5bcc01b";

async function fetchWalletVisitCount(address: string): Promise<number | null> {
  // ABI-encode visits(address): selector + 32-byte left-padded address.
  const padded = address.toLowerCase().replace(/^0x/, "").padStart(64, "0");
  const data = "0x" + VISITS_SELECTOR + padded;
  try {
    const r = await fetch(ARC_RPC, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({
        jsonrpc: "2.0",
        id: 1,
        method: "eth_call",
        params: [{ to: VISITOR_WITNESS_ADDRESS, data }, "latest"],
      }),
    });
    const j = await r.json();
    if (!j?.result || j.result === "0x") return 0;
    const n = parseInt(j.result, 16);
    return Number.isFinite(n) ? n : null;
  } catch {
    return null;
  }
}

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

type Status =
  | { kind: "idle" }
  | { kind: "connecting" }
  | { kind: "switching" }
  | { kind: "signing" }
  | { kind: "pending"; txHash: string }
  | { kind: "confirmed"; txHash: string; proofId: number | null }
  | { kind: "error"; message: string };

async function sha256Hex(input: string): Promise<string> {
  const data = new TextEncoder().encode(input);
  const buf = await crypto.subtle.digest("SHA-256", data);
  return Array.from(new Uint8Array(buf))
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
}

function encodeWitnessCall(visitHashHex: string, scenario: string): string {
  // ABI-encode witness(bytes32,string). Tail-encoded string at offset 0x40.
  const hashHex = visitHashHex.replace(/^0x/, "").padStart(64, "0");
  if (hashHex.length !== 64) throw new Error("visitHash must be 32 bytes");
  const offset =
    "0000000000000000000000000000000000000000000000000000000000000040";
  const utf8 = new TextEncoder().encode(scenario);
  const lenHex = utf8.length.toString(16).padStart(64, "0");
  const padBytes = utf8.length === 0 ? 32 : (32 - (utf8.length % 32)) % 32;
  const bytesHex =
    Array.from(utf8)
      .map((b) => b.toString(16).padStart(2, "0"))
      .join("") + "00".repeat(padBytes);
  return "0x" + WITNESS_SELECTOR + hashHex + offset + lenHex + bytesHex;
}

async function waitForReceipt(txHash: string, timeoutMs = 60_000): Promise<{
  status: "success" | "reverted" | "unknown";
  blockNumber: number | null;
  proofId: number | null;
}> {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    try {
      const r = await fetch(ARC_RPC, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          jsonrpc: "2.0",
          id: 1,
          method: "eth_getTransactionReceipt",
          params: [txHash],
        }),
      });
      const j = await r.json();
      const rec = j.result;
      if (rec && rec.blockNumber) {
        const status =
          rec.status === "0x1" ? "success" : rec.status === "0x0" ? "reverted" : "unknown";
        const blockNumber = parseInt(rec.blockNumber, 16);
        // First topic of Visited event is proofId (indexed uint256).
        let proofId: number | null = null;
        if (Array.isArray(rec.logs) && rec.logs.length > 0) {
          const ev = rec.logs.find(
            (l: { address: string; topics?: string[] }) =>
              l.address?.toLowerCase() === VISITOR_WITNESS_ADDRESS.toLowerCase(),
          );
          const idTopic = ev?.topics?.[1];
          if (idTopic) proofId = parseInt(idTopic, 16);
        }
        return { status, blockNumber, proofId };
      }
    } catch {
      // swallow — keep polling
    }
    await new Promise((res) => setTimeout(res, 1800));
  }
  return { status: "unknown", blockNumber: null, proofId: null };
}

export function WitnessButton({
  scenario,
  title = "Run this demo on Arc Testnet",
  helper = "What this proves: the Arc Testnet pipeline works for visitors end-to-end (wallet → contract → arcscan → dashboard feed). What it does NOT prove: that the council picks profitable trades. See the empirical backtest panel below for that. Cost: fractions of a cent in testnet USDC.",
}: {
  scenario: string;
  title?: string;
  helper?: string;
}) {
  const [status, setStatus] = useState<Status>({ kind: "idle" });
  const [address, setAddress] = useState<string | null>(null);
  const [chainId, setChainId] = useState<string | null>(null);
  const [walletVisits, setWalletVisits] = useState<number | null>(null);

  const provider = typeof window !== "undefined" ? window.ethereum : undefined;
  const onArc = chainId === ARC_CHAIN_HEX;

  // Refresh the connected wallet's on-chain visit tally whenever the
  // address changes OR a new witness tx confirms. This is the visitor's
  // personal proof tally — independent of the global feed.
  useEffect(() => {
    if (!address) {
      setWalletVisits(null);
      return;
    }
    let cancelled = false;
    fetchWalletVisitCount(address).then((n) => {
      if (!cancelled) setWalletVisits(n);
    });
    return () => {
      cancelled = true;
    };
  }, [address, status.kind]);

  useEffect(() => {
    if (!provider) return;
    const onAccounts = (...args: unknown[]) => {
      const accts = args[0] as string[] | undefined;
      setAddress(accts && accts.length > 0 ? accts[0] : null);
    };
    const onChain = (...args: unknown[]) => setChainId(args[0] as string);
    provider.on?.("accountsChanged", onAccounts);
    provider.on?.("chainChanged", onChain);
    provider.request({ method: "eth_accounts" })
      .then((a) => onAccounts(a))
      .catch(() => undefined);
    provider.request({ method: "eth_chainId" })
      .then((c) => onChain(c))
      .catch(() => undefined);
    return () => {
      provider.removeListener?.("accountsChanged", onAccounts);
      provider.removeListener?.("chainChanged", onChain);
    };
  }, [provider]);

  const submit = useCallback(async () => {
    if (!provider) {
      setStatus({ kind: "error", message: "No injected wallet. Install MetaMask and refresh." });
      return;
    }
    try {
      // 1. Connect if needed.
      setStatus({ kind: "connecting" });
      const accts = (await provider.request({
        method: "eth_requestAccounts",
      })) as string[];
      const from = accts[0];
      setAddress(from);

      // 2. Switch to Arc if not already there.
      const currentChain = (await provider.request({
        method: "eth_chainId",
      })) as string;
      setChainId(currentChain);
      if (currentChain !== ARC_CHAIN_HEX) {
        setStatus({ kind: "switching" });
        try {
          await provider.request({
            method: "wallet_switchEthereumChain",
            params: [{ chainId: ARC_CHAIN_HEX }],
          });
        } catch (e: unknown) {
          if ((e as { code?: number }).code === 4902) {
            await provider.request({
              method: "wallet_addEthereumChain",
              params: [
                {
                  chainId: ARC_CHAIN_HEX,
                  chainName: "Arc Testnet",
                  nativeCurrency: { name: "USDC", symbol: "USDC", decimals: 6 },
                  rpcUrls: [ARC_RPC],
                  blockExplorerUrls: [ARC_EXPLORER],
                },
              ],
            });
          } else {
            throw e;
          }
        }
      }

      // 3. Build call data — visitHash = SHA-256(address || scenario || nowMs).
      setStatus({ kind: "signing" });
      const visitHashHex = await sha256Hex(`${from}-${scenario}-${Date.now()}`);
      const data = encodeWitnessCall(visitHashHex, scenario);

      // 4. Send tx. Gas is auto-estimated by the wallet.
      const txHash = (await provider.request({
        method: "eth_sendTransaction",
        params: [
          {
            from,
            to: VISITOR_WITNESS_ADDRESS,
            data,
          },
        ],
      })) as string;
      setStatus({ kind: "pending", txHash });

      // 5. Poll for receipt.
      const receipt = await waitForReceipt(txHash);
      if (receipt.status === "reverted") {
        setStatus({ kind: "error", message: "Tx reverted on Arc. Out of USDC?" });
      } else {
        setStatus({ kind: "confirmed", txHash, proofId: receipt.proofId });
      }
    } catch (e: unknown) {
      const code = (e as { code?: number }).code;
      const message =
        code === 4001
          ? "You rejected the request in your wallet."
          : e instanceof Error
            ? e.message
            : String(e);
      setStatus({ kind: "error", message });
    }
  }, [provider, scenario]);

  return (
    <Card className="border-primary/40 bg-card/50">
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm uppercase tracking-wider text-primary">
            {title}
          </CardTitle>
          {address && (
            <Badge variant={onArc ? "success" : "warning"}>
              {onArc ? "Arc Testnet" : `Chain ${chainId ?? "?"}`}
            </Badge>
          )}
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <p className="text-sm leading-[1.6] text-muted-foreground">{helper}</p>

        {address && walletVisits !== null && (
          <div className="flex items-baseline justify-between rounded-md border border-primary/20 bg-card/60 p-3 text-sm">
            <span className="font-mono uppercase tracking-wider text-muted-foreground">
              {address.slice(0, 6)}…{address.slice(-4)} · on-chain witnesses
            </span>
            <span className="font-mono text-lg font-semibold text-primary">
              {walletVisits}
            </span>
          </div>
        )}

        {!provider && (
          <p className="rounded-md border border-amber-500/40 bg-amber-500/10 p-3 text-sm text-amber-200">
            No injected wallet detected. Install MetaMask, Rabby, or Coinbase Wallet and
            reload.
          </p>
        )}

        {provider && status.kind !== "confirmed" && (
          <Button
            onClick={submit}
            disabled={
              status.kind === "connecting" ||
              status.kind === "switching" ||
              status.kind === "signing" ||
              status.kind === "pending"
            }
          >
            {status.kind === "connecting" && "Connecting…"}
            {status.kind === "switching" && "Switching to Arc…"}
            {status.kind === "signing" && "Sign in wallet…"}
            {status.kind === "pending" && "Confirming on Arc…"}
            {(status.kind === "idle" || status.kind === "error") && "Witness my visit on Arc"}
          </Button>
        )}

        {status.kind === "pending" && (
          <p className="text-sm text-primary/80">
            Pending — waiting for first block confirmation…
          </p>
        )}

        {status.kind === "confirmed" && (
          <div className="space-y-3 rounded-md border border-emerald-500/40 bg-emerald-500/10 p-4 text-sm text-emerald-100">
            <div className="flex items-baseline justify-between">
              <span className="font-mono uppercase tracking-wider text-emerald-300">
                ✓ Recorded on Arc Testnet
              </span>
              {status.proofId !== null && (
                <span className="font-mono text-xs text-emerald-200">
                  proof #{status.proofId}
                </span>
              )}
            </div>
            <p className="leading-[1.6] text-emerald-100/85">
              Your wallet wrote a permanent {`"`}I ran the Pantheon demo{`"`} record to the
              VisitorWitness contract. The dashboard restraint feed will reflect it on
              its next 30 s revalidate.
            </p>
            <a
              href={`${ARC_EXPLORER}/tx/${status.txHash}`}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 font-mono text-xs text-emerald-300 underline-offset-4 hover:underline"
            >
              {status.txHash.slice(0, 14)}…{status.txHash.slice(-10)} ↗
            </a>
          </div>
        )}

        {status.kind === "error" && (
          <p className="rounded-md border border-rose-500/40 bg-rose-500/10 p-3 text-sm text-rose-200">
            {status.message}
          </p>
        )}
      </CardContent>
    </Card>
  );
}
