import Link from "next/link";

import type { RestraintSummary } from "../lib/api";

const REASON_LABEL: Record<string, string> = {
  STALENESS: "stale data",
  STALENESS_HARD: "stale data (hard)",
  SPREAD: "spread too wide",
  SPREAD_HARD: "spread too wide (hard)",
  LIQUIDITY: "weak liquidity",
  EDGE: "insufficient edge",
  DAYS_TOO_CLOSE: "resolution too soon",
  DAYS_TOO_FAR: "resolution too far",
  LOW_CONFIDENCE: "council confidence below floor",
  DRAWDOWN_PAUSE: "drawdown circuit-breaker",
  MAX_POSITIONS: "open-position cap reached",
  CATEGORY_EXPOSURE: "category exposure cap",
  TOTAL_EXPOSURE: "portfolio exposure cap",
  SUB_THRESHOLD_KELLY: "half-Kelly below floor",
  NO_EDGE: "no actionable edge",
  ZEUS_VETO: "Zeus constitutional veto",
  SOLON_VETO: "Solon compliance veto",
  POSITION_HARD: "size exceeds hard cap",
};

const REASON_AGENT: Record<string, string> = {
  ZEUS_VETO: "Zeus",
  SOLON_VETO: "Solon",
  LOW_CONFIDENCE: "Council",
  DRAWDOWN_PAUSE: "Olympus",
};

const ARCSCAN_BASE =
  process.env.NEXT_PUBLIC_ARCSCAN_URL ?? "https://testnet.arcscan.app";

const PROOF_OF_RESTRAINT_ADDRESS =
  process.env.NEXT_PUBLIC_PROOF_OF_RESTRAINT_ADDRESS ??
  "0x4b35CE4Bf71B976205f60Fda1EBAb82eD4D34895";

export function RestraintCard({ entry }: { entry: RestraintSummary }) {
  const label = REASON_LABEL[entry.reason_code] ?? entry.reason_code.toLowerCase();
  const vetoedBy = REASON_AGENT[entry.reason_code] ?? "Areopagus";
  return (
    <article className="rounded-lg border border-pantheon-gold/40 bg-pantheon-ink/70 p-5">
      <header className="flex items-baseline justify-between">
        <div className="font-mono text-xs uppercase tracking-[0.2em] text-pantheon-gold/80">
          Areopagus veto
        </div>
        <span className="rounded bg-red-500/10 px-2 py-0.5 text-xs font-mono text-red-300">
          NO TRADE
        </span>
      </header>
      <dl className="mt-3 grid grid-cols-1 gap-y-2 text-sm md:grid-cols-2">
        <dt className="text-pantheon-marble/70">Market</dt>
        <dd className="font-mono text-pantheon-parchment break-all">{entry.market_id}</dd>

        <dt className="text-pantheon-marble/70">Reason</dt>
        <dd>
          <span className="rounded bg-pantheon-gold/10 px-2 py-0.5 font-mono text-pantheon-gold">
            {entry.reason_code}
          </span>
          <span className="ml-2 text-pantheon-parchment">{label}</span>
        </dd>

        <dt className="text-pantheon-marble/70">Vetoed by</dt>
        <dd className="font-mono text-pantheon-parchment">{vetoedBy}</dd>

        <dt className="text-pantheon-marble/70">Signal id</dt>
        <dd className="font-mono text-xs text-pantheon-marble">{entry.signal_id}</dd>

        <dt className="text-pantheon-marble/70">Signal hash</dt>
        <dd className="font-mono text-xs text-pantheon-marble break-all">
          {entry.signal_hash}
        </dd>

        <dt className="text-pantheon-marble/70">Arc proof</dt>
        <dd>
          {entry.explorer_url || entry.tx_hash ? (
            <Link
              href={entry.explorer_url ?? `${ARCSCAN_BASE}/tx/${entry.tx_hash}`}
              target="_blank"
              className="font-mono text-xs text-pantheon-gold underline-offset-4 hover:underline"
            >
              tx {entry.tx_hash ? `${entry.tx_hash.slice(0, 10)}…${entry.tx_hash.slice(-6)}` : "on arcscan"}
            </Link>
          ) : (
            <Link
              href={`${ARCSCAN_BASE}/address/${PROOF_OF_RESTRAINT_ADDRESS}`}
              target="_blank"
              className="font-mono text-xs text-pantheon-marble underline-offset-4 hover:underline"
              title="No on-chain anchor for this proof yet — link points at the contract instead."
            >
              contract on arcscan
            </Link>
          )}
        </dd>

        {entry.onchain_proof_id != null && (
          <>
            <dt className="text-pantheon-marble/70">On-chain id</dt>
            <dd className="font-mono text-pantheon-gold">#{entry.onchain_proof_id}</dd>
          </>
        )}

        <dt className="text-pantheon-marble/70">When</dt>
        <dd className="font-mono text-xs text-pantheon-marble">
          {new Date(entry.created_at).toLocaleString()}
        </dd>
      </dl>
      {entry.note && (
        <p className="mt-3 rounded border border-pantheon-gold/20 bg-pantheon-ink p-2 text-xs text-pantheon-marble">
          {entry.note}
        </p>
      )}
    </article>
  );
}
