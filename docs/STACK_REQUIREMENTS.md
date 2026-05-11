# Stack Requirements

## Runtime Dependencies

### Infrastructure
- **Docker** 24+ and **Docker Compose** v2
- **Redis** 7.x
- **PostgreSQL** 15+
- **Node.js** 20+ (via `.nvmrc`)
- **Python** 3.12+ (managed by uv per service)

### Package Managers
- **pnpm** 9+ (JS monorepo)
- **uv** 0.4+ (Python services)
- **Foundry** (latest stable) for Solidity

### Blockchain
- **Foundry** (forge, cast, anvil) for contract development
- **Canteen Arc CLI** for Arc Testnet RPC
- Access to Arc Testnet (Chain ID: 5042002)

## API Keys Required

| Service | Env Var | Required for |
|---------|---------|-------------|
| Anthropic Claude | `ANTHROPIC_API_KEY` | Agent deliberations |
| Polymarket CLOB | `POLYMARKET_API_KEY` | Trading and data |
| Reddit | `REDDIT_CLIENT_ID`, `REDDIT_CLIENT_SECRET` | Sentiment |
| Bloomberg | `BLOOMBERG_API_KEY` | News (optional) |
| CoinDesk | `COINDESK_API_KEY` | News |
| Irys | `IRYS_KEY` | Permanent storage |
| Arc Testnet | `ARC_RPC_URL` | On-chain operations |

## Compute Requirements

### Development (laptop)
- RAM: 8GB minimum, 16GB recommended
- CPU: 4 cores recommended (parallel LLM calls)
- Disk: 10GB for IPFS cache and logs

### Production (VPS/server)
- RAM: 16GB minimum
- CPU: 8 cores (parallel deliberations)
- Disk: 50GB SSD (IPFS pinning, PostgreSQL)
- Network: low-latency connection to Polymarket CLOB (ideally same region)

### LLM API Budget

Deliberation cost estimate per thesis:
- ~12 agent calls × ~4 rounds × ~300 avg tokens = ~14,400 tokens per deliberation
- At claude-sonnet-4-6 pricing: ~$0.05-0.10 per deliberation
- 10 deliberations/day = ~$0.50-1.00/day in API costs
- 100 deliberations/day = ~$5-10/day

Caching: base system prompts cached with Anthropic prompt caching → reduces token cost by ~40% on repeated calls.

## Development Setup

```bash
# Prerequisites: pnpm, uv, Docker, Foundry, arc-canteen CLI

# 1. Clone and install
git clone <repo>
pnpm install

# 2. Copy env files
cp apps/api/.env.example apps/api/.env
cp apps/web/.env.example apps/web/.env
for dir in services/*/; do cp "$dir/.env.example" "$dir/.env" 2>/dev/null || true; done
cp contracts/.env.example contracts/.env

# 3. Fill in API keys in each .env file

# 4. Start infrastructure
docker compose up -d redis postgres

# 5. Start services
pnpm dev

# 6. Run Foundry tests
cd contracts && forge test
```

## Production Deployment

See `vercel.ts` for Vercel configuration for the web app.

Services are containerized via Docker. `docker-compose.yml` defines the full stack.

For production, deploy each Python service independently or use Kubernetes. Redis and PostgreSQL should be managed services (not containerized for production).
