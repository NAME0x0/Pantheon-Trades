"use client";

/**
 * Non-functional side widgets to fill whitespace without overloading.
 *
 * Each widget is decorative and self-contained — no fetches, no global
 * state. They animate on a timer to feel alive but otherwise sit quiet.
 *
 *  - ChamberClock     : a slow-spinning meander clock with Greek-numeral
 *                       12 / 3 / 6 / 9 markers. Reads as a wall clock in
 *                       the council chamber.
 *  - SpeakingNow      : rotates through the council roster every 8s,
 *                       showing the current "speaker" — pure flavour.
 *  - ConstitutionSnip : cycles through three constitutional rules.
 *
 * These exist to give wide screens something to rest the eye on between
 * the dense reading sections, without adding behaviour to maintain.
 */

import { useEffect, useState } from "react";

import { cn } from "@/lib/utils";
import { MeanderStrip, MedallionOrnament } from "./ornaments";

const COUNCIL = [
  { name: "Ares", greek: "ΑΡΗΣ", role: "presenting the long case" },
  { name: "Hades", greek: "ΑΙΔΗΣ", role: "tracing hidden depth" },
  { name: "Athena", greek: "ΑΘΗΝΑ", role: "drafting the synthesis" },
  { name: "Cassandra", greek: "ΚΑΣΣΑΝΔΡΑ", role: "naming the tail" },
  { name: "Zeus", greek: "ΖΕΥΣ", role: "weighing the gate" },
  { name: "Solon", greek: "ΣΟΛΩΝ", role: "reading the constitution" },
  { name: "Themis", greek: "ΘΕΜΙΣ", role: "verifying the trace" },
  { name: "Hephaestus", greek: "ΗΦΑΙΣΤΟΣ", role: "designing the fill" },
  { name: "Daedalus", greek: "ΔΑΙΔΑΛΟΣ", role: "auditing the structure" },
  { name: "Humans", greek: "ΑΝΘΡΩΠΟΙ", role: "speaking for the crowd" },
  { name: "Eris", greek: "ΕΡΙΣ", role: "arguing the minority side" },
];

const RULES = [
  {
    article: "Article II §1",
    body: "No position shall exceed five percent of total book equity.",
  },
  {
    article: "Article III §2",
    body: "Crypto-cluster exposure shall not exceed twelve percent at any time.",
  },
  {
    article: "Article IV §1",
    body: "No trade where 24-hour volume falls below fifty thousand USDC.",
  },
  {
    article: "Article V §3",
    body: "Politics positions shall not exceed four percent, sports three, science two.",
  },
  {
    article: "Article VI §1",
    body: "Kelly is taken at one-half. Never full. Never doubled.",
  },
];

export function ChamberClock({ className }: { className?: string }) {
  const [t, setT] = useState(0);
  useEffect(() => {
    const id = setInterval(() => setT((x) => x + 1), 1000);
    return () => clearInterval(id);
  }, []);
  // Slow-rotating outer ring (one revolution / 60s).
  const angle = (t % 60) * 6;
  return (
    <div
      className={cn(
        "relative aspect-square w-full max-w-[220px] select-none",
        className,
      )}
      aria-hidden
    >
      <svg viewBox="0 0 220 220" className="h-full w-full">
        {/* Outer ring — pushed outward so beads + labels don't collide */}
        <circle
          cx={110}
          cy={110}
          r={104}
          fill="none"
          stroke="currentColor"
          strokeWidth={0.8}
          className="text-primary/40"
        />
        <circle
          cx={110}
          cy={110}
          r={95}
          fill="none"
          stroke="currentColor"
          strokeWidth={0.6}
          className="text-primary/25"
        />
        {/* Beaded ring orbits outside the hour glyphs (r=86 vs labels at r=60) */}
        <g
          transform={`rotate(${angle} 110 110)`}
          style={{ transition: "transform 1s linear" }}
          className="text-primary/55"
        >
          {Array.from({ length: 60 }).map((_, i) => {
            const a = (i / 60) * Math.PI * 2;
            const x = 110 + Math.cos(a) * 86;
            const y = 110 + Math.sin(a) * 86;
            return (
              <circle
                key={i}
                cx={x}
                cy={y}
                r={i % 5 === 0 ? 1.6 : 0.8}
                fill="currentColor"
              />
            );
          })}
        </g>
        {/* Hour glyphs at radius 60 — inside the bead orbit, outside medallion */}
        {([
          { x: 110, y: 56, label: "I" },
          { x: 164, y: 114, label: "II" },
          { x: 110, y: 168, label: "III" },
          { x: 56, y: 114, label: "IV" },
        ] as const).map((p) => (
          <text
            key={p.label}
            x={p.x}
            y={p.y}
            textAnchor="middle"
            fontFamily="serif"
            fontSize={13}
            className="fill-primary/70"
          >
            {p.label}
          </text>
        ))}
        {/* Central medallion */}
        <circle
          cx={110}
          cy={110}
          r={30}
          fill="none"
          stroke="currentColor"
          strokeWidth={0.9}
          className="text-primary/60"
        />
        <text
          x={110}
          y={117}
          textAnchor="middle"
          fontFamily="serif"
          fontSize={20}
          className="fill-primary"
        >
          Π
        </text>
      </svg>
    </div>
  );
}

export function SpeakingNow({ className }: { className?: string }) {
  const [i, setI] = useState(0);
  useEffect(() => {
    const id = setInterval(() => setI((x) => (x + 1) % COUNCIL.length), 8000);
    return () => clearInterval(id);
  }, []);
  const c = COUNCIL[i];
  return (
    <div
      className={cn(
        "rounded-xl border border-primary/15 bg-card/40 p-5",
        className,
      )}
    >
      <div className="display flex items-center gap-2 text-[10px] uppercase tracking-[0.4em] text-primary/70">
        <span className="inline-block size-1.5 animate-pulse rounded-full bg-primary" />
        In chamber · live
      </div>
      <div className="serif mt-4 text-xs uppercase tracking-[0.25em] text-primary/55">
        {c.greek}
      </div>
      <div className="display mt-1 text-2xl tracking-[0.08em] text-foreground">
        {c.name}
      </div>
      <p className="serif mt-2 text-sm italic text-muted-foreground">
        {c.role}
      </p>
      <div className="mt-4">
        <MeanderStrip className="h-4 opacity-60" />
      </div>
    </div>
  );
}

export function ConstitutionSnip({ className }: { className?: string }) {
  const [i, setI] = useState(0);
  useEffect(() => {
    const id = setInterval(() => setI((x) => (x + 1) % RULES.length), 12000);
    return () => clearInterval(id);
  }, []);
  const r = RULES[i];
  return (
    <div
      className={cn(
        "relative rounded-xl border border-primary/15 bg-card/40 p-5",
        className,
      )}
    >
      <div className="display flex items-center justify-between text-[10px] uppercase tracking-[0.4em] text-primary/65">
        <span>{r.article}</span>
        <MedallionOrnament glyph="§" className="h-6 w-6 opacity-80" />
      </div>
      <p className="serif mt-4 text-base italic leading-relaxed text-foreground/90">
        &ldquo;{r.body}&rdquo;
      </p>
      <div className="mt-4 flex justify-end gap-1">
        {RULES.map((_, k) => (
          <span
            key={k}
            className={cn(
              "h-px w-3 transition-colors duration-500",
              k === i ? "bg-primary" : "bg-primary/15",
            )}
          />
        ))}
      </div>
    </div>
  );
}
