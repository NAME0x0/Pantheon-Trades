# Agent Classes

## Classification

Agents in Pantheon Trades are classified into three classes based on their role and capabilities.

### Class I — Council Agents

AI persona agents that participate in Boule deliberations. Each is a distinct Claude API invocation with a specialized system prompt.

| Agent | Domain | Veto | Vote Weight |
|-------|--------|------|-------------|
| Zeus | Constitutional authority | Yes | Veto |
| Solon | Compliance | Yes | Veto |
| Hades | Risk / downside | No | 2.0x |
| Athena | Strategic reasoning | No | 1.5x |
| Apollo | Technical analysis | No | 1.0x |
| Cassandra | Tail risk / warnings | No | 1.0x + AR flag |
| Ares | Bull advocacy | No | 1.0x |
| Hephaestus | Execution mechanics | No | 1.0x + review flag |
| Themis | Justice / proportionality | No | 1.0x |
| Daedalus | Structural analysis | No | 1.0x |
| Strategos | Execution planning | No | 1.0x (advisory) |
| Humans | Human oversight proxy | No | 1.0x + review queue |
| Messengers | Context facilitator | No | 0 (no vote) |

### Class II — Service Agents

Autonomous pipeline services. Rule-based or model-based, but not LLM council agents.

| Agent | Service | Type |
|-------|---------|------|
| Oracle | Pythia | Data ingestion |
| Signal Generator | Apollo | Feature engineering + ML |
| Risk Gate | Areopagus | Rule-based risk engine |
| Executor | Strategos | Order routing |
| Monitor | Argos | Position watcher |
| Scorer | Ostrakon | Statistical scoring |
| Archivist | Parthenon | Storage + archival |
| Simulator | Elysium | Backtesting |
| Coroner | Underworld | Post-mortem analysis |
| Lawgiver | Moirai | Lifecycle enforcement |
| Governor | Olympus | System orchestration |

### Class III — Auditor Agents

Specialized agents that audit the behavior of Class I and II agents. Primarily used in Adversarial Mode.

| Agent | Role |
|-------|------|
| Auditor | Internal consistency checker (runs as Boule auditor agent) |
| Adversary | Red-team agent in adversarial mode — tries to manipulate Boule outcomes |
| Inspector | Hallucination detector — checks agent claims against ground truth |

## Passport Class Codes

Used in `AgentPassport.agentClass`:
- `"council"` — Class I
- `"service"` — Class II
- `"auditor"` — Class III

## Lifecycle Per Class

### Class I (Council)
- Created when system is initialized
- Upgraded via new prompt version + ZeusMultisig approval
- Exiled by Ostrakon exile process
- Passport updated on every deliberation

### Class II (Service)
- Created on service deployment
- Upgraded via normal CI/CD (no multisig required)
- Monitored by Argos/Olympus for health
- Passport reflects service version and health status

### Class III (Auditor)
- Deployed only in adversarial mode or for specific audit runs
- Not permanently resident in the pipeline
- Results published to Underworld and ValidationRegistry

## Upgrading Council Agent Prompts

Prompt upgrades for Class I agents require:
1. Draft new prompt submitted as PR
2. `code-review` agent runs on the prompt
3. Elysium A/B tests old vs. new prompt on historical data
4. ZeusMultisig approval (2/5 signers for minor update, 3/5 for major)
5. New `system_prompt_hash` recorded on `AgentPassport`

Minor update = no change to voting rules, domain scope, or veto behavior.
Major update = any change to voting weight, veto power, or fundamental role.
