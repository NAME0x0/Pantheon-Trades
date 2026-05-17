/**
 * Greek-aesthetic ornament primitives.
 *
 * All SVG, all inline, no external deps. Use as decorative side rails,
 * dividers, and section anchors. Every primitive accepts a `className`
 * so callers can position / tint without forking the SVG.
 *
 * Drawing principles:
 *  - Stroke-only, never filled — keeps file weight tiny and lets the
 *    primary gold tint show through.
 *  - currentColor stroke so they pick up text-primary / opacity-* classes
 *    without prop drilling.
 *  - Aspect-ratio preserved via viewBox; height controlled by parent.
 */

import { cn } from "@/lib/utils";

interface OrnamentProps {
  className?: string;
}

/** Stylised classical bust silhouette — line-art profile facing right. */
export function BustOrnament({ className }: OrnamentProps) {
  return (
    <svg
      viewBox="0 0 120 220"
      aria-hidden
      fill="none"
      stroke="currentColor"
      strokeWidth={0.8}
      strokeLinecap="round"
      strokeLinejoin="round"
      className={cn("text-primary/50", className)}
    >
      {/* Hair */}
      <path d="M44 32 q-8 -10 -4 -20 q12 -10 28 -6 q14 4 18 14 q4 8 -2 18" />
      <path d="M40 28 q-6 -6 -2 -12" />
      <path d="M52 18 q-2 -8 6 -10" />
      <path d="M70 16 q4 -6 12 -2" />
      {/* Brow + forehead */}
      <path d="M44 52 q2 -12 14 -16 q18 -4 30 8 q6 6 6 16" />
      {/* Eye */}
      <ellipse cx={62} cy={70} rx={6} ry={2} />
      <path d="M58 66 q4 -3 8 0" />
      <circle cx={62} cy={70} r={1} fill="currentColor" />
      {/* Nose */}
      <path d="M76 60 q2 12 -4 28 q-6 6 -4 12" />
      <path d="M68 96 q4 4 12 0" />
      {/* Mouth */}
      <path d="M70 110 q8 -2 16 0" />
      <path d="M72 114 q6 4 14 0" />
      {/* Chin + jaw */}
      <path d="M86 118 q6 10 -4 22 q-12 8 -22 10" />
      {/* Neck */}
      <path d="M62 142 q0 12 -6 22" />
      <path d="M80 138 q4 14 -2 28" />
      {/* Drapery / plinth */}
      <path d="M30 188 q30 -12 70 -4 q12 4 16 14" />
      <path d="M28 196 l92 -2" />
      <path d="M30 204 l88 -2" />
      <path d="M32 212 l84 -2" />
      {/* Decorative laurel hint */}
      <path d="M36 28 q-2 -6 -8 -4" />
      <path d="M28 26 q-4 0 -6 4" />
      <path d="M22 32 q-3 2 -3 6" />
      <path d="M86 22 q4 -4 10 -2" />
      <path d="M96 22 q4 0 6 4" />
      <path d="M102 28 q3 2 3 6" />
    </svg>
  );
}

/** Doric column — base, fluted shaft, capital. */
export function ColumnOrnament({ className }: OrnamentProps) {
  return (
    <svg
      viewBox="0 0 60 360"
      aria-hidden
      fill="none"
      stroke="currentColor"
      strokeWidth={0.9}
      strokeLinecap="round"
      strokeLinejoin="round"
      className={cn("text-primary/45", className)}
    >
      {/* Capital — abacus + echinus */}
      <rect x={4} y={6} width={52} height={6} />
      <rect x={6} y={12} width={48} height={4} />
      <path d="M8 16 q22 -2 44 0" />
      <path d="M10 22 q20 -4 40 0" />
      <rect x={12} y={24} width={36} height={4} />
      {/* Shaft fluting (12 vertical channels) */}
      {[15, 19, 23, 27, 31, 35, 39, 43, 47].map((x) => (
        <line key={x} x1={x} y1={32} x2={x} y2={328} />
      ))}
      <line x1={12} y1={32} x2={12} y2={328} strokeWidth={1.2} />
      <line x1={48} y1={32} x2={48} y2={328} strokeWidth={1.2} />
      {/* Subtle taper marks every 80px */}
      {[110, 200, 280].map((y) => (
        <path key={y} d={`M14 ${y} q16 -2 32 0`} className="opacity-50" />
      ))}
      {/* Base — torus + plinth */}
      <rect x={12} y={328} width={36} height={4} />
      <path d="M8 332 q22 4 44 0" />
      <path d="M6 338 q24 4 48 0" />
      <rect x={4} y={342} width={52} height={6} />
      <rect x={2} y={348} width={56} height={6} />
    </svg>
  );
}

