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
  { name: "Athena", greek: "ΑΘΗΝΑ", role: "drafting the synthesis" },
  { name: "Hades", greek: "ΑΙΔΗΣ", role: "tracing hidden depth" },
  { name: "Cassandra", greek: "ΚΑΣΣΑΝΔΡΑ", role: "naming the tail" },
  { name: "Zeus", greek: "ΖΕΥΣ", role: "weighing the gate" },
  { name: "Solon", greek: "ΣΟΛΩΝ", role: "reading the constitution" },
  { name: "Themis", greek: "ΘΕΜΙΣ", role: "verifying the trace" },
  { name: "Hephaestus", greek: "ΗΦΑΙΣΤΟΣ", role: "designing the fill" },
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
        "relative aspect-square w-full max-w-[180px] select-none",
        className,
      )}
      aria-hidden
    >
      <svg viewBox="0 0 200 200" className="h-full w-full">
        {/* Outer ring */}
        <circle
          cx={100}
          cy={100}
          r={92}
          fill="none"
          stroke="currentColor"
          strokeWidth={0.8}
          className="text-primary/40"
        />
        <circle
          cx={100}
          cy={100}
          r={84}
          fill="none"
          stroke="currentColor"
          strokeWidth={0.6}
          className="text-primary/25"
        />
        {/* Beaded inner ring rotates slowly */}
        <g
          transform={`rotate(${angle} 100 100)`}
          style={{ transition: "transform 1s linear" }}
          className="text-primary/55"
        >
          {Array.from({ length: 60 }).map((_, i) => {
            const a = (i / 60) * Math.PI * 2;
            const x = 100 + Math.cos(a) * 78;
            const y = 100 + Math.sin(a) * 78;
            return (
              <circle
                key={i}
                cx={x}
                cy={y}
                r={i % 5 === 0 ? 1.5 : 0.7}
                fill="currentColor"
              />
            );
          })}
        </g>
        {/* Hour glyphs: I (12), II (3), III (6), IV (9) — placed cardinal */}
        {([
          { x: 100, y: 32, label: "I" },
          { x: 168, y: 105, label: "II" },
          { x: 100, y: 178, label: "III" },
          { x: 32, y: 105, label: "IV" },
        ] as const).map((p) => (
          <text
            key={p.label}
            x={p.x}
            y={p.y}
            textAnchor="middle"
            fontFamily="serif"
            fontSize={12}
            className="fill-primary/70"
          >
            {p.label}
          </text>
        ))}
        {/* Central medallion */}
        <circle
          cx={100}
          cy={100}
          r={28}
          fill="none"
          stroke="currentColor"
          strokeWidth={0.9}
          className="text-primary/60"
        />
        <text
          x={100}
          y={106}
          textAnchor="middle"
          fontFamily="serif"
          fontSize={18}
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
