import { getArcStatus, listSignals, listTheses, listTrades } from "../../lib/api";

async function safe<T>(p: Promise<T>): Promise<T | null> {
  try {
    return await p;
  } catch {
    return null;
  }
}

export const dynamic = "force-dynamic";

export default async function Dashboard() {
  const [signals, theses, trades, arc] = await Promise.all([
    safe(listSignals()),
    safe(listTheses()),
    safe(listTrades()),
    safe(getArcStatus()),
  ]);

  const allDown = !signals && !theses && !trades && !arc;

  return (
    <section className="space-y-8">
      <div>
        <h1 className="font-mono text-4xl tracking-tight text-pantheon-gold">
          Dashboard
        </h1>
        <p className="mt-2 text-pantheon-marble">
          Live read-out from the Pantheon FastAPI gateway. Requires the backend to be running.
        </p>
        {allDown && (
          <div className="mt-4 rounded-lg border border-amber-700/40 bg-amber-900/10 p-4 text-sm text-amber-200">
            Backend not reachable at <code className="font-mono">NEXT_PUBLIC_API_URL</code>.
            Start it locally with <code className="font-mono">pnpm dev</code> or visit{" "}
            <a className="underline" href="/demo">the demo</a> to see a captured run.
          </div>
        )}
      </div>

      <div className="grid gap-4 md:grid-cols-4">
        <Card label="Open signals">{signals?.count ?? "—"}</Card>
        <Card label="Recent theses">{theses?.count ?? "—"}</Card>
        <Card label="Trades booked">{trades?.count ?? "—"}</Card>
        <Card label="Arc block">
          {arc ? arc.block_number.toLocaleString() : "—"}
        </Card>
      </div>

      {arc && (
        <div className="rounded-lg border border-pantheon-gold/30 bg-pantheon-ink/60 p-6">
          <h2 className="font-mono text-pantheon-gold">Arc Testnet</h2>
          <dl className="mt-4 grid grid-cols-2 gap-y-2 text-sm text-pantheon-marble">
            <dt>Chain id</dt>
            <dd className="text-right">{arc.chain_id}</dd>
            <dt>RPC</dt>
            <dd className="text-right truncate">{arc.rpc_url}</dd>
            <dt>Latest block</dt>
            <dd className="text-right">{arc.block_number.toLocaleString()}</dd>
            <dt>Gas price (wei)</dt>
            <dd className="text-right">{arc.gas_price_wei.toLocaleString()}</dd>
            <dt>Thesis registry</dt>
            <dd className="text-right font-mono text-xs">
              {arc.registry_address || "(unset)"}
            </dd>
          </dl>
        </div>
      )}
    </section>
  );
}

function Card({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="rounded-lg border border-pantheon-gold/30 bg-pantheon-ink/60 p-4">
      <div className="text-xs uppercase tracking-wider text-pantheon-marble/70">
        {label}
      </div>
      <div className="mt-2 text-2xl font-mono text-pantheon-gold">{children}</div>
    </div>
  );
}
