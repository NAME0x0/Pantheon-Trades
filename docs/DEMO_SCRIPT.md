# Demo Script

Step-by-step walkthrough for demonstrating Pantheon Trades.

## Audience

Technical or semi-technical: developers, crypto traders, prediction market participants.

## Setup (Before Demo)

1. Start all services: `docker compose up`
2. Open web UI: `http://localhost:3000`
3. Ensure at least 1 signal is in Band A queue (or pre-load a demo signal)
4. Have the Trace Viewer ready for a recent deliberation
5. Have the Leaderboard open in a second tab

## Demo Flow

### 1. The Problem (1 min)

> "Prediction markets have millions of dollars in inefficient pricing every day. The challenge is identifying which markets are mispriced and having conviction to trade them."

Show the Agora (/signals page):
- Live signal feed with band classifications
- Point to an S or A band signal: "Apollo identified this market has 12% edge — the market is pricing it at 38%, but our model thinks it's 50% likely to resolve YES."

### 2. The Council (3 min)

> "Before we touch a penny, 13 AI agents debate the thesis."

Click into a recent deliberation on /theses:
- Show the council vote table — agents disagreed (some APPROVE, some REJECT)
- Open the Trace Viewer for that thesis
- Walk through one agent's Round 1 statement (pick Hades for drama)
- Show Cassandra's flag
- Show Athena's synthesis
- Show the final vote: 9/11 weighted approval, Zeus approved, Solon approved

> "Zeus could have killed this. Solon could have killed this. But the math checked out and the risk was within bounds."

### 3. The Restraint (2 min)

Navigate to Leaderboard → Restraint Quality section:

> "Here's something unusual: we track every time we chose NOT to trade. Out of 47 S/A signals, we traded 12 and restrained 35."

Show the No-Trade Alpha panel:
> "Of those 35 restraints, 22 were correct — the market would have lost money. We didn't. That's not missing an opportunity; that's the system working correctly."

Show a specific ProofOfRestraint entry:
> "This is on-chain. The SEC decision Cassandra warned about? We didn't trade it. The market resolved NO two days later."

### 4. On-Chain Accountability (2 min)

Navigate to any trade's `/arc/proof/{thesis_id}`:

> "Everything is on-chain. Every thesis hash, every vote, every trade proof, every restraint. You can audit our full track record on Arc Testnet."

Show the Arc block explorer link (testnet.arcscan.app) with the ThesisRegistry contract.

> "Agent identities are ERC-8004 passports. Hades's track record is public. If he keeps making bad calls, the system exiles him."

Show an agent passport with Brier score history.

### 5. The System Learning (1 min)

Navigate to Leaderboard → Agent Brier Scores:

> "The agents get better over time. After every market resolves, their calibration is updated. Poorly performing agents lose influence. The best agents get more weight in future votes."

> "And when a trade fails, we run a post-mortem. The system learns which assumptions were wrong and includes those lessons in future deliberations."

### 6. Wrap-Up (1 min)

> "This is the first prediction market trading system where every decision is provably transparent, agents are publicly accountable, and not-trading is as first-class as trading. We're not trying to hide our mistakes — we're building a system that learns from them publicly."

## Q&A Prep

**Q: Can the agents be manipulated?**
A: Show `docs/ADVERSARIAL_MODE.md` — monthly red-team testing. Messengers filters injection attempts. Auditor watches for hallucinations.

**Q: What's the edge source?**
A: Multi-dimensional signal scoring (see `docs/SIGNAL_SPEC.md`). The edge comes from better aggregation of public information, not proprietary data.

**Q: What stops you from just changing the prompts when you lose?**
A: Prompt hashes are on-chain. Any change is publicly visible. ZeusMultisig required for major changes. 72h timelock.

**Q: Is this live?**
A: Currently on Arc Testnet with paper trading. See `docs/STRATEGY_LIFECYCLE.md` for the paper→live promotion process.
