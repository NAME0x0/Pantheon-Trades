"use client";

/**
 * Render the checked-in CoinGecko paper-trade artifact as a compact
 * dashboard on the demo page. Everything is computed client-side from
 * the static JSON at /demo/coingecko-paper.json — no API, no fetch
 * to a backend, deterministic across rebuilds.
 *
 * Layout:
 *   - Summary stats row (trades fired, win rate, realised PnL, fees,
 *     max DD, ending equity).
 *   - Pure-SVG equity curve from settled PnLs.
 *   - Trade ribbon — colour-coded wins / losses, hover to inspect.
 *
 * The point is to make the harness from scripts/live_paper_trade_coingecko.py
 * legible without making the visitor read JSON.
 */

import { useEffect, useMemo, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";

type Tick = {
  seq: number;
  price: number;
  fetched_at: string;
  ret_log: number | null;
  council_p: number | null;
  market_p: number;
  edge: number | null;
  direction: string | null;
  size_pct: number;
  kelly_fraction: number;
  reason: string;
  fill_price: number | null;
  settled_pnl_usdc: number | null;
  settle_outcome_yes: number | null;
};

type Artifact = {
  schema: string;
  started_at: string;
  finished_at: string;
  config: {
    mode: string;
    edge_threshold: number;
    momentum_k: number;
    bankroll_usdc: number;
    depth_usdc: number;
    asset: string;
    quote: string;
    history_days?: string | null;
  };
  ticks: Tick[];
  summary: {
    trades_fired: number;
    trades_settled: number;
    wins: number;
    losses: number;
    win_rate: number;
    realised_pnl_usdc: number;
    return_pct: number;
    fees_paid_usdc: number;
    ending_equity_usdc: number;
    max_drawdown_pct: number;
    sharpe_raw_per_tick: number;
  };
};

function pct(n: number, digits = 2): string {
  return `${(n * 100).toFixed(digits)}%`;
}

function usd(n: number): string {
  const sign = n < 0 ? "-" : "";
  return `${sign}$${Math.abs(n).toFixed(2)}`;
}

export function CoinGeckoPanel() {
  const [data, setData] = useState<Artifact | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    fetch("/demo/coingecko-paper.json")
      .then((r) => {
        if (!r.ok) throw new Error(`fetch ${r.status}`);
        return r.json();
      })
      .then((j) => setData(j as Artifact))
      .catch((e) => setErr(String(e)));
  }, []);

  const equityCurve = useMemo(() => {
    if (!data) return [] as { x: number; y: number; pnl: number }[];
    const series: { x: number; y: number; pnl: number }[] = [];
    let cum = 0;
    for (const t of data.ticks) {
      if (t.settled_pnl_usdc !== null) {
        cum += t.settled_pnl_usdc;
        series.push({
          x: t.seq,
          y: data.config.bankroll_usdc + cum,
          pnl: t.settled_pnl_usdc,
        });
      }
    }
    return series;
  }, [data]);

  if (err) {
    return (
      <Card className="border-destructive/40 bg-destructive/10">
        <CardContent className="p-6 text-sm text-destructive">
          Could not load CoinGecko artifact: {err}
        </CardContent>
      </Card>
    );
  }
  if (!data) {
    return (
      <Card>
        <CardContent className="p-8 text-center text-muted-foreground">
          Loading paper-trade artifact…
        </CardContent>
      </Card>
    );
  }

  const s = data.summary;
  const winRateGood = s.win_rate >= 0.5;
  const pnlGood = s.realised_pnl_usdc >= 0;

  return (
    <Card className="border-primary/30">
      <CardHeader className="space-y-2 pb-3">
        <div className="flex flex-wrap items-baseline justify-between gap-3">
          <div>
            <div className="display text-[10px] uppercase tracking-[0.4em] text-primary/70">
              Live data · CoinGecko · 7-day window
            </div>
            <CardTitle className="display mt-1 text-xl tracking-[0.06em] text-foreground">
              Paper trade — BTC/USD hourly bars
            </CardTitle>
          </div>
          <Badge variant={pnlGood ? "success" : "destructive"}>
            {pnlGood ? "Net positive" : "Net negative"} · {pct(s.return_pct)}
          </Badge>
        </div>
        <p className="serif max-w-3xl text-sm italic text-muted-foreground">
          Pulled from CoinGecko&apos;s free <code className="mono">/coins/&#123;id&#125;/market_chart</code>{" "}
          endpoint. Each bar synthesises a binary &ldquo;will the next bar
          print higher?&rdquo; question. Position sizing is the real
          production half-Kelly. Fills go through the real{" "}
          <code className="mono">strategos.paper.PaperBook</code> with
          half-spread + slippage + 2% taker fees. Settles on the next bar.
        </p>
      </CardHeader>
      <CardContent className="space-y-6">
        <div className="grid grid-cols-2 gap-3 md:grid-cols-3 lg:grid-cols-6">
          <Stat label="Trades fired" value={String(s.trades_fired)} />
          <Stat
            label="Win rate"
            value={pct(s.win_rate, 1)}
            tone={winRateGood ? "good" : "bad"}
          />
          <Stat
            label="Realised PnL"
            value={usd(s.realised_pnl_usdc)}
            tone={pnlGood ? "good" : "bad"}
          />
          <Stat label="Fees paid" value={usd(s.fees_paid_usdc)} tone="bad" />
          <Stat label="Max drawdown" value={pct(s.max_drawdown_pct)} tone="bad" />
          <Stat label="Ending equity" value={usd(s.ending_equity_usdc)} />
        </div>

        <EquityChart
          series={equityCurve}
          bankroll={data.config.bankroll_usdc}
        />

        <TradeRibbon ticks={data.ticks} />

        <details className="rounded-md border border-primary/20 bg-card/40 p-3">
          <summary className="cursor-pointer text-xs uppercase tracking-wider text-primary">
            Run configuration
          </summary>
          <dl className="mt-3 grid gap-x-6 gap-y-1 text-xs sm:grid-cols-2 lg:grid-cols-3">
            <Cfg k="mode" v={data.config.mode} />
            <Cfg k="bars" v={String(data.ticks.length)} />
            <Cfg k="history days" v={data.config.history_days ?? "—"} />
            <Cfg k="edge threshold" v={pct(data.config.edge_threshold)} />
            <Cfg k="momentum lookback" v={`${data.config.momentum_k} bars`} />
            <Cfg k="bankroll" v={usd(data.config.bankroll_usdc)} />
            <Cfg k="synthetic depth" v={usd(data.config.depth_usdc)} />
            <Cfg k="asset" v={`${data.config.asset.toUpperCase()}/${data.config.quote.toUpperCase()}`} />
            <Cfg k="sharpe (raw, per-tick)" v={s.sharpe_raw_per_tick.toFixed(3)} />
          </dl>
        </details>

        <p className="rounded-md border border-amber-500/30 bg-amber-900/10 p-3 text-xs text-amber-200/90">
          <strong className="font-mono">Honest disclaimer:</strong> the harness uses a
          toy momentum estimator in place of the council. Naive momentum on every
          tick does not survive 4% round-trip fees — that is by design, so the
          artifact is honest, not flattering. Replace the estimator with an actual
          Boule deliberation (and the LLM bill that goes with it) for the real
          comparison.
        </p>
      </CardContent>
    </Card>
  );
}

