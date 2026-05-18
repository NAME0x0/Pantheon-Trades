"use client";

/**
 * Edge sources panel — shows every Pythia data source + Apollo
 * feature wired into the production scorer, with one-line evidence
 * of what it does.
 *
 * Pure static data — no fetches. The point is to surface what the
 * system *can* see, not to show live numbers. Live numbers vary
 * with the operator's keys + geo-block status; the architecture
 * doesn't.
 */

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

type EdgeRow = {
  source: string;
  apolloFeature: string;
  mechanism: string;
  authNeeded: "none" | "free key" | "operator key";
  tier: "high" | "medium" | "experimental";
};

const EDGES: readonly EdgeRow[] = [
  {
    source: "Odds API",
    apolloFeature: "basis_arb",
    mechanism: "Sportsbook consensus vs Polymarket — vig-stripped, fee-net basis",
    authNeeded: "free key",
    tier: "high",
  },
  {
    source: "Kalshi REST",
    apolloFeature: "basis_arb",
    mechanism: "US-regulated event-contract prices; cross-listing arb with Polymarket",
    authNeeded: "none",
    tier: "high",
  },
  {
    source: "Manifold Markets",
    apolloFeature: "consensus_delta",
    mechanism: "Free human-consensus prior; wide gap = wider council, smaller size",
    authNeeded: "none",
    tier: "high",
  },
  {
    source: "Binance perps",
    apolloFeature: "perps_signal",
    mechanism: "Funding-rate z + OI delta; contrarian on extreme over-leverage",
    authNeeded: "none",
    tier: "high",
  },
  {
    source: "CFTC CoT",
    apolloFeature: "cot_positioning",
    mechanism: "Weekly speculator-net z vs 26-week history; contrarian on crowded longs",
    authNeeded: "none",
    tier: "medium",
  },
  {
    source: "GDELT 2.0",
    apolloFeature: "geopolitical_risk",
    mechanism: "Real-time global news volume + tone, 100+ languages, 15-min cadence",
    authNeeded: "none",
    tier: "medium",
  },
  {
    source: "FRED",
    apolloFeature: "macro_basis",
    mechanism: "816k US macro time series; Fed / CPI / NFP gaps vs threshold",
    authNeeded: "none",
    tier: "medium",
  },
  {
    source: "Wikipedia pageviews",
    apolloFeature: "attention",
    mechanism: "Per-article hourly pageview velocity z-score = investor-attention proxy",
    authNeeded: "none",
    tier: "medium",
  },
  {
    source: "DeFiLlama",
    apolloFeature: "onchain_tvl",
    mechanism: "Chain TVL + stablecoin mints + protocol yields — flow indicator",
    authNeeded: "none",
    tier: "medium",
  },
  {
    source: "Nitter (X/Twitter)",
    apolloFeature: "crowd_sentiment",
    mechanism: "Free RSS scrape; in-tree VADER-style scorer for retail-flow sentiment",
    authNeeded: "none",
    tier: "experimental",
  },
  {
    source: "TradingView screener",
    apolloFeature: "lead_lag",
    mechanism: "Cross-asset technical screens; macro lead/lag for derived markets",
    authNeeded: "none",
    tier: "experimental",
  },
  {
    source: "Polymarket L2 WS",
    apolloFeature: "orderbook_imbalance",
    mechanism: "Live CLOB book depth; per-side imbalance into oracle prior",
    authNeeded: "operator key",
    tier: "high",
  },
] as const;

function tierVariant(tier: EdgeRow["tier"]): "success" | "default" | "warning" {
  if (tier === "high") return "success";
  if (tier === "medium") return "default";
  return "warning";
}

function authVariant(auth: EdgeRow["authNeeded"]): "success" | "default" | "muted" {
  if (auth === "none") return "success";
  if (auth === "free key") return "default";
  return "muted";
}

export function EdgeSourcesPanel() {
  const byTier = {
    high: EDGES.filter((e) => e.tier === "high"),
    medium: EDGES.filter((e) => e.tier === "medium"),
    experimental: EDGES.filter((e) => e.tier === "experimental"),
  };

  return (
    <Card className="border-primary/30">
      <CardHeader className="space-y-3 pb-3">
        <CardTitle className="font-display text-lg font-semibold tracking-[0.02em] text-foreground">
          2 ADOPTED · 10 in falsification · ±0.35 combined cap
        </CardTitle>
        <p className="font-serif text-base leading-[1.6] text-muted-foreground">
          12 sources are plumbed in. Only 2 have survived empirical Brier-delta
          testing — Wikipedia attention + Nitter crowd_sentiment. The other 10 are
          HOLD or UNTESTABLE pending a Polymarket-flavoured corpus. A source only
          graduates to ADOPT when its negative Brier-delta beats noise.
        </p>
      </CardHeader>
      <CardContent className="space-y-4">
        <Section title="High signal-to-noise" rows={byTier.high} />
        <Section title="Medium signal-to-noise" rows={byTier.medium} />
        <Section title="Experimental / qualitative" rows={byTier.experimental} />
        <p className="rounded-md border border-primary/15 bg-card/40 px-4 py-3 text-xs leading-[1.55] text-muted-foreground">
          <strong className="font-mono uppercase tracking-wider text-foreground">
            Falsification protocol ·
          </strong>{" "}
          all 12 sources plumb into{" "}
          <code className="font-mono">apollo.scorer.MarketSnapshot</code>. A source
          graduates HOLD → ADOPT only when its paired Brier test beats the council
          baseline by &gt;0.002. Non-adopted sources stay live for telemetry; their
          oracle delta is set to zero. No source ships unfalsified.
        </p>
      </CardContent>
    </Card>
  );
}

function Section({ title, rows }: { title: string; rows: readonly EdgeRow[] }) {
  return (
    <div className="space-y-2">
      <div className="display text-[10px] uppercase tracking-[0.4em] text-primary/65">
        {title}
      </div>
      <div className="overflow-hidden rounded-md border border-primary/15">
        <table className="w-full text-sm">
          <thead className="bg-card/40">
            <tr>
              <Th>Source</Th>
              <Th>Apollo feature</Th>
              <Th>Mechanism</Th>
              <Th>Auth</Th>
              <Th>Tier</Th>
            </tr>
          </thead>
          <tbody className="divide-y divide-primary/10">
            {rows.map((r) => (
              <tr key={r.source} className="hover:bg-primary/[0.03]">
                <Td>
                  <span className="font-mono text-foreground">{r.source}</span>
                </Td>
                <Td>
                  <code className="font-mono text-primary/80">{r.apolloFeature}</code>
                </Td>
                <Td className="text-muted-foreground">{r.mechanism}</Td>
                <Td>
                  <Badge variant={authVariant(r.authNeeded)}>{r.authNeeded}</Badge>
                </Td>
                <Td>
                  <Badge variant={tierVariant(r.tier)}>{r.tier}</Badge>
                </Td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
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
