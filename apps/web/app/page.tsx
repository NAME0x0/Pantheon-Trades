import Link from "next/link";
import Image from "next/image";
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

// Hero backdrop: Parthenon at golden hour, served by Unsplash's CDN with
// width-cropped params so the bandwidth stays small. Heavily dimmed by an
// overlay so the foreground type stays legible.
const PARTHENON_HERO =
  "https://images.unsplash.com/photo-1555993539-1732b0258235?auto=format&fit=crop&w=1600&q=70";

const COUNCIL_BACKDROP =
  "https://images.unsplash.com/photo-1599423300746-b62533397364?auto=format&fit=crop&w=1400&q=70";

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
  { step: "I",   name: "Apollo",     icon: Eye,         what: "Scores Polymarket signals across 7 dimensions" },
  { step: "II",  name: "Boule",      icon: Vote,        what: "Convenes 10-agent council across 4 rounds of debate" },
  { step: "III", name: "Areopagus",  icon: Gavel,       what: "Half-Kelly sizing and constitutional gates" },
  { step: "IVa", name: "Strategos",  icon: Hammer,      what: "Routes approved trade to CLOB" },
  { step: "IVb", name: "Parthenon",  icon: ShieldCheck, what: "Writes Proof of Restraint on rejection" },
  { step: "V",   name: "Argos",      icon: CircleDot,   what: "Monitors the position, fires the exit when conditions trigger" },
  { step: "VI",  name: "Ostrakon",   icon: Sparkles,    what: "Scores every agent's contribution after settlement" },
];

