"use client";

import Link from "next/link";
import Image from "next/image";
import dynamic from "next/dynamic";
import { useState } from "react";
import { ArrowRight, ArrowUpRight } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Reveal, Counter, Typewriter, Marquee } from "@/components/anim";
import {
  Magnetic,
  ScaleTiltSlider,
  VoteSimulator,
} from "@/components/widgets";
import { BRAND_MARK, PHOTO } from "@/lib/cdn";

// R3F is heavy — keep it client-only and lazy so first paint stays cheap.
const HeroScene = dynamic(() => import("@/components/hero-scene"), {
  ssr: false,
  loading: () => <HeroSceneFallback />,
});

const FIRST_PROOF_TX =
  "0xf9ae0e7ba73ecaece1af840b20e2ef5a20868df960e62ba238e53a828dfa4edb";
const ARCSCAN_BASE = "https://testnet.arcscan.app";

const AGENTS = [
  { name: "Apollo",     greek: "ΑΠΟΛΛΩΝ",        role: "Sees the future. Scores Polymarket signals." },
  { name: "Boule",      greek: "ΒΟΥΛΗ",          role: "Convenes the council. Four rounds of debate." },
  { name: "Ares",       greek: "ΑΡΗΣ",           role: "Bull researcher — argues the long case." },
  { name: "Hades",      greek: "ΑΙΔΗΣ",          role: "Bull researcher — surfaces hidden depth." },
  { name: "Athena",     greek: "ΑΘΗΝΑ",          role: "Bear researcher and synthesiser." },
  { name: "Cassandra",  greek: "ΚΑΣΣΑΝΔΡΑ",      role: "Bear researcher — flags tail risk." },
  { name: "Solon",      greek: "ΣΟΛΩΝ",          role: "Constitutional check. Veto authority.", veto: true },
  { name: "Zeus",       greek: "ΖΕΥΣ",           role: "Supreme veto. Hard constitutional gate.", veto: true },
  { name: "Themis",     greek: "ΘΕΜΙΣ",          role: "Procedural integrity. Reviews the trace." },
  { name: "Hephaestus", greek: "ΗΦΑΙΣΤΟΣ",       role: "Execution — sizes and routes." },
  { name: "Daedalus",   greek: "ΔΑΙΔΑΛΟΣ",       role: "Execution — strategy fit." },
  { name: "Humans",     greek: "ΑΝΘΡΩΠΟΙ",       role: "Execution — crowd sentiment." },
  { name: "Eris",       greek: "ΕΡΙΣ",           role: "Adversarial dissent. Breaks groupthink.", adversarial: true },
];

// Seven-tier robustness pass — what landed after the founding council.
const TIER_BUILD = [
  {
    tier: "A",
    title: "Survival foundation",
    features: [
      "Prometheus + Grafana on every council service",
      "Polymarket L2 WebSocket depth",
      "Correlation-aware portfolio sizing",
      "Multi-sig admin migration script",
      "Hypothesis property tests across sizing / slippage / calibration",
    ],
  },
  {
    tier: "B",
    title: "Execution quality",
    features: [
      "Drawdown-adjusted Kelly haircut",
      "Walk-forward + decayed agent calibration",
      "Argos resolution-lag state machine",
      "Strategos maker/taker chooser",
      "Online slippage learner from realised fills",
    ],
  },
  {
    tier: "C",
    title: "Intelligence",
    features: [
      "RAG over resolved markets (in-memory + ChromaDB)",
      "Eris adversarial dissenter against consensus",
      "Reflection-driven prompt evolution",
      "Leave-one-out agent ablation scoring",
      "Nitter RSS crowd-sentiment feed",
    ],
  },
  {
    tier: "D",
    title: "Venues and data",
    features: [
      "Kalshi venue connector",
      "DeFiLlama TVL + stablecoin flows + yields",
      "TradingView screener adapter",
      "spaCy / regex headline NER → market matcher",
    ],
  },
  {
    tier: "E",
    title: "Operational maturity",
    features: [
      "Alembic async migrations",
      "Hourly Postgres + Redis backup service",
      "Mozilla SOPS + age secrets",
      "slowapi global rate limiting",
      "Deep /health/deep probes",
    ],
  },
  {
    tier: "F",
    title: "Frontend",
    features: [
      "Pure-SVG Sankey trace flow",
      "Equity / Sharpe / PnL chart primitives",
      "Manual trade-approval card",
      "Brier-ranked agent leaderboard",
    ],
  },
  {
    tier: "G",
    title: "Safety hygiene",
    features: [
      "mutmut mutation testing scaffold",
      "Shopify Toxiproxy chaos drills",
      "a16z Halmos symbolic verification",
      "IRS Form 8949 tax CSV export",
    ],
  },
];

