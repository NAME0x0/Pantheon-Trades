"use client";

import { useEffect, useState } from "react";

import { listSignals, SignalSummary } from "../lib/api";

export function useSignals(token?: string | null): {
  signals: SignalSummary[];
  loading: boolean;
  error: string | null;
} {
  const [signals, setSignals] = useState<SignalSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    listSignals(token)
      .then((res) => {
        if (!cancelled) setSignals(res.items);
      })
      .catch((e) => {
        if (!cancelled) setError(String(e));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [token]);

  return { signals, loading, error };
}
