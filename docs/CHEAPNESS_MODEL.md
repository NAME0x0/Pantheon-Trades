# Cheapness Model

How Pantheon Trades minimizes costs while maintaining quality.

## LLM API Cost

The dominant cost is Anthropic Claude API calls for council agent deliberations.

### Prompt Caching

System prompts for each agent are large (400-800 tokens). With Anthropic's prompt caching:
- First call: cache miss, full token price
- Subsequent calls within 5-min cache window: cache hit, ~90% cheaper

Implementation in `services/boule/`:
- Each agent's system prompt is sent with `cache_control: {"type": "ephemeral"}` on the first call
- Subsequent calls reuse the cached prompt
- Cache TTL: 5 minutes (server-side)
- During a deliberation (all rounds), the same prompt is used → most round 2-4 calls hit cache

**Expected savings**: ~40% reduction in total token cost per deliberation.

### Token Budget Per Agent

| Role | Round 1 | Round 2 | Round 3 | Round 4 | Total |
|------|---------|---------|---------|---------|-------|
| Zeus | 250 | 150 | — | 100 | 500 |
| Solon | 250 | 150 | — | 100 | 500 |
| Hades | 350 | 200 | — | 100 | 650 |
| Athena | 300 | 200 | 400 | 100 | 1000 |
| Others (×9) | 250 | 150 | — | 100 | 500 |

Total per deliberation: ~8,000 tokens (uncached). With caching: ~5,000 effective billable tokens.

At claude-sonnet-4-6 pricing: ~$0.04-0.06 per deliberation.

### Band Filtering

Only S and A bands trigger deliberation. B/C/D markets (~95% of scanned markets) are scored without LLM calls. This is the biggest cost control: most work is done by the cheap statistical scoring in Apollo.

### Short-Circuit on Veto

Zeus or Solon veto in Round 1 ends deliberation immediately — no Round 2, 3, or 4 costs incurred.

## IPFS / Irys Storage

IPFS pinning is essentially free for the volume of data generated. Irys uses a one-time endowment model — pay once for permanent storage. Estimated cost: < $0.01 per artifact.

## Arc Testnet Gas

Gas on Arc Testnet is paid in USDC. Current gas prices are very low (testnet). Estimated < $0.01 per on-chain call.

Batching reduces call frequency: thesis registrations are batched hourly, Merkle roots daily.

## Redis

In-memory cache and pub/sub. Minimal storage (signal data is small, TTL-bounded). Cloud Redis costs < $20/month for expected volume.

## PostgreSQL

Only long-term state stored. Each thesis JSON is ~5-10KB. 1,000 theses/month = ~10MB/month storage growth. Minimal cost.

## Polymarket CLOB

API is free. CLOB charges fees on filled trades (typically 1-2% of trade value). This is a trading cost, not an infrastructure cost.

## Cost Summary (estimated, 10 deliberations/day)

| Cost | Monthly |
|------|---------|
| Anthropic API | ~$20-30 |
| Redis | ~$20 |
| PostgreSQL | ~$15 |
| Irys/IPFS | ~$5 |
| Arc Testnet gas | ~$2 |
| Total infrastructure | ~$60-70/month |

Trading fees depend on trade volume and are separate from infrastructure costs.
