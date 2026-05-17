"use client";

/**
 * Pure-SVG Sankey diagram for visualising deliberation flow.
 *
 * No external dep (no d3-sankey / visx) so the bundle stays light.
 * Layout is a layered DAG: nodes per round, links carry width
 * proportional to ``value``. Edges are smoothstep bezier curves.
 *
 * Input shape mirrors d3-sankey for portability:
 *   nodes: { id, label, round }[]
 *   links: { source, target, value }[]
 */

import * as React from "react";

export interface SankeyNode {
  id: string;
  label: string;
  round: number;
  color?: string;
}

export interface SankeyLink {
  source: string;
  target: string;
  value: number;
  label?: string;
}

export interface SankeyProps {
  nodes: SankeyNode[];
  links: SankeyLink[];
  width?: number;
  height?: number;
  nodeWidth?: number;
  nodePadding?: number;
  className?: string;
}

interface LaidOutNode extends SankeyNode {
  x: number;
  y: number;
  w: number;
  h: number;
  inSum: number;
  outSum: number;
}

interface LaidOutLink {
  source: LaidOutNode;
  target: LaidOutNode;
  value: number;
  label?: string;
  sourceY: number;
  targetY: number;
  thickness: number;
}

const DEFAULT_PALETTE = [
  "#6366f1", // round 0
  "#22c55e", // round 1
  "#facc15", // round 2
  "#fb923c", // round 3
  "#ef4444", // round 4
];

export function Sankey({
  nodes,
  links,
  width = 720,
  height = 360,
  nodeWidth = 14,
  nodePadding = 12,
  className,
}: SankeyProps) {
  const layout = React.useMemo(
    () => buildLayout({ nodes, links, width, height, nodeWidth, nodePadding }),
    [nodes, links, width, height, nodeWidth, nodePadding],
  );

  if (layout.nodes.length === 0) {
    return (
      <div className={className}>
        <p className="text-sm text-muted-foreground">No deliberation flow to visualise.</p>
      </div>
    );
  }

  return (
    <svg
      viewBox={`0 0 ${width} ${height}`}
      width="100%"
      height={height}
      className={className}
      role="img"
      aria-label="Deliberation flow Sankey diagram"
    >
      <g>
        {layout.links.map((l, i) => (
          <SankeyLinkPath key={i} link={l} />
        ))}
      </g>
      <g>
        {layout.nodes.map((n) => (
          <g key={n.id} transform={`translate(${n.x}, ${n.y})`}>
            <rect width={n.w} height={n.h} fill={n.color ?? DEFAULT_PALETTE[n.round % DEFAULT_PALETTE.length]} rx={2} />
            <text
              x={n.x < width / 2 ? n.w + 6 : -6}
              y={n.h / 2}
              dy="0.32em"
              textAnchor={n.x < width / 2 ? "start" : "end"}
              fontSize={11}
              fill="currentColor"
            >
              {n.label}
            </text>
          </g>
        ))}
      </g>
    </svg>
  );
}

function SankeyLinkPath({ link }: { link: LaidOutLink }) {
  const x0 = link.source.x + link.source.w;
  const x1 = link.target.x;
  const mx = (x0 + x1) / 2;
  const d = `M ${x0} ${link.sourceY} C ${mx} ${link.sourceY}, ${mx} ${link.targetY}, ${x1} ${link.targetY}`;
  return (
    <path
      d={d}
      fill="none"
      stroke={link.source.color ?? DEFAULT_PALETTE[link.source.round % DEFAULT_PALETTE.length]}
      strokeOpacity={0.35}
      strokeWidth={Math.max(1, link.thickness)}
      strokeLinecap="butt"
    >
      {link.label ? <title>{link.label}</title> : null}
    </path>
  );
}

interface LayoutOptions {
  nodes: SankeyNode[];
  links: SankeyLink[];
  width: number;
  height: number;
  nodeWidth: number;
  nodePadding: number;
}

interface LayoutResult {
  nodes: LaidOutNode[];
  links: LaidOutLink[];
}

function buildLayout(opts: LayoutOptions): LayoutResult {
  const { nodes, links, width, height, nodeWidth, nodePadding } = opts;
  if (nodes.length === 0) return { nodes: [], links: [] };

  // Group nodes by round.
  const byRound = new Map<number, SankeyNode[]>();
  for (const n of nodes) {
    const arr = byRound.get(n.round) ?? [];
    arr.push(n);
    byRound.set(n.round, arr);
  }
  const rounds = Array.from(byRound.keys()).sort((a, b) => a - b);

  // Per-node aggregate in/out sums.
  const flows = new Map<string, { inSum: number; outSum: number }>();
  for (const n of nodes) flows.set(n.id, { inSum: 0, outSum: 0 });
  for (const l of links) {
    const s = flows.get(l.source);
    const t = flows.get(l.target);
    if (s) s.outSum += l.value;
    if (t) t.inSum += l.value;
  }

  // Round x positions evenly across width with margins.
  const marginX = Math.max(40, nodeWidth);
  const roundCount = Math.max(1, rounds.length);
  const xStep = roundCount === 1 ? 0 : (width - 2 * marginX) / (roundCount - 1);

  // Compute node heights based on max(inSum, outSum) within round, scaled.
  const laidOut: LaidOutNode[] = [];
  rounds.forEach((round, roundIdx) => {
    const group = (byRound.get(round) ?? []).slice();
    const x = marginX + xStep * roundIdx;
    // Total flow in this column = sum of max(in, out) of each node.
    const totalFlow =
      group.reduce((acc, n) => {
        const f = flows.get(n.id)!;
        return acc + Math.max(f.inSum, f.outSum);
      }, 0) || 1;
    const availableHeight = height - 2 * 20 - (group.length - 1) * nodePadding;
    let y = 20;
    for (const n of group) {
      const f = flows.get(n.id)!;
      const hRaw = (Math.max(f.inSum, f.outSum) / totalFlow) * availableHeight;
      const h = Math.max(12, hRaw);
      laidOut.push({
        ...n,
        x,
        y,
        w: nodeWidth,
        h,
        inSum: f.inSum,
        outSum: f.outSum,
      });
      y += h + nodePadding;
    }
  });

  const byId = new Map(laidOut.map((n) => [n.id, n]));

  // Order links so we can stack them on each node deterministically.
  const ordered = [...links].sort((a, b) => {
    if (a.source !== b.source) return a.source.localeCompare(b.source);
    return a.target.localeCompare(b.target);
  });

  // Track current y offset on each node for stacking.
  const sourceOffset = new Map<string, number>();
  const targetOffset = new Map<string, number>();
  const out: LaidOutLink[] = [];
  for (const l of ordered) {
    const s = byId.get(l.source);
    const t = byId.get(l.target);
    if (!s || !t || l.value <= 0) continue;
    const sScale = s.outSum > 0 ? s.h / s.outSum : 0;
    const tScale = t.inSum > 0 ? t.h / t.inSum : 0;
    const thickness = Math.max(sScale, tScale) * l.value;
    const so = sourceOffset.get(s.id) ?? 0;
    const to = targetOffset.get(t.id) ?? 0;
    out.push({
      source: s,
      target: t,
      value: l.value,
      label: l.label,
      sourceY: s.y + so + thickness / 2,
      targetY: t.y + to + thickness / 2,
      thickness,
    });
    sourceOffset.set(s.id, so + thickness);
    targetOffset.set(t.id, to + thickness);
  }

  return { nodes: laidOut, links: out };
}
