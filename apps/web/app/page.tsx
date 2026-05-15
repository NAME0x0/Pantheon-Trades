import Link from "next/link";
import {
  ArrowRight,
  Code2,
  Gavel,
  ShieldCheck,
  Sparkles,
  CircleDot,
  Vote,
  Hammer,
  Eye,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";

export const metadata = {
  title: "Pantheon Trades — AI council prediction-market trading",
  description:
    "A ten-agent AI council deliberates every Polymarket trade. Trades and restraint witnesses are anchored on Arc Testnet.",
};

const AGENTS = [
  { name: "Apollo", role: "Sees the future", class: "Signal" },
  { name: "Boule", role: "Convenes the council", class: "Deliberation" },
  { name: "Ares", role: "Bull researcher — argues the long case", class: "Bull" },
  { name: "Hades", role: "Bull researcher — surfaces hidden depth", class: "Bull" },
  { name: "Athena", role: "Bear researcher + synthesizer", class: "Bear" },
  { name: "Cassandra", role: "Bear researcher — flags tail risk", class: "Bear" },
  { name: "Solon", role: "Risk authority — constitutional check", class: "Risk", veto: true },
  { name: "Zeus", role: "Supreme veto — hard constitutional gate", class: "Risk", veto: true },
  { name: "Themis", role: "Procedural integrity", class: "Risk" },
  { name: "Hephaestus", role: "Execution — sizes and routes", class: "Execution" },
  { name: "Daedalus", role: "Execution — strategy fit", class: "Execution" },
  { name: "Humans", role: "Execution — crowd sentiment", class: "Execution" },
  { name: "Areopagus", role: "Final gate — half-Kelly + constitutional caps", class: "Gate" },
  { name: "Strategos", role: "Order router — paper + live CLOB", class: "Execution" },
  { name: "Argos", role: "Position monitor — exits", class: "Monitor" },
  { name: "Ostrakon", role: "Scoring — agent performance ledger", class: "Memory" },
  { name: "Parthenon", role: "On-chain archive — IPFS + Arc", class: "Archive" },
  { name: "Pythia", role: "Signal source — validates inputs", class: "Signal" },
  { name: "Elysium", role: "Reward — winning trades", class: "Memory" },
  { name: "Underworld", role: "Penalty — losing trades & rejections", class: "Memory" },
  { name: "Moirai", role: "Lifecycle — strategy retirement", class: "Lifecycle" },
  { name: "Olympus", role: "Coordinator — orchestrates everyone", class: "Coordinator" },
];

const PIPELINE = [
  { step: "1", name: "Apollo", icon: Eye, what: "Scores Polymarket signals across 7 dimensions" },
  { step: "2", name: "Boule", icon: Vote, what: "Convenes 10-agent council; 4 rounds of debate" },
  { step: "3", name: "Areopagus", icon: Gavel, what: "Half-Kelly sizing + constitutional gates" },
  { step: "4a", name: "Strategos", icon: Hammer, what: "Routes approved trade to CLOB" },
  { step: "4b", name: "Parthenon", icon: ShieldCheck, what: "Writes Proof of Restraint on rejection" },
  { step: "5", name: "Argos", icon: CircleDot, what: "Monitors position; exits on trigger" },
  { step: "6", name: "Ostrakon", icon: Sparkles, what: "Scores each agent's contribution post-settlement" },
];

export default function Home() {
  return (
    <div className="space-y-24 py-8">
      {/* ── Hero ─────────────────────────────────────────────────────── */}
      <section className="space-y-6">
        <Badge variant="outline" className="border-primary/40">
          Multi-agent prediction-market trading · Arc Testnet
        </Badge>
        <h1 className="font-mono text-5xl md:text-6xl tracking-tight leading-tight">
          A council of ten gods
          <br />
          <span className="text-primary">debates every trade.</span>
        </h1>
        <p className="max-w-2xl text-lg text-muted-foreground">
          Pantheon Trades runs Polymarket signals through a structured four-round deliberation
          between Greek-god-named AI agents. Bulls argue. Bears challenge. Risk vetoes.
          Execution sizes. Every approval — and every restraint — is anchored on-chain on
          Circle&apos;s Arc Testnet.
        </p>
        <div className="flex flex-wrap gap-3 pt-2">
          <Button asChild size="lg">
            <Link href="/demo">
              Watch a deliberation
              <ArrowRight className="ml-1" />
            </Link>
          </Button>
          <Button asChild size="lg" variant="outline">
            <a href="https://github.com" target="_blank" rel="noopener noreferrer">
              <Code2 />
              Source code
            </a>
          </Button>
        </div>

        <div className="mt-10 grid grid-cols-2 gap-4 md:grid-cols-4">
          <Stat label="Council agents" value="10" />
          <Stat label="Rounds of debate" value="4" />
          <Stat label="Veto powers" value="2" />
          <Stat label="On-chain witnesses" value="∞" />
        </div>
      </section>

      <Separator />

      {/* ── How it works ─────────────────────────────────────────────── */}
      <section className="space-y-8">
        <SectionHeader index="01" eyebrow="Architecture" title="How it works" />
        <ol className="space-y-3">
          {PIPELINE.map((p) => {
            const Icon = p.icon;
            return (
              <li key={p.step}>
                <Card className="transition-colors hover:border-primary/50">
                  <CardContent className="flex items-center gap-4 p-4">
                    <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-md bg-primary/15 font-mono text-sm text-primary">
                      {p.step}
                    </div>
                    <Icon className="size-5 shrink-0 text-primary/70" />
                    <div className="font-mono w-32 shrink-0 text-foreground">{p.name}</div>
                    <div className="text-sm text-muted-foreground">{p.what}</div>
                  </CardContent>
                </Card>
              </li>
            );
          })}
        </ol>
      </section>

      {/* ── Proof of Restraint ───────────────────────────────────────── */}
      <Card className="border-primary/40 bg-gradient-to-br from-card/80 to-primary/5">
        <CardHeader className="p-8 md:p-12">
          <Badge variant="outline" className="w-fit border-primary/50">
            02 · The flagship feature
          </Badge>
          <CardTitle className="!mt-4 text-3xl">Proof of Restraint</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4 px-8 pb-8 md:px-12 md:pb-12">
          <p className="max-w-3xl text-muted-foreground">
            When the council declines a trade, it does not simply walk away. Areopagus writes a
            cryptographic witness to the{" "}
            <code className="font-mono text-primary">ProofOfRestraint</code> contract on Arc,
            recording the signal hash, the rejection reason, and the price the council refused.
            If the market later moves against the rejected direction, that restraint is
            retroactively a winning decision — and it is provably ours.
          </p>
          <p className="max-w-3xl text-muted-foreground">
            The watchword: <em className="text-primary">no-trade alpha</em>. Discipline is alpha.
            Restraint is witnessed.
          </p>
          <Button asChild variant="link" className="px-0 text-primary">
            <Link href="/demo?scenario=restraint">
              See a Zeus veto in action <ArrowRight />
            </Link>
          </Button>
        </CardContent>
      </Card>

      {/* ── Agent roster ─────────────────────────────────────────────── */}
      <section className="space-y-8">
        <SectionHeader
          index="03"
          eyebrow="The pantheon"
          title="22 agents, one council"
          subtitle="Ten deliberate. Twelve more orchestrate, archive, and score. Each has a specific role, a specific weight, and — for Zeus and Solon — the authority to halt a trade unilaterally."
        />
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {AGENTS.map((a) => (
            <Card key={a.name} className="transition-colors hover:border-primary/50">
              <CardContent className="p-4">
                <div className="flex items-center justify-between gap-2">
                  <div className="font-mono text-primary">{a.name}</div>
                  <div className="flex items-center gap-2">
                    {a.veto && <Badge variant="destructive">Veto</Badge>}
                    <Badge variant="muted">{a.class}</Badge>
                  </div>
                </div>
                <div className="mt-1 text-sm text-muted-foreground">{a.role}</div>
              </CardContent>
            </Card>
          ))}
        </div>
      </section>

      {/* ── Stack ────────────────────────────────────────────────────── */}
      <section className="space-y-6">
        <SectionHeader index="04" eyebrow="Stack" title="Built on" />
        <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
          <StackItem label="Council" value="Claude / Gemini" />
          <StackItem label="Settlement" value="Polymarket CLOB" />
          <StackItem label="Chain" value="Circle Arc Testnet" />
          <StackItem label="Storage" value="IPFS + Irys" />
          <StackItem label="Backend" value="FastAPI · Redis · Postgres" />
          <StackItem label="Contracts" value="Solidity 0.8.24 + Foundry" />
          <StackItem label="Frontend" value="Next.js 14 + shadcn/ui" />
          <StackItem label="Mono" value="pnpm · Turborepo · uv" />
        </div>
      </section>

      {/* ── CTA ──────────────────────────────────────────────────────── */}
      <Card className="border-primary/40">
        <CardContent className="p-12 text-center">
          <CardTitle className="text-3xl">See the council in session</CardTitle>
          <CardDescription className="mx-auto mt-3 max-w-xl">
            A captured Gemini deliberation. Watch ten agents argue a BTC $120k market,
            then watch Areopagus size — or refuse — the trade.
          </CardDescription>
          <div className="mt-6 flex flex-wrap justify-center gap-3">
            <Button asChild size="lg">
              <Link href="/demo?scenario=approve">
                Approval scenario <ArrowRight />
              </Link>
            </Button>
            <Button asChild size="lg" variant="outline">
              <Link href="/demo?scenario=restraint">
                Restraint scenario <ArrowRight />
              </Link>
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

function SectionHeader({
  index,
  eyebrow,
  title,
  subtitle,
}: {
  index: string;
  eyebrow: string;
  title: string;
  subtitle?: string;
}) {
  return (
    <div className="space-y-2">
      <Badge variant="outline" className="border-primary/40">
        {index} · {eyebrow}
      </Badge>
      <h2 className="font-mono text-3xl text-foreground">{title}</h2>
      {subtitle && <p className="max-w-2xl text-muted-foreground">{subtitle}</p>}
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <Card>
      <CardContent className="p-4">
        <div className="font-mono text-3xl text-primary">{value}</div>
        <div className="mt-1 text-xs uppercase tracking-wider text-muted-foreground">
          {label}
        </div>
      </CardContent>
    </Card>
  );
}

function StackItem({ label, value }: { label: string; value: string }) {
  return (
    <Card>
      <CardContent className="p-4">
        <div className="text-xs uppercase tracking-wider text-muted-foreground">{label}</div>
        <div className="mt-1 font-mono text-foreground">{value}</div>
      </CardContent>
    </Card>
  );
}
