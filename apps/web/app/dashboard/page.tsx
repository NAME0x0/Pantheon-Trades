import Link from "next/link";

import { Reveal } from "@/components/anim";

/**
 * Dashboard is a server component that talks directly to Arc Testnet
 * via public JSON-RPC. No FastAPI backend required — the page always
 * has live data the moment the chain is reachable.
 *
 * Three blocks:
 *
 *   1. Arc chain status (block height, gas, chain id).
 *   2. On-chain restraint feed — eth_getLogs against the deployed
 *      ProofOfRestraint contract, filtered to the Restrained event sig.
 *   3. Pantheon static facts (council size, veto count, etc.).
 *
 * Revalidates every 30 s so the page is always recent without hammering
 * the RPC.
 */

export const revalidate = 30;

const ARC_RPC = "https://rpc.testnet.arc.network";
const ARCSCAN = "https://testnet.arcscan.app";
const POR_CONTRACT = "0x4b35CE4Bf71B976205f60Fda1EBAb82eD4D34895";
const VW_CONTRACT =
  process.env.NEXT_PUBLIC_VISITOR_WITNESS_ADDRESS ??
  "0xF35B1fa5A6026C61C187881eA17d77F97Cd1AFA7";
const ARC_CHAIN_ID = 5042002;

// keccak256("Restrained(uint256,bytes32,string,string,string,address,uint64)")
const RESTRAINED_TOPIC =
  "0x86071ec604ff0d442a66a1c44538c3b91553fb8f55fdc5ea10f8841ba6412f0a";
// keccak256("Visited(uint256,address,bytes32,string,uint64)")
const VISITED_TOPIC =
  "0x5c375a1d562e39c417094b3e0b5fe2e49202eaaa8fc9cd51306d6caed52102ce";

// Arc Testnet RPC caps eth_getLogs at a 10,000-block range (error -32614).
// We scan multiple chunks back from head to cover ~14 hours of testnet
// activity — enough to surface every recent restraint + visitor witness
// without tripping the rate-limit.
const LOG_CHUNK = 9_500;
const LOG_CHUNK_COUNT = 6;
const LOG_SCAN_WINDOW = LOG_CHUNK * LOG_CHUNK_COUNT;

type ArcStatus = {
  block: number | null;
  gasWei: number | null;
  chainId: number | null;
};

type RestraintLog = {
  txHash: string;
  blockNumber: number;
  signalHash: string;
  onchainProofId: number;
};

type VisitLog = {
  txHash: string;
  blockNumber: number;
  visitor: string;
  proofId: number;
};

async function rpc<T>(method: string, params: unknown[]): Promise<T | null> {
  try {
    const r = await fetch(ARC_RPC, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ jsonrpc: "2.0", id: 1, method, params }),
      // Next.js cache hint; lib.dom RequestInit doesn't model `next`.
      next: { revalidate: 20 },
    } as RequestInit & { next?: { revalidate?: number } });
    if (!r.ok) return null;
    const j = await r.json();
    return j.result ?? null;
  } catch {
    return null;
  }
}

async function fetchArcStatus(): Promise<ArcStatus> {
  const [bn, gp, ch] = await Promise.all([
    rpc<string>("eth_blockNumber", []),
    rpc<string>("eth_gasPrice", []),
    rpc<string>("eth_chainId", []),
  ]);
  return {
    block: bn ? parseInt(bn, 16) : null,
    gasWei: gp ? parseInt(gp, 16) : null,
    chainId: ch ? parseInt(ch, 16) : null,
  };
}

type RawLog = {
  transactionHash: string;
  blockNumber: string;
  topics: string[];
};

async function fetchLogsChunked(
  address: string,
  topic: string,
  latestBlock: number,
): Promise<RawLog[]> {
  // Build chunk windows back from latest until LOG_SCAN_WINDOW exhausted.
  const ranges: Array<{ from: number; to: number }> = [];
  let head = latestBlock;
  for (let i = 0; i < LOG_CHUNK_COUNT && head > 0; i++) {
    const from = Math.max(head - LOG_CHUNK + 1, 0);
    ranges.push({ from, to: head });
    head = from - 1;
  }
  const results = await Promise.all(
    ranges.map((r) =>
      rpc<RawLog[]>("eth_getLogs", [
        {
          address,
          topics: [topic],
          fromBlock: "0x" + r.from.toString(16),
          toBlock: "0x" + r.to.toString(16),
        },
      ]),
    ),
  );
  return results.flatMap((r) => (Array.isArray(r) ? r : []));
}

async function fetchRecentRestraints(latestBlock: number | null): Promise<RestraintLog[]> {
  if (latestBlock === null) return [];
  const logs = await fetchLogsChunked(POR_CONTRACT, RESTRAINED_TOPIC, latestBlock);
  return logs
    .map((l) => ({
      txHash: l.transactionHash,
      blockNumber: parseInt(l.blockNumber, 16),
      signalHash: l.topics[2] ?? "0x",
      onchainProofId: parseInt(l.topics[1] ?? "0x0", 16),
    }))
    .sort((a, b) => b.blockNumber - a.blockNumber);
}

