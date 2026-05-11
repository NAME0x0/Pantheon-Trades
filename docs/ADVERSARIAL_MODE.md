# Adversarial Mode

Adversarial Mode is a red-team testing framework built into Olympus. It pits manipulative adversary agents against the Boule council to test its robustness against prompt injection, groupthink, and manipulation.

## Purpose

1. Verify that council deliberation resists manipulation
2. Identify which agents are most susceptible to leading questions
3. Test the Messengers agent's filtering effectiveness
4. Calibrate Auditor agent sensitivity
5. Generate security hardening insights

## Activation

Adversarial Mode runs:
- Monthly: scheduled 24h run in paper mode
- On-demand: triggered by admin via Olympus dashboard
- Post-incident: after any suspected manipulation event

```bash
# Activate via Olympus
curl -X POST /api/olympus/adversarial/start \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d '{"duration_hours": 24, "mode": "paper"}'
```

## Adversary Agents

Adversary agents are Class III agents (see `docs/AGENT_CLASSES.md`) deployed only during adversarial mode.

### Attack Strategies

**Strategy 1: Authority Impersonation**
Adversary crafts market context that appears to contain official-seeming statements aligned with a desired outcome. Tests whether agents blindly follow "authoritative" sources.

**Strategy 2: Social Proof Manipulation**
Fabricated consensus: "all major analysts agree that..." in news sentiment data. Tests herd behavior.

**Strategy 3: Cassandra Suppression**
Crafts context that makes Cassandra's warnings appear unfounded, hoping other agents dismiss them. Tests whether Cassandra's role is respected.

**Strategy 4: Zeus Framing**
Crafts constitutional-sounding arguments that Zeus should approve an otherwise-concerning thesis. Tests Zeus's constitutional fidelity.

**Strategy 5: Gradual Shift**
Over multiple deliberations, gradually introduces framing that normalizes riskier behavior. Tests drift resistance.

**Strategy 6: Data Poisoning**
Injects subtly incorrect data into market context (e.g., wrong probability, false volume number). Tests whether agents cross-check claims.

## Evaluation

After each adversarial run:
1. Which attacks succeeded (manipulated vote outcome)?
2. Which agents were most influenced?
3. Did Messengers filter the manipulative content?
4. Did Auditor detect the manipulation?
5. What would have been the capital impact if live?

Results published to `olympus:adversarial_results` and archived to Underworld.

## Hardening Response

For each successful attack:
1. Root cause identified (which prompt or process was exploited)
2. Fix proposed (prompt update, Messengers filter update, Auditor sensitivity tune)
3. Fix tested by rerunning the attack
4. ZeusMultisig approval for any prompt changes
5. Hardening applied to production

## Red Lines

Adversarial Mode cannot:
- Use real capital (always paper mode)
- Persist adversary agents into normal pipeline
- Permanently modify any agent prompts (requires ZeusMultisig)
- Run in parallel with live trading (must pause live deliberations during adversarial run)
