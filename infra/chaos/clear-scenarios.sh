#!/usr/bin/env sh
# Remove every toxic from every Toxiproxy proxy. Proxies themselves
# are left in place so the next scenario does not have to re-create
# them.

set -eu
HOST="${TOXIPROXY_HOST:-localhost}"
PORT="${TOXIPROXY_PORT:-8474}"

curl -fsS "http://${HOST}:${PORT}/proxies" | jq -r 'keys[]' | while read -r name; do
    toxics=$(curl -fsS "http://${HOST}:${PORT}/proxies/${name}/toxics" | jq -r '.[].name' || true)
    for t in ${toxics}; do
        echo "  - removing toxic ${name}/${t}"
        curl -fsS -X DELETE "http://${HOST}:${PORT}/proxies/${name}/toxics/${t}" >/dev/null
    done
done
echo "All toxics cleared."