/** Coin / medallion. Outer beaded ring, inner glyph slot. */
export function MedallionOrnament({
  className,
  glyph,
}: OrnamentProps & { glyph?: string }) {
  return (
    <svg
      viewBox="0 0 100 100"
      aria-hidden
      fill="none"
      stroke="currentColor"
      strokeWidth={0.9}
      strokeLinecap="round"
      className={cn("text-primary/55", className)}
    >
      <circle cx={50} cy={50} r={46} />
      <circle cx={50} cy={50} r={42} className="opacity-60" />
      {/* Beaded ring */}
      {Array.from({ length: 36 }).map((_, i) => {
        const a = (i / 36) * Math.PI * 2;
        const x = 50 + Math.cos(a) * 44;
        const y = 50 + Math.sin(a) * 44;
        return <circle key={i} cx={x} cy={y} r={0.6} fill="currentColor" />;
      })}
      {/* Inner glyph (Greek letter / numeral) */}
      {glyph && (
        <text
          x={50}
          y={56}
          textAnchor="middle"
          fontSize={28}
          fontFamily="serif"
          fill="currentColor"
          stroke="none"
          className="font-medium"
        >
          {glyph}
        </text>
      )}
    </svg>
  );
}

/** Greek meander / key fret strip — repeats horizontally. */
export function MeanderStrip({ className }: OrnamentProps) {
  return (
    <svg
      viewBox="0 0 400 24"
      preserveAspectRatio="xMidYMid meet"
      aria-hidden
      fill="none"
      stroke="currentColor"
      strokeWidth={0.9}
      strokeLinecap="square"
      strokeLinejoin="miter"
      className={cn("text-primary/45", className)}
    >
      {Array.from({ length: 10 }).map((_, i) => {
        const x = i * 40;
        return (
          <path
            key={i}
            d={`M${x} 4 h32 v16 h-24 v-12 h16 v8 h-8`}
          />
        );
      })}
      <line x1={0} y1={0} x2={400} y2={0} />
      <line x1={0} y1={24} x2={400} y2={24} />
    </svg>
  );
}

/** Laurel wreath half — designed to flank a centred heading. */
export function LaurelHalf({ className, side = "left" }: OrnamentProps & { side?: "left" | "right" }) {
  const flip = side === "right" ? "scale(-1, 1) translate(-200, 0)" : "";
  return (
    <svg
      viewBox="0 0 200 80"
      aria-hidden
      fill="none"
      stroke="currentColor"
      strokeWidth={1}
      strokeLinecap="round"
      strokeLinejoin="round"
      className={cn("text-primary/55", className)}
    >
      <g transform={flip}>
        {/* Stem */}
        <path d="M20 40 q60 -8 140 -4" />
        {/* Leaves above stem */}
        {Array.from({ length: 10 }).map((_, i) => {
          const x = 30 + i * 14;
          const y = 38 - i * 0.4;
          return (
            <ellipse
              key={`a${i}`}
              cx={x}
              cy={y - 8}
              rx={5}
              ry={2.5}
              transform={`rotate(${-30 + i * 2} ${x} ${y - 8})`}
            />
          );
        })}
        {/* Leaves below stem */}
        {Array.from({ length: 10 }).map((_, i) => {
          const x = 30 + i * 14;
          const y = 42 + i * 0.4;
          return (
            <ellipse
              key={`b${i}`}
              cx={x}
              cy={y + 8}
              rx={5}
              ry={2.5}
              transform={`rotate(${30 - i * 2} ${x} ${y + 8})`}
            />
          );
        })}
        {/* End cluster — three berries */}
        <circle cx={166} cy={34} r={1.6} fill="currentColor" />
        <circle cx={170} cy={40} r={1.8} fill="currentColor" />
        <circle cx={166} cy={46} r={1.6} fill="currentColor" />
      </g>
    </svg>
  );
}

/** Horizontal divider: meander strip flanked by laurel half-wreaths. */
export function ClassicalDivider({ className }: OrnamentProps) {
  return (
    <div className={cn("flex items-center gap-4 py-4", className)}>
      <LaurelHalf side="left" className="h-8 w-32 shrink-0" />
      <MeanderStrip className="h-5 flex-1" />
      <LaurelHalf side="right" className="h-8 w-32 shrink-0" />
    </div>
  );
}

/** Vertical decorative side rail — anchored column with medallion stack.
 *  Designed to sit fixed against the left/right edge on wide screens.
 *  Hidden on narrow viewports.
 */
export function SideRail({
  side = "left",
  glyphs = ["Α", "Β", "Γ"],
  className,
}: {
  side?: "left" | "right";
  glyphs?: readonly string[];
  className?: string;
}) {
  const sideClass = side === "left" ? "left-2" : "right-2";
  return (
    <aside
      aria-hidden
      className={cn(
        "pointer-events-none fixed top-1/2 z-0 hidden -translate-y-1/2 xl:flex",
        "flex-col items-center gap-6",
        sideClass,
        className,
      )}
    >
      <ColumnOrnament className="h-72 w-12 opacity-60" />
      <div className="flex flex-col items-center gap-3">
        {glyphs.map((g) => (
          <MedallionOrnament
            key={g}
            glyph={g}
            className="h-10 w-10 opacity-70"
          />
        ))}
      </div>
      <ColumnOrnament className="h-72 w-12 opacity-60" />
    </aside>
  );
}
