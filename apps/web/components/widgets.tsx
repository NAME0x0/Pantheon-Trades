"use client";

import { useEffect, useMemo, useState } from "react";
import { motion, useScroll } from "framer-motion";
import { cn } from "@/lib/utils";

/* ─── Scroll progress bar ────────────────────────────────────────────
 * Thin gold bar across the very top of the viewport that fills as the
 * reader scrolls.
 *
 * Recommendation G: dropped useSpring. The spring added damped motion
 * but produced 60-80 motion-value updates per scroll second on
 * mid-range hardware. Binding scrollYProgress to scaleX directly is
 * effectively free — framer-motion subscribes the DOM transform to
 * the scroll listener without intermediate spring math. */
export function ScrollProgress() {
  const { scrollYProgress } = useScroll();
  return (
    <motion.div
      style={{ scaleX: scrollYProgress }}
      className="fixed left-0 right-0 top-0 z-50 h-[2px] origin-left bg-gradient-to-r from-primary via-primary/80 to-primary/40"
    />
  );
}

/* ─── Scale tilt slider ─────────────────────────────────────────────
 * Drag the slider, the 3D scale in the hero physically tips. The 3D
 * model reads the same shared state via React lifting. */
export function ScaleTiltSlider({
  tilt,
  onTilt,
  className,
}: {
  tilt: number;
  onTilt: (n: number) => void;
  className?: string;
}) {
  return (
    <div className={cn("w-full", className)}>
      <div className="display mb-3 flex items-center justify-between text-[10px] uppercase tracking-[0.35em] text-muted-foreground">
        <span>← Bear weight</span>
        <span>Tip the scale</span>
        <span>Bull weight →</span>
      </div>
      <div className="relative">
        <div className="h-px w-full bg-primary/30" />
        <div
          className="absolute top-1/2 h-px bg-primary"
          style={{
            left: tilt < 0 ? `${50 + tilt * 50}%` : "50%",
            right: tilt > 0 ? `${50 - tilt * 50}%` : "50%",
          }}
        />
        <input
          type="range"
          min={-1}
          max={1}
          step={0.01}
          value={tilt}
          onChange={(e) => onTilt(parseFloat(e.target.value))}
          className="absolute inset-0 h-full w-full cursor-pointer appearance-none bg-transparent
            [&::-webkit-slider-thumb]:appearance-none
            [&::-webkit-slider-thumb]:h-5
            [&::-webkit-slider-thumb]:w-5
            [&::-webkit-slider-thumb]:rounded-full
            [&::-webkit-slider-thumb]:border
            [&::-webkit-slider-thumb]:border-primary
            [&::-webkit-slider-thumb]:bg-background
            [&::-webkit-slider-thumb]:shadow-[0_0_18px_rgba(212,168,94,0.45)]
            [&::-webkit-slider-thumb]:transition-transform
            [&::-webkit-slider-thumb]:hover:scale-110
            [&::-moz-range-thumb]:h-5
            [&::-moz-range-thumb]:w-5
            [&::-moz-range-thumb]:rounded-full
            [&::-moz-range-thumb]:border
            [&::-moz-range-thumb]:border-primary
            [&::-moz-range-thumb]:bg-background"
        />
      </div>
    </div>
  );
}

/* ─── Council vote simulator ──────────────────────────────────────── */

type Vote = "APPROVE" | "REJECT" | "ABSTAIN";

const AGENT_WEIGHTS = [
  { name: "Ares",       weight: 1.0, veto: false },
  { name: "Hades",      weight: 1.0, veto: false },
  { name: "Athena",     weight: 1.2, veto: false },
  { name: "Cassandra",  weight: 1.0, veto: false },
  { name: "Solon",      weight: 1.5, veto: true },
  { name: "Zeus",       weight: 2.0, veto: true },
  { name: "Themis",     weight: 1.0, veto: false },
  { name: "Hephaestus", weight: 1.0, veto: false },
  { name: "Daedalus",   weight: 1.0, veto: false },
  { name: "Humans",     weight: 1.0, veto: false },
  { name: "Eris",       weight: 0.8, veto: false },
];
const MIN_QUORUM = 7;
const APPROVAL_THRESHOLD = 0.6;

