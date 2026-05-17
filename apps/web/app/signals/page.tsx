import { listSignals } from "../../lib/api";

export const dynamic = "force-dynamic";

interface SignalRow {
  signal_id: string;
  band: string;
  question: string;
  edge_abs: number;
  oracle_probability: number;
  market_probability: number;
  created_at: string;
}

export default async function SignalsPage() {
  let signals: SignalRow[];
  try {
    signals = (await listSignals()).items as SignalRow[];
  } catch {
    signals = [];
  }
  return (
    <section>
      <h1 className="font-mono text-3xl text-pantheon-gold">Signals</h1>
      <p className="text-pantheon-marble">S/A-band candidates from Apollo.</p>
      <div className="mt-6 overflow-hidden rounded-lg border border-pantheon-gold/30">
        <table className="min-w-full divide-y divide-pantheon-gold/20 text-sm">
          <thead className="bg-pantheon-ink/80 text-pantheon-marble">
            <tr>
              <Th>Band</Th>
              <Th>Market</Th>
              <Th>Edge</Th>
              <Th>Oracle p</Th>
              <Th>Market p</Th>
              <Th>Created</Th>
            </tr>
          </thead>
          <tbody className="divide-y divide-pantheon-gold/10">
            {signals.length === 0 && (
              <tr>
                <td className="px-4 py-6 text-pantheon-marble/60" colSpan={6}>
                  No signals yet — start Apollo with{" "}
                  <code className="font-mono">python -m apollo.cli serve</code>.
                </td>
              </tr>
            )}
            {signals.map((s) => (
              <tr key={s.signal_id} className="hover:bg-pantheon-ink/40">
                <Td>
                  <span className="font-mono text-pantheon-gold">{s.band}</span>
                </Td>
                <Td className="max-w-xs truncate">{s.question}</Td>
                <Td>{(s.edge_abs * 100).toFixed(2)}%</Td>
                <Td>{(s.oracle_probability * 100).toFixed(1)}%</Td>
                <Td>{(s.market_probability * 100).toFixed(1)}%</Td>
                <Td className="text-pantheon-marble/70">
                  {new Date(s.created_at).toLocaleString()}
                </Td>
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
const Td = ({ children, className = "" }: { children: React.ReactNode; className?: string }) => (
  <td className={`px-4 py-3 ${className}`}>{children}</td>
);
