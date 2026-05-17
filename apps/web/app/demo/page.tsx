import { Badge } from "@/components/ui/badge";

import { CircleStackPanel } from "./circle-stack-panel";
import { CoinGeckoPanel } from "./coingecko-panel";
import { EdgeSourcesPanel } from "./edge-sources-panel";
import { ReplayPlayer } from "./replay-player";
import { WalletConnect } from "./wallet-connect";

export const metadata = {
  title: "Demo — Pantheon Council deliberation",
  description:
    "Replay a captured Gemini council deliberation: ten agents, four rounds, Areopagus verdict, Proof of Restraint.",
};

const SCENARIOS = {
  "btc-120k-approve": {
    title: "Pantheon Council — BTC $120k by 2026-12-31",
    label: "Crypto · Approval",
    intro:
      "Ten agents deliberate a +17pp edge signal on a Bitcoin price-target market. Watch the four rounds, the synthesis, the votes, and the Areopagus verdict that sizes the position at the constitutional cap.",
  },
  "btc-120k-restraint": {
    title: "Pantheon Council — BTC $120k by 2026-12-31",
    label: "Crypto · Proof of Restraint",
    intro:
      "A constitutional cluster-correlation violation on the same Bitcoin market. Zeus identifies it in Round 1 and casts the supreme veto. The debate short-circuits. Areopagus writes a Proof of Restraint witness to Arc Testnet.",
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
        <p className="max-w-3xl font-serif text-lg leading-relaxed text-muted-foreground">
          {meta.intro}
        </p>
      </header>

      <WalletConnect />

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
          Live paper trade — real BTC bars
        </h2>
        <p className="max-w-3xl font-serif text-base leading-relaxed text-muted-foreground">
          Below: the checked-in run of{" "}
          <code className="font-mono">scripts/live_paper_trade_coingecko.py</code> against
          the last 7 days of BTC/USD hourly bars from CoinGecko. The plumbing is real
          (Apollo signal → Areopagus half-Kelly → Strategos paper book). The strategy
          is intentionally a toy momentum estimator, not the council — so the result
          is honest. Naïve momentum loses to fees. That is the system telling you the
          truth.
        </p>
      </div>

      <CoinGeckoPanel />

      <div className="space-y-3 pt-8">
        <h2 className="font-display text-3xl font-medium tracking-[0.02em] text-foreground md:text-4xl">
          Where the council&apos;s prior comes from
        </h2>
        <p className="max-w-3xl font-serif text-base leading-relaxed text-muted-foreground">
          12 Pythia data sources feed 7 bounded Apollo features into{" "}
          <code className="font-mono">Signal.oracle_probability</code>. Each delta is
          capped at ±0.05 — combined cap ±0.35. The council still votes on top of
          this prior; the constitution still gates the size.
        </p>
      </div>

      <EdgeSourcesPanel />

      <div className="space-y-3 pt-8">
        <h2 className="font-display text-3xl font-medium tracking-[0.02em] text-foreground md:text-4xl">
          Settles on Arc — powered by Circle
        </h2>
        <p className="max-w-3xl font-serif text-base leading-relaxed text-muted-foreground">
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
