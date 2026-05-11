## Summary

<!-- What does this PR do? 1-3 bullets. -->

-
-

## Type of Change

- [ ] Bug fix
- [ ] New feature
- [ ] Refactor
- [ ] Docs / comments only
- [ ] Infrastructure / CI
- [ ] On-chain contract change

## Affected Services

- [ ] Apollo
- [ ] Areopagus
- [ ] Argos
- [ ] Boule / agent prompts
- [ ] Contracts
- [ ] Elysium
- [ ] Moirai
- [ ] Olympus
- [ ] Ostrakon
- [ ] Parthenon
- [ ] Pythia
- [ ] Strategos
- [ ] Underworld
- [ ] apps/api
- [ ] apps/web

## Constitution / Policy Check

Does this PR require ZeusMultisig approval?

- [ ] No — no constitution, risk policy, or agent prompt changes
- [ ] Yes — `PantheonConstitution.sol` change
- [ ] Yes — risk policy change (limits, thresholds, Kelly fraction)
- [ ] Yes — major agent prompt change
- [ ] Yes — Moirai laws change

If yes, link the governance proposal: <!-- proposal link -->

## Test Plan

- [ ] Unit tests pass (`pnpm test` / `uv run pytest`)
- [ ] Integration tests pass
- [ ] Affected service(s) tested end-to-end in paper mode
- [ ] No regressions in Areopagus gates
- [ ] Contract changes: Foundry tests pass + gas snapshot updated

## Deployment Notes

<!-- Any migration steps, env var changes, contract deployments, or rollout order requirements. -->

None required.

## Related Issues

Closes #