const PIPELINE = [
  { numeral: "I",   name: "Pythia",     role: "the oracle",      what: "Watches Polymarket. Watches the news. Listens." },
  { numeral: "II",  name: "Apollo",     role: "the seer",        what: "Scores every signal across seven dimensions." },
  { numeral: "III", name: "Boule",      role: "the assembly",    what: "Calls the council. Four rounds. Ten voices." },
  { numeral: "IV",  name: "Areopagus",  role: "the court",       what: "Gates the verdict. Sizes by half-Kelly. Vetoes the rest." },
  { numeral: "V",   name: "Strategos",  role: "the general",     what: "Routes the trade. Or watches it pass." },
  { numeral: "VI",  name: "Parthenon",  role: "the temple",      what: "Anchors the witness. On chain. Forever." },
];

export default function Home() {
  const [tilt, setTilt] = useState(0);

  return (
    <div className="pb-12">
      {/* ── HERO ────────────────────────────────────────────────────── */}
      <section className="relative -mx-6 min-h-[88vh] overflow-hidden px-6 pb-12 pt-12">
        <div className="absolute inset-0 -z-10">
          <Image
            src={PHOTO.parthenon}
            alt=""
            fill
            priority
            sizes="100vw"
            className="object-cover opacity-[0.18]"
          />
          <div className="absolute inset-0 bg-gradient-to-b from-background/70 via-background/85 to-background" />
          <div className="absolute inset-0 bg-gradient-to-r from-background via-background/60 to-transparent" />
        </div>

        <div className="grid items-center gap-12 lg:grid-cols-[1.15fr_1fr] lg:gap-16">
          {/* Left column — copy */}
          <div className="space-y-10 pt-10">
            <Reveal y={12}>
              <div className="display flex items-center gap-3 text-[10px] uppercase tracking-[0.45em] text-primary">
                <span className="inline-block size-1.5 rounded-full bg-primary animate-pulse" />
                Arc Testnet · chain 5042002
              </div>
            </Reveal>

            <Reveal delay={0.05}>
              <h1 className="display text-[clamp(3.25rem,7.6vw,7rem)] font-medium leading-[0.94] tracking-[-0.018em] text-foreground">
                A council of
                <br />
                <span className="serif font-medium italic text-primary">
                  ten gods
                </span>
                <br />
                debates every trade.
              </h1>
            </Reveal>

            <Reveal delay={0.15}>
              <p className="serif max-w-[42ch] text-[1.35rem] leading-[1.65] text-muted-foreground">
                Bulls argue. Bears challenge. Risk vetoes. Execution sizes.
                Every approval — and{" "}
                <span className="italic text-primary">every restraint</span> —
                is anchored on chain.
              </p>
            </Reveal>

            <Reveal delay={0.25}>
              <div className="flex flex-wrap items-center gap-5 pt-2">
                <Button asChild size="lg" className="display h-12 px-7 text-[11px] uppercase tracking-[0.32em]">
                  <Link href="/demo">
                    Watch the council <ArrowRight className="ml-1" />
                  </Link>
                </Button>
                <Link
                  href="/demo?scenario=restraint"
                  className="display group inline-flex items-center gap-2 text-[11px] uppercase tracking-[0.32em] text-muted-foreground transition-colors hover:text-primary"
                >
                  See a Zeus veto
                  <ArrowUpRight className="size-3 transition-transform group-hover:translate-x-0.5 group-hover:-translate-y-0.5" />
                </Link>
              </div>
            </Reveal>

            <Reveal delay={0.4}>
              <div className="rule max-w-md" />
            </Reveal>

            <div className="grid max-w-2xl grid-cols-2 gap-x-10 gap-y-6 pt-2 md:grid-cols-4">
              <HeroStat value={11} label="Council agents" />
              <HeroStat value={4} label="Rounds of debate" />
              <HeroStat value={334} label="Python tests" />
              <HeroStat value={1} label="On-chain witness" />
            </div>
          </div>

          {/* Right column — 3D scene with caption + interactive tilt */}
          <div className="flex flex-col items-center gap-6">
            <div className="relative h-[420px] w-full overflow-visible lg:h-[540px]">
              <HeroScene tilt={tilt} />
            </div>
            <div className="display text-center text-[10px] uppercase tracking-[0.45em] text-primary/60">
              ✦ Pondera Iustitiae ✦
            </div>
            <div className="w-full max-w-sm">
              <ScaleTiltSlider tilt={tilt} onTilt={setTilt} />
            </div>
          </div>
        </div>
      </section>

      {/* ── MARQUEE ─────────────────────────────────────────────────── */}
      <Reveal>
        <div className="-mx-6 my-10 border-y border-primary/15 bg-card/30 py-5">
          <Marquee speed={48}>
            {[
              "ΑΠΟΛΛΩΝ — sees the future",
              "ΑΡΗΣ — argues the long case",
              "ΑΘΗΝΑ — synthesises the council",
              "ΖΕΥΣ — supreme veto",
              "ΣΟΛΩΝ — constitutional check",
              "ΗΦΑΙΣΤΟΣ — sizes the trade",
              "ΘΕΜΙΣ — procedural integrity",
              "ΚΑΣΣΑΝΔΡΑ — flags tail risk",
              "ΑΙΔΗΣ — surfaces hidden depth",
              "ΑΝΘΡΩΠΟΙ — crowd sentiment",
            ].map((t) => (
              <span
                key={t}
                className="display text-[11px] uppercase tracking-[0.4em] text-muted-foreground"
              >
                {t}
                <span className="ml-12 text-primary/40">✦</span>
              </span>
            ))}
          </Marquee>
        </div>
      </Reveal>

      {/* ── PREMISE — editorial drop-cap paragraph ─────────────────── */}
      <section className="relative mx-auto max-w-3xl py-24">
        <div className="absolute inset-y-0 right-0 -z-10 hidden w-1/3 opacity-[0.10] lg:block">
          <Image
            src={PHOTO.columns}
            alt=""
            fill
            sizes="33vw"
            className="object-cover"
          />
        </div>

        <Reveal>
          <Eyebrow numeral="I" label="The premise" />
        </Reveal>
        <Reveal delay={0.1}>
          <h2 className="display mb-10 text-5xl font-medium leading-[1.05] tracking-[-0.01em] text-foreground md:text-6xl">
            Most trading bots optimise one number.
            <br />
            <span className="serif italic text-primary">
              We optimise for the trades we refuse.
            </span>
          </h2>
        </Reveal>
        <Reveal delay={0.15}>
          <p className="serif dropcap text-[1.25rem] leading-[1.8] text-muted-foreground">
            Pantheon Trades is built on a single conviction: discipline is alpha.
            Every Polymarket signal flows through a structured four-round
            deliberation between ten Greek-god-named AI agents. The bulls
            argue the long case. The bears challenge it. The risk triad —
            Zeus, Solon, Themis — checks the constitution. Athena synthesises.
            Then the council votes. The verdict, whether to trade or to refuse,
            is anchored as a cryptographic witness on Circle&apos;s Arc Testnet.
            Discipline becomes auditable. Restraint becomes provable. The
            chain remembers what we chose not to do.
          </p>
        </Reveal>
      </section>

      {/* ── PIPELINE — six classical acts ──────────────────────────── */}
      <section className="py-20">
        <Reveal>
          <Eyebrow numeral="II" label="The architecture" />
        </Reveal>
        <Reveal delay={0.05}>
          <h2 className="display mb-16 max-w-3xl text-5xl font-medium leading-[1.05] tracking-[-0.01em] text-foreground md:text-6xl">
            Six acts. One thesis.
            <br />
            <span className="serif italic text-primary">
              From signal to settlement.
            </span>
          </h2>
        </Reveal>

        <ol className="space-y-px">
          {PIPELINE.map((step, i) => (
            <Reveal key={step.numeral} delay={i * 0.04}>
              <div className="group relative grid grid-cols-[5rem_1fr] items-baseline gap-6 border-t border-primary/15 py-8 transition-colors hover:bg-primary/[0.03] md:grid-cols-[6rem_15rem_1fr]">
                <span className="display text-3xl font-semibold text-primary/70 transition-colors group-hover:text-primary md:text-4xl">
                  {step.numeral}
                </span>
                <div className="md:col-span-1">
                  <div className="display text-xl tracking-[0.16em] text-foreground md:text-2xl">
                    {step.name.toUpperCase()}
                  </div>
                  <div className="serif mt-1 text-base italic text-primary/80">
                    {step.role}
                  </div>
                </div>
                <p className="serif col-start-2 text-lg leading-[1.7] text-muted-foreground md:col-start-3 md:text-xl">
                  {step.what}
                </p>
              </div>
            </Reveal>
          ))}
          <div className="border-t border-primary/15" />
        </ol>
      </section>

      {/* ── TIER A-G — what landed after the founding council ──────── */}
      <section className="py-20">
        <Reveal>
          <Eyebrow numeral="II·5" label="Seven tiers of hardening" />
        </Reveal>
        <Reveal delay={0.05}>
          <h2 className="display mb-6 max-w-3xl text-5xl font-medium leading-[1.05] tracking-[-0.01em] text-foreground md:text-6xl">
            Built for the trades we refuse,
            <br />
            <span className="serif italic text-primary">
              hardened for the ones we take.
            </span>
          </h2>
        </Reveal>
        <Reveal delay={0.1}>
          <p className="serif mb-12 max-w-3xl text-lg leading-[1.7] text-muted-foreground">
            Thirty-five commits across seven tiers landed the safety,
            intelligence, observability, and venue surface a live trading
            council needs. Every upstream picked is open-source MIT or
            Apache — no paid vendor lock-in.
          </p>
        </Reveal>
        <div className="grid gap-5 md:grid-cols-2 lg:grid-cols-3">
          {TIER_BUILD.map((t) => (
            <Reveal key={t.tier} delay={0.05}>
              <article className="h-full rounded-lg border border-primary/20 bg-card/40 p-6">
                <header className="mb-4 flex items-baseline justify-between">
                  <span className="display text-[10px] uppercase tracking-[0.45em] text-primary">
                    Tier {t.tier}
                  </span>
                  <span className="serif italic text-sm text-muted-foreground">
                    {t.title}
                  </span>
                </header>
                <ul className="space-y-2">
                  {t.features.map((f) => (
                    <li
                      key={f}
                      className="serif text-sm leading-relaxed text-foreground/90"
                    >
                      <span className="mr-2 text-primary/60">·</span>
                      {f}
                    </li>
                  ))}
                </ul>
              </article>
            </Reveal>
          ))}
        </div>
      </section>

      {/* ── VOTE SIMULATOR (interactive widget) ─────────────────────── */}
      <section className="relative -mx-6 my-12 overflow-hidden rounded-3xl border border-primary/15 px-6 py-20 md:py-24">
        <div className="absolute inset-0 -z-10">
          <Image
            src={PHOTO.olympia}
            alt=""
            fill
            sizes="100vw"
            className="object-cover opacity-[0.08]"
          />
          <div className="absolute inset-0 bg-gradient-to-br from-background/95 to-background/80" />
        </div>

        <div className="mx-auto max-w-5xl">
          <Reveal>
            <Eyebrow numeral="III" label="Cast a vote" />
          </Reveal>
          <Reveal delay={0.05}>
            <h2 className="display mb-4 max-w-3xl text-5xl font-medium leading-[1.05] tracking-[-0.01em] text-foreground md:text-6xl">
              Take a seat in the Areopagus.
            </h2>
          </Reveal>
          <Reveal delay={0.1}>
            <p className="serif mb-12 max-w-2xl text-xl leading-[1.7] text-muted-foreground">
              The full council. Three states. Real weights from the
              constitution. Click an agent to cycle their vote — watch the
              verdict update live. Zeus and Solon can veto the whole room.
            </p>
          </Reveal>
          <Reveal delay={0.15}>
            <VoteSimulator />
          </Reveal>
        </div>
      </section>

      {/* ── PROOF OF RESTRAINT — cinematic ─────────────────────────── */}
      <section className="relative -mx-6 my-12 overflow-hidden px-6 py-32">
        <div className="absolute inset-0 -z-10">
          <Image
            src={PHOTO.bust}
            alt=""
            fill
            sizes="100vw"
            className="object-cover opacity-[0.16]"
          />
          <div className="absolute inset-0 bg-gradient-to-br from-background via-background/85 to-background/95" />
        </div>

        <div className="mx-auto max-w-4xl">
          <Reveal>
            <Eyebrow numeral="IV" label="The flagship feature" />
          </Reveal>
          <Reveal delay={0.05}>
            <h2 className="display mt-6 text-[clamp(2.75rem,6.5vw,5.5rem)] font-medium leading-[0.98] tracking-[-0.015em] text-foreground">
              <span className="serif italic text-primary">When the council says no,</span>
              <br />
              the chain remembers.
            </h2>
          </Reveal>

          <Reveal delay={0.15}>
            <p className="serif mt-10 max-w-2xl text-[1.35rem] leading-[1.75] text-muted-foreground">
              Areopagus writes a <code className="mono text-primary">Restrained</code>{" "}
              event to the <code className="mono text-primary">ProofOfRestraint</code>{" "}
              contract on Arc — binding signal hash, market, reason, and the
              note the council attached to the refusal. If the market later
              moves against the rejected direction, that restraint is provably
              ours.
            </p>
          </Reveal>

          <Reveal delay={0.25}>
            <div className="plinth mt-14 rounded-2xl p-6 md:p-8">
              <div className="display text-[10px] uppercase tracking-[0.45em] text-primary">
                First witness · block 42,337,549
              </div>
              <div className="mt-4 break-all">
                <Typewriter
                  text={FIRST_PROOF_TX}
                  speed={18}
                  className="text-[0.9rem] leading-relaxed text-primary/90 md:text-[1.05rem]"
                />
              </div>
              <div className="mt-6 grid grid-cols-1 gap-x-8 gap-y-3 text-sm md:grid-cols-3">
                <KV k="onchain_proof_id" v="1" />
                <KV k="reason" v="ZEUS_VETO" />
                <KV k="contract" v="0x4b35…4895" />
              </div>
              <a
                href={`${ARCSCAN_BASE}/tx/${FIRST_PROOF_TX}`}
                target="_blank"
                rel="noopener noreferrer"
                className="display mt-8 inline-flex items-center gap-2 text-[11px] uppercase tracking-[0.32em] text-primary transition-opacity hover:opacity-80"
              >
                Verify on Arcscan <ArrowUpRight className="size-3.5" />
              </a>
            </div>
          </Reveal>

          <Reveal delay={0.3}>
            <p className="serif mt-10 text-2xl italic text-primary md:text-3xl">
              The watchword: <span className="not-italic">no-trade alpha</span>.
            </p>
          </Reveal>
        </div>
      </section>

      {/* ── COUNCIL — agent roster (stacked Greek over English) ────── */}
      <section className="relative py-24">
        <div className="absolute right-0 top-12 -z-10 hidden h-full w-1/3 opacity-[0.08] lg:block">
          <Image
            src={PHOTO.profile}
            alt=""
            fill
            sizes="33vw"
            className="object-cover object-right"
          />
        </div>

        <Reveal>
          <Eyebrow numeral="V" label="The pantheon" />
        </Reveal>
        <Reveal delay={0.05}>
          <h2 className="display mb-4 max-w-3xl text-5xl font-medium leading-[1.05] tracking-[-0.01em] text-foreground md:text-6xl">
            Twelve in the chamber.
            <br />
            <span className="serif italic text-primary">
              Two with the supreme veto.
            </span>
          </h2>
        </Reveal>
        <Reveal delay={0.1}>
          <p className="serif mb-14 max-w-2xl text-xl leading-[1.7] text-muted-foreground">
            Ten deliberate. Two more orchestrate the room. Each has a name,
            a weight, and a voice — and Zeus or Solon can halt a trade
            unilaterally if it breaches the constitution.
          </p>
        </Reveal>

        <div className="grid grid-cols-1 gap-px overflow-hidden rounded-2xl border border-primary/15 sm:grid-cols-2 lg:grid-cols-3">
          {AGENTS.map((a, i) => (
            <Reveal key={a.name} delay={Math.min(i * 0.03, 0.3)}>
              <div className="group relative h-full bg-card/40 p-7 transition-colors hover:bg-primary/[0.04]">
                <div className="display mb-1 text-[10px] uppercase tracking-[0.45em] text-primary/65">
                  {a.greek}
                </div>
                <div className="display flex items-center gap-2 text-2xl tracking-[0.12em] text-foreground">
                  {a.name.toUpperCase()}
                  {a.veto && (
                    <span
                      className="mono rounded-sm border border-destructive/40 bg-destructive/15 px-1.5 py-0.5 text-[9px] uppercase tracking-[0.18em] text-destructive-foreground/90"
                      title="veto authority"
                    >
                      ⚡ veto
                    </span>
                  )}
                </div>
                <div className="serif mt-3 text-base leading-[1.6] text-muted-foreground">
                  {a.role}
                </div>
                <div className="mt-4 h-px w-8 bg-primary/40 transition-all duration-500 group-hover:w-20" />
              </div>
            </Reveal>
          ))}
        </div>
      </section>

      {/* ── STACK ──────────────────────────────────────────────────── */}
      <section className="relative -mx-6 overflow-hidden px-6 py-24">
        <div className="absolute inset-0 -z-10">
          <Image
            src={PHOTO.marble}
            alt=""
            fill
            sizes="100vw"
            className="object-cover opacity-[0.08]"
          />
          <div className="absolute inset-0 bg-gradient-to-b from-background via-background/90 to-background" />
        </div>

        <Reveal>
          <Eyebrow numeral="VI" label="The stack" />
        </Reveal>
        <Reveal delay={0.05}>
          <h2 className="display mb-14 max-w-3xl text-5xl font-medium leading-[1.05] tracking-[-0.01em] text-foreground md:text-6xl">
            Built on the things
            <br />
            <span className="serif italic text-primary">
              that don&apos;t break.
            </span>
          </h2>
        </Reveal>
        <div className="grid grid-cols-1 gap-px overflow-hidden rounded-xl border border-primary/15 sm:grid-cols-2 lg:grid-cols-4">
          {[
            { k: "Council",    v: "Claude · Gemini" },
            { k: "Markets",    v: "Polymarket CLOB" },
            { k: "Chain",      v: "Arc Testnet" },
            { k: "Storage",    v: "IPFS · Irys" },
            { k: "Backend",    v: "FastAPI · Redis" },
            { k: "Contracts",  v: "Solidity 0.8.24" },
            { k: "Frontend",   v: "Next.js · shadcn" },
            { k: "Mono",       v: "pnpm · Turborepo" },
          ].map((s, i) => (
            <Reveal key={s.k} delay={i * 0.04}>
              <Magnetic strength={6}>
                <div className="h-full bg-card/40 p-6 transition-colors hover:bg-primary/[0.04]">
                  <div className="display text-[10px] uppercase tracking-[0.35em] text-primary/60">
                    {s.k}
                  </div>
                  <div className="display mt-2 text-lg tracking-[0.06em] text-foreground">
                    {s.v}
                  </div>
                </div>
              </Magnetic>
            </Reveal>
          ))}
        </div>
      </section>

      {/* ── CLOSING CTA ────────────────────────────────────────────── */}
      <section className="relative my-20 overflow-hidden rounded-3xl border border-primary/30 bg-card/40 px-6 py-20 text-center md:py-28">
        <div className="absolute inset-0 -z-10">
          <Image
            src={PHOTO.acropolis}
            alt=""
            fill
            sizes="(min-width: 1024px) 1024px, 100vw"
            className="object-cover opacity-[0.10]"
          />
        </div>

        <Reveal>
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={BRAND_MARK}
            alt=""
            width={56}
            height={56}
            className="mx-auto mb-6 opacity-90 drop-shadow-[0_0_24px_hsl(var(--primary)/0.35)]"
          />
        </Reveal>
        <Reveal delay={0.05}>
          <h2 className="display text-[clamp(2.5rem,6vw,5rem)] font-medium leading-[1.0] tracking-[-0.015em] text-foreground">
            Watch the council
            <br />
            <span className="serif italic text-primary">in session.</span>
          </h2>
        </Reveal>
        <Reveal delay={0.15}>
          <p className="serif mx-auto mt-6 max-w-xl text-xl leading-[1.65] text-muted-foreground">
            A captured Gemini deliberation. Ten agents. Four rounds.
            Watch Areopagus size — or refuse — the trade.
          </p>
        </Reveal>
        <Reveal delay={0.25}>
          <div className="mt-10 flex flex-wrap justify-center gap-4">
            <Button asChild size="lg" className="display h-12 px-8 text-[11px] uppercase tracking-[0.32em]">
              <Link href="/demo?scenario=approve">
                Approval scenario <ArrowRight />
              </Link>
            </Button>
            <Button asChild size="lg" variant="outline" className="display h-12 px-8 text-[11px] uppercase tracking-[0.32em]">
              <Link href="/demo?scenario=restraint">
                Restraint scenario <ArrowRight />
              </Link>
            </Button>
          </div>
        </Reveal>
      </section>
    </div>
  );
}

