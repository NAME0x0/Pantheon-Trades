# Pantheon Trades — task runner (https://github.com/casey/just).
#
# `just` is preferred over Make for cross-platform compatibility.
# Common workflows: install, test, lint, audit, mutation tests,
# chaos drills, formal-verification, deploy.

# Default target prints the list.
default:
    @just --list

# ─── Install / setup ──────────────────────────────────────────────────

# Install all JS + Python deps.
install:
    pnpm install
    uv sync --all-packages

# ─── Test ─────────────────────────────────────────────────────────────

test:
    pnpm test
    cd contracts && forge test

# Run a single service's pytest suite.
test-service service:
    cd services/{{service}} && uv run pytest -q

# ─── Lint / format ────────────────────────────────────────────────────

lint:
    uvx ruff check .
    pnpm lint
    cd contracts && forge fmt --check

fmt:
    uvx ruff check --fix .
    uvx ruff format .

# ─── Mutation testing (mutmut) ────────────────────────────────────────

# Run mutation tests on the high-impact financial modules. Mutmut
# generates one mutant per source-line change, runs the test suite,
# and reports which mutants survived (= tests that don't actually
# test). See infra/quality/MUTATION_TESTING.md for the full workflow.
mutmut:
    uv run --with mutmut mutmut run --paths-to-mutate=services/areopagus/src/areopagus/kelly.py,services/areopagus/src/areopagus/drawdown.py,services/areopagus/src/areopagus/correlation_sizing.py,services/strategos/src/strategos/slippage.py,services/strategos/src/strategos/execution_mode.py,services/strategos/src/strategos/slippage_learner.py --runner="uv run pytest -x services/areopagus/tests services/strategos/tests" --tests-dir=services/areopagus/tests --backup=False

# Show survivors after a mutmut run.
mutmut-results:
    uv run --with mutmut mutmut results

# Inspect a single surviving mutant.
mutmut-show id:
    uv run --with mutmut mutmut show {{id}}

# ─── Chaos drills (toxiproxy) ─────────────────────────────────────────

# Start the chaos sidecar + apply default fault scenarios. The
# scenarios are defined in infra/chaos/scenarios.yaml and consumed
# by the runner script.
chaos-up:
    docker compose --profile chaos up -d toxiproxy
    bash infra/chaos/apply-scenarios.sh

chaos-down:
    bash infra/chaos/clear-scenarios.sh
    docker compose --profile chaos down

# ─── Formal verification (Halmos) ─────────────────────────────────────

# Symbolic checks for Solidity invariants. Run halmos against the
# contracts/test/*Symbolic.t.sol suite — Halmos picks up tests named
# check_<invariant>(...) automatically.
halmos:
    cd contracts && uvx halmos --solver-timeout-assertion 30000

# ─── Migrations / backups ─────────────────────────────────────────────

migrate:
    cd apps/api && uv run alembic upgrade head

migrate-revision msg:
    cd apps/api && uv run alembic revision --autogenerate -m "{{msg}}"

backup-once:
    docker compose exec backup /usr/local/bin/backup.sh

# ─── Compose lifecycle ────────────────────────────────────────────────

up:
    docker compose up -d

down:
    docker compose down

logs service:
    docker compose logs -f {{service}}
