# Mutation Testing — `mutmut`

## Why

Code coverage tells us which lines tests *touch*. Mutation testing tells
us which lines tests *actually check*. mutmut (MIT, https://github.com/boxed/mutmut)
mutates one operator / constant / branch at a time and re-runs the
suite; a mutant the suite still passes against means the suite did not
actually test the affected behaviour.

We target the modules where a silent bug would directly cost money:

| Module                                                  | Why                            |
| ------------------------------------------------------- | ------------------------------ |
| `services/areopagus/src/areopagus/kelly.py`             | Position sizing math           |
| `services/areopagus/src/areopagus/drawdown.py`          | DD haircut multiplier          |
| `services/areopagus/src/areopagus/correlation_sizing.py`| Correlation-aware downsizing   |
| `services/strategos/src/strategos/slippage.py`          | Slippage curve                 |
| `services/strategos/src/strategos/execution_mode.py`    | Maker/taker chooser            |
| `services/strategos/src/strategos/slippage_learner.py`  | EWMA learner                   |

## Workflow

```bash
# Full run — slow. Each mutation re-runs the affected pytest suite.
# Expect 5-15 minutes on a laptop.
just mutmut

# Show survivors (mutants the test suite did NOT kill).
just mutmut-results

# Inspect a specific surviving mutant.
just mutmut-show 42
```

A surviving mutant is one of:

1. **A genuine test gap.** Add a test that distinguishes the original
   behaviour from the mutated behaviour. Re-run mutmut until killed.
2. **An equivalent mutation.** Some mutations produce semantically
   identical code (`>` becomes `>=` when the boundary is never hit).
   Mark via `# pragma: no mutate` on the line, with a one-line
   justification in the commit message.
3. **A dead-code mutation.** The mutated line is unreachable. Delete
   the line — dead code never needed a test in the first place.

## Goals

- **Mutation score ≥ 90%** on the modules above.
- Every new survivor is either killed or annotated within the same PR.
- CI does *not* run mutmut on every push (too slow). It runs nightly
  on `main` and fails the build if the survivor count climbs.

## Anti-patterns

- Do not mutmut configuration / schema / Pydantic-model modules.
  Mutating a literal default in a config object will survive because
  no test depends on the default, and that's not actually a gap.
- Do not chase a 100% mutation score on every module. The above list
  was chosen deliberately; expansion needs a discussion of why.
