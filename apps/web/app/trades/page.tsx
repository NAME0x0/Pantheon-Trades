import { listTrades } from "../../lib/api";

export const dynamic = "force-dynamic";

interface TradeRow {
  trade_id: string;
  direction: string;
  status: string;
  size_pct: number;
  size_usdc: number;
  entry_price: number;
  fill_price?: number | null;
}

export default async function TradesPage() {
  let trades: TradeRow[];
  try {
    trades = (await listTrades()).items as TradeRow[];
  } catch {
    trades = [];
  }
  return (
    <section>
      <h1 className="font-mono text-3xl text-pantheon-gold">Trades</h1>
      <p className="text-pantheon-marble">Paper + live execution log.</p>
      <div className="mt-6 overflow-hidden rounded-lg border border-pantheon-gold/30">
        <table className="min-w-full divide-y divide-pantheon-gold/20 text-sm">
          <thead className="bg-pantheon-ink/80 text-pantheon-marble">
            <tr>
              <Th>Side</Th>
              <Th>Status</Th>
              <Th>Size %</Th>
              <Th>USDC</Th>
              <Th>Entry</Th>
              <Th>Fill</Th>
            </tr>
          </thead>
          <tbody className="divide-y divide-pantheon-gold/10">
            {trades.length === 0 && (
              <tr>
                <td colSpan={6} className="px-4 py-6 text-pantheon-marble/60">
                  No trades yet.
                </td>
              </tr>
            )}
            {trades.map((t) => (
              <tr key={t.trade_id}>
                <Td>
                  <span className="font-mono text-pantheon-gold">{t.direction}</span>
                </Td>
                <Td>{t.status}</Td>
                <Td>{(t.size_pct * 100).toFixed(2)}%</Td>
                <Td>${t.size_usdc.toFixed(2)}</Td>
                <Td>{t.entry_price.toFixed(3)}</Td>
                <Td>{t.fill_price?.toFixed(3) ?? "—"}</Td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

const Th = ({ children }: { children: React.ReactNode }) => (
  <th className="px-4 py-2 text-left text-xs uppercase tracking-wider">{children}</th>
);
const Td = ({ children }: { children: React.ReactNode }) => (
  <td className="px-4 py-3">{children}</td>
);