/* ─── Sub-components ─────────────────────────────────────────────── */

function Eyebrow({ numeral, label }: { numeral: string; label: string }) {
  return (
    <div className="display flex items-center gap-4 text-[10px] uppercase tracking-[0.45em] text-primary">
      <span className="text-primary/80">{numeral}</span>
      <span className="block h-px w-10 bg-primary/40" />
      <span className="text-muted-foreground">{label}</span>
    </div>
  );
}

function HeroStat({ value, label }: { value: number; label: string }) {
  return (
    <div>
      <div className="display text-4xl font-semibold leading-none text-primary md:text-5xl">
        <Counter to={value} duration={2.4} />
      </div>
      <div className="display mt-2 text-[10px] uppercase tracking-[0.32em] text-muted-foreground">
        {label}
      </div>
    </div>
  );
}

function KV({ k, v }: { k: string; v: string }) {
  return (
    <div>
      <div className="mono text-[10px] uppercase tracking-[0.25em] text-muted-foreground/70">
        {k}
      </div>
      <div className="mono mt-1 text-primary">{v}</div>
    </div>
  );
}

function HeroSceneFallback() {
  return (
    <div className="flex h-full w-full items-center justify-center">
      <div className="display text-[10px] uppercase tracking-[0.45em] text-muted-foreground/40">
        sculpting…
      </div>
    </div>
  );
}