async function fetchRecentVisits(latestBlock: number | null): Promise<VisitLog[]> {
  if (latestBlock === null) return [];
  const logs = await fetchLogsChunked(VW_CONTRACT, VISITED_TOPIC, latestBlock);
  return logs
    .map((l) => ({
      txHash: l.transactionHash,
      blockNumber: parseInt(l.blockNumber, 16),
      proofId: parseInt(l.topics[1] ?? "0x0", 16),
      // visitor is indexed topic[2], stored as 32-byte-padded address
      visitor: "0x" + (l.topics[2] ?? "0x").slice(-40),
    }))
    .sort((a, b) => b.blockNumber - a.blockNumber);
}

export default async function Dashboard() {
  const arc = await fetchArcStatus();
  const [restraints, visits] = await Promise.all([
    fetchRecentRestraints(arc.block),
    fetchRecentVisits(arc.block),
  ]);
  const liveRpc = arc.block !== null;

  return (
    <section className="space-y-16 py-12">
      {/* ── Header ─────────────────────────────────────────────────── */}
      <Reveal>
        <div>
          <div className="display flex items-center gap-3 text-[10px] uppercase tracking-[0.45em] text-primary">
            <span
              className={`inline-block size-1.5 rounded-full ${
                liveRpc ? "bg-emerald-400 animate-pulse" : "bg-amber-500"
              }`}
            />
            {liveRpc ? "Arc Testnet · live" : "Arc Testnet · unreachable"}
          </div>
          <h1 className="display mt-4 text-6xl font-medium leading-[1.05] tracking-[-0.01em] text-foreground md:text-7xl">
            Dashboard
          </h1>
          <p className="serif mt-4 max-w-2xl text-xl leading-[1.7] text-muted-foreground">
            Direct read of Arc Testnet — block height, gas, and every{" "}
            <code className="mono text-primary">Restrained</code> event ever
            written by the council. No backend dependency.
          </p>
          <p className="mt-3 max-w-2xl rounded-md border border-amber-500/30 bg-amber-500/5 p-3 font-mono text-xs leading-[1.5] text-amber-200/85">
            ⚠ Testnet only. Contracts have passed{" "}
            <code className="text-amber-100">forge test</code> + Halmos symbolic
            verification on <code className="text-amber-100">ProofOfRestraint</code> and{" "}
            <code className="text-amber-100">PantheonConstitution</code>, but have not
            undergone external audit. Do not deploy to mainnet without one.
          </p>
        </div>
      </Reveal>

      {/* ── Chain stats ────────────────────────────────────────────── */}
      <Reveal delay={0.05}>
        <div className="grid gap-px overflow-hidden rounded-2xl border border-primary/15 sm:grid-cols-2 lg:grid-cols-5">
          <Stat
            label="Block height"
            value={arc.block !== null ? arc.block.toLocaleString() : "—"}
          />
          <Stat
            label="Gas price"
            value={arc.gasWei !== null ? `${(arc.gasWei / 1e9).toFixed(2)} gwei` : "—"}
          />
          <Stat
            label="Chain id"
            value={arc.chainId !== null ? arc.chainId.toString() : "—"}
            note={arc.chainId === ARC_CHAIN_ID ? "verified" : undefined}
          />
          <Stat label="Restraints anchored" value={restraints.length.toString()} />
          <Stat label="Demo visits" value={visits.length.toString()} />
        </div>
      </Reveal>

      {/* ── Restraint feed ─────────────────────────────────────────── */}
      <Reveal delay={0.1}>
        <div>
          <div className="display mb-4 flex items-baseline justify-between text-[10px] uppercase tracking-[0.32em] text-muted-foreground">
            <span>On-chain restraint feed</span>
            <a
              href={`${ARCSCAN}/address/${POR_CONTRACT}`}
              target="_blank"
              rel="noopener noreferrer"
              className="text-primary transition-colors hover:text-primary/70"
            >
              ProofOfRestraint contract ↗
            </a>
          </div>
          {restraints.length === 0 ? (
            <div className="serif rounded-2xl border border-primary/15 bg-card/40 p-10 text-center text-muted-foreground">
              {liveRpc
                ? "No restraint witnesses anchored in the last ~16 hours. The council has approved everything we've seen so far — or simply has not been running."
                : "Arc RPC unreachable. Retry in a moment."}
            </div>
          ) : (
            <ol className="space-y-px overflow-hidden rounded-2xl border border-primary/15">
              {restraints.map((r) => (
                <li
                  key={r.txHash}
                  className="group grid grid-cols-[5rem_1fr_auto] items-center gap-4 bg-card/40 px-6 py-5 transition-colors hover:bg-primary/[0.04]"
                >
                  <span className="display text-2xl font-semibold text-primary">
                    #{r.onchainProofId}
                  </span>
                  <div>
                    <div className="display text-[10px] uppercase tracking-[0.28em] text-muted-foreground">
                      Block {r.blockNumber.toLocaleString()}
                    </div>
                    <div className="mono mt-1 truncate text-sm text-primary">
                      {r.txHash}
                    </div>
                  </div>
                  <a
                    href={`${ARCSCAN}/tx/${r.txHash}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="display shrink-0 text-[10px] uppercase tracking-[0.32em] text-muted-foreground transition-colors hover:text-primary"
                  >
                    Verify ↗
                  </a>
                </li>
              ))}
            </ol>
          )}
        </div>
      </Reveal>

      {/* ── Visitor witness feed — populated by /demo's WitnessButton */}
      <Reveal delay={0.15}>
        <div>
          <div className="display mb-4 flex items-baseline justify-between text-[10px] uppercase tracking-[0.32em] text-muted-foreground">
            <span>Visitor witness feed</span>
            <a
              href={`${ARCSCAN}/address/${VW_CONTRACT}`}
              target="_blank"
              rel="noopener noreferrer"
              className="text-primary transition-colors hover:text-primary/70"
            >
              VisitorWitness contract ↗
            </a>
          </div>
          {visits.length === 0 ? (
            <div className="serif rounded-2xl border border-primary/15 bg-card/40 p-10 text-center text-muted-foreground">
              <p>
                Nobody has run the demo on Arc yet.{" "}
                <a
                  href="/demo"
                  className="text-primary underline-offset-4 hover:underline"
                >
                  Open the demo
                </a>
                , connect a wallet, and witness your visit on chain — it shows
                up here within seconds.
              </p>
            </div>
          ) : (
            <ol className="space-y-px overflow-hidden rounded-2xl border border-primary/15">
              {visits.map((v) => (
                <li
                  key={v.txHash}
                  className="group grid grid-cols-[5rem_1fr_auto] items-center gap-4 bg-card/40 px-6 py-5 transition-colors hover:bg-primary/[0.04]"
                >
                  <span className="display text-2xl font-semibold text-primary">
                    #{v.proofId}
                  </span>
                  <div>
                    <div className="display text-[10px] uppercase tracking-[0.28em] text-muted-foreground">
                      Block {v.blockNumber.toLocaleString()} · visitor{" "}
                      <span className="mono text-primary/80">
                        {v.visitor.slice(0, 6)}…{v.visitor.slice(-4)}
                      </span>
                    </div>
                    <div className="mono mt-1 truncate text-sm text-primary">
                      {v.txHash}
                    </div>
                  </div>
                  <a
                    href={`${ARCSCAN}/tx/${v.txHash}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="display shrink-0 text-[10px] uppercase tracking-[0.32em] text-muted-foreground transition-colors hover:text-primary"
                  >
                    Verify ↗
                  </a>
                </li>
              ))}
            </ol>
          )}
        </div>
      </Reveal>

      {/* ── Static facts ───────────────────────────────────────────── */}
      <Reveal delay={0.15}>
        <div>
          <div className="display mb-4 text-[10px] uppercase tracking-[0.32em] text-muted-foreground">
            Constants
          </div>
          <div className="grid gap-px overflow-hidden rounded-2xl border border-primary/15 sm:grid-cols-2 lg:grid-cols-4">
            <Constant k="Council agents" v="11" />
            <Constant k="Veto powers" v="2 — Zeus, Solon" />
            <Constant k="Rounds of debate" v="4" />
            <Constant k="Foundry tests" v="51 / 51" />
            <Constant k="Quorum" v="≥ 7 participating" />
            <Constant k="Approval threshold" v="≥ 60% weighted" />
            <Constant k="Max position" v="5% of NAV (half-Kelly)" />
            <Constant k="Native gas" v="USDC" />
          </div>
        </div>
      </Reveal>

      <Reveal delay={0.2}>
        <div className="text-center">
          <Link
            href="/demo"
            className="display inline-flex items-center gap-2 text-[11px] uppercase tracking-[0.32em] text-primary transition-opacity hover:opacity-80"
          >
            Watch a council deliberation ↗
          </Link>
        </div>
      </Reveal>
    </section>
  );
}

function Stat({
  label,
  value,
  note,
}: {
  label: string;
  value: string;
  note?: string;
}) {
  return (
    <div className="bg-card/40 p-6">
      <div className="display text-[10px] uppercase tracking-[0.35em] text-muted-foreground">
        {label}
      </div>
      <div className="display mt-3 text-3xl font-semibold text-primary">{value}</div>
      {note && (
        <div className="mono mt-1 text-[10px] uppercase tracking-[0.22em] text-emerald-400/80">
          ✓ {note}
        </div>
      )}
    </div>
  );
}

function Constant({ k, v }: { k: string; v: string }) {
  return (
    <div className="bg-card/40 p-5">
      <div className="display text-[10px] uppercase tracking-[0.32em] text-muted-foreground">
        {k}
      </div>
      <div className="display mt-2 text-lg tracking-[0.04em] text-foreground">
        {v}
      </div>
    </div>
  );
}
