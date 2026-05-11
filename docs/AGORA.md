# Agora — Signal Marketplace

The Agora (Ἀγορά) was the Athenian marketplace and civic center. In Pantheon Trades, the Agora is the signal layer — where market opportunities are identified, scored, and made available to the Boule council.

## Components

The Agora is not a single service — it's the conceptual layer between raw data and deliberation:

```
Pythia (data oracle)
     │
     ▼
Apollo (signal engine)
     │
     ├── Band S/A signals → Boule queue
     ├── Band B signals   → Monitor queue
     └── Band C/D signals → Logged, discarded
```

## Signal Flow

1. **Pythia** fetches market snapshots from Polymarket CLOB
2. **Apollo** scores each market across 6 feature dimensions
3. Scored markets are assigned to bands (S, A, B, C, D)
4. S/A signals are published to `apollo:signals` Redis stream
5. Boule polls this stream and picks up signals for deliberation

## Real-Time Signal Feed

The web UI `Signal Band` view at `/signals` shows live signals:
- Band classification (color-coded S/A/B/C/D)
- Edge score and direction
- Liquidity, catalyst, and sentiment scores
- Time since last update
- Status: queued / deliberating / expired

WebSocket feed: `ws://api/ws/signals` — streams `signal.created` and `signal.banded` events.

## Signal Market Coverage

Apollo scans all active Polymarket markets with:
- Open interest > $25,000 USDC
- Days to resolution: 2-180 days
- Question categorized as crypto, politics, sports, science, or other

Typical scan: 200-500 active markets per poll. ~5-15% score into band B or above. ~1-3% reach band S/A on any given day.

## Market Scanner

The `market_scanner.py` agent in Boule is not an LLM agent — it's the signal ingestion module that receives signals from Apollo and decides which to queue for immediate deliberation vs. watch list.

Scanner priority rules:
1. Band S signals → immediate deliberation
2. Band A signals → deliberation within 5 minutes
3. Band A signals already in queue → deduplicated (no duplicate deliberations on same market)
4. Cooldown: a market cannot enter deliberation more than once per 4 hours unless the signal band changes

## Agora Metrics

Web UI dashboard card:
- Markets scanned today
- Signals generated (by band)
- Deliberations triggered
- Signal-to-deliberation conversion rate
- Average edge of S/A signals

These metrics are stored in PostgreSQL and updated by Apollo on each scan.
