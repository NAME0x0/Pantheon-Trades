# ERC-8004 Integration

ERC-8004 is an on-chain standard for AI agent identity and reputation on EVM chains. Pantheon Trades uses ERC-8004 to give every agent a portable, publicly verifiable identity.

See `docs/ARC_INTEGRATION.md` for Arc Testnet setup.

## Contracts

Deployed on Arc Testnet (Chain ID: 5042002):

### IdentityRegistry (`contracts/src/erc8004/IdentityRegistry.sol`)
Maps agent IDs to identity metadata:
```solidity
function registerAgent(bytes32 agentId, string calldata name, string calldata metadataURI) external
function getAgent(bytes32 agentId) external view returns (AgentIdentity memory)
function isActive(bytes32 agentId) external view returns (bool)
```

### ReputationRegistry (`contracts/src/erc8004/ReputationRegistry.sol`)
Accumulates immutable reputation events:
```solidity
function recordReputation(
    bytes32 agentId,
    bytes32 thesisId,
    int256 brierDelta,
    int256 sharpeDelta
) external

function getReputation(bytes32 agentId) external view returns (ReputationSummary memory)
```

### ValidationRegistry (`contracts/src/erc8004/ValidationRegistry.sol`)
Records audits and certifications:
```solidity
function recordValidation(
    bytes32 agentId,
    bytes32 validationType,  // "calibration_audit" | "hallucination_check" | "adversarial_test"
    bool passed,
    bytes32 evidenceHash
) external
```

### IERC8004 (`contracts/src/erc8004/IERC8004.sol`)
Standard interface unifying the three registries.

## Python Client

`services/parthenon/src/parthenon/erc8004_client.py`:

```python
class ERC8004Client:
    async def register_agent(self, agent_id: str, name: str, metadata_uri: str) -> TxHash
    async def update_reputation(self, agent_id: str, thesis_id: str, 
                                brier_delta: float, sharpe_delta: float) -> TxHash
    async def record_validation(self, agent_id: str, validation_type: str, 
                                passed: bool, evidence_hash: str) -> TxHash
    async def get_agent(self, agent_id: str) -> AgentIdentity
    async def get_reputation(self, agent_id: str) -> ReputationSummary
```

Uses Canteen Arc RPC (`ARC_RPC_URL` env var). Gas paid in USDC via Paymaster.

## Agent Passport Flow

### On Agent Deployment
```python
# Called once during system initialization
agent_id = keccak256(f"{agent_name}:{deployment_timestamp}".encode())
metadata = {
    "name": agent_name,
    "description": agent_role_description,
    "system_prompt_hash": keccak256(system_prompt.encode()),
    "model": "claude-sonnet-4-6",
    "version": "1.0.0"
}
metadata_cid = await ipfs.add(json.dumps(metadata))
await erc8004.register_agent(agent_id, agent_name, f"ipfs://{metadata_cid}")
```

### After Each Market Resolution
```python
await erc8004.update_reputation(
    agent_id=agent.id,
    thesis_id=thesis.thesis_id,
    brier_delta=brier_score,
    sharpe_delta=sharpe_contribution
)
```

### After Validation Runs
```python
await erc8004.record_validation(
    agent_id=agent.id,
    validation_type="calibration_audit",
    passed=calibration_passed,
    evidence_hash=report_cid
)
```

## Public Auditability

Anyone can query an agent's full history:

```bash
# Via Arc RPC
arc-canteen rpc eth_call --to $REPUTATION_REGISTRY --data "getReputation(bytes32)(0xagentId)"

# Via block explorer
https://testnet.arcscan.app/address/$REPUTATION_REGISTRY
```

This makes every agent's track record publicly verifiable without needing access to Pantheon Trades.

## AgentPassport Wrapper

`AgentPassport.sol` (`contracts/src/AgentPassport.sol`) provides a unified view combining all three ERC-8004 registries with Pantheon-specific fields.
