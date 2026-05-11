# Agent Passports — ERC-8004

Every council agent and service agent has an on-chain identity via ERC-8004. Agent passports are the portable, verifiable credential system for AI agents in Pantheon Trades.

## What is ERC-8004?

ERC-8004 is a standard for AI agent identity on EVM chains. It defines:
- `IdentityRegistry` — maps agent IDs to identity metadata
- `ReputationRegistry` — accumulates scoring records per agent
- `ValidationRegistry` — records audits and certifications of agent behavior

Contracts are deployed on Arc Testnet. See `docs/ARC_INTEGRATION.md`.

## Agent Passport Fields

```solidity
struct AgentPassport {
    bytes32 agentId;        // keccak256(agent_name + deployment_timestamp)
    string name;            // Human-readable name (e.g., "zeus", "hades")
    string agentClass;      // "council" | "service" | "auditor"
    string version;         // Semver
    address operator;       // Address that controls this passport
    uint256 createdAt;
    uint256 updatedAt;
    bool active;            // false if exiled
    string metadataURI;     // IPFS URI to full passport JSON
}
```

## Passport Metadata (IPFS)

```json
{
  "agentId": "0xabc...",
  "name": "hades",
  "description": "Risk Sovereign — worst-case and downside analysis",
  "role": "council",
  "domain": ["risk", "downside", "black_swans"],
  "veto_power": false,
  "vote_weight_base": 2.0,
  "system_prompt_hash": "0xdef...",
  "model": "claude-sonnet-4-6",
  "deployment_date": "2024-01-01",
  "reputation": {
    "brier_score_30d": 0.18,
    "sharpe_30d": 1.24,
    "total_deliberations": 847,
    "approval_rate": 0.62,
    "veto_rate": null
  }
}
```

## Reputation Registry

`ReputationRegistry.sol` accumulates immutable scoring events:

```solidity
event ReputationUpdated(
    bytes32 indexed agentId,
    bytes32 thesisId,
    int256 brierDelta,   // scaled 1e4
    int256 sharpeDelta,  // scaled 1e4
    uint256 timestamp
);
```

Every market resolution triggers a `ReputationUpdated` event for all participating agents. These events are public and can be independently audited.

## Passport Operations

Managed by `services/parthenon/src/parthenon/passport.py` and `erc8004_client.py`:

```python
# Create passport on agent deployment
await passport.create(agent_name, agent_class, version, operator_address)

# Update reputation after resolution
await passport.update_reputation(agent_id, brier_delta, sharpe_delta, thesis_id)

# Exile an agent
await passport.exile(agent_id, reason)

# Read passport
passport_data = await passport.get(agent_id)
```

## Validation

`ValidationRegistry.sol` records when the system has audited an agent's behavior:
- Calibration audit passed/failed
- Hallucination check results
- Adversarial mode stress test results

Validation records are created by Ostrakon and Underworld.

## Public Verifiability

Anyone can:
1. Read any agent's passport from Arc Testnet `IdentityRegistry`
2. Query the full reputation history from `ReputationRegistry` events
3. Download the metadata JSON from IPFS
4. Verify the system prompt hash matches the deployed prompt file

This makes agent behavior publicly auditable without needing access to the Pantheon Trades system.

## Agent Classes

See `docs/AGENT_CLASSES.md` for the full taxonomy.
