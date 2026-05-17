// Thin fetch helpers for the Pantheon Trades FastAPI gateway.

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export type ApiOptions = {
  token?: string | null;
  revalidateSeconds?: number;
};

async function api<T>(path: string, options: ApiOptions = {}): Promise<T> {
  const headers: Record<string, string> = { "content-type": "application/json" };
  if (options.token) {
    headers.authorization = `Bearer ${options.token}`;
  }
  // The `next` extension is a Next.js-specific RequestInit field that
  // lib.dom doesn't model. Cast to satisfy strict TypeScript without
  // adding @types/next as a runtime dep.
  const res = await fetch(`${API_BASE}${path}`, {
    headers,
    next: { revalidate: options.revalidateSeconds ?? 5 },
  } as RequestInit & { next?: { revalidate?: number } });
  if (!res.ok) {
    throw new Error(`api ${path} failed: ${res.status}`);
  }
  return (await res.json()) as T;
}

export type SignalSummary = {
  signal_id: string;
  market_id: string;
  question: string;
  category: string;
  band: string;
  edge_abs: number;
  oracle_probability: number;
  market_probability: number;
  band_score: number;
  created_at: string;
};

export type ThesisSummary = {
  thesis_id: string;
  signal_id: string;
  market_id: string;
  direction: "YES" | "NO";
  council_probability: number;
  confidence: number;
  status: string;
  weighted_approval: number;
  recommended_size_pct: number;
  archived_cid?: string | null;
  created_at: string;
};

export type TradeSummary = {
  trade_id: string;
  thesis_id: string;
  market_id: string;
  direction: "YES" | "NO";
  status: string;
  size_pct: number;
  size_usdc: number;
  entry_price: number;
  fill_price: number | null;
};

export type ArcStatus = {
  rpc_url: string;
  expected_chain_id: number;
  chain_id: number;
  block_number: number;
  gas_price_wei: number;
  registry_address: string;
};

export async function listSignals(token?: string | null) {
  return api<{ items: SignalSummary[]; count: number }>("/signals/", { token });
}

export async function listTheses(token?: string | null) {
  return api<{ items: ThesisSummary[]; count: number }>("/theses/", { token });
}

export async function listTrades(token?: string | null) {
  return api<{ items: TradeSummary[]; count: number }>("/trades/", { token });
}

export async function getArcStatus(token?: string | null) {
  return api<ArcStatus>("/arc/status", { token });
}

export type RestraintSummary = {
  proof_id: string;
  signal_id: string;
  market_id: string;
  reason_code: string;
  note: string;
  signal_hash: string;
  created_at: string;
  // Populated by the API when the on-chain anchor has landed.
  // The Areopagus consumer fires declineTrade(...) in the background
  // and persists the receipt to areopagus:restraint:tx:<proof_id>;
  // the gateway merges those fields into the list response.
  tx_hash?: string | null;
  onchain_proof_id?: number | null;
  explorer_url?: string | null;
};

export async function listRestraint(token?: string | null) {
  return api<{ items: RestraintSummary[]; count: number }>("/restraint/", { token });
}
