import Link from "next/link";
import Image from "next/image";
import dynamic from "next/dynamic";
import { ArrowRight, ArrowUpRight } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Reveal, Counter, Typewriter, Marquee } from "@/components/anim";
import { BRAND_MARK, ICON, PHOTO } from "@/lib/cdn";

// R3F is heavy — keep it client-only and lazy so first paint stays cheap.
const HeroScene = dynamic(() => import("@/components/hero-scene"), {
  ssr: false,
  loading: () => <HeroSceneFallback />,
});

const FIRST_PROOF_TX =
  "0xf9ae0e7ba73ecaece1af840b20e2ef5a20868df960e62ba238e53a828dfa4edb";
const ARCSCAN_BASE = "https://testnet.arcscan.app";

export const metadata = {
  title: "Pantheon Trades — A council of ten gods debates every trade",
  description:
    "A ten-agent AI council deliberates every Polymarket trade. Every approval — and every restraint — is anchored on Circle's Arc Testnet.",
};

const AGENTS = [
  { name: "Apollo",     greek: "ΑΠΟΛΛΩΝ",        role: "Sees the future. Scores Polymarket signals." },
  { name: "Boule",      greek: "ΒΟΥΛΗ",          role: "Convenes the council. Four rounds of debate." },
  { name: "Ares",       greek: "ΑΡΗΣ",           role: "Bull researcher — argues the long case." },
  { name: "Hades",      greek: "ΑΙΔΗΣ",          role: "Bull researcher — surfaces hidden depth." },
  { name: "Athena",     greek: "ΑΘΗΝΑ",          role: "Bear researcher + synthesizer." },
  { name: "Cassandra",  greek: "ΚΑΣΣΑΝΔΡΑ",      role: "Bear researcher — flags tail risk." },
  { name: "Solon",      greek: "ΣΟΛΩΝ",          role: "Constitutional check. Veto authority.", veto: true },
  { name: "Zeus",       greek: "ΖΕΥΣ",           role: "Supreme veto. Hard constitutional gate.", veto: true },
  { name: "Themis",     greek: "ΘΕΜΙΣ",          role: "Procedural integrity. Reviews the trace." },
  { name: "Hephaestus", greek: "ΗΦΑΙΣΤΟΣ",       role: "Execution — sizes and routes." },
  { name: "Daedalus",   greek: "ΔΑΙΔΑΛΟΣ",       role: "Execution — strategy fit." },
  { name: "Humans",     greek: "ΑΝΘΡΩΠΟΙ",       role: "Execution — crowd sentiment." },
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
  return (
    <div className="pb-12">
      {/* ── HERO ────────────────────────────────────────────────────── */}
      <section className="relative -mx-6 min-h-[88vh] overflow-hidden px-6 pb-8 pt-12">
        {/* Parthenon at golden hour, deeply dimmed */}
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
          <div className="space-y-10 pt-10">
            <Reveal y={12}>
              <div className="display flex items-center gap-3 text-[10px] uppercase tracking-[0.45em] text-primary">
                <span className="inline-block size-1.5 rounded-full bg-primary animate-pulse" />
                Arc Testnet · chain 5042002
              </div>
            </Reveal>

            <Reveal delay={0.05}>
              <h1 className="display text-[clamp(3.5rem,8vw,7.5rem)] font-medium leading-[0.92] tracking-[-0.018em] text-foreground">
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
              <HeroStat value={10} suffix="" label="Council agents" />
              <HeroStat value={4} suffix="" label="Rounds of debate" />
              <HeroStat value={51} suffix="" label="Foundry tests" />
              <HeroStat value={1} suffix="" label="On-chain witness" />
            </div>
          </div>

          {/* 3D scene right column */}
          <div className="relative h-[440px] lg:h-[560px]">
            <HeroScene />
            <div className="display absolute bottom-6 right-6 text-[9px] uppercase tracking-[0.4em] text-primary/60">
              Pondera Iustitiae
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

      {/* ── PREMISE — drop-cap editorial paragraph ─────────────────── */}
      <section className="relative mx-auto max-w-3xl py-24">
        <Reveal>
          <Eyebrow numeral="I" label="The premise" />
        </Reveal>
        <Reveal delay={0.1}>
          <h2 className="display mb-10 text-5xl font-medium leading-[1.05] tracking-[-0.01em] text-foreground">
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
          <h2 className="display mb-16 max-w-3xl text-5xl font-medium leading-[1.05] tracking-[-0.01em] text-foreground">
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
              <div className="group relative grid grid-cols-[6rem_1fr_auto] items-baseline gap-6 border-t border-primary/15 py-8 transition-colors hover:bg-primary/[0.025] md:grid-cols-[7rem_18rem_1fr]">
                <span className="display text-3xl font-semibold text-primary/70 transition-colors group-hover:text-primary md:text-4xl">
                  {step.numeral}
                </span>
                <div>
                  <div className="display text-xl tracking-[0.18em] text-foreground md:text-2xl">
                    {step.name.toUpperCase()}
                  </div>
                  <div className="serif mt-1 text-base italic text-primary/80">
                    {step.role}
                  </div>
                </div>
                <p className="serif text-lg leading-[1.7] text-muted-foreground md:text-xl">
                  {step.what}
                </p>
              </div>
            </Reveal>
          ))}
          <div className="border-t border-primary/15" />
        </ol>
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
            <Eyebrow numeral="III" label="The flagship feature" />
          </Reveal>
          <Reveal delay={0.05}>
            <h2 className="display mt-6 text-[clamp(3rem,7vw,6rem)] font-medium leading-[0.96] tracking-[-0.015em] text-foreground">
              <span className="serif italic text-primary">When the council says no,</span>
              <br />
              the chain remembers.
            </h2>
          </Reveal>

          <Reveal delay={0.15}>
            <p className="serif mt-10 max-w-2xl text-[1.35rem] leading-[1.75] text-muted-foreground">
              Areopagus writes a <code className="mono text-primary">Restrained</code>{" "}
              event to the <code className="mono text-primary">ProofOfRestraint</code>{" "}
              contract on Arc — binding signal hash, market, reason, and a note
              the council attached to the refusal. If the market later moves
              against the rejected direction, that restraint is provably ours.
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

      {/* ── COUNCIL — agent roster ─────────────────────────────────── */}
      <section className="py-24">
        <Reveal>
          <Eyebrow numeral="IV" label="The pantheon" />
        </Reveal>
        <Reveal delay={0.05}>
          <h2 className="display mb-4 max-w-3xl text-5xl font-medium leading-[1.05] tracking-[-0.01em] text-foreground">
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

        <div className="grid grid-cols-1 gap-px overflow-hidden rounded-2xl border border-primary/15 md:grid-cols-2">
          {AGENTS.map((a, i) => (
            <Reveal key={a.name} delay={Math.min(i * 0.03, 0.3)}>
              <div className="group relative flex items-baseline gap-5 bg-card/40 p-7 transition-colors hover:bg-primary/[0.03]">
                <div className="display w-20 shrink-0 text-[11px] uppercase tracking-[0.32em] text-primary/60">
                  {a.greek}
                </div>
                <div className="flex-1">
                  <div className="display flex items-center gap-2 text-xl tracking-[0.16em] text-foreground">
                    {a.name.toUpperCase()}
                    {a.veto && (
                      <span
                        className="mono text-[10px] uppercase tracking-[0.25em] text-destructive-foreground/80"
                        title="veto authority"
                      >
                        ⚡ veto
                      </span>
                    )}
                  </div>
                  <div className="serif mt-1 text-base leading-[1.55] text-muted-foreground">
                    {a.role}
                  </div>
                </div>
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
          <Eyebrow numeral="V" label="The stack" />
        </Reveal>
        <Reveal delay={0.05}>
          <h2 className="display mb-14 max-w-3xl text-5xl font-medium leading-[1.05] tracking-[-0.01em] text-foreground">
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
              <div className="bg-card/40 p-6 transition-colors hover:bg-primary/[0.03]">
                <div className="display text-[10px] uppercase tracking-[0.35em] text-primary/60">
                  {s.k}
                </div>
                <div className="display mt-2 text-lg tracking-[0.06em] text-foreground">
                  {s.v}
                </div>
              </div>
            </Reveal>
          ))}
        </div>
      </section>

      {/* ── CLOSING CTA ────────────────────────────────────────────── */}
      <section className="relative my-20 overflow-hidden rounded-3xl border border-primary/30 bg-card/40 px-6 py-20 text-center md:py-28">
        <div className="absolute inset-0 -z-10">
          <Image
            src={PHOTO.ruin}
            alt=""
            fill
            sizes="(min-width: 1024px) 1024px, 100vw"
            className="object-cover opacity-[0.08]"
          />
        </div>

        <Reveal>
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={BRAND_MARK}
            alt=""
            width={56}
            height={56}
            className="mx-auto mb-6 opacity-90 drop-shadow-[0_0_24px_rgba(212,168,94,0.35)]"
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

function HeroStat({
  value,
  suffix,
  label,
}: {
  value: number;
  suffix?: string;
  label: string;
}) {
  return (
    <div>
      <div className="display text-4xl font-semibold leading-none text-primary md:text-5xl">
        <Counter to={value} duration={2.4} />
        {suffix}
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
