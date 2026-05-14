"use client";

import { useEffect, useState } from "react";

type EthereumWindow = Window & { ethereum?: any };


export function useWallet(): {
  address: string | null;
  chainId: number | null;
  connect: () => Promise<void>;
  disconnect: () => void;
} {
  const [address, setAddress] = useState<string | null>(null);
  const [chainId, setChainId] = useState<number | null>(null);

  useEffect(() => {
    if (typeof window === "undefined") return;
    const eth = (window as EthereumWindow).ethereum;
    if (!eth) return;
    eth.request({ method: "eth_accounts" })
      .then((accs: string[]) => setAddress(accs[0] ?? null))
      .catch(() => undefined);
    eth.request({ method: "eth_chainId" })
      .then((id: string) => setChainId(parseInt(id, 16)))
      .catch(() => undefined);
    const onAccts = (accs: string[]) => setAddress(accs[0] ?? null);
    const onChain = (id: string) => setChainId(parseInt(id, 16));
    eth.on?.("accountsChanged", onAccts);
    eth.on?.("chainChanged", onChain);
    return () => {
      eth.removeListener?.("accountsChanged", onAccts);
      eth.removeListener?.("chainChanged", onChain);
    };
  }, []);

  async function connect() {
    const eth = (window as EthereumWindow).ethereum;
    if (!eth) throw new Error("no injected wallet");
    const accs: string[] = await eth.request({ method: "eth_requestAccounts" });
    setAddress(accs[0] ?? null);
  }

  function disconnect() {
    setAddress(null);
  }

  return { address, chainId, connect, disconnect };
}
