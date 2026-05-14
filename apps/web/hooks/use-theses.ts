"use client";

import { useEffect, useState } from "react";

import { listTheses, ThesisSummary } from "../lib/api";

export function useTheses(token?: string | null): {
  theses: ThesisSummary[];
  loading: boolean;
  error: string | null;
} {
  const [theses, setTheses] = useState<ThesisSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    listTheses(token)
      .then((res) => {
        if (!cancelled) setTheses(res.items);
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

  return { theses, loading, error };
}
