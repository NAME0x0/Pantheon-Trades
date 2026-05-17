"use client";

/**
 * Brier-ranked agent leaderboard.
 *
 * Pure-presentational table — caller fetches the rows and passes them
 * in. Sort defaults to credibility weight descending so the top
 * performers headline. Visual cues:
 *   - mini Brier bar per agent (lower = better, inverted fill)
 *   - sign-coloured 30d delta vs cohort
 *   - medals for top 3 by credibility
 */

import * as React from "react";

export interface AgentRow {
  agent: string;
  prediction_count: number;
  brier: number;          // lower is better
  sharpe: number;
  win_rate: number;       // 0..1
  credibility_weight: number; // 0..1+
  delta_30d?: number;     // change in credibility over trailing 30 days
}

export interface AgentLeaderboardProps {
  rows: AgentRow[];
  className?: string;
}

type SortKey = "credibility_weight" | "brier" | "sharpe" | "win_rate" | "prediction_count";

export function AgentLeaderboard({ rows, className }: AgentLeaderboardProps) {
  const [sortKey, setSortKey] = React.useState<SortKey>("credibility_weight");
  const [asc, setAsc] = React.useState(false);

  const sorted = React.useMemo(() => {
    const out = [...rows].sort((a, b) => {
      const av = (a[sortKey] ?? 0) as number;
      const bv = (b[sortKey] ?? 0) as number;
      return asc ? av - bv : bv - av;
    });
    return out;
  }, [rows, sortKey, asc]);

  const maxBrier = Math.max(...rows.map((r) => r.brier), 0.5);

  const onSort = (key: SortKey) => {
    if (key === sortKey) {
      setAsc(!asc);
    } else {
      setSortKey(key);
      setAsc(key === "brier");
    }
  };

  if (sorted.length === 0) {
    return (
      <div className={className}>
        <p className="text-sm text-muted-foreground">No agent rows yet.</p>
      </div>
    );
  }

  return (
    <div className={`overflow-x-auto ${className ?? ""}`}>
      <table className="w-full text-sm">
        <thead className="text-xs uppercase tracking-wider text-muted-foreground">
          <tr className="border-b border-border/40">
            <th className="px-3 py-2 text-left">Rank</th>
            <th className="px-3 py-2 text-left">Agent</th>
            <SortHeader label="N" k="prediction_count" sortKey={sortKey} asc={asc} onSort={onSort} />
            <SortHeader label="Brier" k="brier" sortKey={sortKey} asc={asc} onSort={onSort} />
            <SortHeader label="Sharpe" k="sharpe" sortKey={sortKey} asc={asc} onSort={onSort} />
            <SortHeader label="Win%" k="win_rate" sortKey={sortKey} asc={asc} onSort={onSort} />
            <SortHeader label="Weight" k="credibility_weight" sortKey={sortKey} asc={asc} onSort={onSort} />
            <th className="px-3 py-2 text-right">D30d</th>
          </tr>
        </thead>
        <tbody>
          {sorted.map((row, i) => (
            <tr key={row.agent} className="border-b border-border/20 hover:bg-muted/10">
              <td className="px-3 py-2 font-mono text-foreground">
                {i === 0 ? "1st" : i === 1 ? "2nd" : i === 2 ? "3rd" : `#${i + 1}`}
              </td>
              <td className="px-3 py-2 font-medium text-foreground">{row.agent}</td>
              <td className="px-3 py-2 text-right text-muted-foreground">{row.prediction_count}</td>
              <td className="px-3 py-2 text-right">
                <BrierCell value={row.brier} max={maxBrier} />
              </td>
              <td className="px-3 py-2 text-right font-mono">{row.sharpe.toFixed(2)}</td>
              <td className="px-3 py-2 text-right font-mono">{(row.win_rate * 100).toFixed(1)}%</td>
              <td className="px-3 py-2 text-right font-mono">{row.credibility_weight.toFixed(3)}</td>
              <td className="px-3 py-2 text-right">
                <DeltaCell value={row.delta_30d} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function SortHeader({
  label,
  k,
  sortKey,
  asc,
  onSort,
}: {
  label: string;
  k: SortKey;
  sortKey: SortKey;
  asc: boolean;
  onSort: (k: SortKey) => void;
}) {
  const active = sortKey === k;
  return (
    <th
      className={`px-3 py-2 text-right cursor-pointer select-none ${active ? "text-foreground" : ""}`}
      onClick={() => onSort(k)}
    >
      <span>
        {label}
        {active ? (asc ? " up" : " down") : ""}
      </span>
    </th>
  );
}

function BrierCell({ value, max }: { value: number; max: number }) {
  const pct = Math.min(1, value / max);
  return (
    <div className="flex flex-col items-end gap-1">
      <span className="font-mono text-xs">{value.toFixed(4)}</span>
      <div className="h-1 w-20 rounded bg-muted/30 overflow-hidden">
        <div className="h-full bg-emerald-500/70" style={{ width: `${(1 - pct) * 100}%` }} />
      </div>
    </div>
  );
}

function DeltaCell({ value }: { value: number | undefined }) {
  if (value === undefined || value === null) return <span className="text-muted-foreground">.</span>;
  const cls = value > 0 ? "text-emerald-400" : value < 0 ? "text-rose-400" : "text-muted-foreground";
  const sign = value > 0 ? "+" : "";
  return <span className={`font-mono text-xs ${cls}`}>{sign}{value.toFixed(3)}</span>;
}