export function VoteSimulator() {
  const [votes, setVotes] = useState<Record<string, Vote>>(
    Object.fromEntries(AGENT_WEIGHTS.map((a) => [a.name, "ABSTAIN"])),
  );

  function cycle(name: string) {
    setVotes((v) => ({
      ...v,
      [name]:
        v[name] === "ABSTAIN"
          ? "APPROVE"
          : v[name] === "APPROVE"
          ? "REJECT"
          : "ABSTAIN",
    }));
  }

  function reset() {
    setVotes(Object.fromEntries(AGENT_WEIGHTS.map((a) => [a.name, "ABSTAIN"])));
  }

  const verdict = useMemo(() => evaluate(votes), [votes]);

  return (
    <div className="grid gap-8 lg:grid-cols-[1fr_18rem]">
      <div>
        <div className="display mb-4 text-[10px] uppercase tracking-[0.35em] text-muted-foreground">
          Tap an agent to cycle Abstain → Approve → Reject
        </div>
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-5">
          {AGENT_WEIGHTS.map((a) => {
            const v = votes[a.name];
            return (
              <button
                key={a.name}
                type="button"
                onClick={() => cycle(a.name)}
                className={cn(
                  "group flex flex-col items-center justify-center gap-1 rounded-lg border p-3 text-center transition-all",
                  v === "APPROVE" && "border-emerald-500/50 bg-emerald-900/15 text-emerald-200",
                  v === "REJECT"  && "border-destructive/60 bg-destructive/15 text-destructive-foreground",
                  v === "ABSTAIN" && "border-primary/20 bg-card/40 text-muted-foreground hover:border-primary/40 hover:bg-primary/5",
                )}
              >
                <span className="display text-[10px] uppercase tracking-[0.22em]">
                  {a.name}
                </span>
                <span className="mono text-[9px] opacity-70">
                  w {a.weight.toFixed(1)} {a.veto ? "⚡" : ""}
                </span>
                <span className="mono mt-1 text-[10px] uppercase tracking-wider">
                  {v === "ABSTAIN" ? "—" : v}
                </span>
              </button>
            );
          })}
        </div>
        <button
          type="button"
          onClick={reset}
          className="display mt-4 text-[10px] uppercase tracking-[0.32em] text-muted-foreground transition-colors hover:text-primary"
        >
          ↺ reset
        </button>
      </div>

      {/* Verdict panel */}
      <div className="plinth rounded-xl p-6">
        <div className="display text-[10px] uppercase tracking-[0.35em] text-primary">
          Areopagus verdict
        </div>

        <div className="mt-4">
          <ApprovalRing percent={verdict.weighted * 100} />
        </div>

        <div className="mt-5 space-y-2 text-sm">
          <Row k="weighted approval" v={`${(verdict.weighted * 100).toFixed(0)}%`} />
          <Row k="quorum" v={`${verdict.participating} / ${MIN_QUORUM}`} />
          <Row k="status" v={verdict.label} highlight />
        </div>
        {verdict.note && (
          <p className="serif mt-4 text-sm italic text-muted-foreground">
            {verdict.note}
          </p>
        )}
      </div>
    </div>
  );
}

