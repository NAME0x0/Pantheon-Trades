# Chaos drills — Toxiproxy

[Toxiproxy](https://github.com/Shopify/toxiproxy) is Shopify's MIT-licensed
TCP proxy designed for resilience testing. It sits between services and
their dependencies (Redis, Postgres, RPC) and lets us inject latency,
packet loss, timeouts, and bandwidth caps via a simple HTTP admin API.

## Why Toxiproxy

- **Open source, MIT.** Single static binary, single Docker image.
- **L4-level**, so it works for anything that speaks TCP — no need
  for service-specific shims.
- **Reversible.** Toxics can be removed without restarting any
  service. A drill that goes wrong is a 1-command rollback.
- **Scriptable.** Scenarios live in YAML, applied via a shell script.
  No GUI, no manual fiddling.

## Layout

```
infra/chaos/
  scenarios.yaml          declarative scenarios
  apply-scenarios.sh      apply one scenario by name
  clear-scenarios.sh      strip every toxic, leave proxies in place
  README.md               this file
```

## Running a drill

The chaos stack is gated behind a compose profile so it does not run
in normal `docker compose up`:

```
just chaos-up                          # start toxiproxy + apply baseline
just chaos-up redis_high_latency       # specific scenario
just chaos-down                        # tear down
```

Or directly:

```
docker compose --profile chaos up -d toxiproxy
bash infra/chaos/apply-scenarios.sh redis_high_latency
# ... observe via Grafana / logs ...
bash infra/chaos/clear-scenarios.sh
```

## Available scenarios

| Name                  | What it does                                    |
| --------------------- | ----------------------------------------------- |
| `baseline`            | Proxies up, no toxics. Sanity check.            |
| `redis_high_latency`  | 500ms +/- 100ms Redis latency                   |
| `redis_packet_loss`   | Caps each Redis connection at 10KB              |
| `postgres_slow`       | 300ms Postgres latency                          |
| `rpc_flaky`           | 30% RPC calls time out at 5s                    |
| `catastrophe`         | All three degraded simultaneously               |

## Pointing services at the proxy

In `docker-compose.yml`, services that should use the chaos path should
read their dependency URLs from chaos-specific env vars when the
`chaos` profile is active:

```yaml
environment:
  REDIS_URL: ${REDIS_URL:-redis://redis:6379/0}     # default = direct
# When CHAOS=1: REDIS_URL=redis://toxiproxy:16379/0
```

A toggle script can swap the URLs for a drill. Out of scope for this
commit — handled per-service as drills are scoped.

## Sample drill checklist

1. `just chaos-up redis_high_latency`
2. Trigger a deliberation through the API.
3. Verify Boule still produces a thesis within the SLA, just slower.
4. Verify Argos still publishes exit signals.
5. Verify Areopagus does not bypass gates under stress.
6. `just chaos-down`

Document anything that broke in a short post-mortem under
`docs/CHAOS_DRILLS/<date>.md` so the next drill builds on the last.