function Stat({
  label,
  value,
  tone,
}: {
  label: string;
  value: string;
  tone?: "good" | "bad";
}) {
  const color =
    tone === "good"
      ? "text-emerald-300"
      : tone === "bad"
        ? "text-rose-300"
        : "text-foreground";
  return (
    <div className="rounded-md border border-primary/15 bg-card/40 p-3">
      <div className="display text-[9px] uppercase tracking-[0.32em] text-muted-foreground/80">
        {label}
      </div>
      <div className={cn("mono mt-1 text-base", color)}>{value}</div>
    </div>
  );
}

function Cfg({ k, v }: { k: string; v: string }) {
  return (
    <div className="flex items-center justify-between gap-3 border-b border-primary/10 py-1">
      <dt className="mono text-muted-foreground/80">{k}</dt>
      <dd className="mono text-foreground">{v}</dd>
    </div>
  );
}

function EquityChart({
  series,
  bankroll,
}: {
  series: { x: number; y: number; pnl: number }[];
  bankroll: number;
}) {
  if (series.length < 2) {
    return (
      <div className="rounded-md border border-primary/15 bg-card/30 p-6 text-center text-sm text-muted-foreground">
        Not enough settled trades to render an equity curve.
      </div>
    );
  }
  const w = 700;
  const h = 200;
  const pad = { l: 50, r: 12, t: 14, b: 22 };
  const innerW = w - pad.l - pad.r;
  const innerH = h - pad.t - pad.b;
  const ys = series.map((p) => p.y);
  const minY = Math.min(bankroll, ...ys);
  const maxY = Math.max(bankroll, ...ys);
  const xMin = series[0].x;
  const xMax = series[series.length - 1].x;
  const toX = (x: number) =>
    pad.l + ((x - xMin) / (xMax - xMin || 1)) * innerW;
  const toY = (y: number) =>
    pad.t + (1 - (y - minY) / (maxY - minY || 1)) * innerH;
  const d = series
    .map((p, i) => `${i === 0 ? "M" : "L"}${toX(p.x).toFixed(1)},${toY(p.y).toFixed(1)}`)
    .join(" ");
  const baselineY = toY(bankroll);
  return (
    <div className="rounded-md border border-primary/15 bg-card/30 p-3">
      <div className="display mb-2 text-[10px] uppercase tracking-[0.4em] text-primary/65">
        Equity curve · ${bankroll.toFixed(0)} starting → final ${ys[ys.length - 1].toFixed(0)}
      </div>
      <svg
        viewBox={`0 0 ${w} ${h}`}
        className="h-auto w-full text-primary"
        preserveAspectRatio="xMidYMid meet"
      >
        {/* Grid */}
        {[0, 0.25, 0.5, 0.75, 1].map((f) => (
          <line
            key={f}
            x1={pad.l}
            x2={w - pad.r}
            y1={pad.t + f * innerH}
            y2={pad.t + f * innerH}
            stroke="currentColor"
            strokeOpacity={0.08}
            strokeWidth={0.5}
          />
        ))}
        {/* Bankroll baseline */}
        <line
          x1={pad.l}
          x2={w - pad.r}
          y1={baselineY}
          y2={baselineY}
          stroke="currentColor"
          strokeOpacity={0.35}
          strokeDasharray="4 4"
        />
        <text
          x={pad.l - 6}
          y={baselineY + 4}
          textAnchor="end"
          className="fill-muted-foreground text-[10px]"
        >
          ${bankroll.toFixed(0)}
        </text>
        {/* Equity line */}
        <path
          d={d}
          fill="none"
          stroke="currentColor"
          strokeWidth={1.4}
          strokeOpacity={0.85}
        />
        {/* Min / max labels */}
        <text
          x={pad.l - 6}
          y={pad.t + 8}
          textAnchor="end"
          className="fill-muted-foreground text-[10px]"
        >
          ${maxY.toFixed(0)}
        </text>
        <text
          x={pad.l - 6}
          y={pad.t + innerH}
          textAnchor="end"
          className="fill-muted-foreground text-[10px]"
        >
          ${minY.toFixed(0)}
        </text>
      </svg>
    </div>
  );
}

function TradeRibbon({ ticks }: { ticks: Tick[] }) {
  const settled = ticks.filter((t) => t.settled_pnl_usdc !== null);
  if (settled.length === 0) {
    return null;
  }
  return (
    <div className="rounded-md border border-primary/15 bg-card/30 p-3">
      <div className="display mb-2 text-[10px] uppercase tracking-[0.4em] text-primary/65">
        Trades · green = win · red = loss
      </div>
      <div className="flex flex-wrap gap-[2px]">
        {settled.map((t) => {
          const pnl = t.settled_pnl_usdc ?? 0;
          const win = pnl > 0;
          return (
            <span
              key={t.seq}
              title={`bar ${t.seq} · pnl ${usd(pnl)} · price $${t.price.toFixed(0)}`}
              className={cn(
                "inline-block h-4 w-2 rounded-sm transition-opacity hover:opacity-80",
                win
                  ? "bg-emerald-500/70"
                  : pnl < 0
                    ? "bg-rose-500/70"
                    : "bg-muted",
              )}
            />
          );
        })}
      </div>
    </div>
  );
}
