# Threat Model

## Assets

| Asset | Value | Location |
|-------|-------|----------|
| Trading capital (USDC) | High | Polymarket positions + wallet |
| Private keys | Critical | Env vars + ZeusMultisig hardware keys |
| API keys (Polymarket, Anthropic) | High | Env vars |
| Agent logic (prompts) | Medium | Git repo |
| Historical data and traces | Medium | IPFS + PostgreSQL |
| On-chain reputation | Medium | Arc Testnet contracts |

## Threat Categories

### T1: Account Compromise
**Threat**: Attacker gains access to operator wallet private key.

**Impact**: Unauthorized on-chain transactions, ZeusMultisig proposal spam.

**Mitigations**:
- Hot wallet holds minimal funds (gas only)
- ZeusMultisig requires 3/5 independent signers for treasury ops
- Hardware keys for ZeusMultisig signers
- 72h timelock on all upgrades

### T2: API Key Theft
**Threat**: `POLYMARKET_API_KEY` or `ANTHROPIC_API_KEY` leaked.

**Impact**: Unauthorized trading (Polymarket), billing abuse (Anthropic).

**Mitigations**:
- Keys stored only in env vars, never in code
- Pre-commit secret scanning
- Key rotation on any suspected exposure
- Polymarket key scoped to specific account only

### T3: Prompt Injection via Market Data
**Threat**: Attacker crafts a Polymarket market question or news article designed to manipulate LLM agent reasoning.

**Impact**: Agents make irrational votes, bypassing normal deliberation logic.

**Mitigations**:
- Messengers agent strips unusual unicode, HTML, and injection-pattern strings from market context before distribution
- Auditor agent role specifically checks for "suspiciously manipulated reasoning"
- Vote anomaly detection in Boule: if all agents suddenly change to unanimous extreme position, flag for human review
- Ostrakon detects calibration anomalies that may indicate manipulation

### T4: Inference Attack on Agent Prompts
**Threat**: Attacker reverse-engineers agent prompts by analyzing public traces.

**Impact**: Understanding how to craft market conditions that trigger desired agent behavior.

**Mitigations**:
- Traces are public by design — this is a considered tradeoff (transparency > secrecy)
- System correctness does not depend on prompt secrecy
- Prompt hashes are on-chain; any prompt modification is detectable
- Adversarial mode regularly tests whether manipulated inputs can game the council

### T5: Oracle Manipulation
**Threat**: Attacker feeds Pythia manipulated data (e.g., fake news articles, spoofed API responses).

**Impact**: False signals generated, triggering erroneous trades.

**Mitigations**:
- Multi-source validation: signals require agreement across 2+ independent sources
- Source trust scoring degrades sources behaving anomalously
- Staleness sentinels detect sudden data discontinuities
- Correlation feature in Apollo detects abnormal price movements

### T6: Smart Contract Exploits
**Threat**: Vulnerabilities in on-chain contracts exploited.

**Impact**: Loss of on-chain records, reputation manipulation, governance attacks.

**Mitigations**:
- Foundry test suite with 100% coverage target for critical paths
- No funds held in contracts (USDC stays in Polymarket positions, not Pantheon contracts)
- `PantheonConstitution.sol` non-upgradeable
- All upgradeable contracts behind ZeusMultisig + timelock
- `EmergencyPause.sol` can halt all contract interactions

### T7: Denial of Service on Deliberation
**Threat**: Flood signal queue to overwhelm Boule or exhaust Anthropic API quota.

**Impact**: System unable to deliberate; legitimate signals expire.

**Mitigations**:
- Signal TTL prevents indefinite queue buildup
- Rate limiting on signal ingestion (Apollo cannot generate more than N signals/hour)
- Anthropic API has rate limits; Boule has circuit breaker on API errors
- Band filters: only S/A signals trigger deliberation

### T8: Insider Threat
**Threat**: Operator with admin access makes unauthorized changes.

**Impact**: Risk policy modified, agent exiled incorrectly, treasury drained.

**Mitigations**:
- ZeusMultisig: no single admin can approve governance changes
- All admin actions logged and immutably archived
- Risk policy changes require 72h timelock (gives time to detect)
- Human review queue requires 2nd eyes on sensitive decisions

### T9: MEV / Front-Running
**Threat**: MEV bots observe on-chain thesis registration and front-run the Polymarket position.

**Impact**: Worse fill prices.

**Mitigations**:
- On-chain thesis registration happens *after* order submission (not before)
- Limit orders with slippage budget absorb moderate front-running
- MEV analysis documented in `docs/MEV_NOTES.md`

## Residual Risks

1. LLM model behavioral changes (Anthropic updates Claude) could alter agent behavior
2. Polymarket platform risk (counterparty risk on USDC positions)
3. Arc Testnet availability (oracle/settlement risk)
4. Regulatory risk (prediction market legality varies by jurisdiction)
