"use client";

/**
 * Empirical-backtest panel — shows the live measured numbers from
 * scripts/backtest_sources_xml.py. Pure static content (no fetches)
 * so the panel renders instantly on page load and the numbers stay
 * pinned to the actual artifacts checked into the repo.
 *
 * When the operator re-runs the harness (Manifold sample refresh,
 * better LLM provider, etc.), update LATEST_RUN below to point at
 * the new artifact + numbers.
 */

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

const LATEST_RUN = {
  artifact: "artifacts/sources_brier_20260517T181232Z.json",
  date: "2026-05-17",
  n_markets: 200,
  cost_usd: 0.12,
  provider: "Gemini flash-lite (council, 5 roles × 8 batches)",
};

interface ForecasterRow {
  label: string;
  brier: number;
  reliability: number;
  resolution: number;
  highlight?: boolean;
  note?: string;
}

const FORECASTERS: readonly ForecasterRow[] = [
  {
    label: "Manifold consensus (baseline)",
    brier: 0.126,
    reliability: 0.012,
    resolution: 0.123,
    note: "free play-money human consensus — the wall to beat",
  },
  {
    label: "Single-shot Gemini",
    brier: 0.260,
    reliability: 0.046,
    resolution: 0.049,
    note: "raw LLM alone — worse than play-money humans",
  },
  {
    label: "5-role council aggregated",
    brier: 0.149,
    reliability: 0.019,
    resolution: 0.088,
    highlight: true,
    note: "closes 80% of the gap to Manifold",
  },
];

interface SourceRow {
  source: string;
  delta: number;
  applicability: number;
  verdict: "ADOPT" | "HOLD" | "REJECT" | "UNTESTABLE";
}

const SOURCE_VERDICTS: readonly SourceRow[] = [
  { source: "attention (Wikipedia)", delta: -0.0040, applicability: 0.335, verdict: "ADOPT" },
  { source: "crowd_sentiment (Nitter)", delta: -0.0040, applicability: 0.360, verdict: "ADOPT" },
  { source: "geopolitical_risk (GDELT)", delta: -0.0013, applicability: 0.080, verdict: "HOLD" },
  { source: "lead_lag (TradingView)", delta: -0.0006, applicability: 0.140, verdict: "HOLD" },
  { source: "perps_signal (Binance)", delta: -0.0001, applicability: 0.063, verdict: "HOLD" },
  { source: "orderbook_imbalance", delta: -0.0001, applicability: 0.080, verdict: "HOLD" },
  { source: "onchain_tvl (DeFiLlama)", delta: +0.0004, applicability: 0.075, verdict: "HOLD" },
  { source: "basis_arb", delta: +0.0003, applicability: 0.060, verdict: "HOLD" },
  { source: "cot_positioning (CFTC)", delta: +0.0010, applicability: 0.055, verdict: "HOLD" },
  { source: "consensus_delta", delta: 0.0, applicability: 0.0, verdict: "UNTESTABLE" },
  { source: "macro_basis (FRED)", delta: 0.0, applicability: 0.040, verdict: "UNTESTABLE" },
  { source: "macro_release_consensus", delta: 0.0, applicability: 0.040, verdict: "UNTESTABLE" },
];

function verdictVariant(v: SourceRow["verdict"]): "success" | "default" | "warning" | "muted" {
  if (v === "ADOPT") return "success";
  if (v === "REJECT") return "destructive" as "warning";  // re-use warning style if no destructive
  if (v === "HOLD") return "default";
  return "muted";
}

