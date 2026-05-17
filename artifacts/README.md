# Artifacts

Captured live-test outputs from `scripts/live_test_gemini.py`. Each
file is a JSON snapshot of one deliberation run against the Gemini
API, with per-call timing, token counts, and an estimated USD cost.

## Schema

```
{
  "schema": "pantheon-live-test-v1",
  "model":         "gemini-flash-lite-latest",
  "started_at":    "2026-05-17T03:42:19.890159+00:00",
  "finished_at":   "2026-05-17T03:48:23.841087+00:00",
  "total_duration_ms": 363950,
  "spacing_seconds_between_calls": 8.0,
  "signal":  { ... thesis-bearing signal ... },
  "rounds":  [
    {
      "round": 1,
      "agents": [
        { agent, http_status, duration_ms, tokens_in, tokens_out,
          model_version, preview, finish_reason, retried_429 },
        ...
      ]
    },
    { "round": 4, ... }
  ],
  "tokens": { "in": 12345, "out": 4567 },
  "cost_usd_estimate":  0.00266,
  "pricing_assumed":    { input_per_mtok: 0.10, output_per_mtok: 0.40 },
  "failure_count":      0,
  "agent_count":        10
}
```

## Captured runs

### `live_test_20260517T034219Z.json` (canonical)
- model: `gemini-flash-lite-latest` (resolved to `gemini-3.1-flash-lite`)
- 10 agents × 2 rounds (opening + vote) = 20 calls
- failures: 0
- total duration: 363,950 ms (~6 min)
- spacing: 8.0 s between calls (free-tier compliant)
- tokens: 12,000+ in / 4,500+ out
- estimated cost: **$0.00266**

This is the canonical successful baseline. Every agent (ares, athena,
hades, cassandra, zeus, solon, themis, hephaestus, humans, eris) emits
a round-1 opening and a round-4 vote with all required fields.

### `live_test_20260517T020122Z.json` (partial)
- model: `gemini-2.5-flash-lite`
- 20 calls, 16 OK, 4 RPM-throttled (HTTP 429)
- demonstrates the retry-on-429 path with `Please retry in Xs` parsing

Kept as the canonical *throttled-tier* artifact — useful for showing
what a deliberation looks like on the free-tier rate ceiling.

## Reproducing

```bash
# 10 agents × 2 rounds, ~6 minutes on free tier
uv run --project services/boule --with httpx python scripts/live_test_gemini.py

# Slimmer roster + tighter spacing on a paid tier
LIVE_TEST_ROSTER="ares,athena,zeus,solon,eris" \
LIVE_TEST_SPACING_S=2 \
BOULE_GEMINI_MODEL=gemini-2.5-flash-lite \
uv run --project services/boule --with httpx python scripts/live_test_gemini.py
```

`gemini-flash-lite-latest` resolves to whichever flash-lite SKU Google
currently calls "latest" (Gemini 3.1 flash-lite as of 2026-05). Pin
explicitly with `BOULE_GEMINI_MODEL=gemini-2.5-flash-lite` for
deterministic comparison runs.
