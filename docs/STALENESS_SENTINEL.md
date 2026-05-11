# Staleness Sentinel

The Staleness Sentinel monitors all data sources in Pythia and enforces data freshness requirements across the pipeline.

## What It Monitors

| Source | Max Staleness | Alert Threshold | Block Threshold |
|--------|---------------|-----------------|-----------------|
| Polymarket CLOB | 60s | 45s | 60s |
| Crypto prices | 30s | 20s | 30s |
| DeFiLlama | 5 min | 3 min | 5 min |
| News feeds | 15 min | 10 min | 15 min |
| Reddit | 30 min | 20 min | 30 min |
| Hyperliquid | 5 min | 3 min | 5 min |

**Alert threshold**: emits warning event to Olympus.
**Block threshold**: signals from this source are marked stale and cannot proceed.

## Implementation

`services/pythia/src/pythia/staleness.py`:

```python
class StalenessSentinel:
    async def check(self, source: str, fetched_at: datetime) -> StalenessStatus:
        staleness_seconds = (now() - fetched_at).total_seconds()
        
        if staleness_seconds > BLOCK_THRESHOLD[source]:
            return StalenessStatus(
                status="blocked",
                staleness_seconds=staleness_seconds,
                degraded_trust=0.0
            )
        elif staleness_seconds > ALERT_THRESHOLD[source]:
            await self.alert(source, staleness_seconds)
            return StalenessStatus(
                status="degraded",
                staleness_seconds=staleness_seconds,
                degraded_trust=1.0 - (staleness_seconds / BLOCK_THRESHOLD[source])
            )
        
        return StalenessStatus(status="ok", staleness_seconds=staleness_seconds, degraded_trust=1.0)
```

## Effect on Signals

When a source is blocked:
1. `source_trust_score` for affected markets is set to 0
2. Affected markets cannot generate band S/A signals
3. Apollo logs staleness event

When a source is degraded (alert but not blocked):
1. `source_trust_score` is proportionally reduced
2. Band score is adjusted downward
3. Band upgrades suppressed until source recovers

## Effect on Open Positions

Argos checks staleness before each monitoring cycle. If Polymarket CLOB is stale > 120s:
1. Argos marks positions as "unmonitored"
2. Alert sent to Olympus
3. If stale > 300s: emergency protocol — Strategos cancels all GTC orders

## Recovery

When a blocked source recovers:
1. Source trust score restored to baseline
2. Apollo resumes normal scoring for affected markets
3. Recovery event emitted to Olympus

## Olympus Dashboard

Staleness status visible at web UI `/settings` → Data Sources panel:
- Green: all sources fresh
- Yellow: one or more sources degraded
- Red: critical source (Polymarket CLOB) blocked
