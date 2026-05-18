import { Badge } from "@/components/ui/badge";

import { BacktestPanel } from "./backtest-panel";
import { CircleStackPanel } from "./circle-stack-panel";
import { CoinGeckoPanel } from "./coingecko-panel";
import { EdgeSourcesPanel } from "./edge-sources-panel";
import { FaucetCard } from "./faucet-card";
import { ReplayPlayer } from "./replay-player";
import { WalletConnect } from "./wallet-connect";
import { WitnessButton } from "./witness-button";

export const metadata = {
  title: "Demo — Pantheon Council deliberation",
  description:
    "Replay a captured Gemini council deliberation: eleven agents, four rounds, Areopagus verdict, Proof of Restraint.",
};

const SCENARIOS = {
  "btc-120k-approve": {
    title: "Pantheon Council — BTC $120k by 2026-12-31",
    label: "Crypto · Approval",
    intro:
      "Identical +17pp edge signal — clean portfolio, no correlated BTC exposure already on the books. Eleven agents deliberate, Themis resizes from raw half-Kelly 10.5% to a category-capped 5% NAV, Areopagus approves. Watch the four rounds and the final size land at the constitutional cap.",
  },
  "btc-120k-restraint": {
    title: "Pantheon Council — BTC $120k by 2026-12-31",
    label: "Crypto · Proof of Restraint",
    intro:
      "Identical +17pp edge signal — but the portfolio already holds correlated crypto exposure (ETH-3500-Q2 long). Zeus runs the cluster-correlation check, finds the macro-cluster correlation at 0.78 above the 0.65 constitutional ceiling, casts the supreme veto in Round 1. Debate short-circuits. Areopagus writes the Proof of Restraint witness on Arc.",
  },
  "election-2028-approve": {
    title: "Pantheon Council — US Presidential 2028 (incumbent)",
    label: "Politics · NO Approval",
    intro:
      "A 2028 election market trades 62% YES for the incumbent. Four data sources (RCP, 538, Polymarket, news) and a –10pp sentiment skew push council toward NO. Approved with a Themis resize from raw half-Kelly 10.5% to a category-capped 3.5% NAV.",
  },
  "nfl-superbowl-restraint": {
    title: "Pantheon Council — NFL Super Bowl LXIII (Chiefs)",
    label: "Sports · Liquidity Floor Reject",
    intro:
      "Genuine signal but a thin book — $11k 24h volume against a $50k constitutional floor. Solon early-rejects on Article IV §1. No deliberation happens. Restraint witness written.",
  },
} as const;

type ScenarioId = keyof typeof SCENARIOS;

const VALID_SCENARIOS = Object.keys(SCENARIOS) as ScenarioId[];

function resolveScenario(raw: string | undefined): ScenarioId {
  if (raw === "approve") return "btc-120k-approve";
  if (raw === "restraint") return "btc-120k-restraint";
  if (raw && (VALID_SCENARIOS as readonly string[]).includes(raw)) {
    return raw as ScenarioId;
  }
  return "btc-120k-approve";
}

