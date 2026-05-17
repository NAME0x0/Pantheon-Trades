/**
 * Performance metrics derivation for the dashboard.
 *
 * Stays small and dependency-free. Equity curve, drawdown, daily PnL,
 * rolling Sharpe — everything we need to graph the system''s scorecard.
 */

export interface TradePnL {
  at: string; // ISO date
  pnl_usdc: number; // realised PnL on this trade
}

export interface DailyBar {
  date: string; // YYYY-MM-DD
  pnl: number;
  equity: number;
}

export function dailyBars(trades: TradePnL[], startEquity = 0): DailyBar[] {
  const byDate = new Map<string, number>();
  for (const t of trades) {
    const d = (t.at ?? "").slice(0, 10);
    if (!d) continue;
    byDate.set(d, (byDate.get(d) ?? 0) + t.pnl_usdc);
  }
  const out: DailyBar[] = [];
  let equity = startEquity;
  for (const date of Array.from(byDate.keys()).sort()) {
    const pnl = byDate.get(date)!;
    equity += pnl;
    out.push({ date, pnl, equity });
  }
  return out;
}

export interface RollingMetric {
  date: string;
  value: number;
}

export function rollingSharpe(
  bars: DailyBar[],
  windowDays = 30,
  annualisation = Math.sqrt(252),
): RollingMetric[] {
  if (bars.length === 0) return [];
  const out: RollingMetric[] = [];
  const returns = bars.map((b) => b.pnl);
  for (let i = windowDays - 1; i < bars.length; i += 1) {
    const window = returns.slice(i - windowDays + 1, i + 1);
    const mean = window.reduce((a, b) => a + b, 0) / window.length;
    const variance =
      window.reduce((a, b) => a + (b - mean) * (b - mean), 0) / Math.max(1, window.length - 1);
    const sd = Math.sqrt(variance);
    const sharpe = sd > 0 ? (mean / sd) * annualisation : 0;
    out.push({ date: bars[i].date, value: Number(sharpe.toFixed(3)) });
  }
  return out;
}

export function maxDrawdown(bars: DailyBar[]): number {
  let peak = bars[0]?.equity ?? 0;
  let maxDd = 0;
  for (const b of bars) {
    if (b.equity > peak) peak = b.equity;
    const dd = peak > 0 ? (peak - b.equity) / peak : 0;
    if (dd > maxDd) maxDd = dd;
  }
  return maxDd;
}

export interface ScorecardSummary {
  total_pnl: number;
  trade_count: number;
  win_rate: number;
  max_drawdown: number;
  sharpe_30d: number | null;
  best_day: number;
  worst_day: number;
}

export function scorecard(trades: TradePnL[]): ScorecardSummary {
  const bars = dailyBars(trades);
  const total = trades.reduce((a, t) => a + t.pnl_usdc, 0);
  const wins = trades.filter((t) => t.pnl_usdc > 0).length;
  const rolling = rollingSharpe(bars, 30);
  const sharpe = rolling.length > 0 ? rolling[rolling.length - 1].value : null;
  return {
    total_pnl: Number(total.toFixed(2)),
    trade_count: trades.length,
    win_rate: trades.length === 0 ? 0 : Number((wins / trades.length).toFixed(4)),
    max_drawdown: Number(maxDrawdown(bars).toFixed(4)),
    sharpe_30d: sharpe,
    best_day: bars.length === 0 ? 0 : Math.max(...bars.map((b) => b.pnl)),
    worst_day: bars.length === 0 ? 0 : Math.min(...bars.map((b) => b.pnl)),
  };
}