export default function Home() {
  return (
    <div className="space-y-28 pb-12">
      {/* ── Hero ─────────────────────────────────────────────────────── */}
      <section className="relative -mx-6 -mt-8 overflow-hidden px-6 py-20 md:py-28">
        <div className="absolute inset-0 -z-10">
          <Image
            src={PARTHENON_HERO}
            alt=""
            fill
            priority
            sizes="100vw"
            className="object-cover opacity-25"
          />
          <div className="absolute inset-0 bg-gradient-to-b from-background/95 via-background/85 to-background" />
        </div>

        <div className="relative space-y-7">
          <div className="flex items-center gap-3">
            <Image
              src="/mark.svg"
              alt="Pantheon Trades emblem"
              width={64}
              height={64}
              priority
              className="drop-shadow-[0_0_20px_rgba(200,168,90,0.35)]"
            />
            <Badge variant="outline" className="border-primary/40 font-display tracking-[0.25em]">
              Arc Testnet · chain id 5042002
            </Badge>
          </div>

          <h1 className="font-display text-5xl md:text-7xl font-semibold tracking-[0.02em] leading-[1.05] text-foreground">
            A council of ten gods
            <br />
            <span className="italic font-serif font-medium text-primary">
              debates every trade.
            </span>
          </h1>

          <p className="max-w-2xl font-serif text-xl md:text-[1.35rem] leading-relaxed text-muted-foreground">
            Pantheon Trades runs Polymarket signals through a structured four-round
            deliberation between Greek-god-named AI agents. Bulls argue. Bears challenge.
            Risk vetoes. Execution sizes. Every approval — and every restraint — is anchored
            on-chain on Circle&apos;s Arc Testnet.
          </p>

          <div className="flex flex-wrap gap-3 pt-2">
            <Button asChild size="lg">
              <Link href="/demo">
                Watch a deliberation
                <ArrowRight className="ml-1" />
              </Link>
            </Button>
            <Button asChild size="lg" variant="outline">
              <a
                href="https://github.com/NAME0x0/Pantheon-Trades"
                target="_blank"
                rel="noopener noreferrer"
              >
                <Code2 />
                Source code
              </a>
            </Button>
          </div>

          <div className="mt-12 grid grid-cols-2 gap-4 md:grid-cols-4">
            <Stat label="Council agents" value="10" />
            <Stat label="Rounds of debate" value="4" />
            <Stat label="Veto powers" value="2" />
            <Stat label="On-chain witnesses" value="∞" />
          </div>
        </div>
      </section>

      <Meander />

      {/* ── How it works ─────────────────────────────────────────────── */}
      <section className="space-y-8">
        <SectionHeader index="I" eyebrow="Architecture" title="How it works" />
        <ol className="space-y-3">
          {PIPELINE.map((p) => {
            const Icon = p.icon;
            return (
              <li key={p.step}>
                <Card className="transition-colors hover:border-primary/50">
                  <CardContent className="flex items-center gap-4 p-4">
                    <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-md border border-primary/40 bg-primary/10 font-display text-base text-primary">
                      {p.step}
                    </div>
                    <Icon className="size-5 shrink-0 text-primary/70" />
                    <div className="w-32 shrink-0 font-display tracking-[0.16em] text-foreground">
                      {p.name}
                    </div>
                    <div className="font-serif text-base text-muted-foreground">
                      {p.what}
                    </div>
                  </CardContent>
                </Card>
              </li>
            );
          })}
        </ol>
      </section>

      <Meander />

      {/* ── Proof of Restraint ───────────────────────────────────────── */}
      <Card className="relative overflow-hidden border-primary/40">
        <Image
          src={COUNCIL_BACKDROP}
          alt=""
          fill
          sizes="(min-width: 1024px) 1024px, 100vw"
          className="object-cover opacity-[0.07]"
        />
        <CardHeader className="relative p-8 md:p-12">
          <Badge variant="outline" className="w-fit border-primary/50 font-display tracking-[0.25em]">
            II · The flagship feature
          </Badge>
          <CardTitle className="!mt-4 font-display text-4xl tracking-[0.02em] text-foreground">
            Proof of Restraint
          </CardTitle>
        </CardHeader>
        <CardContent className="relative space-y-4 px-8 pb-12 md:px-12 md:pb-14">
          <p className="max-w-3xl font-serif text-lg leading-relaxed text-muted-foreground">
            When the council declines a trade, it does not simply walk away. Areopagus writes
            a cryptographic witness to the{" "}
            <code className="font-mono text-primary">ProofOfRestraint</code> contract on Arc,
            recording the signal hash, the rejection reason, and the price the council
            refused. If the market later moves against the rejected direction, that restraint
            is retroactively a winning decision — and it is provably ours.
          </p>
          <p className="max-w-3xl font-serif text-lg italic leading-relaxed text-muted-foreground">
            The watchword: <span className="not-italic text-primary">no-trade alpha</span>.
            Discipline is alpha. Restraint is witnessed.
          </p>
          <Button asChild variant="link" className="px-0 text-primary">
            <Link href="/demo?scenario=restraint">
              See a Zeus veto in action <ArrowRight />
            </Link>
          </Button>
        </CardContent>
      </Card>

      <Meander />

      {/* ── Agent roster ─────────────────────────────────────────────── */}
      <section className="space-y-8">
        <SectionHeader
          index="III"
          eyebrow="The pantheon"
          title="22 agents, one council"
          subtitle="Ten deliberate. Twelve more orchestrate, archive, and score. Each has a specific role, a specific weight, and — for Zeus and Solon — the authority to halt a trade unilaterally."
        />
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {AGENTS.map((a) => (
            <Card key={a.name} className="transition-colors hover:border-primary/50">
              <CardContent className="p-4">
                <div className="flex items-center justify-between gap-2">
                  <div className="font-display tracking-[0.15em] text-primary">{a.name}</div>
                  <div className="flex items-center gap-2">
                    {a.veto && <Badge variant="destructive">Veto</Badge>}
                    <Badge variant="muted">{a.class}</Badge>
                  </div>
                </div>
                <div className="mt-1 font-serif text-sm text-muted-foreground">{a.role}</div>
              </CardContent>
            </Card>
          ))}
        </div>
      </section>

      <Meander />

      {/* ── Stack ────────────────────────────────────────────────────── */}
      <section className="space-y-6">
        <SectionHeader index="IV" eyebrow="Stack" title="Built on" />
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

      <Meander />

      {/* ── CTA ──────────────────────────────────────────────────────── */}
      <Card className="border-primary/40">
        <CardContent className="p-12 text-center">
          <CardTitle className="font-display text-4xl tracking-[0.02em] text-foreground">
            See the council in session
          </CardTitle>
          <CardDescription className="mx-auto mt-3 max-w-xl font-serif text-base">
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
      <Badge variant="outline" className="border-primary/40 font-display tracking-[0.25em]">
        {index} · {eyebrow}
      </Badge>
      <h2 className="font-display text-4xl font-medium tracking-[0.02em] text-foreground">
        {title}
      </h2>
      {subtitle && (
        <p className="max-w-2xl font-serif text-lg leading-relaxed text-muted-foreground">
          {subtitle}
        </p>
      )}
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <Card>
      <CardContent className="p-4">
        <div className="font-display text-3xl font-semibold text-primary">{value}</div>
        <div className="mt-1 font-display text-[10px] uppercase tracking-[0.2em] text-muted-foreground">
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
        <div className="font-display text-[10px] uppercase tracking-[0.2em] text-muted-foreground">
          {label}
        </div>
        <div className="mt-1 font-display text-lg tracking-[0.08em] text-foreground">
          {value}
        </div>
      </CardContent>
    </Card>
  );
}

function Meander() {
  // Decorative Greek-key divider between sections.
  return (
    <div className="flex justify-center" aria-hidden>
      <Image
        src="/meander.svg"
        alt=""
        width={240}
        height={16}
        className="opacity-60"
      />
    </div>
  );
}
