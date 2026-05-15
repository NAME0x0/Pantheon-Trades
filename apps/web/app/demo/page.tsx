import { Badge } from "@/components/ui/badge";

import { ReplayPlayer } from "./replay-player";

export const metadata = {
  title: "Demo — Pantheon Council deliberation",
  description:
    "Replay a captured Gemini council deliberation: ten agents, four rounds, Areopagus verdict, Proof of Restraint.",
};

export default function DemoPage({
  searchParams,
}: {
  searchParams: { scenario?: string };
}) {
  const scenario = searchParams.scenario === "restraint" ? "restraint" : "approve";

  return (
    <div className="space-y-8 py-8">
      <header className="space-y-3">
        <Badge variant="outline" className="border-primary/40 font-display tracking-[0.25em]">
          Council replay · {scenario === "approve" ? "Approval scenario" : "Proof of Restraint"}
        </Badge>
        <h1 className="font-display text-4xl md:text-5xl font-medium tracking-[0.02em] text-foreground">
          Pantheon Council — BTC $120k by 2026-12-31
        </h1>
        <p className="max-w-3xl font-serif text-lg leading-relaxed text-muted-foreground">
          {scenario === "approve"
            ? "Ten agents deliberate a +17pp edge signal. Watch the four rounds, the synthesis, the votes, and the Areopagus verdict that sizes the position at exactly the constitutional cap."
            : "A constitutional cluster-correlation violation. Zeus identifies it in Round 1 and casts the supreme veto. The debate short-circuits. Areopagus writes a Proof of Restraint witness to Arc Testnet."}
        </p>
      </header>

      <ReplayPlayer scenario={scenario} />

      <p className="rounded-md border border-primary/20 bg-card/40 p-4 text-xs text-muted-foreground">
        <strong className="font-mono text-foreground">Source:</strong>{" "}
        Agent dialogue is curated from prior live Gemini runs; signal scoring, Areopagus
        verdict, half-Kelly sizing, and the paper trade are computed by the actual
        production code paths (<code className="font-mono">apollo.scorer</code>,{" "}
        <code className="font-mono">areopagus.court</code>,{" "}
        <code className="font-mono">strategos.paper</code>) at bundle-build time.
      </p>
    </div>
  );
}
