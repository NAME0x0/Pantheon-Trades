import { ArrowUpRight } from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

/**
 * FaucetCard — drip-feed Arc Testnet USDC to a visitor's wallet so they
 * can pay gas for the WitnessButton tx. Arc Testnet uses USDC as native
 * gas, so a single faucet drip covers both gas AND any future contract
 * interactions. Card is purely informational — clicking opens the
 * official faucets in a new tab.
 */

const CIRCLE_FAUCET = "https://faucet.circle.com/";
const ARC_FAUCET = "https://faucet.testnet.arc.network/";

export function FaucetCard() {
  return (
    <Card className="border-primary/30 bg-card/50">
      <CardHeader className="pb-2">
        <CardTitle className="text-sm uppercase tracking-wider text-primary">
          Need test USDC for gas?
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <p className="text-sm leading-[1.6] text-muted-foreground">
          Arc Testnet uses USDC as native gas. The faucets drip free testnet USDC to
          any wallet — no real funds required. Each demo witness tx costs less than
          one US cent.
        </p>
        <div className="grid gap-3 sm:grid-cols-2">
          <FaucetLink
            href={CIRCLE_FAUCET}
            label="Circle Faucet"
            note="Multi-chain USDC drip (select Arc Sepolia / Arc Testnet)"
          />
          <FaucetLink
            href={ARC_FAUCET}
            label="Arc Testnet Faucet"
            note="Direct from the Arc team — paste your 0x address"
          />
        </div>
        <p className="text-xs text-muted-foreground/70">
          After connecting your wallet, paste your address into one of the faucets
          above. Drip arrives in seconds.
        </p>
      </CardContent>
    </Card>
  );
}

function FaucetLink({
  href,
  label,
  note,
}: {
  href: string;
  label: string;
  note: string;
}) {
  return (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      className="group flex items-start justify-between gap-3 rounded-md border border-primary/20 bg-card/60 p-4 transition-colors hover:border-primary/50 hover:bg-primary/[0.04]"
    >
      <div>
        <div className="font-mono text-sm uppercase tracking-wider text-primary">
          {label}
        </div>
        <div className="mt-1 text-xs leading-[1.55] text-muted-foreground">{note}</div>
      </div>
      <ArrowUpRight className="size-4 shrink-0 text-primary/60 transition-transform group-hover:-translate-y-0.5 group-hover:translate-x-0.5" />
    </a>
  );
}