export default function DemoPage({
  searchParams,
}: {
  searchParams: { scenario?: string };
}) {
  const scenario = resolveScenario(searchParams.scenario);
  const meta = SCENARIOS[scenario];

  return (
    <div className="space-y-8 py-8">
      <header className="space-y-3">
        <Badge variant="outline" className="border-primary/40 font-display tracking-[0.25em]">
          Council replay · {meta.label}
        </Badge>
        <h1 className="font-display text-4xl md:text-5xl font-medium tracking-[0.02em] text-foreground">
          {meta.title}
        </h1>
        <p className="max-w-3xl font-serif text-lg leading-[1.7] text-muted-foreground">
          {meta.intro}
        </p>
        {(scenario === "btc-120k-approve" || scenario === "btc-120k-restraint") && (
          <div className="mt-4 max-w-3xl rounded-md border border-primary/25 bg-primary/[0.04] p-4">
            <p className="font-mono text-xs uppercase tracking-[0.18em] text-primary/80">
              Twin scenarios — same signal, different portfolio
            </p>
            <p className="mt-2 font-serif text-sm leading-[1.6] text-muted-foreground">
              The Bitcoin approval and Bitcoin restraint scenarios use the
              <em> identical</em> +17pp edge signal — 0.59 oracle vs 0.42 market.
              What differs is the portfolio state: clean book → APPROVED, already-correlated
              book → VETOED. This is the discipline the system encodes: an edge alone
              does not justify a trade; the constitution still gates it.
            </p>
          </div>
        )}
      </header>

      <WalletConnect />

      <div className="grid gap-6 lg:grid-cols-2">
        <WitnessButton
          scenario={scenario}
          title="Run this demo on Arc Testnet"
        />
        <FaucetCard />
      </div>

      <ReplayPlayer scenario={scenario} />

      <p className="rounded-md border border-primary/20 bg-card/40 p-4 text-xs text-muted-foreground">
        <strong className="font-mono text-foreground">Source:</strong>{" "}
        Agent dialogue is curated from prior live Gemini runs; signal scoring, Areopagus
        verdict, half-Kelly sizing, and the paper trade are computed by the actual
        production code paths (<code className="font-mono">apollo.scorer</code>,{" "}
        <code className="font-mono">areopagus.court</code>,{" "}
        <code className="font-mono">strategos.paper</code>) at bundle-build time.
      </p>

      <div className="space-y-3 pt-6">
        <h2 className="font-display text-3xl font-medium tracking-[0.02em] text-foreground md:text-4xl">
          Pipeline integrity check — real BTC bars, no council
        </h2>
        <div className="max-w-3xl rounded-md border border-amber-500/40 bg-amber-500/5 p-4">
          <p className="font-mono text-xs uppercase tracking-[0.18em] text-amber-200">
            ⚠ This panel is NOT the council — it&apos;s the plumbing check
          </p>
          <p className="mt-2 font-serif text-sm leading-[1.6] text-muted-foreground">
            What you are about to see lost $3,951 on $10,000 starting equity. That is{" "}
            <em>by design</em>. The panel uses a deliberately naïve momentum estimator
            (long if last bar was up, short if down) in place of the council so we can
            prove the plumbing — Apollo signal → Areopagus half-Kelly → Strategos paper
            book — survives real market data without simulator tricks. A 4% round-trip
            cost mathematically kills naïve momentum. The council&apos;s job is to refuse
            those trades. The empirical backtest panel below shows what happens when
            the council <em>is</em> in the loop.
          </p>
        </div>
        <p className="max-w-3xl font-serif text-base leading-[1.7] text-muted-foreground">
          Run:{" "}
          <code className="font-mono text-primary">scripts/live_paper_trade_coingecko.py</code>{" "}
          against 7 days of BTC/USD hourly bars. Fills go through the real{" "}
          <code className="font-mono">strategos.paper.PaperBook</code> with half-spread,
          slippage, and 2% taker fees. No mock.
        </p>
      </div>

      <CoinGeckoPanel />

      <div className="space-y-3 pt-8">
        <h2 className="font-display text-3xl font-medium tracking-[0.02em] text-foreground md:text-4xl">
          Empirical backtest — does the council actually beat the market?
        </h2>
        <p className="max-w-3xl font-serif text-lg leading-[1.7] text-muted-foreground">
          200 resolved Manifold binary markets, run through the 5-role council via{" "}
          <code className="font-mono">scripts/backtest_sources_xml.py</code>. Brier scores,
          per-source adoption verdicts, $0.12 cost on Gemini flash-lite.
        </p>
      </div>

      <BacktestPanel />

      <div className="space-y-3 pt-8">
        <h2 className="font-display text-3xl font-medium tracking-[0.02em] text-foreground md:text-4xl">
          Where the council&apos;s prior comes from
        </h2>
        <p className="max-w-3xl font-serif text-lg leading-[1.7] text-muted-foreground">
          12 Pythia data sources are plumbed in, but only the 2 that have survived
          empirical Brier-delta falsification on a 200-market Manifold sample contribute
          to <code className="font-mono">Signal.oracle_probability</code>. Each ADOPTED
          delta is capped at ±0.05 — combined cap ±0.35. The remaining 10 stay HOLD until
          a Polymarket-flavoured corpus is available. The council still votes on top of
          this prior; the constitution still gates the size.
        </p>
      </div>

      <EdgeSourcesPanel />

      <div className="space-y-3 pt-8">
        <h2 className="font-display text-3xl font-medium tracking-[0.02em] text-foreground md:text-4xl">
          Settles on Arc — powered by Circle
        </h2>
        <p className="max-w-3xl font-serif text-lg leading-[1.7] text-muted-foreground">
          Pantheon is built end-to-end on Circle&apos;s developer platform. USDC is the
          native settlement currency; Arc gives sub-second finality at ~$0.01/tx.
          Builder codes attribute every fill to a payout address. Trace anchors hash
          every council deliberation onto Arc.
        </p>
      </div>

      <CircleStackPanel />
    </div>
  );
}
