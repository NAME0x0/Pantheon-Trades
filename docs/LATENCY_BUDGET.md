# Latency Budget

Pantheon Trades is not a high-frequency trading system, but latency still matters. Signals decay, council deliberation has timeouts, and order placement must complete before signal TTL expires.

## End-to-End Budget

Total budget from "signal appears" to "order submitted": **12 minutes**

```
Signal generation (Apollo)          ~30s
Signal queuing + Boule pickup        ~5s
Boule deliberation                  ~3-5 min  ← dominant cost
Areopagus review                    ~5s
Strategos order submission           ~2s
Order fill (async, not blocking)     N/A

Buffer before signal TTL (15 min)  ~5-7 min
```

## Per-Stage Budget

| Stage | Target | Hard Limit | On Breach |
|-------|--------|------------|-----------|
| Pythia snapshot freshness | 60s | 300s | Staleness rejection |
| Apollo signal scoring | 10s | 30s | Alert + retry |
| Redis queue pickup | 1s | 5s | Alert |
| Boule Round 1 (parallel agents) | 30s | 60s | Agent marked ABSTAIN |
| Boule Round 2 (challenge) | 45s | 90s | Skipped if over budget |
| Boule Round 3 (synthesis) | 20s | 40s | Athena timeout = ABSTAIN |
| Boule Round 4 (vote) | 15s | 30s | Non-responding = ABSTAIN |
| Total deliberation | 3 min | 6 min | Abort with timeout trace |
| Areopagus gate check | 2s | 10s | Alert |
| Strategos order submission | 1s | 5s | Retry 3x |

## LLM Latency

Agent calls use Anthropic Claude API. Typical latency per agent call:
- Round 1 (opening, ~300 tokens output): ~1.5-2.5s
- Round 2 (challenge, ~200 tokens): ~1-2s
- Round 3 (synthesis by Athena, ~400 tokens): ~2-4s
- Round 4 (vote, ~100 tokens): ~0.5-1s

With 12 agents running in parallel in Round 1: total Round 1 latency = slowest agent ≈ 2-3s.

Rounds 2-4 are more sequential due to dependencies. Total deliberation P50: 3.5 min, P95: 5.5 min.

## Optimization Strategies

1. **Parallel Rounds 1 and early 2**: All agents start Round 1 simultaneously
2. **Streaming responses**: Agents use streaming API; results processed as they arrive
3. **Prompt caching**: Base system prompts are cached at the API level (reduces tokens billed + latency on repeated calls)
4. **Timeout-as-ABSTAIN**: Slow agents don't block the quorum if minimum quorum is met
5. **Early exit on veto**: Zeus/Solon veto in Round 1 = deliberation ends immediately

## Signal TTL vs. Deliberation Time

Signal TTL: 15 minutes
Deliberation hard limit: 6 minutes
Areopagus + execution: <1 minute
Remaining buffer: ~8 minutes for order fill

If deliberation exceeds 6 minutes, the signal is expired and a `ProofOfRestraint` is issued with reason `DELIBERATION_TIMEOUT`. A fresh signal must be generated before a new deliberation can start.

## Polymarket CLOB Latency

- Order submission API call: typically 200-500ms
- Order acknowledgment: 1-2s
- Fill notification (WebSocket): near real-time after match

Strategos tracks submission-to-fill latency and flags if > 60s (may indicate thin liquidity).

## Monitoring

Latency metrics exported to Argos monitoring:
- `boule.deliberation_duration_ms` (histogram)
- `boule.round_{n}_duration_ms` (per round)
- `boule.agent_{name}_latency_ms` (per agent)
- `strategos.order_submission_ms`
- `pipeline.total_signal_to_order_ms`

Alerts configured in Olympus:
- P95 deliberation > 5 min → page on-call
- Any stage hard limit breach → alert
- Signal TTL expired before execution → log + ProofOfRestraint
