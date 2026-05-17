#!/usr/bin/env sh
# Apply a chaos scenario to the running Toxiproxy sidecar.
# Usage:
#   bash apply-scenarios.sh                  # interactive picker
#   bash apply-scenarios.sh redis_high_latency
#
# Reads infra/chaos/scenarios.yaml. Hits the Toxiproxy admin API at
# http://${TOXIPROXY_HOST:-localhost}:${TOXIPROXY_PORT:-8474}.

set -eu

HOST="${TOXIPROXY_HOST:-localhost}"
PORT="${TOXIPROXY_PORT:-8474}"
SCENARIOS="${SCENARIOS_PATH:-infra/chaos/scenarios.yaml}"

# Pull the list of scenario names. yq is preferred; awk fallback parses
# the simple "  - name: foo" pattern.
list_scenarios() {
    if command -v yq >/dev/null 2>&1; then
        yq -r '.scenarios[].name' "${SCENARIOS}"
    else
        awk '/^  - name:/ { sub(/^[[:space:]]*-[[:space:]]*name:[[:space:]]*/, ""); print }' "${SCENARIOS}"
    fi
}

if [ "$#" -lt 1 ]; then
    echo "Available scenarios:"
    list_scenarios | sed 's/^/  - /'
    echo
    echo "Usage: $0 <scenario_name>"
    exit 0
fi

SCENARIO="$1"
echo "Applying scenario: ${SCENARIO}"

if ! command -v yq >/dev/null 2>&1; then
    echo "yq not found; this script requires yq for non-baseline scenarios" >&2
    echo "install with: brew install yq, or https://github.com/mikefarah/yq" >&2
    exit 1
fi

# Walk the proxies + toxics for the chosen scenario. Two stages:
#  1. POST /proxies for each proxy definition (idempotent — 409 ok)
#  2. POST /proxies/<name>/toxics for each toxic
yq -o=json ".scenarios[] | select(.name == \"${SCENARIO}\")" "${SCENARIOS}" \
| jq -c '.proxies[]' | while read -r proxy; do
    name=$(echo "${proxy}" | jq -r '.name')
    body=$(echo "${proxy}" | jq -c '{name, listen, upstream, enabled: true}')
    echo "  + proxy ${name}"
    curl -fsS -X POST "http://${HOST}:${PORT}/proxies" \
         -H 'Content-Type: application/json' -d "${body}" >/dev/null \
        || echo "    (already exists; updating)"
    # Apply toxics (if any).
    echo "${proxy}" | jq -c '.toxics // [] | .[]' | while read -r toxic; do
        tname=$(echo "${toxic}" | jq -r '.name')
        echo "    - toxic ${tname}"
        curl -fsS -X POST "http://${HOST}:${PORT}/proxies/${name}/toxics" \
             -H 'Content-Type: application/json' -d "${toxic}" >/dev/null
    done
done

echo "Scenario applied. Clear with infra/chaos/clear-scenarios.sh"
