"use client";

/** Pure-SVG bar chart. */

import * as React from "react";

export interface BarPoint {
  x: string;
  y: number;
}

export interface BarChartProps {
  data: BarPoint[];
  width?: number;
  height?: number;
  positiveColor?: string;
  negativeColor?: string;
  label?: string;
  yFormat?: (v: number) => string;
  className?: string;
}

const M_LEFT = 44;
const M_RIGHT = 12;
const M_TOP = 10;
const M_BOTTOM = 28;

export function BarChart({
  data,
  width = 720,
  height = 240,
  positiveColor = "#22c55e",
  negativeColor = "#ef4444",
  label,
  yFormat,
  className,
}: BarChartProps) {
  if (data.length === 0) {
    return (
      <div className={className} style={{ height }}>
        <p className="text-xs text-muted-foreground">No data.</p>
      </div>
    );
  }

  const plotW = width - M_LEFT - M_RIGHT;
  const plotH = height - M_TOP - M_BOTTOM;

  const yMin = Math.min(0, ...data.map((d) => d.y));
  const yMax = Math.max(0, ...data.map((d) => d.y));
  const yPad = Math.max(1, (yMax - yMin) * 0.08);
  const yLo = yMin - yPad;
  const yHi = yMax + yPad;
  const yScale = (v: number) => M_TOP + (1 - (v - yLo) / (yHi - yLo)) * plotH;
  const barGap = 6;
  const barW = Math.max(2, (plotW - barGap * (data.length - 1)) / data.length);
  const formatter = yFormat ?? ((v: number) => v.toLocaleString(undefined, { maximumFractionDigits: 2 }));

  return (
    <svg viewBox={`0 0 ${width} ${height}`} width="100%" height={height} className={className} role="img" aria-label={label ?? "Bar chart"}>
      <g>
        {/* Zero line */}
        <line
          x1={M_LEFT}
          x2={M_LEFT + plotW}
          y1={yScale(0)}
          y2={yScale(0)}
          stroke="currentColor"
          strokeOpacity={0.35}
        />
        {data.map((d, i) => {
          const x = M_LEFT + i * (barW + barGap);
          const zero = yScale(0);
          const y = d.y >= 0 ? yScale(d.y) : zero;
          const h = Math.max(1, Math.abs(yScale(d.y) - zero));
          return (
            <g key={`${d.x}-${i}`}>
              <rect
                x={x}
                y={y}
                width={barW}
                height={h}
                fill={d.y >= 0 ? positiveColor : negativeColor}
                rx={2}
              />
              {i % Math.max(1, Math.floor(data.length / 8)) === 0 && (
                <text
                  x={x + barW / 2}
                  y={M_TOP + plotH + 14}
                  textAnchor="middle"
                  fontSize={10}
                  fill="currentColor"
                  opacity={0.55}
                >
                  {d.x}
                </text>
              )}
            </g>
          );
        })}
        {/* Y ticks */}
        {[yLo, (yLo + yHi) / 2, yHi].map((t, i) => (
          <text
            key={i}
            x={M_LEFT - 6}
            y={yScale(t)}
            dy="0.32em"
            textAnchor="end"
            fontSize={10}
            fill="currentColor"
            opacity={0.55}
          >
            {formatter(t)}
          </text>
        ))}
      </g>
    </svg>
  );
}
