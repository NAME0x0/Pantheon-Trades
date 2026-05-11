# Pantheon Constitution

The Constitution defines the immutable operating principles of Pantheon Trades. These rules are encoded in `PantheonConstitution.sol` and cannot be changed after deployment.

## Article I — Deliberation Before Capital

No capital may be deployed without a completed Boule deliberation. Direct execution without council approval is forbidden.

*Enforced by*: Areopagus (requires valid `ApprovalToken`); `DecisionCourt.sol` on-chain.

## Article II — Veto is Absolute

A Zeus constitutional veto or Solon compliance veto is final and cannot be overridden by any other mechanism. No appeal process exists for vetoed theses.

*Enforced by*: Boule orchestrator; `PantheonConstitution.sol` records all vetoes.

## Article III — Proof of Restraint

Every signal that reaches band S or A but does not result in a trade must produce a `ProofOfRestraint`. Restraint is a first-class outcome, not an absence of action.

*Enforced by*: Areopagus on every rejection; `ProofOfRestraint.sol` on-chain.

## Article IV — Immutable Archive

Every Thesis, Signal, Trade, and Trace must be archived permanently. No deletion of historical records is permitted. Archival is the Parthenon's sole responsibility.

*Enforced by*: Parthenon service; IPFS + Irys permanent storage; Merkle roots anchored on-chain.

## Article V — Lifecycle Law

Every strategy must pass through Moirai lifecycle checkpoints: creation (Clotho), assignment (Lachesis), termination (Atropos). No strategy bypasses lifecycle. No strategy runs indefinitely without a scheduled termination review.

*Enforced by*: Moirai service; `StrategyLifecycle.sol` on-chain.

## Article VI — Human Oversight

The Humans agent participates in every deliberation. Any Humans flag creates a queue item for human review. The system will not suppress or ignore human flags.

*Enforced by*: Boule orchestrator; human review queue in web UI.

## Article VII — Agent Accountability

Every council agent carries a public passport (ERC-8004). Their votes, calibration scores, and veto history are permanently on-chain and publicly readable. No anonymous voting.

*Enforced by*: Ostrakon scoring; Parthenon archival; `AgentPassport.sol` on-chain.

## Article VIII — No Insider Edge

The system may not trade on material non-public information. All data sources must be publicly accessible and documented in `docs/PYTHIA.md`. Novel proprietary data sources require ZeusMultisig approval before activation.

*Enforced by*: Pythia source registry; ZeusMultisig approval gate.

## Article IX — Counterfactual Honesty

For every no-trade decision on an S/A signal, Elysium must compute and archive the counterfactual outcome after resolution. The system must not be able to selectively suppress unflattering counterfactuals.

*Enforced by*: Elysium runs automatically post-resolution; `CounterfactualOracle.sol` on-chain.

## Article X — Emergency Pause

The ZeusMultisig may pause the entire system at any time. During a pause, no new trades may be entered. Open positions continue to be managed. Resume requires explicit multisig action.

*Enforced by*: `EmergencyPause.sol`; Olympus state machine.

## Immutability

`PantheonConstitution.sol` is deployed as a non-upgradeable contract. Its address is hardcoded into Areopagus, Boule, and Moirai service configurations. The contract stores the keccak256 hash of this document; any modification to this file is recorded as a hash mismatch by the on-chain verifier.

See `docs/ZEUS_MULTISIG.md` for what governance can and cannot change.
