# Smart-Contract Formal Verification — Halmos

[Halmos](https://github.com/a16z/halmos) is a16z's MIT-licensed symbolic
testing tool for Ethereum smart contracts. It runs your Foundry test
suite under an SMT solver: any function named `check_*` is executed
symbolically, with every input treated as an unknown the solver tries
to make fail. A passing run is a proof; a failing run hands you a
concrete counter-example to the assertion.

## Why Halmos

- **Same language as our test suite.** Halmos consumes Solidity Foundry
  tests — no separate spec language to learn.
- **MIT licensed, open source.** No vendor lock-in vs Certora.
- **Fast enough for CI.** The mid-sized contracts in this repo
  symbolically verify in seconds.

## What we verify

| Contract | Spec file | Invariants |
|----------|-----------|------------|
| `ProofOfRestraint` | `test/ProofOfRestraintSymbolic.t.sol` | proofId strictly monotonic; record integrity; role-gated writes; empty-input revert |
| `PantheonConstitution` | `test/PantheonConstitutionSymbolic.t.sol` | soft <= hard caps; non-degenerate windows; Kelly fraction exactly 50% ; size-bound monotonicity; portfolio room |

These are the immutable / append-only contracts where a bug after
deploy is unfixable.

## Running locally

```bash
# Via just (preferred — picks up the install-on-demand path):
just halmos

# Direct:
cd contracts && uvx halmos --solver-timeout-assertion 30000
```

Halmos auto-discovers every function in the `test/*Symbolic.t.sol`
files whose name starts with `check_`. The default solver-timeout
should be enough for everything we ship; bump it if a future check
runs into a more complex constraint.

## Writing a new symbolic check

1. Name the file `<Contract>Symbolic.t.sol` and the function
   `check_<invariant>(...)`.
2. Use `vm.assume(...)` to filter inputs that are out of scope (e.g.
   the empty-string case the contract refuses anyway). Skip
   `vm.assume` entirely for assertions you want Halmos to drive
   negative through.
3. Use plain `assert(...)` — Halmos picks it up.
4. Avoid concrete numeric guards; let Halmos pick everything. If you
   constrain too much you're proving a tautology.

## CI

Halmos runs in CI on every PR that touches `contracts/`. A failing
symbolic check blocks merge until either the contract is fixed or
the assertion is provably too strict (rare; usually a real bug).

## Troubleshooting

- "solver timeout" -> add `--solver-timeout-assertion` flag or split
  the invariant into smaller checks.
- "halmos: unsupported opcode" -> check the contract is not using
  features the symbolic backend cannot model (rare in our code).
- "counter-example" -> Halmos prints the concrete input that broke
  the assertion. Treat it like any other failing test.
