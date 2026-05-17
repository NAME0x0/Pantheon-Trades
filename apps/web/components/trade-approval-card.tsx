"use client";

/**
 * Trade-approval UI for the first-N manual approval phase.
 *
 * Renders a single proposed trade with:
 *   - thesis summary, council votes, sizing breakdown
 *   - Approve / Reject / Resize controls
 *   - keyboard shortcuts: a (approve), r (reject), e (edit size)
 *
 * Submission posts to /api/trades/{thesis_id}/approve|reject|resize.
 * The component is purely presentational — the caller owns fetching.
 */

import * as React from "react";

export interface ProposedTrade {
  thesis_id: string;
  market_id: string;
  question: string;
  direction: "YES" | "NO";
  size_pct: number;
  size_usdc: number;
  mid_price: number;
  confidence: number;
  edge_abs: number;
  approve_count: number;
  reject_count: number;
  abstain_count: number;
  notes?: string;
}

export interface TradeApprovalCardProps {
  trade: ProposedTrade;
  onApprove: (thesis_id: string) => Promise<void> | void;
  onReject: (thesis_id: string, reason: string) => Promise<void> | void;
  onResize: (thesis_id: string, new_size_pct: number) => Promise<void> | void;
  disabled?: boolean;
}

export function TradeApprovalCard({ trade, onApprove, onReject, onResize, disabled }: TradeApprovalCardProps) {
  const [busy, setBusy] = React.useState(false);
  const [mode, setMode] = React.useState<"idle" | "reject" | "resize">("idle");
  const [reason, setReason] = React.useState("");
  const [newSize, setNewSize] = React.useState((trade.size_pct * 100).toFixed(2));

  const wrap = async (fn: () => Promise<void> | void) => {
    setBusy(true);
    try {
      await fn();
    } finally {
      setBusy(false);
    }
  };

  // Keyboard shortcuts: a/r/e while idle.
  React.useEffect(() => {
    if (disabled) return;
    const handler = (e: KeyboardEvent) => {
      if (mode !== "idle") return;
      const target = e.target as HTMLElement | null;
      if (target && ["INPUT", "TEXTAREA"].includes(target.tagName)) return;
      if (e.key === "a") wrap(() => onApprove(trade.thesis_id));
      else if (e.key === "r") setMode("reject");
      else if (e.key === "e") setMode("resize");
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [mode, disabled, onApprove, trade.thesis_id]);

  return (
    <div className="rounded-lg border border-border/60 bg-card/60 p-5 space-y-4">
      <div className="flex items-start justify-between gap-3">
        <div className="space-y-1">
          <div className="text-xs uppercase tracking-wider text-muted-foreground">
            Pending Approval · {trade.market_id}
          </div>
          <h3 className="font-display text-lg leading-snug text-foreground">{trade.question}</h3>
        </div>
        <Badge direction={trade.direction} />
      </div>

      <dl className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-sm">
        <Stat label="Mid" value={`${(trade.mid_price * 100).toFixed(1)}¢`} />
        <Stat label="Edge" value={`${(trade.edge_abs * 100).toFixed(2)}pp`} />
        <Stat label="Size" value={`${(trade.size_pct * 100).toFixed(2)}% · $${trade.size_usdc.toFixed(0)}`} />
        <Stat label="Confidence" value={trade.confidence.toFixed(2)} />
      </dl>

      <div className="text-xs text-muted-foreground">
        Council vote: <span className="text-emerald-400">{trade.approve_count} approve</span> ·{" "}
        <span className="text-rose-400">{trade.reject_count} reject</span> · {trade.abstain_count} abstain
      </div>

      {trade.notes ? (
        <p className="rounded border border-border/40 bg-muted/20 px-3 py-2 text-xs text-muted-foreground">
          {trade.notes}
        </p>
      ) : null}

      {mode === "idle" && (
        <div className="flex flex-wrap gap-2">
          <button
            className="rounded bg-emerald-600/20 px-4 py-2 text-sm text-emerald-300 hover:bg-emerald-600/30 disabled:opacity-50"
            disabled={busy || disabled}
            onClick={() => wrap(() => onApprove(trade.thesis_id))}
          >
            Approve <kbd className="ml-2 text-xs opacity-60">A</kbd>
          </button>
          <button
            className="rounded bg-rose-600/20 px-4 py-2 text-sm text-rose-300 hover:bg-rose-600/30 disabled:opacity-50"
            disabled={busy || disabled}
            onClick={() => setMode("reject")}
          >
            Reject <kbd className="ml-2 text-xs opacity-60">R</kbd>
          </button>
          <button
            className="rounded bg-amber-600/20 px-4 py-2 text-sm text-amber-300 hover:bg-amber-600/30 disabled:opacity-50"
            disabled={busy || disabled}
            onClick={() => setMode("resize")}
          >
            Resize <kbd className="ml-2 text-xs opacity-60">E</kbd>
          </button>
        </div>
      )}

      {mode === "reject" && (
        <div className="space-y-2">
          <label className="block text-xs uppercase tracking-wider text-muted-foreground">
            Reason
          </label>
          <textarea
            className="w-full rounded border border-border/60 bg-card/40 px-3 py-2 text-sm"
            rows={2}
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            placeholder="why this trade should not happen"
          />
          <div className="flex gap-2">
            <button
              className="rounded bg-rose-600/30 px-4 py-2 text-sm text-rose-200 hover:bg-rose-600/40 disabled:opacity-50"
              disabled={busy || disabled || reason.trim().length < 3}
              onClick={() => wrap(() => onReject(trade.thesis_id, reason.trim()))}
            >
              Confirm reject
            </button>
            <button
              className="rounded border border-border/40 px-4 py-2 text-sm hover:bg-muted/20"
              onClick={() => setMode("idle")}
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {mode === "resize" && (
        <div className="space-y-2">
          <label className="block text-xs uppercase tracking-wider text-muted-foreground">
            New size (% of book)
          </label>
          <input
            type="number"
            min={0.1}
            max={10}
            step={0.05}
            className="w-32 rounded border border-border/60 bg-card/40 px-3 py-2 text-sm"
            value={newSize}
            onChange={(e) => setNewSize(e.target.value)}
          />
          <div className="flex gap-2">
            <button
              className="rounded bg-amber-600/30 px-4 py-2 text-sm text-amber-200 hover:bg-amber-600/40 disabled:opacity-50"
              disabled={busy || disabled}
              onClick={() => wrap(() => onResize(trade.thesis_id, Number(newSize) / 100))}
            >
              Confirm resize
            </button>
            <button
              className="rounded border border-border/40 px-4 py-2 text-sm hover:bg-muted/20"
              onClick={() => setMode("idle")}
            >
              Cancel
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

function Badge({ direction }: { direction: "YES" | "NO" }) {
  const isYes = direction === "YES";
  const cls = isYes
    ? "bg-emerald-600/20 text-emerald-300 border-emerald-700/40"
    : "bg-rose-600/20 text-rose-300 border-rose-700/40";
  return <span className={`rounded border px-2 py-1 text-xs font-mono ${cls}`}>{direction}</span>;
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-[10px] uppercase tracking-widest text-muted-foreground">{label}</dt>
      <dd className="font-mono text-sm text-foreground">{value}</dd>
    </div>
  );
}
