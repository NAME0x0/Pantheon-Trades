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

  const isTwinScenario =
    scenario === "btc-120k-approve" || scenario === "btc-120k-restraint";

  return (
    <div className="space-y-16 py-10">
      {/* ── Page header ─────────────────────────────────────────────── */}
      <header className="space-y-5">
        <Badge variant="outline" className="border-primary/40 font-display tracking-[0.32em]">
          Council replay · {meta.label}
        </Badge>
        <h1 className="font-display text-4xl font-medium leading-[1.05] tracking-[-0.01em] text-foreground md:text-5xl">
          {meta.title}
        </h1>
        <p className="max-w-3xl font-serif text-lg leading-[1.65] text-muted-foreground md:text-xl">
          {meta.intro}
        </p>
      </header>

      {/* ── Try-it-yourself row: wallet + witness + faucet ──────────── */}
      <section className="space-y-6">
        <div className="space-y-2">
          <span className="display text-[11px] uppercase tracking-[0.32em] text-primary">
            Try it yourself · free, no charge
          </span>
          <h2 className="font-display text-3xl font-medium leading-[1.1] tracking-[-0.01em] text-foreground md:text-4xl">
            Sign one tx. Your wallet lands on chain.
          </h2>
        </div>
        <WalletConnect />
        <div className="grid gap-6 lg:grid-cols-2">
          <WitnessButton scenario={scenario} />
          <FaucetCard />
        </div>
      </section>

      {/* ── Council replay ─────────────────────────────────────────── */}
      <section className="space-y-6">
        <div className="space-y-2">
          <span className="display text-[11px] uppercase tracking-[0.32em] text-primary">
            Captured deliberation · production code paths
          </span>
          <h2 className="font-display text-3xl font-medium leading-[1.1] tracking-[-0.01em] text-foreground md:text-4xl">
            Watch the council deliberate.
          </h2>
        </div>

        {isTwinScenario && (
          <div className="max-w-3xl rounded-md border border-primary/25 bg-primary/[0.04] p-5">
            <p className="font-mono text-[11px] uppercase tracking-[0.32em] text-primary">
              Twin scenarios · same signal, different portfolio
            </p>
            <p className="mt-2 font-serif text-base leading-[1.6] text-muted-foreground">
              Approval and Restraint scenarios share the <em>identical</em> +17pp
              edge signal (0.59 oracle vs 0.42 market). What differs is the
              portfolio state: clean book → APPROVED, already-correlated book →
              VETOED. An edge alone does not justify a trade.
            </p>
          </div>
        )}

        <ReplayPlayer scenario={scenario} />

        <p className="max-w-3xl rounded-md border border-primary/20 bg-card/40 px-4 py-3 text-xs leading-[1.55] text-muted-foreground">
          <strong className="font-mono uppercase tracking-wider text-foreground">
            Source ·
          </strong>{" "}
          Dialogue is captured from prior live Gemini runs. Signal scoring,
          Areopagus verdict, half-Kelly sizing, and paper trade all compute through
          production code paths (<code className="font-mono">apollo.scorer</code>,{" "}
          <code className="font-mono">areopagus.court</code>,{" "}
          <code className="font-mono">strategos.paper</code>).
        </p>
      </section>

      {/* ── CoinGecko paper-trade — plumbing check ─────────────────── */}
      <section className="space-y-6">
        <div className="space-y-2">
          <span className="display text-[11px] uppercase tracking-[0.32em] text-primary">
            Pipeline integrity check · NOT the council
          </span>
          <h2 className="font-display text-3xl font-medium leading-[1.1] tracking-[-0.01em] text-foreground md:text-4xl">
            Real BTC bars, naïve estimator.
          </h2>
        </div>
        <div className="max-w-3xl rounded-md border border-amber-500/40 bg-amber-500/5 px-5 py-4">
          <p className="font-mono text-[11px] uppercase tracking-[0.32em] text-amber-200">
            ⚠ This panel lost money — by design
          </p>
          <p className="mt-2 font-serif text-base leading-[1.6] text-muted-foreground">
            The strategy is naïve momentum (long if last bar up, short if down) — a
            deliberate stand-in for the council. The point is to prove the plumbing
            survives real market data: 4% round-trip fees mathematically kill
            momentum. The council&apos;s job is to refuse those trades.
          </p>
        </div>
        <p className="max-w-3xl font-serif text-base leading-[1.65] text-muted-foreground md:text-lg">
          Run:{" "}
          <code className="font-mono text-primary">
            scripts/live_paper_trade_coingecko.py
          </code>{" "}
          on 7 days of BTC/USD hourly bars. Fills route through the real{" "}
          <code className="font-mono">strategos.paper.PaperBook</code> with
          half-spread, slippage, and 2% taker fees.
        </p>
        <CoinGeckoPanel />
      </section>

      {/* ── Empirical backtest — does the council help? ─────────────── */}
      <section className="space-y-6">
        <div className="space-y-2">
          <span className="display text-[11px] uppercase tracking-[0.32em] text-primary">
            Empirical backtest · 200 resolved markets
          </span>
          <h2 className="font-display text-3xl font-medium leading-[1.1] tracking-[-0.01em] text-foreground md:text-4xl">
            Does the council help?
          </h2>
        </div>
        <p className="max-w-3xl font-serif text-base leading-[1.65] text-muted-foreground md:text-lg">
          200 resolved Manifold binary markets, run through the 5-role council via{" "}
          <code className="font-mono">scripts/backtest_sources_xml.py</code>. Brier
          decomposition, per-source verdicts, $0.12 cost on Gemini flash-lite.
        </p>
        <BacktestPanel />
      </section>

      {/* ── Edge sources panel — the council's prior ──────────────── */}
      <section className="space-y-6">
        <div className="space-y-2">
          <span className="display text-[11px] uppercase tracking-[0.32em] text-primary">
            What the council sees · 12 sources, 2 adopted
          </span>
          <h2 className="font-display text-3xl font-medium leading-[1.1] tracking-[-0.01em] text-foreground md:text-4xl">
            Where the prior comes from.
          </h2>
        </div>
        <EdgeSourcesPanel />
      </section>

      {/* ── Circle stack panel ─────────────────────────────────────── */}
      <section className="space-y-6">
        <div className="space-y-2">
          <span className="display text-[11px] uppercase tracking-[0.32em] text-primary">
            Settles on Arc · powered by Circle
          </span>
          <h2 className="font-display text-3xl font-medium leading-[1.1] tracking-[-0.01em] text-foreground md:text-4xl">
            Built end-to-end on the Circle stack.
          </h2>
        </div>
        <CircleStackPanel />
      </section>
    </div>
  );
}
