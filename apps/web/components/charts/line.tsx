"use client";

/** Minimal pure-SVG line chart. No external dep.
 *
 * Designed for the performance dashboard — equity curve, Sharpe
 * rolling, etc. Single series; consumers stack multiple charts for
 * compound views. ``baseline`` is an optional horizontal reference
 * line (useful for $-zero on PnL, 0% on returns, etc).
 */

import * as React from "react";

export interface LinePoint {
  x: number | string;
  y: number;
}

export interface LineChartProps {
  data: LinePoint[];
  width?: number;
  height?: number;
  stroke?: string;
  fill?: string;
  baseline?: number;
  label?: string;
  yFormat?: (v: number) => string;
  className?: string;
}

const M_LEFT = 44;
const M_RIGHT = 12;
const M_TOP = 10;
const M_BOTTOM = 24;

export function LineChart({
  data,
  width = 720,
  height = 240,
  stroke = "#22c55e",
  fill = "rgba(34, 197, 94, 0.10)",
  baseline,
  label,
  yFormat,
  className,
}: LineChartProps) {
  if (data.length === 0) {
    return (
      <div className={className} style={{ height }}>
        <p className="text-xs text-muted-foreground">No data.</p>
      </div>
    );
  }

  const plotW = width - M_LEFT - M_RIGHT;
  const plotH = height - M_TOP - M_BOTTOM;

  const ys = data.map((d) => d.y);
  const yMin = Math.min(...ys, baseline ?? Number.POSITIVE_INFINITY);
  const yMax = Math.max(...ys, baseline ?? Number.NEGATIVE_INFINITY);
  const yPad = (yMax - yMin) * 0.06 || 1;
  const yLo = yMin - yPad;
  const yHi = yMax + yPad;
  const xScale = (i: number) =>
    M_LEFT + (data.length === 1 ? plotW / 2 : (i / (data.length - 1)) * plotW);
  const yScale = (v: number) => M_TOP + (1 - (v - yLo) / (yHi - yLo)) * plotH;

  const path = data.map((d, i) => `${i === 0 ? "M" : "L"} ${xScale(i)} ${yScale(d.y)}`).join(" ");
  const areaPath = `${path} L ${xScale(data.length - 1)} ${M_TOP + plotH} L ${xScale(0)} ${M_TOP + plotH} Z`;

  const yTicks = niceTicks(yLo, yHi, 4);
  const formatter = yFormat ?? ((v: number) => v.toLocaleString(undefined, { maximumFractionDigits: 2 }));

  return (
    <svg viewBox={`0 0 ${width} ${height}`} width="100%" height={height} className={className} role="img" aria-label={label ?? "Line chart"}>
      {/* Y grid */}
      <g>
        {yTicks.map((t) => (
          <g key={t}>
            <line
              x1={M_LEFT}
              x2={M_LEFT + plotW}
              y1={yScale(t)}
              y2={yScale(t)}
              stroke="currentColor"
              strokeOpacity={0.08}
            />
            <text x={M_LEFT - 6} y={yScale(t)} dy="0.32em" textAnchor="end" fontSize={10} fill="currentColor" opacity={0.55}>
              {formatter(t)}
            </text>
          </g>
        ))}
      </g>
      {/* Baseline */}
      {typeof baseline === "number" && baseline >= yLo && baseline <= yHi ? (
        <line
          x1={M_LEFT}
          x2={M_LEFT + plotW}
          y1={yScale(baseline)}
          y2={yScale(baseline)}
          stroke="currentColor"
          strokeOpacity={0.35}
          strokeDasharray="4 4"
        />
      ) : null}
      {/* Area + line */}
      <path d={areaPath} fill={fill} stroke="none" />
      <path d={path} fill="none" stroke={stroke} strokeWidth={1.75} strokeLinecap="round" strokeLinejoin="round" />
      {/* X-axis baseline */}
      <line
        x1={M_LEFT}
        x2={M_LEFT + plotW}
        y1={M_TOP + plotH}
        y2={M_TOP + plotH}
        stroke="currentColor"
        strokeOpacity={0.25}
      />
    </svg>
  );
}

function niceTicks(min: number, max: number, count: number): number[] {
  const range = max - min || 1;
  const step = Math.pow(10, Math.floor(Math.log10(range / count)));
  const err = (count * step) / range;
  const m = err >= 7.5 ? 0.1 : err >= 1.5 ? 0.2 : err >= 0.75 ? 0.5 : 1;
  const tickStep = step * m;
  const start = Math.ceil(min / tickStep) * tickStep;
  const out: number[] = [];
  for (let v = start; v <= max + 1e-12; v += tickStep) {
    out.push(Number(v.toFixed(6)));
    if (out.length > 16) break;
  }
  return out;
}
