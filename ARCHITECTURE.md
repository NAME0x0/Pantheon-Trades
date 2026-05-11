# Architecture Overview

See [docs/ARCHITECTURE.md](./docs/ARCHITECTURE.md) for the full design.

## One-Line Summary

Polymarket signal ingestion → multi-agent debate → risk gating → CLOB execution → on-chain archival.

## Service Map

```
Pythia ──► Apollo ──► Boule ──► Areopagus ──► Strategos
  (data)   (signals)  (debate)   (risk gate)   (execution)
                                                    │
                              Argos ◄──────────────┘
                            (monitor)
                                │
              Ostrakon ◄────────┘       Parthenon
             (scoring)               (archive/IPFS)
                │                          ▲
              Elysium ◄──────────────────────
             (backtest)

Moirai ── lifecycle enforcement across all services
Olympus ─ system governance, goals board, adversarial mode
Underworld ─ post-mortems on failed strategies
```

## Data Flow

1. Pythia polls Polymarket CLOB + data feeds every N seconds
2. Apollo scores each market with edge/liquidity/sentiment features → emits `Signal`
3. Boule receives `Signal`, spawns council, runs structured debate → emits `Thesis`
4. Areopagus validates `Thesis` against risk policy → approve / reject / resize
5. Strategos submits approved `Thesis` to Polymarket CLOB → emits `Trade`
6. Argos watches open positions, fires `ExitSignal` on invalidation or target
7. Ostrakon records outcomes, updates Brier scores and leaderboard
8. Parthenon hashes and pins every artifact to IPFS, anchors Merkle root on-chain