export function BacktestPanel() {
  return (
    <Card className="border-primary/30">
      <CardHeader className="space-y-2 pb-3">
        <div className="display text-[10px] uppercase tracking-[0.4em] text-primary/70">
          Empirical backtest · {LATEST_RUN.date}
        </div>
        <CardTitle className="display text-xl tracking-[0.06em] text-foreground">
          Council closes 80% of the LLM-vs-human Brier gap
        </CardTitle>
        <p className="serif max-w-3xl text-sm leading-[1.55] italic text-muted-foreground">
          Honest framing: the council does <strong className="not-italic">not</strong> beat
          free human consensus on this 200-market Manifold sample
          (0.149 vs 0.126 Brier). What it does do is close 80% of the gap between a
          single-shot LLM and the human prior. Aggregation across 5 distinct roles is
          worth ~0.11 Brier — an order of magnitude more than any individual data source.
          Total cost ${LATEST_RUN.cost_usd.toFixed(3)} on {LATEST_RUN.provider}.
        </p>
      </CardHeader>
      <CardContent className="space-y-6">
        <div>
          <div className="display mb-2 text-[10px] uppercase tracking-[0.4em] text-primary/65">
            Forecaster comparison (lower Brier is sharper)
          </div>
          <div className="overflow-hidden rounded-md border border-primary/15">
            <table className="w-full text-sm">
              <thead className="bg-card/40">
                <tr>
                  <Th>Forecaster</Th>
                  <Th>Brier</Th>
                  <Th>Reliability</Th>
                  <Th>Resolution</Th>
                </tr>
              </thead>
              <tbody className="divide-y divide-primary/10">
                {FORECASTERS.map((f) => (
                  <tr
                    key={f.label}
                    className={
                      f.highlight
                        ? "bg-primary/[0.05] hover:bg-primary/[0.08]"
                        : "hover:bg-primary/[0.03]"
                    }
                  >
                    <Td>
                      <div className={f.highlight ? "font-semibold" : ""}>{f.label}</div>
                      {f.note && (
                        <div className="text-xs italic text-muted-foreground">{f.note}</div>
                      )}
                    </Td>
                    <Td>
                      <code className="font-mono text-primary">{f.brier.toFixed(3)}</code>
                    </Td>
                    <Td>
                      <code className="font-mono text-muted-foreground">{f.reliability.toFixed(3)}</code>
                    </Td>
                    <Td>
                      <code className="font-mono text-muted-foreground">{f.resolution.toFixed(3)}</code>
                    </Td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <div>
          <div className="display mb-2 text-[10px] uppercase tracking-[0.4em] text-primary/65">
            Per-source adoption verdicts (at single-shot baseline)
          </div>
          <div className="overflow-hidden rounded-md border border-primary/15">
            <table className="w-full text-sm">
              <thead className="bg-card/40">
                <tr>
                  <Th>Source</Th>
                  <Th>Δ Brier</Th>
                  <Th>Applicability</Th>
                  <Th>Verdict</Th>
                </tr>
              </thead>
              <tbody className="divide-y divide-primary/10">
                {SOURCE_VERDICTS.map((s) => (
                  <tr key={s.source} className="hover:bg-primary/[0.03]">
                    <Td>
                      <code className="font-mono text-foreground">{s.source}</code>
                    </Td>
                    <Td>
                      <code
                        className={
                          s.delta < 0
                            ? "font-mono text-emerald-300"
                            : s.delta > 0
                              ? "font-mono text-rose-300"
                              : "font-mono text-muted-foreground"
                        }
                      >
                        {s.delta === 0 ? "—" : `${s.delta > 0 ? "+" : ""}${s.delta.toFixed(4)}`}
                      </code>
                    </Td>
                    <Td>
                      <code className="font-mono text-muted-foreground">
                        {(s.applicability * 100).toFixed(1)}%
                      </code>
                    </Td>
                    <Td>
                      <Badge variant={verdictVariant(s.verdict)}>{s.verdict}</Badge>
                    </Td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <p className="rounded-md border border-amber-500/30 bg-amber-900/10 p-3 text-xs text-amber-200/90">
          <strong className="font-mono">What this means:</strong> council aggregation alone is
          worth ~0.11 Brier vs single-shot, while individual source signals are worth ~0.003–0.004
          each. Aggregation &gt; sources by an order of magnitude. The two ADOPT sources (Wikipedia
          attention + Nitter crowd_sentiment) are already wired in{" "}
          <code className="font-mono">apollo.scorer</code> at ±0.05 contribution caps. The HOLD sources
          may shine on a Polymarket-flavoured corpus once the geo-block proxy is deployed.
        </p>
      </CardContent>
    </Card>
  );
}

function Th({ children }: { children: React.ReactNode }) {
  return (
    <th className="px-3 py-2 text-left text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
      {children}
    </th>
  );
}

function Td({
  children,
  className = "",
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return <td className={`px-3 py-2.5 ${className}`}>{children}</td>;
}
