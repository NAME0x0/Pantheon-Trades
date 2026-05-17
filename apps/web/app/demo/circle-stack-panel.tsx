"use client";

/**
 * Circle stack panel — surfaces every Circle developer-platform
 * primitive Pantheon uses, with concrete repo paths so judges and
 * operators can verify by `grep`.
 *
 * Pure static. Built for the Agora Agents Hackathon submission but
 * useful generally as documentation of "what Circle gives us."
 */

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

type ToolRow = {
  tool: string;
  status: "shipped" | "wired" | "partial";
  use: string;
  path: string;
};

const TOOLS: readonly ToolRow[] = [
  {
    tool: "Arc Testnet",
    status: "shipped",
    use: "Settlement L1; native USDC gas; chain id 5042002",
    path: "services/areopagus/src/areopagus/chain.py",
  },
  {
    tool: "USDC",
    status: "shipped",
    use: "Settlement token throughout PaperBook + FeeLedger + BuilderLedger",
    path: "services/strategos/src/strategos/paper.py",
  },
  {
    tool: "Contracts",
    status: "shipped",
    use: "8 Solidity contracts incl. ProofOfRestraint + PantheonConstitution (Halmos-proved)",
    path: "contracts/src/",
  },
  {
    tool: "Wallets",
    status: "shipped",
    use: "EIP-1193 SIWE flow + Arc network-switch with 4902 add-network fallback",
    path: "apps/web/app/demo/wallet-connect.tsx",
  },
  {
    tool: "Paymaster",
    status: "shipped",
    use: "USDC-denominated gas client + native↔paymaster routing intent",
    path: "services/strategos/src/strategos/paymaster_client.py",
  },
  {
    tool: "Gateway",
    status: "shipped",
    use: "Unified USDC balance reads + per-chain breakdown + transfer intents",
    path: "services/strategos/src/strategos/gateway_client.py",
  },
  {
    tool: "USYC",
    status: "shipped",
    use: "Idle-bankroll parking with mint/redeem intents + yield projection",
    path: "services/strategos/src/strategos/usyc_treasury.py",
  },
  {
    tool: "Polymarket V2 builder codes",
    status: "shipped",
    use: "Per-fill USDC attribution to operator payout. Per-category fee math.",
    path: "services/strategos/src/strategos/polymarket_builder.py",
  },
  {
    tool: "Trace anchors (Arc)",
    status: "shipped",
    use: "Keccak256 bundle hash of every council deliberation + IPFS canonical bytes",
    path: "services/parthenon/src/parthenon/trace_anchor.py",
  },
  {
    tool: "App Kit",
    status: "wired",
    use: "Bridge / Send / Unified Balance consume Gateway transfer intents",
    path: "services/strategos/src/strategos/gateway_client.py",
  },
  {
    tool: "CCTP",
    status: "wired",
    use: "Cross-chain USDC moves flow through GatewayTransferIntent",
    path: "services/strategos/src/strategos/gateway_client.py",
  },
  {
    tool: "Nanopayments",
    status: "partial",
    use: "High-frequency maker rebates rely on sub-cent Arc gas — designed use case",
    path: "services/strategos/src/strategos/maker_rebate.py",
  },
];

function statusVariant(s: ToolRow["status"]): "success" | "default" | "warning" {
  if (s === "shipped") return "success";
  if (s === "wired") return "default";
  return "warning";
}

export function CircleStackPanel() {
  const shipped = TOOLS.filter((t) => t.status === "shipped");
  const wired = TOOLS.filter((t) => t.status === "wired");
  const partial = TOOLS.filter((t) => t.status === "partial");

  return (
    <Card className="border-primary/30">
      <CardHeader className="space-y-2 pb-3">
        <div className="display text-[10px] uppercase tracking-[0.4em] text-primary/70">
          Settles on Arc · powered by Circle
        </div>
        <CardTitle className="display text-xl tracking-[0.06em] text-foreground">
          {shipped.length} Circle tools shipped · {wired.length} wired · {partial.length} partial
        </CardTitle>
        <p className="serif max-w-3xl text-sm italic text-muted-foreground">
          Pantheon Trades is built for Circle&apos;s Arc — sub-second deterministic finality,
          ~$0.01 USDC gas, no volatile token to source. Every row below is verifiable
          by clicking the path into the repo.
        </p>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="overflow-hidden rounded-md border border-primary/15">
          <table className="w-full text-sm">
            <thead className="bg-card/40">
              <tr>
                <Th>Tool</Th>
                <Th>What it does for Pantheon</Th>
                <Th>Repo path</Th>
                <Th>Status</Th>
              </tr>
            </thead>
            <tbody className="divide-y divide-primary/10">
              {TOOLS.map((t) => (
                <tr key={t.tool} className="hover:bg-primary/[0.03]">
                  <Td>
                    <span className="font-mono text-foreground">{t.tool}</span>
                  </Td>
                  <Td className="text-muted-foreground">{t.use}</Td>
                  <Td>
                    <code className="break-all font-mono text-xs text-primary/80">
                      {t.path}
                    </code>
                  </Td>
                  <Td>
                    <Badge variant={statusVariant(t.status)}>{t.status}</Badge>
                  </Td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="rounded-md border border-primary/15 bg-card/40 p-3 text-xs text-muted-foreground">
          <strong className="font-mono text-foreground">First on-chain witness</strong> — block 42,337,549 on Arc Testnet:{" "}
          <a
            href="https://testnet.arcscan.app/tx/0xf9ae0e7ba73ecaece1af840b20e2ef5a20868df960e62ba238e53a828dfa4edb"
            target="_blank"
            rel="noopener noreferrer"
            className="font-mono text-primary hover:underline"
          >
            0xf9ae0e7b…df960e62ba238e53a828dfa4edb ↗
          </a>
        </p>
      </CardContent>
    </Card>
  );
}

function Th({ children }: { children: React.ReactNode }) {
  return (
    <th className="px-3 py-2 text-left text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
      {children}
    </th>
  );
}

function Td({
  children,
  className = "",
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return <td className={`px-3 py-2.5 ${className}`}>{children}</td>;
}