function evaluate(votes: Record<string, Vote>) {
  let wApproveConf = 0;
  let wParticipating = 0;
  let approveCount = 0;
  let rejectCount = 0;
  let zeusReject = false;
  let solonReject = false;
  for (const a of AGENT_WEIGHTS) {
    const v = votes[a.name];
    if (v === "ABSTAIN") continue;
    wParticipating += a.weight;
    if (v === "APPROVE") {
      approveCount += 1;
      wApproveConf += a.weight; // confidence assumed 1.0 for the demo
    } else {
      rejectCount += 1;
      if (a.name === "Zeus") zeusReject = true;
      if (a.name === "Solon") solonReject = true;
    }
  }
  const weighted = wParticipating > 0 ? wApproveConf / wParticipating : 0;
  const participating = approveCount + rejectCount;
  if (zeusReject) {
    return {
      weighted,
      participating,
      label: "VETOED · ZEUS",
      note: "Zeus cast the supreme veto. The trade is refused; the chain remembers.",
    };
  }
  if (solonReject) {
    return {
      weighted,
      participating,
      label: "VETOED · SOLON",
      note: "Solon flagged a constitutional violation. Refused.",
    };
  }
  if (participating < MIN_QUORUM) {
    return {
      weighted,
      participating,
      label: "NO QUORUM",
      note: `Need ${MIN_QUORUM} participating votes; have ${participating}.`,
    };
  }
  if (weighted >= APPROVAL_THRESHOLD) {
    return {
      weighted,
      participating,
      label: "APPROVED",
      note: "Areopagus would size at up to 5% of NAV via half-Kelly.",
    };
  }
  return {
    weighted,
    participating,
    label: "SUB-THRESHOLD",
    note: `Weighted approval ${(weighted * 100).toFixed(0)}% below 60% threshold.`,
  };
}

function Row({ k, v, highlight }: { k: string; v: string; highlight?: boolean }) {
  return (
    <div className="flex items-center justify-between">
      <span className="mono text-[10px] uppercase tracking-[0.22em] text-muted-foreground">
        {k}
      </span>
      <span
        className={cn(
          "display tracking-[0.1em]",
          highlight ? "text-primary" : "text-foreground",
        )}
      >
        {v}
      </span>
    </div>
  );
}

function ApprovalRing({ percent }: { percent: number }) {
  const size = 144;
  const stroke = 8;
  const r = (size - stroke) / 2;
  const c = 2 * Math.PI * r;
  const pct = Math.max(0, Math.min(100, percent));
  const offset = c - (pct / 100) * c;
  return (
    <div className="relative mx-auto" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90">
        <circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          stroke="hsl(var(--primary) / 0.15)"
          strokeWidth={stroke}
          fill="none"
        />
        <motion.circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          stroke="hsl(var(--primary))"
          strokeWidth={stroke}
          fill="none"
          strokeLinecap="round"
          initial={false}
          animate={{ strokeDashoffset: offset }}
          transition={{ duration: 0.6, ease: [0.22, 1, 0.36, 1] }}
          style={{ strokeDasharray: c }}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <div className="display text-3xl font-semibold text-primary">
          {pct.toFixed(0)}%
        </div>
        <div className="display text-[9px] uppercase tracking-[0.32em] text-muted-foreground">
          approval
        </div>
      </div>
    </div>
  );
}

/* ─── Magnetic hover wrapper ─────────────────────────────────────────
 * Wraps any block; on hover, the contents subtly follow the cursor.
 * Used for hi-fi card interactions. */
export function Magnetic({
  children,
  strength = 18,
  className,
}: {
  children: React.ReactNode;
  strength?: number;
  className?: string;
}) {
  const [pos, setPos] = useState({ x: 0, y: 0 });
  return (
    <div
      className={cn("relative transition-transform duration-200 ease-out", className)}
      style={{ transform: `translate3d(${pos.x}px, ${pos.y}px, 0)` }}
      onMouseMove={(e) => {
        const r = (e.currentTarget as HTMLDivElement).getBoundingClientRect();
        const dx = (e.clientX - (r.left + r.width / 2)) / r.width;
        const dy = (e.clientY - (r.top + r.height / 2)) / r.height;
        setPos({ x: dx * strength, y: dy * strength });
      }}
      onMouseLeave={() => setPos({ x: 0, y: 0 })}
    >
      {children}
    </div>
  );
}
